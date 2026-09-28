"""Native CPU-only all-study preparation; model weights are never imported."""
import argparse,gc,math,pathlib,sys
from common import *
from cases import crossover,geometry,retain
from PIL import Image,ImageChops
SCALES=[.55,.75,1.]
def scaled_images(g,side,scale):
 # Rasterize once on the validated base canvas. Resize the complete page, including
 # its whitespace, then center on an identical white canvas. No reflow/cropping.
 base=render(g,g['base_side']);out=[]
 for im in base:
  size=max(1,round(side*scale));small=im.resize((size,size),Image.Resampling.LANCZOS);canvas=Image.new('RGB',(side,side),'white');offset=(side-size)//2;canvas.paste(small,(offset,offset));im.close();small.close();out.append(canvas)
 return out
def main(assets,dest):
 import torch,transformers
 from transformers import AutoProcessor
 from tokenizers import Tokenizer
 verify_source()
 assert transformers.__version__=='5.3.0' and torch.__version__=='2.10.0+cpu','Pinned CPU environment required'
 dest.mkdir(parents=True,exist_ok=False);put(dest/'ENVIRONMENT.json',environment())
 tokenizer=Tokenizer.from_file(str(LEGACY/'assets/reference_tokenizer.json'));tokenizer.no_padding();tokenizer.no_truncation();count=lambda s:len(tokenizer.encode(s,add_special_tokens=False).ids)
 cross=[c for i in range(30) for c in crossover(i,count)];geo=[geometry(i,count) for i in range(32)]
 for name,cases in [(STUDIES[0],cross),(STUDIES[1],geo)]:
  for c in cases:put(dest/name/'cases'/(c['id']+'.json'),c)
 rows={s:[] for s in STUDIES};budgets={};c4side={};models=read(LEGACY/'PROTOCOL.json')['models']
 def save(reader,study,case,arm,processor,config,images=None,g=None,memory=None,extra=None,side=None,scale=1.):
  memory=case['memory'] if memory is None else memory;images=images or []
  folder=dest/study/'inputs'/reader/case['id']/arm;folder.mkdir(parents=True)
  m=measure(processor,config,memory,case['question'],images);full_native=len(processor.tokenizer.encode(case['memory'],add_special_tokens=False));kept=len(processor.tokenizer.encode(memory,add_special_tokens=False))
  assert m['total_input_tokens']+64<=m['native_context_limit']
  if study==STUDIES[0]:assert m['total_input_tokens']<=budgets[reader]['B']
  # Exact aggregate is authoritative; source and prompt BPE counts are not
  # claimed to be an additive split when a token straddles their boundary.
  accounting={'source_native_tokens':full_native,'retained_source_native_tokens':kept,'vision_tokens':m['vision_tokens'],'text_input_tokens':m['nonvision_input_tokens'],'other_input_tokens':0,'total_input_tokens':m['total_input_tokens'],'note':'text_input_tokens includes chat/question/image boundary scaffolding; no disjoint source-vs-scaffolding BPE attribution','realized_C':full_native/m['vision_tokens'] if images else None}
  geom=None
  if images:
   geom={'layout':g,'final_side':side,'scale':scale,'resampling':'Pillow LANCZOS','pages':[]}
   for i,im in enumerate(images):
    bbox=ImageChops.difference(im,Image.new('RGB',im.size,'white')).getbbox()
    assert bbox and bbox[0]>0 and bbox[1]>0 and bbox[2]<side and bbox[3]<side,'ink clipping'
    ratio=m['image_grid_thw'][i][1]*m['patch_size']/g['base_side']*round(side*scale)/side
    geom['pages'].append({'ink_bbox':bbox,'text_bbox_width':bbox[2]-bbox[0],'text_bbox_height':bbox[3]-bbox[1],'width_utilization':(bbox[2]-bbox[0])/side,'height_utilization':(bbox[3]-bbox[1])/side,'effective_font_em_height':12*ratio,'smallest_ascii_bbox_height':min(font().getbbox(c,anchor='ls')[3]-font().getbbox(c,anchor='ls')[1] for c in '0123456789abcdefghijklmnopqrstuvwxyz')*ratio,'minimum_line_bbox_height':min(l['bbox'][3]-l['bbox'][1] for l in g['pages'][i]['lines'])*ratio,'realized_scale':round(side*scale)/side})
    im.save(folder/f'page_{i:03}.png');im.close()
  req={'study':study,'reader':reader,'case_id':case['id'],'base_id':case.get('base_id',case['id']),'regime':case.get('regime'),'arm':arm,'memory':memory,'full_source_sha256':digest(case['memory']),'inference_source_sha256':digest(memory),'question':case['question'],'images':[f'page_{i:03}.png' for i in range(len(images))],'geometry':geom,'accounting':accounting,'diagnostics':extra or {},'max_new_tokens':1 if study==STUDIES[2] else 64}
  put(folder/'REQUEST.json',req);put(folder/'MEASUREMENT.json',m)
  row={'reader':reader,'case_id':case['id'],'arm':arm,'path':folder.relative_to(dest).as_posix(),'request_sha256':sha(folder/'REQUEST.json'),'measurement_sha256':sha(folder/'MEASUREMENT.json')}
  rows[study].append(row);return req,m
 for reader in READERS:
  model=models[reader];asset=assets/model.replace('/','--')
  for r in read(LEGACY/'environment/ASSET_PINS.json'):
   if r['model']==model:assert sha(asset/r['file'])==r['sha256']
  processor=AutoProcessor.from_pretrained(asset,local_files_only=True,trust_remote_code=False,use_fast=True);config=read(asset/'config.json');side=SIDES[reader]
  # C2 budget is fixed at the already audited four-page side for each reader.
  # Question overhead calibration never generates answers.
  overhead=[];blank=[Image.new('RGB',(side,side),'white') for _ in range(4)]
  for c in cross[::3]:
   m=measure(processor,config,'',c['question'],blank);assert m['vision_tokens']==VISION[reader];overhead.append(m['nonvision_input_tokens'])
  for im in blank:im.close()
  budgets[reader]={'B':VISION[reader]+max(overhead),'vision_operating_point':VISION[reader],'side':side,'max_optical_nonvision':max(overhead)}
  # C4 for systems view A alone: same pre-existing renderer, source-specific side
  # selected by native processor geometry and a frozen nearest-rate rule.
  for ci,c in enumerate(cross):
   g=plan(c['memory'],'L3_fullwidth_wordwrap');b=budgets[reader]['B'];empty=text_count(processor,'',c['question']);native=len(processor.tokenizer.encode(c['memory'],add_special_tokens=False));ratio=native/(b-empty)
   bounds={'short':(0,.8),'medium':(1.1,1.8),'long':(1.8,2.5)}[c['regime']];assert bounds[0]<ratio<bounds[1],('length regime invalid',reader,c['id'],ratio)
   fullfits=text_count(processor,c['memory'],c['question'])<=b
   if c['regime']=='short':assert fullfits
   kept,indices=(c['memory'],list(range(len(c['records'])))) if fullfits else retain(c['records'],c['base_id'],lambda text:text_count(processor,text,c['question'])<=b)
   diag={'B':b,'available_text_budget':b-empty,'normalized_source_length':ratio,'target_record_retained':c['target_record'] in kept.splitlines(),'records_retained':len(indices),'source_records':len(c['records']),'fraction_records_retained':len(indices)/len(c['records']),'fraction_native_tokens_retained':len(processor.tokenizer.encode(kept,add_special_tokens=False))/native}
   save(reader,STUDIES[0],c,'text',processor,config,memory=kept,extra=diag)
   save(reader,STUDIES[0],c,'optical',processor,config,images=render(g,side),g=g,side=side,extra={'B':b,'normalized_source_length':ratio,'all_source_spans':True})
   if c['index']==0:
    for arm,mem,ims,gg,ss in [('A_full_text',c['memory'],[],None,None),('B_text',kept,[],None,None),('B_optical',c['memory'],render(g,side),g,side)]:
     save(reader,STUDIES[2],c,arm,processor,config,images=ims,g=gg,side=ss,memory=mem,extra={'representative_case':'cross-000','B':b,'normalized_source_length':ratio})
    patch=int(processor.image_processor.patch_size);merge=int(processor.image_processor.merge_size)
    for target_c in [2,4]:
     nominal=math.sqrt(native/(4*target_c))*patch*merge;trials=[]
     for s in range(224,2030,28):
      if abs(s-nominal)>112:continue
      im=Image.new('RGB',(s,s),'white');batch=processor.image_processor(images=[im],return_tensors='pt');v=4*math.prod(batch['image_grid_thw'].tolist()[0])//merge**2;im.close();trials.append((abs(native/v/target_c-1),s,v));del batch
     error,s,v=min(trials);assert error<=.15,'Systems rate geometry unavailable; stop before freeze'
     save(reader,STUDIES[2],c,f'A_optical_C{target_c}',processor,config,images=render(g,s),g=g,side=s,extra={'representative_case':'cross-000','target_C':target_c})
   print(reader,'crossover CPU',ci+1,'/90',flush=True)
  for ci,c in enumerate(geo):
   g=plan(c['memory'],'L3_fullwidth_wordwrap');ms=[]
   for scale in SCALES:
    req,m=save(reader,STUDIES[1],c,f'scale_{scale:.2f}',processor,config,images=scaled_images(g,side,scale),g=g,side=side,scale=scale);ms.append(m)
   for m in ms[1:]:
    for k in ['input_token_ids','image_grid_thw','vision_tokens','nonvision_input_tokens','total_input_tokens']:assert m[k]==ms[0][k],('geometry mismatch',k)
   print(reader,'geometry CPU',ci+1,'/32',flush=True)
  del processor;gc.collect()
 for study,expected in zip(STUDIES,[540,288,45]):
  assert len(rows[study])==expected
  d=dest/study
  # This is the final input freeze, written only after all three readers pass.
  put(d/'FREEZE.json',{'status':'all-inputs-sealed-no-model-outputs','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'protocol_sha256':sha(ROOT/study/'PROTOCOL.md'),'expected_unique_inputs':expected,'rows':rows[study],'budgets':budgets if study==STUDIES[0] else None,'environment_sha256':sha(dest/'ENVIRONMENT.json'),'files':package_files(d)})
 put(dest/'ALL_INPUTS.json',{'status':'CPU-complete-awaiting-independent-audit','quality_inputs':828,'systems_inputs':45,'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'freeze_hashes':{s:sha(dest/s/'FREEZE.json') for s in STUDIES}})
 print('ALL CPU INPUTS SEALED. Return checkpoint for independent audit. No model answers generated.',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--assets',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();main(a.assets,a.output)
