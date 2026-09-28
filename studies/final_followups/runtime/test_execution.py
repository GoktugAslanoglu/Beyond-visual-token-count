"""Synthetic execution-analysis tests; never scientific evidence."""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from audit_results_final import analyze_cross,analyze_geometry,analyze_systems,independent_score,expected_order,independently_check_signflip
from common import READERS
def row(reader,i,regime,arm,correct):
 return {'reader':reader,'base_id':f'case-{i:03}','case_id':f'case-{i:03}-{regime}','regime':regime,'arm':arm,'scores':{'containment':correct,'em':correct,'cer':1-correct,'literal_em':correct},'cap_hit':False,'diagnostics':{'normalized_source_length':{'short':.5,'medium':1.5,'long':2.}[regime],'target_record_retained':bool(correct)}}
def test_known_crossover_and_no_crossover():
 rows=[]
 for reader in READERS:
  for i in range(30):
   for regime in ['short','medium','long']:
    for arm in ['text','optical']:rows.append(row(reader,i,regime,arm,int((regime=='short' and arm=='text') or (regime=='long' and arm=='optical'))))
 a=analyze_cross(rows)
 for r in a['readers'].values():
  assert r['primary_interaction']['effect']==2. and r['descriptive_crossover'] and r['supported_long_optical_advantage']
 for r in rows:r['scores']={k:0 for k in r['scores']}
 a=analyze_cross(rows)
 assert all(not r['descriptive_crossover'] and r['primary_interaction']['p']==1 and r['both_long_collapse_flag'] for r in a['readers'].values())
def test_geometry_known_omnibus():
 rows=[]
 for reader in READERS:
  for i in range(32):
   for arm in ['scale_0.55','scale_0.75','scale_1.00']:
    r=row(reader,i,'short',arm,int(arm=='scale_1.00'));r['case_id']=f'case-{i:03}';rows.append(r)
 a=analyze_geometry(rows)
 assert all(r['primary']['holm_p']<.05 and r['table']['scale_1.00']['correct']==32 for r in a['readers'].values())
def test_independent_scoring_and_exact_arithmetic():
 assert independent_score('<|begin_of_box|> ABC <|end_of_box|>','ABC')['em']==1
 assert independent_score('prefix ABC','ABC')['em']==0
 assert independent_score('prefix ABC','ABC')['containment']==1
 assert independent_score('AXC','ABC')['cer']==1/3
 independently_check_signflip([2]*30,2/2**30)
def test_profile_schedule_counts_and_balance():
 rows=[{'case_id':'cross-000-'+regime,'arm':arm} for regime in ['short','medium','long'] for arm in ['A_full_text','A_optical_C2','A_optical_C4','B_text','B_optical']]
 order=expected_order(rows,'Qwen2B',True);assert len(order)==195
 assert all(phase=='warmup' for _,phase,_ in order[:45])
 for r in rows:
  assert sum(rr==r and phase=='measured' for rr,phase,_ in order)==10
  assert sum(rr==r and phase=='warmup' for rr,phase,_ in order)==3

def test_export_excludes_weights_preserves_failure(tmp_path):
 import zipfile
 from gpu_colab import archive
 for name in ['output/call/RAW.json','PRIVATE_RUN.log','materialized_snapshot/model.safetensors','environment/env/lib/package.py']:
  q=tmp_path/'work'/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('fixture')
 archive(tmp_path/'work',tmp_path/'checkpoint.zip')
 with zipfile.ZipFile(tmp_path/'checkpoint.zip') as z:assert set(z.namelist())=={'output/call/RAW.json','PRIVATE_RUN.log'}

def test_tensor_gate_detects_changed_input_and_pixels():
 import torch,hashlib,pytest
 from common import tensor_check
 batch={'input_ids':torch.tensor([[4,5]]),'pixel_values':torch.tensor([[1.,2.]])}
 m={'input_token_ids':[4,5],'tensor_inventory':{}}
 for k,v in batch.items():
  a=v.numpy();m['tensor_inventory'][k]={'shape':list(a.shape),'dtype':str(a.dtype),'sha256':hashlib.sha256(a.tobytes()).hexdigest()}
 tensor_check(batch,m)
 with pytest.raises(AssertionError):tensor_check(dict(batch,input_ids=torch.tensor([[4,6]])),m)
 with pytest.raises(AssertionError):tensor_check(dict(batch,pixel_values=torch.tensor([[1.,3.]])),m)
