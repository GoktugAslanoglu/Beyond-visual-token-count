import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit import validate_journal

def test_journal_requires_exact_prompt_and_generated_ids():
    validate_journal([[[10,11]],[20],[21]],[10,11],[20,21])
    with pytest.raises(AssertionError):validate_journal([[[10,12]],[20]],[10,11],[20])
    with pytest.raises(AssertionError):validate_journal([[[10,11]],[22]],[10,11],[20])
    with pytest.raises(AssertionError):validate_journal([[[10,11]],[[20]]],[10,11],[20])
    with pytest.raises(AssertionError):validate_journal([[[10,11]],[True]],[10,11],[1])
