"""Synthetic temporary approval fixtures never authorize the actual experiment."""
import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_inference as runner

REAL_ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((REAL_ROOT/'config.json').read_text())

def fixture(tmp_path):
    root=tmp_path/'SYNTHETIC-NOT-AN-EVALUATION';root.mkdir()
    (root/'config.json').write_text(json.dumps(CONFIG))
    (root/'PROTOCOL.md').write_text('invented protocol fixture')
    (root/'FREEZE.json').write_text('{}')
    approval={'experiment_id':CONFIG['experiment_id'],'protocol_sha256':runner.file_sha(root/'PROTOCOL.md'),
              'freeze_sha256':runner.file_sha(root/'FREEZE.json'),'approved':True,'approved_by':'user','max_calls':450}
    path=root/'synthetic_approval.json';path.write_text(json.dumps(approval))
    return root,path,approval

def manifest():
    rows=[{'case_id':f'fixture-{i:03}','arm':arm,'path':f'inputs/fixture-{i:03}/{arm}',
           'request_sha256':'x','measurement_sha256':'y'} for i in range(150) for arm in CONFIG['arms']]
    return {'experiment_id':CONFIG['experiment_id'],'rows':rows}

def test_no_approval_fails_before_outputs_or_model_import(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    with pytest.raises(RuntimeError,match='approval file'):runner.run(None,None)
    assert not list(tmp_path.iterdir())

def test_approval_is_bound_to_exact_freeze(tmp_path):
    root,path,a=fixture(tmp_path);runner.approval_gate(root,path)
    (root/'FREEZE.json').write_text('{"changed":true}')
    with pytest.raises(RuntimeError,match='freeze_sha256'):runner.approval_gate(root,path)

@pytest.mark.parametrize('key,value',[('approved',1),('approved_by','assistant'),('max_calls',451),('max_calls',450.0),('protocol_sha256','wrong')])
def test_invalid_approval_rejected(tmp_path,key,value):
    root,path,a=fixture(tmp_path);a[key]=value;path.write_text(json.dumps(a))
    with pytest.raises(RuntimeError):runner.approval_gate(root,path)

def test_schedule_is_paired_balanced_and_deterministic():
    rows=runner.schedule_rows(manifest(),CONFIG)
    assert rows==runner.schedule_rows(manifest(),CONFIG) and len(rows)==450
    for i in range(0,450,3):
        assert len({r['case_id'] for r in rows[i:i+3]})==1
        assert {r['arm'] for r in rows[i:i+3]}==set(CONFIG['arms'])
    for pos in range(3):
        assert all(sum(r['arm']==arm for r in rows[pos::3])==50 for arm in CONFIG['arms'])

def test_incomplete_design_and_path_escape_fail(tmp_path):
    m=manifest();m['rows'][-1]=copy.deepcopy(m['rows'][0])
    with pytest.raises(RuntimeError):runner.schedule_rows(m,CONFIG)
    with pytest.raises(RuntimeError):runner.input_folder(tmp_path,{'path':'../escape'})

def test_uncertain_invocation_cannot_be_retried(tmp_path):
    schedule=runner.schedule_rows(manifest(),CONFIG);row=schedule[0]
    folder=tmp_path/f"0000--{row['case_id']}--{row['arm']}";folder.mkdir()
    (folder/'START.json').write_text('{}')
    with pytest.raises(RuntimeError,match='Uncertain/incomplete'):runner.committed_prefix(tmp_path,schedule,tmp_path,CONFIG,'freeze')

def test_raw_schema_rejects_invalid_tokens_cap_and_identity():
    row=manifest()['rows'][0]
    raw={'experiment_id':CONFIG['experiment_id'],'case_id':row['case_id'],'arm':row['arm'],
         'request_sha256':'x','measurement_sha256':'y','generated_token_ids':[1],
         'prediction':'','decoded_with_special_tokens':'<eos>','cap_hit':False}
    runner.validate_raw(raw,row,CONFIG,'x','y')
    for key,value in [('generated_token_ids',[]),('generated_token_ids',[True]),('cap_hit',True),('arm','other')]:
        bad={**raw,key:value}
        with pytest.raises(RuntimeError):runner.validate_raw(bad,row,CONFIG,'x','y')

def test_no_real_approval_or_results_exist():
    assert not (REAL_ROOT/'APPROVAL.json').exists()
