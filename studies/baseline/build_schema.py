"""Build the versioned schema once; refuses overwriting an existing schema."""
import json
from pathlib import Path


def obj(properties, required=None):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties) if required is None else required}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def make_schema():
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    revision = {"type": "string", "pattern": "^[0-9a-f]{40}$"}
    text = {"type": "string"}
    nonempty = {"type": "string", "minLength": 1}
    integer = {"type": "integer", "minimum": 0}
    positive = {"type": "integer", "minimum": 1}
    number = {"type": "number", "minimum": 0}
    nullable_number = {"type": ["number", "null"], "minimum": 0}
    ref = {"$ref": "#/$defs/file"}
    nullable_ref = {"anyOf": [ref, {"type": "null"}]}
    statuses = ["planned", "running", "complete-unverified", "verified", "development-only", "invalid"]
    checks = ["schema", "hashes", "keys", "raw_outputs", "scorer", "pairing", "budgets", "revisions", "environment", "renders"]
    latency_fields = ["retrieval_s", "render_s", "preprocess_s", "transfer_s", "vision_encode_s",
                      "prefill_s", "first_token_s", "decode_s", "generation_s", "end_to_end_s"]
    schema = obj({
        "schema_version": {"const": 1},
        "run_id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{8,100}$"},
        "snapshot_index": integer,
        "previous_manifest_sha256": {"anyOf": [sha, {"type": "null"}]},
        "created_utc": {"type": "string", "format": "date-time"},
        "status": {"enum": statuses},
        "experiment": {"enum": ["P1.1", "P1.2", "P1.3", "P1.4", "P2.1", "smoke"]},
        "protocol": ref,
        "execution_lock": ref,
        "expected_keys": ref,
        "scorer": ref,
        "prompt": ref,
        "models": array({"$ref": "#/$defs/model"}, 1),
        "environment": obj({"inventory": ref, "gpu_name": nonempty, "gpu_uuid": nonempty,
                            "vram_bytes": positive, "dtype": {"const": "bfloat16"},
                            "attention_backend": nonempty, "software_lock": ref}),
        "seeds": obj({k: positive for k in ["dataset", "inference", "order", "statistics"]}),
        "generation": obj({"do_sample": {"const": False}, "num_beams": {"const": 1},
                           "batch_size": {"const": 1}, "use_cache": {"const": True},
                           "max_new_tokens": {"enum": [32, 64, 96]}}),
        "artifacts": array(ref, 1),
        "rows": array({"$ref": "#/$defs/row"}),
        "attempt_log": ref,
        "validation": obj({"passed": {"type": "boolean"},
                           "checks": {"type": "array", "uniqueItems": True, "items": {"enum": checks}},
                           "report": nullable_ref,
                           "limitations": array(nonempty)})
    })
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema",
                   "$id": "urn:slm-agents:iclr:run-manifest:1",
                   "title": "ICLR immutable run metadata snapshot v1",
                   "description": "Every transition creates a new snapshot; semantic validator and external file hashes are mandatory."})
    schema["$defs"] = {
        "file": obj({"path": {"type": "string", "minLength": 1, "pattern": "^[A-Za-z0-9_. /-]+$"},
                     "sha256": sha, "bytes": integer}),
        "model": obj({"id": nonempty, "model_revision": revision,
                      "processor_id": nonempty, "processor_revision": revision,
                      "tokenizer_id": nonempty, "tokenizer_revision": revision,
                      "snapshot_inventory": ref, "chat_template": ref}),
        "counts": obj({"source_text_tokens": positive, "memory_text_tokens": integer,
                       "vision_tokens": integer, "nonvision_input_tokens": integer,
                       "total_input_tokens": positive, "page_count": integer,
                       "merge_size": positive,
                       "image_grid_thw": array({"type": "array", "items": positive, "minItems": 3, "maxItems": 3}),
                       "vision_tokens_per_page": array(integer),
                       "matched_target_input_tokens": {"type": ["integer", "null"], "minimum": 1},
                       "source_to_vision_ratio": nullable_number}),
        "latency": obj({**{k: nullable_number for k in latency_fields},
                        "unavailable_reasons": {"type": "object", "additionalProperties": nonempty},
                        "definitions": ref, "cuda_synchronized": {"type": "boolean"},
                        "warmup": {"type": "boolean"},
                        "peak_allocated_bytes": {"type": ["integer", "null"], "minimum": 0},
                        "peak_reserved_bytes": {"type": ["integer", "null"], "minimum": 0}}),
        "row": obj({"item_id": nonempty, "cluster_id": nonempty, "condition": nonempty,
                    "model_id": nonempty, "model_revision": revision, "replicate": integer,
                    "status": {"enum": statuses}, "task": {"enum": ["controlled", "locomo"]},
                    "category": {"enum": [None, 1, 2, 4]}, "reference": text,
                    "memory": ref, "selected_turn_ids": {"type": "array", "uniqueItems": True, "items": nonempty},
                    "page_text_segments": array(ref), "images": array(ref),
                    "serialized_input": ref, "input_tensor_inventory": ref,
                    "raw_output": ref, "generated_token_ids": ref,
                    "generated_tokens": integer, "termination": {"enum": ["eos", "cap", "empty"]},
                    "counts": {"$ref": "#/$defs/counts"},
                    "latency": {"$ref": "#/$defs/latency"},
                    "scores": {"type": "object", "additionalProperties": {"type": ["string", "number"]}}})
    }
    schema["allOf"] = [
        {"if": {"properties": {"snapshot_index": {"const": 0}}},
         "then": {"properties": {"previous_manifest_sha256": {"type": "null"}}},
         "else": {"properties": {"previous_manifest_sha256": sha}}},
        {"if": {"properties": {"status": {"const": "verified"}}},
         "then": {"properties": {"rows": {"minItems": 1}, "validation": {
             "properties": {"passed": {"const": True}, "checks": {"minItems": len(checks)}, "report": ref}}}}}
    ]
    return schema


if __name__ == "__main__":
    path = Path(__file__).with_name("RUN_MANIFEST.schema.json")
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(make_schema(), f, indent=2)
        f.write("\n")
    print(path)
