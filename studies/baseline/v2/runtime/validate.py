"""V2 wrapper for inherited validation plus protocol-specific invariants."""
import argparse
import json
import math
from pathlib import Path
from . import core_validation as core

ICLR = Path(__file__).resolve().parents[2]
V2 = ICLR / "v2"
key = core.key
read_ref = core.read_ref


def check_lock(lock, base=ICLR):
    blockers = core.check_lock(lock, base)
    if lock.get("protocol_id") != "iclr-2027-v2":
        blockers.append("Missing v2 protocol identity")
    for name in ["scorer_conformance", "ruler_source", "reference_tokenizer", "identifier_contract",
                 "input_materialization", "paired_coverage_thresholds", "implementation_inventory"]:
        if not isinstance(lock.get(name), dict):
            blockers.append(f"Missing locked {name}")
    reports = {}
    for name in ["v2_readiness", "scorer_conformance", "gpu_authorization_record"]:
        if isinstance(lock.get(name), dict):
            try:
                reports[name] = json.loads(read_ref(base, lock[name]))
            except (ValueError, OSError, KeyError) as error:
                blockers.append(f"Unreadable {name}: {error}")
    readiness = reports.get("v2_readiness", {})
    required_checks = {"native_context", "processor_counts", "render_coverage", "no_answer_leakage", "adapter_roundtrip", "paired_eligibility"}
    if readiness.get("passed") is not True or not all(readiness.get("checks", {}).get(k) is True for k in required_checks):
        blockers.append("V2 readiness report has not passed required measured checks")
    conformance = reports.get("scorer_conformance", {})
    if conformance.get("passed") is not True or conformance.get("scorer_sha256") != core.digest((V2 / "runtime/scoring.py").read_bytes()):
        blockers.append("Scorer conformance does not identify the passing current scorer")
    approval = reports.get("gpu_authorization_record", {})
    if (approval.get("authorized") is not True or approval.get("authorized_by") != "user"
            or not approval.get("authorization_reference")
            or type(approval.get("max_reader_calls")) is not int or approval["max_reader_calls"] <= 0
            or type(approval.get("max_gpu_seconds")) is not int or approval["max_gpu_seconds"] <= 0):
        blockers.append("Explicit user GPU approval and positive call/time ceilings are missing")
    return blockers


def validate_eligibility(nominal, eligible, excluded):
    all_keys, kept = {key(r) for r in nominal}, {key(r) for r in eligible}
    if len(all_keys) != len(nominal) or len(kept) != len(eligible):
        raise ValueError("Duplicate nominal/eligible keys")
    omitted = set()
    allowed = {"context_limit", "image_limit", "unattainable_budget", "render_coverage",
               "empty_envelope_exceeds_target", "missing_pair"}
    for row in excluded:
        k = key(row)
        if k in omitted or row.get("reason") not in allowed or row.get("determined_without_predictions") is not True:
            raise ValueError("Invalid or prediction-dependent exclusion")
        omitted.add(k)
    if kept & omitted or kept | omitted != all_keys:
        raise ValueError("Eligibility accounting does not partition nominal keys")


def validate_row_extras(row, expected, actual, complete, base):
    if row["benchmark_task"] != expected["benchmark_task"]:
        raise ValueError("Benchmark task changed")
    counts = row["counts"]
    target = counts["matched_target_input_tokens"]
    gap = None if target is None else target - counts["total_input_tokens"]
    if counts["unused_matched_budget"] != gap:
        raise ValueError("Incorrect unused matched budget")
    targets = {"retrieved_text_matched": "full_optical_c2",
               "retrieved_text_matched_selected": "retrieved_optical_8px"}
    if row["condition"] in targets:
        baseline = actual.get((row["item_id"], row["model_id"], targets[row["condition"]], row["replicate"]))
        if baseline is None and complete:
            raise ValueError("Missing matched-budget baseline")
        if baseline and target != baseline["counts"]["total_input_tokens"]:
            raise ValueError("Matched budget target is not baseline's measured total input")
        if not row["retrieval_metadata"]:
            raise ValueError("Missing retrieval materialization metadata")
        retrieval = json.loads(read_ref(base, row["retrieval_metadata"]))
        if row["condition"] == "retrieved_text_matched_selected":
            if retrieval.get("rule") != "longest_complete_ranked_prefix":
                raise ValueError("New matched arm is not a complete ranked prefix")
            candidates = retrieval["candidate_counts"]
            if [c["prefix_length"] for c in candidates] != list(range(len(candidates))):
                raise ValueError("Missing ranked-prefix count candidates")
            possible = [c["prefix_length"] for c in candidates if c["total_input_tokens"] <= target]
            if not possible or retrieval["prefix_length"] != max(possible):
                raise ValueError("Did not choose longest feasible ranked prefix")
            if retrieval["selected_turn_ids"] != row["selected_turn_ids"] or retrieval["evidence_sha256"] != row["memory"]["sha256"]:
                raise ValueError("Prefix evidence metadata mismatch")
    elif target is not None:
        raise ValueError("Unexpected matched target on unmatched condition")
    if row["task"] in {"controlled", "ruler"} and row["condition"] != "full_raw":
        raw = actual.get((row["item_id"], row["model_id"], "full_raw", row["replicate"]))
        if raw is None and complete:
            raise ValueError("Missing raw same-evidence reference")
        if raw and raw["memory"]["sha256"] != row["memory"]["sha256"]:
            raise ValueError("Optical evidence differs from raw canonical source")
    if counts["page_count"]:
        if not row["render_metadata"]:
            raise ValueError("Missing render metadata")
        metadata = json.loads(read_ref(base, row["render_metadata"]))
        if not metadata.get("processor_measured") or not metadata.get("coverage_verified"):
            raise ValueError("Render lacks processor measurement or coverage validation")
        if metadata["source_sha256"] != row["memory"]["sha256"]:
            raise ValueError("Render metadata refers to different memory")
        if len(metadata["pages"]) != counts["page_count"]:
            raise ValueError("Render metadata page count mismatch")
        for i, page in enumerate(metadata["pages"]):
            if page["image_sha256"] != row["images"][i]["sha256"]:
                raise ValueError("Render image hash mismatch")
            height = page.get("effective_glyph_height_px")
            if not isinstance(height, (int, float)) or not math.isfinite(height) or height <= 0:
                raise ValueError("Missing measured effective glyph height")
            for line in page["lines"]:
                left, top, right, bottom = line["bbox"]
                if not (0 <= left <= right <= page["width"] and 0 <= top <= bottom <= page["height"]):
                    raise ValueError("Clipped glyph geometry")
    elif row["render_metadata"] is not None:
        raise ValueError("Text row has optical render metadata")


def validate_manifest(manifest, base=ICLR, previous_path=None):
    previous = None
    if previous_path is not None:
        data = Path(previous_path).read_bytes()
        if core.digest(data) != manifest["previous_manifest_sha256"]:
            raise ValueError("Previous snapshot hash mismatch")
        previous = json.loads(data)
    if manifest["status"] != "planned":
        blockers = check_lock(json.loads(read_ref(base, manifest["execution_lock"])), base)
        if blockers:
            raise ValueError("; ".join(blockers))
    if previous:
        for name in ["plan_freeze", "source_manifest", "template_manifest", "reference_tokenizer",
                     "eligibility_manifest", "implementation_inventory"]:
            if manifest[name] != previous[name]:
                raise ValueError(f"Immutable v2 metadata changed: {name}")
    result = core.validate_manifest(manifest, base, previous)
    expected = json.loads(read_ref(base, manifest["expected_keys"]))
    eligibility = json.loads(read_ref(base, manifest["eligibility_manifest"]))
    nominal = json.loads(read_ref(base, eligibility["nominal_keys"]))
    validate_eligibility(nominal, expected, eligibility["excluded"])
    actual = {key(r): r for r in manifest["rows"]}
    expected_map = {key(r): r for r in expected}
    for row in manifest["rows"]:
        validate_row_extras(row, expected_map[key(row)], actual, manifest["status"] in core.COMPLETE, base)
    result["note"] = "V2 byte/schema/score/accounting validation; execution seal separately requires measured processor and adapter QA."
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    if args.lock:
        blockers = check_lock(json.loads(args.lock.read_text(encoding="utf-8")))
        print(json.dumps({"ready_for_inference": not blockers, "blockers": blockers}, indent=2))
        raise SystemExit(2 if blockers else 0)
    if not args.manifest:
        parser.error("--manifest or --lock required")
    print(json.dumps(validate_manifest(json.loads(args.manifest.read_text(encoding="utf-8")), previous_path=args.previous), indent=2))


if __name__ == "__main__":
    main()
