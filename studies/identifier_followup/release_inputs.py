"""Independent structural review of a returned CPU checkpoint. No inference."""
import argparse,pathlib,math
from core import D,read,put,sha,verify_files,plan

def validate(prepared):
 p=read(D/'PROTOCOL.json');freeze=read(prepared/'INPUT_FREEZE.json');verify_files(D,read(D/'DEV_FREEZE.json')['files']);verify_files(prepared,freeze['files'])
 if freeze['dev_freeze_sha256']!=sha(D/'DEV_FREEZE.json') or freeze['protocol_sha256']!=sha(D/'PROTOCOL.json') or freeze['status']!='all-inputs-verified-no-inference':raise ValueError('Wrong source freeze')
 stage=freeze['stage']
 if stage=='cap':
  if freeze['cap_protocol_sha256']!=sha(D/'CAP_PROTOCOL.json') or len(freeze['rows'])!=247:raise ValueError('Cap inventory differs')
  return freeze
 if stage not in ['dev','eval']:raise ValueError('Unknown stage')
 cases={c['id']:c for c in (read(q) for q in sorted((D/'cases'/stage).glob('*.json')))}
 readers=['Qwen2B'] if stage=='dev' else list(p['models']);arms=p['layouts'] if stage=='dev' else p['eval_arms']
 expected={(r,c,a) for r in readers for c in cases for a in arms};rows=freeze['rows']
 if len(rows)!=len(expected) or freeze['expected_calls']!=len(expected) or {(r['reader'],r['case_id'],r['arm']) for r in rows}!=expected:raise ValueError('Incomplete input inventory')
 listed={f['path'] for f in freeze['files']};lookup={};selected=None
 if stage=='eval':
  selection=read(prepared/'SELECTION.json')
  if sha(prepared/'SELECTION.json')!=freeze['selection_sha256'] or selection['status']!='development-verified' or selection['dev_freeze_sha256']!=sha(D/'DEV_FREEZE.json') or selection['verified_rows']!=36:raise ValueError('Selection provenance differs')
  selected=selection['selected_layout']
 for row in rows:
  folder=prepared/row['path'];req=read(folder/'REQUEST.json');m=read(folder/'MEASUREMENT.json');case=cases[row['case_id']];arm=row['arm']
  if not folder.resolve().is_relative_to(prepared.resolve()):raise ValueError('Escaping row path')
  for name,key in [('REQUEST.json','request_sha256'),('MEASUREMENT.json','measurement_sha256')]:
   if (row['path']+'/'+name) not in listed or sha(folder/name)!=row[key]:raise ValueError('Unbound row file')
  if any(req[k]!=v for k,v in [('reader',row['reader']),('case_id',row['case_id']),('arm',arm),('model',p['models'][row['reader']]),('memory',case['memory']),('question',case['question']),('max_new_tokens',64)]):raise ValueError('Source or request changed')
  if m['total_input_tokens']!=len(m['input_token_ids']) or m['total_input_tokens']+64>m['native_context_limit']:raise ValueError('Context accounting differs')
  if m['vision_tokens']+m['nonvision_input_tokens']!=m['total_input_tokens']:raise ValueError('Token sum differs')
  if arm=='full_raw':
   if req['images'] or m['vision_tokens']:raise ValueError('Raw arm contains images')
  else:
   if req['images']!=[f'page_{i:03}.png' for i in range(4)]:raise ValueError('Image inventory differs')
   for name in req['images']:
    if (row['path']+'/'+name) not in listed:raise ValueError('Unbound image')
   layout=arm if stage=='dev' else ('original' if arm=='original_c2_p4' else selected)
   original=plan(case['memory'],layout);g=req['geometry']
   if any(g[k]!=v for k,v in original.items()):raise ValueError('Geometry/source coverage differs')
   if arm=='readable_p4':
    if min(g['effective_font_em_pixels'])<16 or min(g['minimum_ascii_alphanumeric_height_pixels'])<10:raise ValueError('Readable control fails')
   elif abs(m['source_text_tokens']/m['vision_tokens']/2-1)>.10:raise ValueError('C2 budget fails')
  lookup[row['reader'],row['case_id'],arm]=m
 if stage=='eval':
  for reader in readers:
   for case in cases:
    a=lookup[reader,case,'original_c2_p4'];b=lookup[reader,case,'efficient_c2_p4'];c=lookup[reader,case,'readable_p4']
    for key in ['source_text_tokens','vision_tokens','nonvision_input_tokens','total_input_tokens','input_token_ids','image_grid_thw']:
     if a[key]!=b[key]:raise ValueError('Matched-budget contrast fails: '+key)
    if c['vision_tokens']<=b['vision_tokens']:raise ValueError('Readable control not expanded')
 return freeze

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--prepared',type=pathlib.Path,required=True);parser.add_argument('--review-note',required=True,help='Record completed independent visual/native review; this program alone is not that review');args=parser.parse_args()
 freeze=validate(args.prepared)
 put(args.prepared/'INPUT_RELEASE.json',{'status':'verified-for-inference','input_freeze_sha256':sha(args.prepared/'INPUT_FREEZE.json'),'dev_freeze_sha256':sha(D/'DEV_FREEZE.json'),'stage':freeze['stage'],'review_note':args.review_note})
 print('Release written; retain the review note and original CPU checkpoint.')
