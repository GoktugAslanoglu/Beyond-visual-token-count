"""CPU preflight and explicit gates for not-yet-calibrated Colab stages."""
import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from .prepare import verify_inputs, digest, read
from .validate import check_lock

V2 = Path(__file__).resolve().parents[1]


def preflight():
    hashes = verify_inputs()
    versions = {}
    for name in ["nltk", "regex", "numpy", "jsonschema", "Pillow", "fonttools", "pytest", "torch", "transformers"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    lock_path = V2 / "execution_lock.json"
    blockers = check_lock(read(lock_path)) if lock_path.exists() else ["Missing v2 execution lock"]
    return {"status": "planned", "scope": "CPU environment inventory and readiness; no inference",
            "python": platform.python_version(), "platform": platform.platform(),
            "versions": versions, "frozen_input_hashes_checked": hashes,
            "ready_for_inference": not blockers, "blockers": blockers,
            "gpu_calls": 0, "network_calls": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["cpu-preflight", "processor-calibration", "smoke", "locomo", "ruler", "identifier", "validate"])
    args = parser.parse_args()
    report = preflight()
    print(json.dumps(report, indent=2))
    if args.stage == "cpu-preflight":
        return
    if report["blockers"]:
        raise SystemExit(2)
    raise SystemExit("Stage adapter has not been implemented/calibrated; no inference was dispatched.")


if __name__ == "__main__":
    main()
