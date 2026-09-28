"""CPU-only deterministic v2 schedules, source reuse, and support diagnostics."""
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path
from .retrieval import support_coverage, documents

ICLR = Path(__file__).resolve().parents[2]
ROOT = ICLR.parent
V2 = ICLR / "v2"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path):
    return {"path": path.relative_to(ICLR).as_posix(), "sha256": digest(path),
            "bytes": path.stat().st_size}


def write(path, value, lines=False):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        if lines:
            for row in value:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        else:
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.write("\n")


def verify_inputs():
    checked = 0
    for name, base in [("iclr/design_freeze.json", ICLR),
                       ("iclr/v2/PLAN_FREEZE.json", ROOT)]:
        for entry in read(ROOT / name)["files"]:
            p = base / entry["path"]
            if digest(p) != entry["sha256"]:
                raise ValueError(f"Frozen input changed: {p}")
            checked += 1
    for entry in read(ICLR / "data/external500/manifest.json")["artifacts"]:
        p = ICLR / entry["path"]
        if digest(p) != entry["sha256"] or p.stat().st_size != entry["bytes"]:
            raise ValueError(f"Prepared evidence changed: {p}")
        checked += 1
    selected_path = ICLR / "data/external500/selected_evidence.jsonl"
    for line in selected_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        entry = row["memory"]
        p = ICLR / entry["path"]
        if digest(p) != entry["sha256"] or p.stat().st_size != entry["bytes"] or row["evidence_sha256"] != entry["sha256"]:
            raise ValueError(f"Selected memory bytes changed: {p}")
        checked += 1
    return checked


def prepare():
    checks = verify_inputs()
    out = V2 / "data_cpu_v2"
    out.mkdir(exist_ok=False)
    plan = read(V2 / "plan.json")
    locomo = plan["packages"][0]
    original = ICLR / "data/external500"
    old_keys = read(original / "expected_keys.json")
    extra = [{**row, "condition": "retrieved_text_matched_selected"}
             for row in old_keys if row["condition"] == "retrieved_text_matched"]
    keys = old_keys + extra
    for row in keys:
        row["benchmark_task"] = "locomo_category_" + str(row["category"])
    assert len(keys) == locomo["expected_rows"] == 9000
    assert len({(r["item_id"], r["model_id"], r["condition"]) for r in keys}) == 9000
    write(out / "locomo_expected_keys.private.json", keys)
    selected = {r["item_id"]: r for r in map(json.loads,
                (original / "selected_evidence.jsonl").read_text(encoding="utf-8").splitlines())}
    questions = list(map(json.loads, (original / "questions.private.jsonl").read_text(encoding="utf-8").splitlines()))
    source = ROOT / "work/locomo_source/locomo10.json"
    expected_source = read(original / "manifest.json")["source_sha256"]
    if digest(source) != expected_source:
        raise ValueError("LoCoMo source mismatch")
    conversations = {c["sample_id"]: c for c in read(source)}
    turn_ids = {k: {d["turn_id"] for d in documents(v["conversation"])} for k, v in conversations.items()}
    public, support, normalization_bridge = [], [], []
    for q in questions:
        s = selected[q["item_id"]]
        gold = conversations[q["cluster_id"]]["qa"][q["source_qa_index"]]
        assert str(gold["question"]).strip() == q["question"] and str(gold["answer"]).strip() == q["reference"]
        if gold["question"] != q["question"] or str(gold["answer"]) != q["reference"]:
            normalization_bridge.append({"item_id": q["item_id"], "source_question": gold["question"], "source_reference": str(gold["answer"]), "prepared_question": q["question"], "prepared_reference": q["reference"], "rule": "inherited v1 str.strip; no new normalization"})
        public.append({k: q[k] for k in ["item_id", "cluster_id", "question"]} | {
            "selected_memory": s["memory"], "selected_turn_ids": s["selected_turn_ids"],
            "full_memory": ref(original / "full_memory" / (q["cluster_id"] + ".txt"))})
        support.append({"item_id": q["item_id"], "cluster_id": q["cluster_id"],
                        "category": q["category"], "annotated_support_ids": gold["evidence"],
                        **support_coverage(s["selected_turn_ids"], gold["evidence"], turn_ids[q["cluster_id"]])})
    write(out / "source_normalization_bridge.private.json", normalization_bridge)
    write(out / "locomo_inputs.jsonl", public, True)
    write(out / "locomo_support.private.jsonl", support, True)
    taskplan = plan["packages"][1]
    ruler = [{"item_id": f"ruler-{task}-{i:03d}", "task_id": task,
              "instance": i, "status": "planned", "generation_seed": plan["new_seeds"]["ruler_generation"],
              "reference": None, "source": None}
             for task in taskplan["tasks"] for i in range(taskplan["items_per_task"])]
    write(out / "ruler_schedule.jsonl", ruler, True)
    factors = plan["packages"][2]["factors"]
    controlled = [{"item_id": f"identifier-{i:03d}", "status": "planned",
                   "generation_seed": plan["new_seeds"]["identifier_generation"],
                   "factors": dict(zip(factors, values)), "reference": None, "source": None}
                  for i, values in enumerate(itertools.product(*factors.values()))]
    assert len(ruler) == 180 and len(controlled) == 96
    write(out / "identifier_schedule.jsonl", controlled, True)
    summaries = {}
    for cat in (1, 2, 4):
        rows = [r for r in support if r["category"] == cat]
        known = [r for r in rows if r["support_recall"] is not None]
        summaries[str(cat)] = {"n": len(rows), "resolved_annotation_cases": len(known), "unresolved_annotation_cases": len(rows) - len(known),
            "mean_support_recall": sum(r["support_recall"] for r in known) / len(known) if known else None,
            "all_support_fraction": sum(r["all_annotated_support"] for r in known) / len(known) if known else None}
    write(out / "support_summary.json", {"status": "verified",
          "scope": "CPU annotation coverage for frozen BM25 only; no reader performance",
          "by_category": summaries, "conversation_clusters": len({r["cluster_id"] for r in support})})
    write(out / "manifest.json", {"status": "planned", "protocol_id": plan["protocol_id"],
          "inference_ready": False, "source_manifest": ref(original / "manifest.json"),
          "plan": ref(V2 / "plan.json"), "verified_input_hashes": checks,
          "locomo_expected_rows": len(keys), "ruler_planned_items": len(ruler),
          "identifier_planned_items": len(controlled), "new_histories_generated": 0,
          "artifacts": [ref(p) for p in sorted(out.iterdir()) if p.is_file()]})
    print(json.dumps({"locomo_keys": len(keys), "ruler_schedule": len(ruler),
                      "identifier_schedule": len(controlled), "support": summaries,
                      "new_histories_generated": 0}, indent=2))


if __name__ == "__main__":
    prepare()
