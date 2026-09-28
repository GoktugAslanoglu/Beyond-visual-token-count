import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from score import score_answer

def test_native_containment_and_exact_remain_distinct():
    a=score_answer('The number is 1234567.','1234567')
    assert a['success']==1 and a['canonical_em']==0
    assert score_answer('1234568','1234567')['success']==0
    assert score_answer('No information available','1234567')['abstention']
    assert score_answer('', '1234567')['success']==0
    assert score_answer('012345678','1234567')['success']==1

def test_box_normalization_is_only_diagnostic():
    a=score_answer('<|begin_of_box|>1234567<|end_of_box|>','1234567')
    assert a['success']==1 and a['canonical_em']==1 and a['literal_em']==0

def test_capped_correct_response_is_not_excluded():
    assert score_answer('1234567 '+('x '*200),'1234567')['success']==1
