"""Exclusive raw-attempt archive. No inference, scoring, networking or repair."""
import hashlib
import json
from pathlib import Path


def key_id(key):
    fields = (key["item_id"], key["model_id"], key["condition"], key["replicate"])
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()


def archive_attempt(run_dir, key, attempt_index, raw, token_ids, outcome, error_type=None):
    """Archive decoded raw bytes before any score; incomplete archives block retry."""
    if type(attempt_index) is not int or not 0 <= attempt_index < 3:
        raise ValueError("Infrastructure retry cap is three attempts")
    if not isinstance(raw, str) or outcome not in {"generated", "error"}:
        raise ValueError("Invalid raw output or attempt outcome")
    if outcome == "generated" and (not isinstance(token_ids, list) or any(type(x) is not int or x < 0 for x in token_ids)):
        raise ValueError("Successful generation must preserve integer output token IDs")
    if outcome == "error" and error_type not in {"oom", "runtime", "interrupted"}:
        raise ValueError("Retries are for named infrastructure errors only")
    directory = Path(run_dir) / "attempts" / key_id(key)
    directory.mkdir(parents=True, exist_ok=True)
    existing = sorted(directory.iterdir())
    if [p.name for p in existing] != [f"{i:02d}" for i in range(attempt_index)]:
        raise ValueError("Noncontiguous or existing attempt; manual reconciliation required")
    for previous in existing:
        record = previous / "attempt.json"
        if not record.exists():
            raise ValueError("Incomplete archive; preserve it and reconcile before retry")
        if json.loads(record.read_text())["outcome"] == "generated":
            raise ValueError("Retry after completed generation is forbidden")
    target = directory / f"{attempt_index:02d}"
    target.mkdir(exist_ok=False)
    raw_bytes = raw.encode("utf-8")
    with (target / "raw.txt").open("xb") as f:
        f.write(raw_bytes)
        f.flush()
    tokens = json.dumps(token_ids, separators=(",", ":")).encode()
    with (target / "output_token_ids.json").open("xb") as f:
        f.write(tokens)
        f.flush()
    record = {"key": key, "attempt_index": attempt_index, "outcome": outcome,
              "error_type": error_type, "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
              "token_ids_sha256": hashlib.sha256(tokens).hexdigest(), "scored": False}
    with (target / "attempt.json").open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return target
