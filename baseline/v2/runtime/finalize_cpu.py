"""Hash the tested CPU checkpoint; do not seal execution or touch prior freezes."""
import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from .prepare import digest, ref, read, write, verify_inputs
from .stages import preflight

V2 = Path(__file__).resolve().parents[1]
ICLR = V2.parent
ROOT = ICLR.parent


def main():
    for name in ["SCORER_CONFORMANCE.json", "CPU_PREFLIGHT.json", "CPU_VERIFICATION.json", "IMPLEMENTATION_INVENTORY.json"]:
        if (V2 / name).exists():
            raise FileExistsError("Refusing to overwrite checkpoint " + name)
    junit = V2 / "test_runs/t05_results.xml"
    suites = ET.parse(junit).getroot().findall("testsuite")
    tests = sum(int(s.attrib["tests"]) for s in suites)
    failures = sum(int(s.attrib["failures"]) + int(s.attrib["errors"]) for s in suites)
    assert tests == 52 and failures == 0
    protected = read(ICLR / "audit/audit.json")["protected_inventory"]
    changed = [p for p, value in protected.items() if digest(ROOT / p) != value]
    assert not changed
    checked = verify_inputs()
    for entry in read(ICLR / "PREPARATION_MANIFEST.json")["files"]:
        assert digest(ICLR / entry["path"]) == entry["sha256"]
    for entry in read(V2 / "data_cpu_v2/manifest.json")["artifacts"]:
        assert digest(ICLR / entry["path"]) == entry["sha256"]
    notebook_count = 0
    for file in (V2 / "colab").glob("*.ipynb"):
        for cell in read(file)["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))
        notebook_count += 1
    write(V2 / "SCORER_CONFORMANCE.json", {
        "status": "verified", "passed": True,
        "scope": "Declared native metric functions and edge-case fixtures; not full upstream execution-wrapper parity",
        "scorer_sha256": digest(V2 / "runtime/scoring.py"),
        "test_report": ref(junit), "test_source": ref(V2 / "tests/test_scoring.py"),
        "locomo_oracle": ref(V2 / "vendor/locomo_metrics.py"),
        "ruler_oracle": "Independent Apache-2.0 primary-source expression preserved in test_scoring.py",
        "ruler_source_url": "https://raw.githubusercontent.com/NVIDIA/RULER/main/scripts/eval/synthetic/constants.py",
        "upstream_git_revisions_resolved": False})
    # This new lock is not part of either earlier freeze. Fill only the completed
    # local conformance field; all external/runtime/approval fields remain blocked.
    lock = read(V2 / "execution_lock.json")
    assert lock["sealed"] is False and lock["gpu_authorization_record"] is None
    lock["scorer_conformance"] = ref(V2 / "SCORER_CONFORMANCE.json")
    (V2 / "execution_lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    readiness = preflight()
    assert not readiness["ready_for_inference"]
    write(V2 / "CPU_PREFLIGHT.json", readiness)
    report = {"status": "verified", "scope": "CPU implementation and source integrity only",
              "tests_passed": tests, "test_report": ref(junit), "protected_files_checked": len(protected),
              "changed_protected_files": changed, "frozen_and_nested_memory_checks": checked,
              "notebook_code_parsed": notebook_count, "working_cpu_notebooks": 1,
              "blocked_stage_scaffolds": 6, "gpu_calls": 0, "new_histories_generated": 0,
              "execution_ready": False, "active_data_manifest": ref(V2 / "data_cpu_v2/manifest.json"),
              "artifact_status_overrides": [
                  {"path": "v2/data", "status": "development-only", "reason": "incomplete preparation stopped on inherited reference whitespace assertion"},
                  {"path": "v2/data_cpu_v1", "status": "development-only", "reason": "support diagnostic preceded unresolved annotation audit; use data_cpu_v2"}],
              "support_annotation_unresolved_cases": 2,
              "inherited_source_normalization_cases": 1}
    write(V2 / "CPU_VERIFICATION.json", report)
    files = []
    for folder in ["runtime", "tests", "vendor", "data_cpu_v2", "colab"]:
        files.extend(p for p in (V2 / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    files.extend(V2 / name for name in ["RUN_MANIFEST.schema.json", "execution_lock.json", "GENERATION_CONTRACT.json", "SNAPSHOT_REQUEST.json", "IMPLEMENTATION_STATE.md", "CPU_VERIFICATION.json", "CPU_PREFLIGHT.json", "SCORER_CONFORMANCE.json"])
    files.append(junit)
    write(V2 / "IMPLEMENTATION_INVENTORY.json", {"status": "verified",
        "scope": "Immutable tested CPU checkpoint; execution unsealed", "files": [ref(p) for p in sorted(files)]})
    print(json.dumps({"tests": tests, "protected_unchanged": len(protected), "input_checks": checked,
                      "files_in_inventory": len(files), "execution_ready": False, "gpu_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
