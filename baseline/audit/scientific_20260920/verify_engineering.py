"""Engineering evidence integrity only; never pooled with performance studies."""
import hashlib,io,json,pathlib,sys,zipfile
from tokenizers import Tokenizer
ROOT=pathlib.Path(__file__).resolve().parents[3]; OUT=pathlib.Path(__file__).resolve().parent
qt=Tokenizer.from_file(str(ROOT/'iclr/stage04c_identifier_amended_20260913/tokenizer/tokenizer.json'))
gt=Tokenizer.from_file(str(OUT/'glm_tokenizer.json'))
def sha(b):return hashlib.sha256(b).hexdigest()
def decode(raw,t):
 ids=raw['generated_token_ids']
 assert t.decode(ids,skip_special_tokens=True)==raw['prediction']
 assert t.decode(ids,skip_special_tokens=False)==raw['decoded_with_special_tokens']
def journal(blob,raw):
 a=[json.loads(x) for x in blob.decode().splitlines()]
 assert [v for line in a[1:] for v in line]==raw['generated_token_ids']
 return a[0][0]
report={'status':'passed','role':'development-only','smoke':[]}
for folder,h,t in [('qwen2b_completed_bbb2e90e12d88921','bbb2e90e12d889210ff10cb6642c99265714da387e216685ed390074c06a2a68',qt),('qwen9b_completed_16347f7526a56430','16347f7526a5643090b4b054ac57a50a8ac26420b4fc945b4ca9acac66ed7203',qt),('glm_completed_24ac5ca3c5221a4b','24ac5ca3c5221a4bb2706cd7d1d760b526a62eed900a5e7f32eda336b69aacfe',gt)]:
 d=ROOT/'iclr/checkpoints'/folder;p=d/'RETURNED_CHECKPOINT.zip';assert sha(p.read_bytes())==h
 val=json.loads((d/'LOCAL_VALIDATION.json').read_text());assert val['validation_passed'] and not val['errors']
 with zipfile.ZipFile(p) as z:
  files=json.loads(z.read('CHECKPOINT_MANIFEST.json'))['files']
  assert {x['path'] for x in files}==set(z.namelist())-{'CHECKPOINT_MANIFEST.json'}
  for f in files:
   b=z.read(f['path']);assert len(b)==f['bytes'] and sha(b)==f['sha256']
  for row in val['rows']:
   prefix='attempts/'+row['key']+'/'
   b=z.read(prefix+'RAW.json');assert sha(b)==row['raw_sha256'];raw=json.loads(b);decode(raw,t)
   inp=journal(z.read(prefix+'TOKENS.jsonl'),raw);res=json.loads(z.read(prefix+'RESULT.json'))
   assert len(inp)==res['total_input_tokens']==res['vision_tokens']+res['nonvision_input_tokens']
   assert res['generation_s']==row['generation_s']
  assert len(val['rows'])==76
 report['smoke'].append({'archive':str(p),'sha256':h,'verified_manifest_files':len(files),'rows':76,'exact_token_decodes':76,'exact_output_journals':76,'input_count_checks':76,'score_scope':'Historical local scoring report retained; development score labels not independently regenerated here.'})
p=ROOT/'iclr/checkpoints/timing26_40dec17635f64c08/ICLR-Timing26-Checkpoint.zip';h=sha(p.read_bytes());assert h=='40dec17635f64c08b83f8729691124f12d8157795fff8a5bea78ca6b0e503c2c'
with zipfile.ZipFile(p) as z:
 eng=json.loads(z.read('TIMING_ENGINEERING.json'));private=z.read('BLINDED_DO_NOT_OPEN.zip');assert sha(private)==eng['blinded_archive_sha256']
 with zipfile.ZipFile(io.BytesIO(private)) as q:
  ix=json.loads(q.read('PRIVATE_INDEX.json'));assert len({v['path'] for v in ix})==len(ix)
  assert {v['member'] for v in ix}==set(q.namelist())-{'PRIVATE_INDEX.json'}
  blobs={}
  for v in ix:
   b=q.read(v['member']);assert sha(b)==v['sha256'];blobs[v['path']]=b
  times=[]
  for i in range(26):
   row=eng[f'TIMING_{i:03}.json'];prefix=f'probe_{i:03}/';raw=json.loads(blobs[prefix+'RAW.json']);decode(raw,qt)
   inp=journal(blobs[prefix+'TOKENS.jsonl'],raw);a=json.loads(blobs[prefix+'INPUT.json']);m=a['measurement']
   assert inp==m['input_token_ids']
   assert len(inp)==m['total_input_tokens']==row['total_input_tokens']==m['vision_tokens']+m['nonvision_input_tokens']
   assert abs(row['total_row_s']-row['generation_s']-row['preprocess_transfer_s'])<1e-8
   assert abs(m['total_input_tokens']/a['profile']['total_input_tokens']-1)<=.05
   times.append(row)
  assert eng['COMPLETE.json']['calls']==26
report['timing']={'archive':str(p),'sha256':h,'rows':26,'verified_private_files':len(ix),'exact_token_decodes':26,'exact_input_and_output_journals':26,'timing_arithmetic_checks':26,'input_shape_matching_within_5_percent':True,'total_row_s':sum(x['total_row_s'] for x in times),'cap_hits':sum(x['output_cap_hit'] for x in times),'first_cell_to_first_call_s':times[0]['elapsed_since_first_cell_before_row_s'],'elapsed_since_first_cell_s':eng['elapsed_since_first_cell_s'],'limitation':'Synthetic timing fixtures; no accuracy inference or population-wide latency/energy comparison.'}
(OUT/'ENGINEERING_REAUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print('Passed: 228 smoke rows and 26 timing rows; hashes, decodes, journals, and timing arithmetic')
