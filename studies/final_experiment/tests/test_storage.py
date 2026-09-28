import inspect
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from storage import pack,serialize,decode_compact,parse_record,rank_records,HEADER
RECORDS=[f'Record {chr(65+i)*10}: {1000000+i}' for i in range(20)]

def test_compact_roundtrip_preserves_every_stored_pair():
    indices=[0,3,5,19]
    assert decode_compact(serialize(RECORDS,indices,True))==[RECORDS[i] for i in indices]

def test_packer_does_not_accept_query_or_truth():
    assert not set(inspect.signature(pack).parameters)&{'question','query','target','answer','reference','target_key','target_position'}
    observed=[]
    memory,indices=pack(RECORDS,'fixture',lambda text:observed.append(text) or len(text),220,30,123,True)
    assert all(isinstance(x,str) and x.startswith(HEADER) for x in observed)
    assert len(memory)+30<=220 and decode_compact(memory)==[RECORDS[i] for i in indices]

def test_external_query_truth_annotations_cannot_change_storage():
    source={'records':RECORDS,'id':'fixture','question':'Question A','reference':'1000001'}
    before=pack(source['records'],source['id'],len,280,30,123,True)
    source.update(question='Entirely different query',reference='9999999',target_key='ZZZZZZZZZZ',target_position=0.99)
    assert before==pack(source['records'],source['id'],len,280,30,123,True)

def test_storage_determinism_and_source_order():
    args=(RECORDS,'fixture',len,280,30,123)
    assert pack(*args,True)==pack(*args,True)
    memory,indices=pack(*args,True);assert indices==sorted(indices)
    assert rank_records(RECORDS,'fixture',123)!=rank_records(RECORDS,'fixture',124)

def test_budget_boundary_is_inclusive():
    one=[RECORDS[0]];memory=serialize(one,[0],True)
    assert pack(one,'fixture',len,len(memory)+128,128,123,True)==(memory,[0])
    assert pack(one,'fixture',len,len(memory)+127,128,123,True)[1]==[]

def test_invalid_grammar_and_duplicate_indices_abort():
    with pytest.raises(ValueError):parse_record('Record A: answer')
    with pytest.raises(ValueError):serialize(RECORDS,[1,1],True)
    with pytest.raises(ValueError):serialize(RECORDS,[-1],True)
    with pytest.raises(ValueError):decode_compact('A=1234567')
    with pytest.raises(ValueError):pack(RECORDS,'fixture',len,10,128,123,True)

def test_adapter_rebinding_preserves_historical_seeds():
    from build_cases import generator_module
    module=generator_module(202609250102)
    import common
    assert module.SEEDS['crossover']==202609250102 and common.SEEDS['crossover']==202609230101

def test_dev_sources_reproduce_and_balance_positions():
    from build_cases import make_cases
    a=make_cases('dev');assert a==make_cases('dev') and len(a)==3
    assert {c['position'] for c in a}=={'early','middle','late'}
    assert all(c['seed']==202609250101 and c['regime']=='long' for c in a)
