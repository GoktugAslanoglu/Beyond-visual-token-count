# Derived from frozen iclr/validate.py; v2 wrapper adds required semantic checks.
"""Fail-closed local validation. Never runs inference or accesses the network."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .scoring import score

ROOT = Path(__file__).resolve().parents[2]
COMPLETE = {"complete-unverified", "verified"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_path(base: Path, name: str) -> Path:
    if Path(name).is_absolute() or "\\" in name or ":" in name or ".." in Path(name).parts:
        raise ValueError(f"Unsafe artifact path: {name}")
    result = (base / name).resolve()
    if result == base.resolve() or base.resolve() not in result.parents:
        raise ValueError(f"Artifact outside ICLR directory: {name}")
    return result


def read_ref(base: Path, ref: dict) -> bytes:
    value = local_path(base, ref["path"]).read_bytes()
    if len(value) != ref["bytes"] or digest(value) != ref["sha256"]:
        raise ValueError(f"Artifact hash/size mismatch: {ref['path']}")
    return value


def references(value):
    if isinstance(value, dict):
        if {"path", "sha256", "bytes"} <= value.keys():
            yield value
        else:
            for sub in value.values():
                yield from references(sub)
    elif isinstance(value, list):
        for sub in value:
            yield from references(sub)


def key(row: dict) -> tuple:
    return row["item_id"], row["model_id"], row["condition"], row["replicate"]


def validate_counts(row: dict):
    c = row["counts"]
    if c["total_input_tokens"] != c["vision_tokens"] + c["nonvision_input_tokens"]:
        raise ValueError("Total input accounting mismatch")
    grid = c['image_grid_thw']
    if len(grid) != c['page_count'] or len(c['vision_tokens_per_page']) != c['page_count']:
        raise ValueError("Page/grid accounting mismatch")
    calculated = [math.prod(g) / c['merge_size'] ** 2 for g in grid]
    if any(v != int(v) for v in calculated) or calculated != c['vision_tokens_per_page']:
        raise ValueError("Placeholder/grid accounting mismatch")
    if sum(calculated) != c['vision_tokens']:
        raise ValueError("Vision-token total mismatch")
    ratio = c['source_text_tokens'] / c['vision_tokens'] if c['vision_tokens'] else None
    if ratio != c['source_to_vision_ratio']:
        raise ValueError("Compression ratio does not match measured counts")
    if c['matched_target_input_tokens'] is not None and c['total_input_tokens'] > c['matched_target_input_tokens']:
        raise ValueError("Matched input budget exceeded")


def check_lock(lock: dict, base: Path = ROOT) -> list[str]:
    blockers = []
    required = ['environment_inventory', 'font', 'processor_calibration', 'render_manifest',
                'controlled_template_manifest', 'validator_report', 'inference_adapter',
                'gpu_authorization_record', 'v2_readiness']
    if not lock.get('sealed'):
        blockers.append('Execution lock is not sealed')
    expected_models = {"Qwen/Qwen3.5-2B", "Qwen/Qwen3.5-9B", "zai-org/GLM-4.6V-Flash"}
    if {m.get('id') for m in lock.get('models', [])} != expected_models:
        blockers.append('Mandatory model set is incomplete')
    for model in lock.get('models', []):
        for field in ['model_revision', 'processor_revision', 'tokenizer_revision']:
            if not re.fullmatch(r'[0-9a-f]{40}', str(model.get(field))):
                blockers.append(f"{model.get('id')}: missing immutable {field}")
        if not model.get('snapshot_inventory'):
            blockers.append(f"{model.get('id')}: missing snapshot inventory")
    for field in required:
        if not isinstance(lock.get(field), dict):
            blockers.append(f'Missing locked {field}')
    for ref in references(lock):
        try:
            read_ref(base, ref)
        except (OSError, ValueError, KeyError) as exc:
            blockers.append(str(exc))
    return blockers


def validate_manifest(manifest: dict, base: Path = ROOT, previous: dict | None = None):
    schema = json.loads((ROOT / 'v2/RUN_MANIFEST.schema.json').read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    for ref in references(manifest):
        read_ref(base, ref)
    if manifest['snapshot_index'] > 0:
        if previous is None:
            raise ValueError('Previous immutable snapshot is required')
        if previous['run_id'] != manifest['run_id'] or previous['snapshot_index'] + 1 != manifest['snapshot_index']:
            raise ValueError('Broken snapshot lineage')
        for field in ['experiment', 'protocol', 'execution_lock', 'expected_keys', 'scorer', 'prompt',
                      'models', 'environment', 'seeds', 'generation']:
            if previous[field] != manifest[field]:
                raise ValueError(f'Immutable run metadata changed: {field}')
        allowed = {'planned': {'running', 'invalid'}, 'running': {'running', 'complete-unverified', 'invalid'},
                   'complete-unverified': {'verified', 'invalid'}, 'verified': {'invalid'},
                   'invalid': set(), 'development-only': {'development-only', 'invalid'}}
        if manifest['status'] not in allowed[previous['status']]:
            raise ValueError('Illegal status transition')
        existing = {key(r): r for r in manifest['rows']}
        for old in previous['rows']:
            if key(old) not in existing or {k:v for k,v in old.items() if k!='status'} != {k:v for k,v in existing[key(old)].items() if k!='status'}:
                raise ValueError('Previously archived row changed or disappeared')
    if manifest['scorer']['sha256'] != digest((ROOT / 'v2/runtime/scoring.py').read_bytes()):
        raise ValueError('Scorer hash does not identify this tested implementation')
    expected = json.loads(read_ref(base, manifest['expected_keys']))
    expected_map = {key(r): r for r in expected}
    actual = {key(r): r for r in manifest['rows']}
    if len(expected_map) != len(expected) or len(actual) != len(manifest['rows']):
        raise ValueError('Duplicate expected or realized keys')
    if not actual.keys() <= expected_map.keys():
        raise ValueError('Unexpected run keys')
    if manifest['status'] in COMPLETE and actual.keys() != expected_map.keys():
        raise ValueError('Missing planned run keys')
    if manifest['status'] == 'planned' and manifest['rows']:
        raise ValueError('Planned run already contains outputs')
    if manifest['status'] != 'planned':
        blockers = check_lock(json.loads(read_ref(base, manifest['execution_lock'])), base)
        if blockers:
            raise ValueError('; '.join(blockers))
    models = {m['id']: m for m in manifest['models']}
    if manifest['status'] != 'planned':
        lock = json.loads(read_ref(base, manifest['execution_lock']))
        locked_models = {m['id']: m for m in lock['models']}
        for name, model in models.items():
            if name not in locked_models or any(model[f] != locked_models[name][f] for f in
                    ['model_revision', 'processor_revision', 'tokenizer_revision', 'snapshot_inventory']):
                raise ValueError('Actual model does not match execution lock')
        if manifest['environment']['inventory'] != lock['environment_inventory']:
            raise ValueError('Actual environment does not match execution lock')
        attempts = json.loads(read_ref(base, manifest['attempt_log']))
        if not isinstance(attempts, list):
            raise ValueError('Attempt log must be a list')
        grouped_attempts = {}
        for attempt in attempts:
            ak = key(attempt)
            if ak not in expected_map:
                raise ValueError('Unexpected attempted key')
            group = grouped_attempts.setdefault(ak, [])
            if attempt['attempt_index'] != len(group) or len(group) >= 3:
                raise ValueError('Attempt index/retry cap violation')
            if any(a['status'] == 'generated' for a in group):
                raise ValueError('Retry after completed generation is forbidden')
            if attempt['status'] not in ['generated', 'error']:
                raise ValueError('Invalid attempt status')
            for ref in references(attempt):
                read_ref(base, ref)
            if not isinstance(attempt.get('raw_output'), dict):
                raise ValueError('Every attempt must archive raw output or error bytes')
            group.append(attempt)
        for rk, row in actual.items():
            successes = [a for a in grouped_attempts.get(rk, []) if a['status'] == 'generated']
            if len(successes) != 1 or successes[0]['raw_output'] != row['raw_output'] or successes[0].get('generated_token_ids') != row['generated_token_ids']:
                raise ValueError('Row is not the first archived successful attempt')
        if manifest['status'] in COMPLETE and any(not any(a['status'] == 'generated' for a in group) for group in grouped_attempts.values()):
            raise ValueError('Unresolved runtime failure in completed run')
    if len(models) != len(manifest['models']):
        raise ValueError('Duplicate models')
    if 20260826 in manifest['seeds'].values():
        raise ValueError('Legacy seed used in a new run')
    for k, row in actual.items():
        expected_row = expected_map[k]
        for field in ['cluster_id', 'reference', 'task', 'category']:
            if row[field] != expected_row[field]:
                raise ValueError(f'Expected data field changed: {field}')
        if row['model_id'] not in models or row['model_revision'] != models[row['model_id']]['model_revision']:
            raise ValueError('Model revision mismatch')
        if manifest['status'] == 'verified' and row['status'] != 'verified':
            raise ValueError('Verified run contains non-verified row')
        if manifest['status'] in COMPLETE and row['status'] not in COMPLETE:
            raise ValueError('Complete run contains incomplete/invalid row')
        raw = read_ref(base, row['raw_output']).decode('utf-8')
        ids = json.loads(read_ref(base, row['generated_token_ids']))
        if not isinstance(ids, list) or any(type(x) is not int or x < 0 for x in ids):
            raise ValueError('Invalid raw generated token IDs')
        if len(ids) != row['generated_tokens'] or len(ids) > manifest['generation']['max_new_tokens']:
            raise ValueError('Generated-token count/cap mismatch')
        if row['termination'] == 'cap' and len(ids) != manifest['generation']['max_new_tokens']:
            raise ValueError('Incorrect cap-termination label')
        if score(raw, row['reference'], row['task'], row['category']) != row['scores']:
            raise ValueError('Scores cannot be reproduced from archived raw output')
        validate_counts(row)
        count = row['counts']
        if expected_row.get('c_target') is not None:
            c = count['source_to_vision_ratio']
            if c is None or abs(c / expected_row['c_target'] - 1) > .1:
                raise ValueError('Realized compression outside predeclared tolerance')
        if expected_row.get('page_count') is not None and count['page_count'] != expected_row['page_count']:
            raise ValueError('Unexpected page count')
        if len(row['images']) != count['page_count'] or len(row['page_text_segments']) != count['page_count']:
            raise ValueError('Missing page image/content map')
        if count['page_count'] and b''.join(read_ref(base, r) for r in row['page_text_segments']) != read_ref(base, row['memory']):
            raise ValueError('Rendered content drops, duplicates or changes evidence')
        for field, value in row['latency'].items():
            if value is None and not row['latency']['unavailable_reasons'].get(field):
                raise ValueError(f'Missing reason for unavailable timing/memory component: {field}')
        if row['condition'] == 'retrieved_optical_8px':
            paired = actual.get((row['item_id'], row['model_id'], 'retrieved_text', row['replicate']))
            if paired is None and manifest['status'] in COMPLETE:
                raise ValueError('Missing same-evidence text pair')
            if paired and (paired['memory']['sha256'] != row['memory']['sha256'] or paired['selected_turn_ids'] != row['selected_turn_ids']):
                raise ValueError('Selected evidence differs across representations')
        if row['condition'] == 'retrieved_text_matched':
            baseline = actual.get((row['item_id'], row['model_id'], 'full_optical_c2', row['replicate']))
            if baseline and count['matched_target_input_tokens'] != baseline['counts']['total_input_tokens']:
                raise ValueError('Matched budget does not reference actual full optical input')
            if baseline is None and manifest['status'] in COMPLETE:
                raise ValueError('Missing full optical matched-budget reference')
    return {'passed': True, 'rows': len(actual), 'expected_rows': len(expected),
            'status': manifest['status'], 'note': 'Byte/content metadata validation; GPU adapter and render QA are separately required.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path)
    p.add_argument('--previous', type=Path)
    p.add_argument('--lock', type=Path)
    args = p.parse_args()
    if args.lock:
        blockers = check_lock(json.loads(args.lock.read_text()))
        print(json.dumps({'ready_for_inference': not blockers, 'blockers': blockers}, indent=2))
        raise SystemExit(2 if blockers else 0)
    if not args.manifest:
        p.error('--manifest or --lock required')
    manifest = json.loads(args.manifest.read_text())
    previous = json.loads(args.previous.read_text()) if args.previous else None
    if args.previous and digest(args.previous.read_bytes()) != manifest['previous_manifest_sha256']:
        raise ValueError('Previous snapshot hash mismatch')
    print(json.dumps(validate_manifest(manifest, previous=previous), indent=2))


if __name__ == '__main__':
    main()
