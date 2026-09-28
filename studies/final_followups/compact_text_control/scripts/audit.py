"""Zero-model prelaunch checks and independent post-run decoding/inventory audit."""
import argparse
import datetime
import json
import math
from pathlib import Path
from experiment_common import ROOT, REPO, CONFIG, read, put, sha, verify_freeze, load_processor

def validate_journal(journal, prompt_ids, generated_ids):
    assert journal and journal[0]==[prompt_ids], 'Journal prompt differs from frozen input'
    tokens=[]
    for step in journal[1:]:
        assert isinstance(step,list) and len(step)==1 and type(step[0]) is int and step[0]>=0
        tokens.extend(step)
    assert tokens==generated_ids, 'Generated IDs differ from durable stream journal'

def prelaunch():
    if (ROOT/'FREEZE.json').exists():
        verify_freeze()
        print('Existing frozen package hashes verified; no model execution.')
        return read(ROOT/'audit/PRELAUNCH.json')
    manifest=read(ROOT/'manifest.json');assert manifest['experiment_id']==CONFIG['experiment_id']
    assert manifest['held_out_inference_started'] is False and manifest['model_calls']==0
    assert len(manifest['rows'])==450
    budget=read(ROOT/'development/QUERY_INDEPENDENT_BUDGET.json')
    assert budget['B']==CONFIG['B']==4025
    assert budget['vision']==3844 and budget['empty_optical_nonvision']==53 and budget['future_query_reserve']==128
    assert budget['question_used']=='' and budget['model_calls']==0
    assert len({(r['case_id'],r['arm']) for r in manifest['rows']})==450
    assert len({r['case_id'] for r in manifest['rows']})==150
    audits={}
    for split in ('dev','smoke','eval'):
        path=ROOT/'audit'/f'{split}_INPUT_AUDIT.json';a=read(path)
        assert a['status']=='passed' and a['model_calls']==0 and a['weights_loaded'] is False
        assert a['inputs']==(450 if split=='eval' else 9)
        mpath=ROOT/('manifest.json' if split=='eval' else f'manifest_{split}.json')
        assert a['manifest_sha256']==sha(mpath)
        audits[split]=sha(path)
    counter=read(ROOT/'audit/COUNTER_CONFORMANCE.json');assert counter['status']=='passed' and counter['differences']==0 and counter['model_calls']==0
    test=read(ROOT/'audit/TESTS.json');assert test['exit_code']==0 and test['synthetic_only'] is True
    assert (ROOT/'PROTOCOL.md').read_bytes()==(ROOT/'FINAL_EXPERIMENT_PROTOCOL.md').read_bytes()
    for folder in ('outputs/raw','outputs/scored','analysis','figures'):
        path=ROOT/folder;path.mkdir(parents=True,exist_ok=True)
        assert not any(p.is_file() for p in path.rglob('*')), 'Held-out result area is not empty: '+folder
    assert not (ROOT/'APPROVAL.json').exists(), 'Preparation must not create approval'
    capacity=read(ROOT/'development/CAPACITY_REPORT.json')
    gains=[c['relative_capacity_gain'] for c in capacity['case_results']]
    assert len(gains)==3 and min(gains)>0 and sum(gains)/3>=.15 and capacity['model_calls']==0
    for row in manifest['rows']:
        folder=ROOT/row['path']
        assert folder.resolve().is_relative_to((ROOT/'inputs/eval').resolve())
        assert sha(folder/'REQUEST.json')==row['request_sha256']
        assert sha(folder/'MEASUREMENT.json')==row['measurement_sha256']
    result={'status':'passed','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'experiment_id':CONFIG['experiment_id'],'held_out_inference_started':False,'model_calls':0,
            'weights_loaded':False,'held_out_cases':150,'held_out_inputs':450,'independent_native_audit_sha256':audits,
            'test_report_sha256':sha(ROOT/'audit/TESTS.json'),'protocol_sha256':sha(ROOT/'PROTOCOL.md'),
            'manifest_sha256':sha(ROOT/'manifest.json'),'approval_exists':False,
            'scope':'CPU source/storage/render/processor reconstruction and synthetic code tests; future GPU remains unallocated'}
    put(ROOT/'audit/PRELAUNCH.json',result)
    print('Prelaunch audit passed. No approval exists; no inference started.')
    return result

def results(raw_root):
    freeze=verify_freeze();manifest=read(ROOT/'manifest.json');freeze_sha=sha(ROOT/'FREEZE.json')
    from run_inference import schedule_rows, committed_prefix, consumed_seconds, validate_raw
    schedule=schedule_rows(manifest,CONFIG)
    assert raw_root.resolve()==(ROOT/'outputs/raw').resolve()
    assert read(raw_root/'ORDER.json')==schedule
    start=read(raw_root/'RUN_START.json');complete=read(raw_root/'RUN_COMPLETE.json')
    assert start['experiment_id']==CONFIG['experiment_id'] and start['freeze_sha256']==freeze_sha
    assert start['max_calls']==450 and start['max_gpu_seconds']==7200
    assert complete=={**start,'generation_invocations':450,'status':'complete-unscored'}
    assert committed_prefix(raw_root,schedule,ROOT,CONFIG,freeze_sha)==450
    assert consumed_seconds(raw_root)<=7200
    env=read(raw_root/'ENVIRONMENT.json')
    assert env['revision']==CONFIG['model_revision'] and env['torch']=='2.10.0+cu128' and env['transformers']=='5.3.0'
    assert env['attention']=='sdpa' and env['dtype']=='bfloat16' and env['thinking'] is False
    for key,value in {'do_sample':False,'num_beams':1,'max_new_tokens':64,'use_cache':True,'disable_compile':True}.items():
        assert env['generation'][key]==value
    assert 'A100' in env['gpu'] and 38*1024**3<env['gpu_total_memory']<42*1024**3
    processor=load_processor();records=[]
    for index,row in enumerate(schedule):
        folder=raw_root/f"{index:04d}--{row['case_id']}--{row['arm']}"
        raw=read(folder/'RAW.json');measurement=read(ROOT/row['path']/'MEASUREMENT.json')
        validate_raw(raw,row,CONFIG,row['request_sha256'],row['measurement_sha256'])
        journal=[json.loads(line) for line in (folder/'TOKENS.jsonl').read_text().splitlines()]
        validate_journal(journal,measurement['input_token_ids'],raw['generated_token_ids'])
        for key,skip in [('prediction',True),('decoded_with_special_tokens',False)]:
            assert processor.tokenizer.decode(raw['generated_token_ids'],skip_special_tokens=skip,clean_up_tokenization_spaces=False)==raw[key]
        records.append({'path':folder.relative_to(raw_root).as_posix(),'row':row,'raw_sha256':sha(folder/'RAW.json'),
                        'complete_sha256':sha(folder/'COMPLETE.json')})
    assert len(list(raw_root.glob('*/RAW.json')))==450
    result={'status':'passed','freeze_sha256':freeze_sha,'raw_root':str(raw_root.resolve()),'records':records,
            'calls':450,'case_count':150,'decoded_journal_verified':True,'model_calls_by_auditor':0}
    put(ROOT/'audit/RESULT_AUDIT.json',result)
    print('All 450 outputs independently audited; no new inference.')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prelaunch',action='store_true');g.add_argument('--results',action='store_true')
    p.add_argument('--raw',type=Path,default=ROOT/'outputs/raw');a=p.parse_args()
    prelaunch() if a.prelaunch else results(a.raw)
