"""Shared final experiment constants; imports audited project utilities unchanged."""
from pathlib import Path
import hashlib
import json
import sys
import importlib.metadata

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
LEGACY = REPO / 'final_iclr/final_followups/runtime/legacy'
sys.path.insert(0, str(LEGACY))
from core import read, put, sha, plan, render, font, verify_files
from vendor.processor_measure import measure, SYSTEM

CONFIG = read(ROOT / 'config.json')

def digest(value):
    return hashlib.sha256(value.encode('utf8')).hexdigest()

def chat(processor, memory, question, images=None):
    content = ([{'type':'text','text':'MEMORY\n'}] +
               [{'type':'image','image':im} for im in images] +
               [{'type':'text','text':'\n\nQUESTION\n'+question}]) if images else [
                   {'type':'text','text':'MEMORY\n'+memory+'\n\nQUESTION\n'+question}]
    return processor.apply_chat_template([
        {'role':'system','content':SYSTEM}, {'role':'user','content':content}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)

def text_count(processor, memory, question=''):
    return len(processor.tokenizer.encode(chat(processor,memory,question),add_special_tokens=False))

def verify_snapshot(snapshot, weights=True):
    snapshot = Path(snapshot)
    pin = read(ROOT/'environment/GLM_SNAPSHOT.json')
    files = pin['files'] if weights else [r for r in pin['files'] if not r['path'].endswith('.safetensors')]
    verify_files(snapshot, files)
    return pin

def load_processor(assets=None):
    import transformers
    import torch
    assert transformers.__version__ == '5.3.0'
    assert torch.__version__ in ('2.10.0+cpu','2.10.0+cu128') or (torch.__version__=='2.10.0' and torch.version.cuda is None)
    for name,version in CONFIG['package_pins'].items():
        assert importlib.metadata.version(name) == version, (name,version,importlib.metadata.version(name))
    assets = Path(assets or ROOT/'assets/GLM')
    verify_snapshot(assets, weights=False)
    return transformers.AutoProcessor.from_pretrained(assets,local_files_only=True,trust_remote_code=False,use_fast=True)

def tensor_check(batch, measurement):
    assert batch['input_ids'][0].tolist() == measurement['input_token_ids'], 'Input IDs changed'
    assert set(batch) == set(measurement['tensor_inventory']), 'Tensor names changed'
    for k,v in measurement['tensor_inventory'].items():
        a=batch[k].detach().cpu().contiguous().numpy()
        assert list(a.shape)==v['shape'] and str(a.dtype)==v['dtype']
        assert hashlib.sha256(a.tobytes()).hexdigest()==v['sha256'], 'Tensor changed: '+k

def verify_freeze():
    freeze = read(ROOT/'FREEZE.json')
    assert freeze['status']=='frozen-awaiting-user-approval'
    assert freeze['held_out_inference_started'] is False
    verify_files(ROOT, freeze['files'])
    verify_files(REPO, freeze['dependencies'])
    assert sha(ROOT/'PROTOCOL.md')==freeze['protocol_sha256']
    assert sha(ROOT/'manifest.json')==freeze['manifest_sha256']
    assert len(read(ROOT/'manifest.json')['rows'])==CONFIG['held_out_calls']
    return freeze

def empty_question_counter(processor):
    """Exact same native backend, with the constant empty-query chat compiled once."""
    marker='FINAL_EXPERIMENT_STORAGE_SENTINEL_20260925'
    scaffold=chat(processor,marker,'')
    assert scaffold.count(marker)==1
    prefix,suffix=scaffold.split(marker)
    backend=processor.tokenizer.backend_tokenizer
    assert backend.padding is None and backend.truncation is None
    def count(memory):
        assert marker not in memory
        return len(backend.encode(prefix+memory+suffix,add_special_tokens=False))
    # The memory grammar contains only ASCII record syntax, no chat special tokens.
    for memory in ('','Record ABCDEFGHIJ: 1234567','Records (key=number):\nABCDEFGHIJ=1234567'):
        assert prefix+memory+suffix==chat(processor,memory,'')
        assert count(memory)==text_count(processor,memory,'')
    return count
