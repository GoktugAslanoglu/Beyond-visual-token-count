"""One-time local copies of frozen validator and scoring oracle; no network."""
import ast
import hashlib
import json
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    iclr = here.parents[1]
    source = iclr / "validate.py"
    text = source.read_text(encoding="utf-8")
    edits = {
        'from scoring import score': 'from .scoring import score',
        'ROOT = Path(__file__).resolve().parent': 'ROOT = Path(__file__).resolve().parents[2]',
        "ROOT / 'RUN_MANIFEST.schema.json'": "ROOT / 'v2/RUN_MANIFEST.schema.json'",
        "ROOT / 'scoring.py'": "ROOT / 'v2/runtime/scoring.py'",
        "'gpu_authorization_record']": "'gpu_authorization_record', 'v2_readiness']",
    }
    for old, new in edits.items():
        if old not in text:
            raise ValueError(f"Missing frozen source anchor: {old}")
        text = text.replace(old, new)
    with (here / "core_validation.py").open("x", encoding="utf-8") as f:
        f.write('# Derived from frozen iclr/validate.py; v2 wrapper adds required semantic checks.\n' + text)
    vendor = here.parent / "vendor"
    vendor.mkdir(exist_ok=False)
    native = iclr.parent / "work/locomo_source/evaluation.py"
    with (vendor / "locomo_evaluation.py").open("xb") as f:
        f.write(native.read_bytes())
    names = {"normalize_answer", "f1_score", "f1"}
    tree = ast.parse(native.read_text(encoding="utf-8"))
    extracted = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    assert len(extracted.body) == 3
    metrics = 'import regex\nimport string\nimport numpy as np\nfrom collections import Counter\nfrom nltk.stem import PorterStemmer\nps = PorterStemmer()\n\n' + ast.unparse(extracted) + '\n'
    with (vendor / "locomo_metrics.py").open("x", encoding="utf-8") as f:
        f.write(metrics)
    metadata = {"status": "verified", "scope": "local source-byte/AST provenance only",
                "validator_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "locomo_source_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
                "locomo_metrics_sha256": hashlib.sha256((vendor / 'locomo_metrics.py').read_bytes()).hexdigest(),
                "upstream_url": "https://github.com/snap-research/locomo/blob/main/task_eval/evaluation.py",
                "upstream_git_revision": None,
                "note": "Pinned local source bytes; upstream git checkout pin remains unresolved. Only native metric AST is executed, avoiding BERT imports."}
    with (vendor / "PROVENANCE.json").open("x", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
