"""Independent span/pixel/inventory auditor; native tensor audit is optional only locally."""
import argparse,pathlib,math,hashlib
from common import *
from cases import retain
from PIL import Image,ImageDraw
def independent_render(g,side,scale):
 out=[]
 for page in g['pages']:
  im=Image.new('RGB',(g['base_side'],g['base_side']),'white');draw=ImageDraw.Draw(im)
  for line in page['lines']:draw.text((line['x'],line['baseline_y']),line['text'],font=font(),anchor='ls',fill='black')
  n=round(side*scale);small=im.resize((n,n),Image.Resampling.LANCZOS);canvas=Image.new('RGB',(side,side),'white');offset=(side-n)//2;canvas.paste(small,(offset,offset));out.append(canvas);im.close();small.close()
 return out
def audit(prepared,assets=None):
 verify_source();allf=read(prepared/'ALL_INPUTS.json');assert allf['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
 processors={};configs={}
 if assets:
  from transformers import AutoProcessor
  for reader,model in read(LEGACY/'PROTOCOL.json')['models'].items():
   p=assets/model.replace('/','--');processors[reader]=AutoProcessor.from_pretrained(p,local_files_only=True,trust_remote_code=False,use_fast=True);configs[reader]=read(p/'config.json')
 counts={};look={};native=0;pages=0
 for study,expected in zip(STUDIES,[540,288,45]):
  f=read(prepared/study/'FREEZE.json');assert sha(prepared/study/'FREEZE.json')==allf['freeze_hashes'][study];verify_files(prepared/study,f['files'])
  assert f['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json') and f['protocol_sha256']==sha(ROOT/study/'PROTOCOL.md')
  rows=f['rows'];assert len(rows)==expected and len({(r['reader'],r['case_id'],r['arm']) for r in rows})==expected
  for r in rows:
   folder=prepared/r['path'];req=read(folder/'REQUEST.json');m=read(folder/'MEASUREMENT.json')
   assert sha(folder/'REQUEST.json')==r['request_sha256'] and sha(folder/'MEASUREMENT.json')==r['measurement_sha256']
   assert all(req[k]==r[k] for k in ['reader','case_id','arm'])
   case_study=STUDIES[0] if study==STUDIES[2] else study;c=read(prepared/case_study/'cases'/(r['case_id']+'.json'))
   assert digest(c['memory'])==req['full_source_sha256'] and digest(req['memory'])==req['inference_source_sha256'] and req['question']==c['question']
   assert req['accounting']['total_input_tokens']==len(m['input_token_ids'])==m['vision_tokens']+m['nonvision_input_tokens']
   assert m['vision_tokens']==sum(math.prod(g)//m['merge_size']**2 for g in m['image_grid_thw'])
   if study==STUDIES[0]:
    b=f['budgets'][r['reader']]['B'];assert m['total_input_tokens']<=b
    if r['arm']=='text':
     lines=req['memory'].splitlines();assert len(lines)==len(set(lines)) and all(x in c['records'] for x in lines)
     assert lines==[x for x in c['records'] if x in set(lines)]
     assert req['diagnostics']['target_record_retained']==(c['target_record'] in lines)
    else:assert req['memory']==c['memory']
   if req['images']:
    geom=req['geometry'];g=geom['layout'];cursor=0
    for page in g['pages']:
     assert page['source_start']==cursor
     for l in page['lines']:
      assert l['start']==cursor and l['text']==c['memory'][l['start']:l['end']].replace('\n',' ');cursor=l['end']
      assert 0<=l['bbox'][0]<l['bbox'][2]<=g['base_side'] and 0<=l['bbox'][1]<l['bbox'][3]<=g['base_side']
     assert cursor==page['source_end']
    assert cursor==len(c['memory'])
    ims=independent_render(g,geom['final_side'],geom['scale'])
    for name,im in zip(req['images'],ims):
     with Image.open(folder/name) as actual:assert actual.size==im.size and actual.convert('RGB').tobytes()==im.tobytes(),'pixel mismatch'
     im.close();pages+=1
   if assets:
    processor=processors[r['reader']];ims=[Image.open(folder/n).convert('RGB') for n in req['images']]
    batch=processor(text=[m['rendered_chat']],images=ims or None,return_tensors='pt',padding=False);tensor_check(batch,m);native+=1
    assert chat(processor,req['memory'],req['question'],ims)==m['rendered_chat']
    if study==STUDIES[0] and r['arm']=='text':
     b=f['budgets'][r['reader']]['B'];packed=c['memory'] if text_count(processor,c['memory'],c['question'])<=b else retain(c['records'],c['base_id'],lambda s:text_count(processor,s,c['question'])<=b)[0]
     assert packed==req['memory'],'packing changed'
    for im in ims:im.close()
    del batch
   look[study,r['reader'],r['case_id'],r['arm']]=(req,m)
  counts[study]=len(rows)
 for reader in READERS:
  for i in range(32):
   rr=[look[STUDIES[1],reader,f'geometry-{i:03}',f'scale_{s:.2f}'] for s in [.55,.75,1.]]
   for req,m in rr[1:]:
    for k in ['input_token_ids','image_grid_thw','nonvision_input_tokens','vision_tokens','total_input_tokens']:assert m[k]==rr[0][1][k]
    assert req['geometry']['layout']==rr[0][0]['geometry']['layout']
   assert len({digest(str(req['geometry']['pages'])) for req,m in rr})==3
  for regime in ['short','medium','long']:
   for orig,prof in [('text','B_text'),('optical','B_optical')]:
    q,m=look[STUDIES[0],reader,f'cross-000-{regime}',orig];qq,mm=look[STUDIES[2],reader,f'cross-000-{regime}',prof]
    assert q['memory']==qq['memory'] and q['geometry']==qq['geometry']
    for k in ['input_token_ids','tensor_inventory']:assert m[k]==mm[k]
 return {'status':'passed','unique_inputs':counts,'native_tensor_rechecks':native,'pixel_exact_pages':pages,'scope':'all inputs, spans, pixels, budgets, pairing; native tensors checked only when assets provided','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'freeze_hashes':allf['freeze_hashes']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=pathlib.Path,required=True);p.add_argument('--assets',type=pathlib.Path);p.add_argument('--report',type=pathlib.Path,required=True);a=p.parse_args();put(a.report,audit(a.prepared,a.assets))
