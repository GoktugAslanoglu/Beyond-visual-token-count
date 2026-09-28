"""Pinned native CPU preparation. No model weights or inference imports."""
import argparse,gc,math,pathlib
from PIL import Image
from core import D,read,put,sha,plan,render,package_files,verify_files,font
from vendor.processor_measure import measure

def main(stage,assets,output,selection=None):
 import torch,transformers
 from transformers import AutoProcessor
 if transformers.__version__!='5.3.0' or not torch.__version__.startswith('2.10.0'):raise RuntimeError('Pinned native processor environment required')
 protocol=read(D/'PROTOCOL.json');freeze=read(D/'DEV_FREEZE.json');verify_files(D,freeze['files'])
 if output.exists():raise RuntimeError('Preserve existing preparation; use a new directory after review')
 output.mkdir(parents=True);rows=[];selection_data=None
 if stage=='eval':
  if selection is None:raise RuntimeError('Audited development selection required')
  selection_data=read(selection)
  if selection_data.get('status')!='development-verified' or selection_data['dev_freeze_sha256']!=sha(D/'DEV_FREEZE.json'):raise RuntimeError('Unverified development selection')
  chosen=selection_data['selected_layout']
  if chosen not in protocol['layouts']:raise RuntimeError('Unknown selected layout')
  put(output/'SELECTION.json',selection_data)
 models=['Qwen2B'] if stage=='dev' else list(protocol['models'])
 cases=[read(p) for p in sorted((D/'cases'/stage).glob('*.json'))];expected=36 if stage=='dev' else 576
 for label in models:
  model=protocol['models'][label];asset=assets/model.replace('/','--');config=read(asset/'config.json')
  for ref in read(D/'environment/ASSET_PINS.json'):
   if ref['model']==model:
    p=asset/ref['file']
    if p.stat().st_size!=ref['bytes'] or sha(p)!=ref['sha256']:raise RuntimeError('Processor asset differs')
  processor=AutoProcessor.from_pretrained(asset,local_files_only=True,trust_remote_code=False,use_fast=True)
  patch=int(processor.image_processor.patch_size);merge=int(processor.image_processor.merge_size);cache={}
  def shape(side):
   if side not in cache:
    im=Image.new('RGB',(side,side),'white')
    b=processor.image_processor(images=[im],return_tensors='pt');grid=b['image_grid_thw'].tolist()[0];im.close()
    cache[side]={'grid':grid,'vision':4*math.prod(grid)//merge**2,'processor_side':grid[1]*patch};del b;gc.collect()
   return cache[side]
  for index,case in enumerate(cases):
   source=len(processor.tokenizer.encode(case['memory'],add_special_tokens=False,truncation=False,padding=False))
   nominal=math.sqrt(source/8)*patch*merge
   sides=[s for s in range(224,4090,28) if abs(s-nominal)<=140]
   trials=[dict(side=s,**shape(s)) for s in sides]
   valid=[x for x in trials if abs(source/x['vision']/2-1)<=.10]
   if not valid:raise RuntimeError('No C2 side passes native budget; stop entire stage')
   best=min(valid,key=lambda x:(abs(source/x['vision']/2-1),x['side']));cside=best['side']
   arms=protocol['layouts'] if stage=='dev' else protocol['eval_arms'];measurements={}
   for arm in arms:
    folder=output/'requests'/label/case['id']/arm;folder.mkdir(parents=True)
    images=[];geometry=None;side=None
    if arm!='full_raw':
     layout_id=arm if stage=='dev' else ('original' if arm=='original_c2_p4' else chosen)
     geometry=plan(case['memory'],layout_id);side=cside
     if arm=='readable_p4':
      minheight=min(font().getbbox(c,anchor='ls')[3]-font().getbbox(c,anchor='ls')[1] for c in '0123456789abcdefghijklmnopqrstuvwxyz')
      side=None
      for s in range(224,4090,28):
       if s<=cside:continue
       scaled=shape(s)['processor_side']/geometry['base_side']
       if 12*scaled>=16 and minheight*scaled>=10 and shape(s)['vision']>best['vision']:
        side=s;break
      if side is None:raise RuntimeError('Positive-control geometry infeasible; no evaluation inference allowed')
     images=render(geometry,side)
    m=measure(processor,config,case['memory'],case['question'],images)
    if m['total_input_tokens']+64>m['native_context_limit']:raise RuntimeError('Native context failure')
    if images:
     if arm!='readable_p4' and (m['vision_tokens']!=best['vision'] or abs(m['source_to_vision_ratio']/2-1)>.10):raise RuntimeError('Actual image budget differs')
     geometry['final_side']=side;geometry['effective_font_em_pixels']=[12*g[1]*patch/geometry['base_side'] for g in m['image_grid_thw']]
     geometry['minimum_ascii_alphanumeric_height_pixels']=[min(font().getbbox(c,anchor='ls')[3]-font().getbbox(c,anchor='ls')[1] for c in '0123456789abcdefghijklmnopqrstuvwxyz')*g[1]*patch/geometry['base_side'] for g in m['image_grid_thw']]
     if arm=='readable_p4' and (min(geometry['effective_font_em_pixels'])<16 or min(geometry['minimum_ascii_alphanumeric_height_pixels'])<10):raise RuntimeError('Actual positive-control legibility check failed')
     for i,im in enumerate(images):im.save(folder/f'page_{i:03}.png');im.close()
    put(folder/'MEASUREMENT.json',m);put(folder/'REQUEST.json',{'case_id':case['id'],'model':model,'reader':label,'arm':arm,'memory':case['memory'],'question':case['question'],'source_sha256':geometry['source_sha256'] if geometry else __import__('hashlib').sha256(case['memory'].encode()).hexdigest(),'images':[f'page_{i:03}.png' for i in range(4)] if images else [],'geometry':geometry,'measurement':'MEASUREMENT.json','max_new_tokens':64})
    rel=folder.relative_to(output).as_posix();rows.append(dict(reader=label,case_id=case['id'],arm=arm,path=rel,request_sha256=sha(folder/'REQUEST.json'),measurement_sha256=sha(folder/'MEASUREMENT.json')));measurements[arm]=m
   if stage=='eval':
    orig=measurements['original_c2_p4'];eff=measurements['efficient_c2_p4']
    for name in ['source_text_tokens','vision_tokens','nonvision_input_tokens','total_input_tokens','image_grid_thw','input_token_ids']:
     if orig[name]!=eff[name]:raise RuntimeError('Exact C2 input-budget match failed: '+name)
   print(label,stage,'CPU cases',index+1,'/',len(cases),flush=True)
  del processor;gc.collect()
 if len(rows)!=expected:raise RuntimeError('Incomplete preparation')
 manifest={'status':'all-inputs-verified-no-inference','stage':stage,'rows':rows,'expected_calls':expected,'dev_freeze_sha256':sha(D/'DEV_FREEZE.json'),'protocol_sha256':sha(D/'PROTOCOL.json'),'selection_sha256':sha(output/'SELECTION.json') if selection_data else None,'files':package_files(output)}
 put(output/'INPUT_FREEZE.json',manifest)
 print('CPU preparation complete; return the checkpoint for review. No GPU calls.',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['dev','eval'],required=True);p.add_argument('--assets',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--selection',type=pathlib.Path);a=p.parse_args();main(a.stage,a.assets,a.output,a.selection)
