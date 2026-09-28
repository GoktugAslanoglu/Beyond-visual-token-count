"""Approval-gated local-only confirmatory runner; never scores or prints answers."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import random
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    """Exclusive durable commit: existing outputs cannot be overwritten."""
    with Path(path).open('x', encoding='utf8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def approval_gate(root, approval):
    """Pure stdlib: fail before model imports, network, or output mutation."""
    root = Path(root)
    if approval is None:
        raise RuntimeError('Held-out inference requires a user-approved approval file; none was supplied.')
    approval = Path(approval)
    if not approval.is_file():
        raise RuntimeError('Approval file absent. Do not create one without explicit user approval.')
    config, decision = read_json(root / 'config.json'), read_json(approval)
    if decision.get('approved') is not True or decision.get('approved_by') != 'user':
        raise RuntimeError('Approval must explicitly record approved:true and approved_by:user.')
    expected = {'experiment_id': config['experiment_id'],
                'protocol_sha256': file_sha(root / 'PROTOCOL.md'),
                'freeze_sha256': file_sha(root / 'FREEZE.json'),
                'max_calls': config['held_out_calls']}
    for key, value in expected.items():
        if decision.get(key) != value or (key == 'max_calls' and type(decision[key]) is not int):
            raise RuntimeError('Approval mismatch: ' + key)
    if config['held_out_calls'] != 450 or config['n_eval'] != 150 or config['max_gpu_seconds'] != 7200:
        raise RuntimeError('Runner requires exactly 150 triplets, 450 calls, and 7200 GPU-run seconds.')
    return config, decision, file_sha(approval)


def input_folder(root, row):
    root = Path(root).resolve()
    p = (root / row['path']).resolve()
    if not p.is_relative_to(root / 'inputs'):
        raise RuntimeError('Manifest path escapes frozen inputs.')
    return p


def schedule_rows(manifest, config):
    rows = manifest['rows']
    if manifest.get('experiment_id') != config['experiment_id'] or len(rows) != config['held_out_calls']:
        raise RuntimeError('Manifest identity or call count mismatch.')
    arms = config['arms']
    if arms != ['optical', 'hash_text', 'compact_text']:
        raise RuntimeError('Unexpected arm family.')
    cases, paths = {}, set()
    for row in rows:
        case, arm = row['case_id'], row['arm']
        if not isinstance(case, str) or not case or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in case):
            raise RuntimeError('Unsafe case ID.')
        if arm not in arms or arm in cases.setdefault(case, {}) or row['path'] in paths:
            raise RuntimeError('Duplicate or unexpected input.')
        cases[case][arm] = row
        paths.add(row['path'])
    if len(cases) != config['n_eval'] or any(set(v) != set(arms) for v in cases.values()):
        raise RuntimeError('Incomplete paired design.')
    order = sorted(cases)
    random.Random(config['seeds']['order']).shuffle(order)
    result = []
    for block, case in enumerate(order):
        offset = block % len(arms)
        result.extend(cases[case][arm] for arm in arms[offset:] + arms[:offset])
    return result


def validate_raw(raw, row, config, request_sha, measurement_sha):
    required = {'experiment_id', 'case_id', 'arm', 'request_sha256', 'measurement_sha256',
                'generated_token_ids', 'prediction', 'decoded_with_special_tokens', 'cap_hit'}
    if set(raw) != required:
        raise RuntimeError('Raw output schema mismatch.')
    for key, expected in [('experiment_id', config['experiment_id']), ('case_id', row['case_id']),
                          ('arm', row['arm']), ('request_sha256', request_sha),
                          ('measurement_sha256', measurement_sha)]:
        if raw[key] != expected:
            raise RuntimeError('Raw output identity mismatch: ' + key)
    ids = raw['generated_token_ids']
    if not isinstance(ids, list) or not 0 < len(ids) <= config['max_new_tokens'] or any(type(v) is not int or v < 0 for v in ids):
        raise RuntimeError('Invalid generated token IDs.')
    if type(raw['cap_hit']) is not bool or raw['cap_hit'] != (len(ids) == config['max_new_tokens']):
        raise RuntimeError('Generation cap metadata mismatch.')
    if not isinstance(raw['prediction'], str) or not isinstance(raw['decoded_with_special_tokens'], str):
        raise RuntimeError('Invalid decoded output schema.')


def validate_journal(path, input_ids, generated_ids):
    with Path(path).open(encoding='utf8') as f:
        records = [json.loads(line) for line in f]
    if not records or records[0] != [input_ids]:
        raise RuntimeError('Token journal does not begin with the exact prompt IDs.')
    if any(not isinstance(row, list) or len(row) != 1 or type(row[0]) is not int for row in records[1:]):
        raise RuntimeError('Invalid batch-one token journal.')
    if [row[0] for row in records[1:]] != generated_ids:
        raise RuntimeError('Token journal differs from generated IDs.')


def committed_prefix(output, schedule, root, config, freeze_sha):
    """Only a verified prefix can resume; any uncertain invocation aborts the run."""
    output = Path(output)
    expected = {f'{i:04d}--{r["case_id"]}--{r["arm"]}' for i, r in enumerate(schedule)}
    if output.exists() and any(p.is_dir() and p.name not in expected for p in output.iterdir()):
        raise RuntimeError('Unexpected output directory.')
    completed, gap = 0, False
    for i, row in enumerate(schedule):
        folder = output / f'{i:04d}--{row["case_id"]}--{row["arm"]}'
        if not folder.exists():
            gap = True
            continue
        if gap:
            raise RuntimeError('Outputs are not a committed schedule prefix.')
        if not (folder / 'COMPLETE.json').is_file():
            raise RuntimeError('Uncertain/incomplete invocation: abort entire confirmatory run; no retry: ' + str(folder))
        complete = read_json(folder / 'COMPLETE.json')
        for key, name in [('raw_sha256', 'RAW.json'), ('journal_sha256', 'TOKENS.jsonl'), ('start_sha256', 'START.json')]:
            if complete.get(key) != file_sha(folder / name):
                raise RuntimeError('Committed output hash mismatch: ' + name)
        start = read_json(folder / 'START.json')
        if start.get('index') != i or start.get('row') != row or start.get('freeze_sha256') != freeze_sha:
            raise RuntimeError('Committed start identity mismatch.')
        source = input_folder(root, row)
        raw = read_json(folder / 'RAW.json')
        validate_raw(raw, row, config, file_sha(source / 'REQUEST.json'), file_sha(source / 'MEASUREMENT.json'))
        for key in ['request_sha256', 'measurement_sha256']:
            if start.get(key) != raw[key]:
                raise RuntimeError('Committed source provenance mismatch.')
        validate_journal(folder / 'TOKENS.jsonl', read_json(source / 'MEASUREMENT.json')['input_token_ids'], raw['generated_token_ids'])
        if complete.get('environment_sha256') != file_sha(output / 'ENVIRONMENT.json'):
            raise RuntimeError('Committed environment hash mismatch.')
        if complete.get('generation_invocations') != 1 or not isinstance(complete.get('generation_s'), (int, float)) or not math.isfinite(complete['generation_s']) or complete['generation_s'] <= 0:
            raise RuntimeError('Invalid committed invocation metadata.')
        if complete.get('generated_tokens') != len(raw['generated_token_ids']) or complete.get('cap_hit') != raw['cap_hit']:
            raise RuntimeError('Committed token/cap metadata mismatch.')
        completed += 1
    return completed


def consumed_seconds(output):
    """Closed session ledgers include model loading, preparation, and generation."""
    total = 0.0
    for start in sorted(Path(output).glob('SESSION_*.START.json')):
        end = start.with_name(start.name.replace('.START.json', '.END.json'))
        if not end.is_file():
            raise RuntimeError('Unclosed GPU session: abort; elapsed budget is uncertain.')
        record = read_json(end)
        seconds = record.get('elapsed_s')
        if record.get('start_sha256') != file_sha(start) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise RuntimeError('Invalid GPU session ledger.')
        total += seconds
    return total


def verify_prelaunch_audit(root, freeze):
    relative = freeze['prelaunch_audit_path']
    if relative not in {r['path'] for r in freeze['files']}:
        raise RuntimeError('Independent prelaunch audit is not bound by the freeze.')
    report = read_json(Path(root) / relative)
    if report.get('status') != 'passed' or report.get('held_out_inference_started') is not False or report.get('model_calls') != 0:
        raise RuntimeError('Independent prelaunch audit does not permit launch.')


def run(approval, snapshot, output=None):
    config, decision, approval_sha = approval_gate(ROOT, approval)
    # Deliberately after the pure-stdlib authorization gate.
    import experiment_common as common
    freeze = common.verify_freeze()
    verify_prelaunch_audit(ROOT, freeze)
    freeze_sha = file_sha(ROOT / 'FREEZE.json')
    if freeze['protocol_sha256'] != decision['protocol_sha256']:
        raise RuntimeError('Frozen protocol differs from approval.')
    schedule = schedule_rows(read_json(ROOT / 'manifest.json'), config)
    for row in schedule:
        input_folder(ROOT, row)
    output = Path(output or ROOT / 'outputs/raw').resolve()
    if output != (ROOT / 'outputs/raw').resolve():
        raise RuntimeError('Only frozen outputs/raw is allowed; independent repeat runs are prohibited.')
    if snapshot is None:
        raise RuntimeError('A complete local pinned snapshot is required; this runner never downloads.')
    snapshot = Path(snapshot).resolve()
    pin = common.verify_snapshot(snapshot, weights=True)
    if pin['revision'] != config['model_revision'] or pin['model_id'] != config['model_id']:
        raise RuntimeError('Snapshot identity differs from protocol.')
    completed = committed_prefix(output, schedule, ROOT, config, freeze_sha)
    previous_seconds = consumed_seconds(output)
    if previous_seconds >= config['max_gpu_seconds']:
        raise RuntimeError('Cumulative GPU-run allocation exhausted.')
    identity = {'experiment_id': config['experiment_id'], 'freeze_sha256': freeze_sha,
                'approval_sha256': approval_sha, 'max_calls': 450, 'max_gpu_seconds': config['max_gpu_seconds']}
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'RUN_START.json').exists():
        if read_json(output / 'RUN_START.json') != identity or read_json(output / 'ORDER.json') != schedule:
            raise RuntimeError('Resume identity/order mismatch.')
    else:
        if any(output.iterdir()):
            raise RuntimeError('Nonempty output directory has no run identity.')
        write_new(output / 'RUN_START.json', identity)
        write_new(output / 'ORDER.json', schedule)
    if completed == 450:
        if not (output / 'RUN_COMPLETE.json').exists():
            write_new(output / 'RUN_COMPLETE.json', {**identity, 'generation_invocations': 450, 'status': 'complete-unscored'})
        return

    import torch
    import transformers
    import numpy as np
    from PIL import Image
    if torch.__version__ != '2.10.0+cu128' or transformers.__version__ != '5.3.0':
        raise RuntimeError('GPU environment does not match pins.')
    for name, version in config['package_pins'].items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError('Package pin mismatch: ' + name)
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('CUDA BF16 GPU required.')
    props = torch.cuda.get_device_properties(0)
    if 'A100' not in props.name or not 38 * 1024**3 < props.total_memory < 42 * 1024**3:
        raise RuntimeError('Frozen hardware requires A100 40GB.')
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    seed = config['seeds']['inference']
    random.seed(seed)
    np.random.seed(seed % 2**32)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    session_index = len(list(output.glob('SESSION_*.START.json')))
    session_path = output / f'SESSION_{session_index:03d}.START.json'
    write_new(session_path, {'epoch': time.time(), 'completed_before': completed,
                             'prior_elapsed_s': previous_seconds, 'freeze_sha256': freeze_sha})
    started = time.monotonic()
    timer = threading.Timer(config['max_gpu_seconds'] - previous_seconds, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        processor = common.load_processor(snapshot)
        model = transformers.AutoModelForImageTextToText.from_pretrained(
            snapshot, local_files_only=True, trust_remote_code=False, dtype=torch.bfloat16,
            attn_implementation='sdpa', use_safetensors=True).to('cuda:0').eval()
        generation = transformers.GenerationConfig.from_dict(model.generation_config.to_dict())
        generation.update(do_sample=False, num_beams=1, use_cache=True, max_new_tokens=64,
                          return_dict_in_generate=True, output_scores=False, disable_compile=True)
        env = {'experiment_id': config['experiment_id'], 'revision': pin['revision'],
               'python': sys.version, 'torch': torch.__version__, 'transformers': transformers.__version__,
               'packages': {n: importlib.metadata.version(n) for n in config['package_pins']},
               'gpu': props.name, 'gpu_total_memory': props.total_memory, 'attention': 'sdpa', 'dtype': 'bfloat16',
               'seed': seed, 'generation': generation.to_dict(), 'thinking': False,
               'cudnn_benchmark': False, 'tf32_matmul': False}
        env_path = output / 'ENVIRONMENT.json'
        if env_path.exists():
            if read_json(env_path) != env:
                raise RuntimeError('Resume environment/generation configuration mismatch.')
        else:
            write_new(env_path, env)
        for index, row in enumerate(schedule[completed:], start=completed):
            if index >= decision['max_calls']:
                raise RuntimeError('Approved invocation budget exhausted.')
            source = input_folder(ROOT, row)
            request, measurement = read_json(source / 'REQUEST.json'), read_json(source / 'MEASUREMENT.json')
            if request['case_id'] != row['case_id'] or request['arm'] != row['arm'] or request['max_new_tokens'] != 64:
                raise RuntimeError('Frozen request identity/cap mismatch.')
            if measurement['total_input_tokens'] > config['B'] or measurement['total_input_tokens'] + 64 > measurement['native_context_limit']:
                raise RuntimeError('Frozen input exceeds budget/context.')
            images = []
            for image_name in request['images']:
                image_path = (source / image_name).resolve()
                if image_path.parent != source:
                    raise RuntimeError('Image path escapes request directory.')
                images.append(Image.open(image_path).convert('RGB'))
            if common.chat(processor, request['memory'], request['question'], images) != measurement['rendered_chat']:
                raise RuntimeError('Frozen chat template or no-thinking contract changed.')
            batch = processor(text=[measurement['rendered_chat']], images=images or None, return_tensors='pt', padding=False)
            common.tensor_check(batch, measurement)
            device = {k: v.to('cuda:0') for k, v in batch.items()}
            torch.cuda.synchronize()
            dest = output / f'{index:04d}--{row["case_id"]}--{row["arm"]}'
            dest.mkdir(exist_ok=False)
            write_new(dest / 'START.json', {'index': index, 'row': row, 'freeze_sha256': freeze_sha,
                       'request_sha256': file_sha(source / 'REQUEST.json'),
                       'measurement_sha256': file_sha(source / 'MEASUREMENT.json')})

            class Journal:
                def put(self, value):
                    with (dest / 'TOKENS.jsonl').open('ab') as f:
                        f.write(json.dumps(value.detach().cpu().tolist()).encode('utf8') + b'\n')
                        f.flush()
                        os.fsync(f.fileno())

                def end(self):
                    pass

            call_start = time.monotonic()
            with torch.inference_mode():
                generated = model.generate(**device, generation_config=generation, streamer=Journal())
            torch.cuda.synchronize()
            generation_s = time.monotonic() - call_start
            ids = generated.sequences[0, len(measurement['input_token_ids']):].detach().cpu().tolist()
            raw = {'experiment_id': config['experiment_id'], 'case_id': row['case_id'], 'arm': row['arm'],
                   'request_sha256': file_sha(source / 'REQUEST.json'),
                   'measurement_sha256': file_sha(source / 'MEASUREMENT.json'),
                   'generated_token_ids': ids,
                   'prediction': processor.tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False),
                   'decoded_with_special_tokens': processor.tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False),
                   'cap_hit': len(ids) == 64}
            validate_raw(raw, row, config, raw['request_sha256'], raw['measurement_sha256'])
            validate_journal(dest / 'TOKENS.jsonl', measurement['input_token_ids'], ids)
            write_new(dest / 'RAW.json', raw)
            write_new(dest / 'COMPLETE.json', {'raw_sha256': file_sha(dest / 'RAW.json'),
                      'journal_sha256': file_sha(dest / 'TOKENS.jsonl'), 'start_sha256': file_sha(dest / 'START.json'),
                      'generation_s': generation_s, 'generation_invocations': 1,
                      'generated_tokens': len(ids), 'cap_hit': raw['cap_hit'], 'environment_sha256': file_sha(env_path)})
            for im in images:
                im.close()
            del generated, device, batch, images
            print(f'Committed {index + 1}/450; answers remain unscored.', flush=True)
        write_new(output / 'RUN_COMPLETE.json', {**identity, 'generation_invocations': 450, 'status': 'complete-unscored'})
    finally:
        timer.cancel()
        write_new(session_path.with_name(session_path.name.replace('.START.json', '.END.json')),
                  {'start_sha256': file_sha(session_path), 'elapsed_s': time.monotonic() - started})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approval', type=Path, help='Approval file created only after actual user approval.')
    parser.add_argument('--snapshot', type=Path, help='Complete locally cached pinned model snapshot.')
    args = parser.parse_args()
    run(args.approval, args.snapshot)


if __name__ == '__main__':
    main()
