"""Extend the byte-frozen v1 schema; generate a new v2 file, exclusively."""
import json
from pathlib import Path
from baseline.build_schema import make_schema as make_v1, obj, array


def make_schema():
    s = make_v1()
    s["$id"] = "urn:slm-agents:iclr:run-manifest:2"
    s["title"] = "ICLR v2 immutable run metadata"
    p = s["properties"]
    p["schema_version"] = {"const": 2}
    p["experiment"] = {"enum": ["locomo500", "ruler180", "identifier96", "smoke"]}
    p["generation"]["properties"]["max_new_tokens"] = {"enum": [64, 96, 128]}
    ref = {"$ref": "#/$defs/file"}
    nref = {"anyOf": [ref, {"type": "null"}]}
    nonempty = {"type": "string", "minLength": 1}
    num = {"type": "number", "minimum": 0}
    integer = {"type": "integer", "minimum": 0}
    extra = {"plan_freeze": ref, "source_manifest": ref, "template_manifest": ref,
             "reference_tokenizer": ref, "eligibility_manifest": ref,
             "implementation_inventory": ref}
    p.update(extra)
    s["required"].extend(extra)
    row = s["$defs"]["row"]
    rp = row["properties"]
    rp["task"] = {"enum": ["locomo", "controlled", "ruler"]}
    rp["reference"] = {"anyOf": [{"type": "string"}, obj({
        "task_id": nonempty, "answers": array(nonempty, 1)})]}
    score_values = {"type": "object", "additionalProperties": {"type": "number"}}
    rp["scores"] = obj({"canonical_answer": {"type": "string"},
                        "native": score_values, "canonical": score_values})
    extras = {"benchmark_task": nonempty, "source_identity": ref,
              "support_coverage": nref, "render_metadata": nref,
              "retrieval_metadata": nref}
    rp.update(extras)
    row["required"].extend(extras)
    counts = s["$defs"]["counts"]
    counts["properties"]["unused_matched_budget"] = {"type": ["integer", "null"], "minimum": 0}
    counts["required"].append("unused_matched_budget")
    return s


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "RUN_MANIFEST.schema.json"
    with target.open("x", encoding="utf-8") as f:
        json.dump(make_schema(), f, indent=2)
        f.write("\n")
