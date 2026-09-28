"""Final-round local GPU runner. Immutable requests, no scoring, no retries."""
import argparse,pathlib,os,time,random,json,gc,sys,hashlib
from common import *
def build_representation(req,c,processor):
 from prepare import scaled_images
 from cases import retain
 if req['images']:
  g=req['geometry'];return req['memory'],scaled_images(g['layout'],g['final_side'],g['scale'])
 if req['arm']=='B_text':
  b=req['diagnostics']['B'];memory=c['memory'] if text_count(processor,c['memory'],c['question'])<=b else retain(c['records'],c['base_id'],lambda s:text_count(processor,s,c['question'])<=b)[0]
 else:memory=str(c['memory'])
 return memory,[]
def run(prepared,reader,study,output,work):
 import torch,transformers,numpy as np
 from PIL import Image
 from huggingface_hub import snapshot_download
 from transformers import AutoProcessor,AutoModelForImageTextToText,GenerationConfig
 from cache_adapter import materialize
 verify_source();execution=read(ROOT/'EXECUTION_FREEZE.json');verify_files(ROOT,execution['files'])
 freeze=read(prepared/study/'FREEZE.json');verify_files(prepared/study,freeze['files']);release=read(prepared/'INPUT_RELEASE.json')
 assert release['status']=='all-inputs-independently-verified' and release['freeze_hashes'][study]==sha(prepared/study/'FREEZE.json') and release['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
 assert torch.__version__=='2.10.0+cu128' and transformers.__version__=='5.3.0' and torch.cuda.is_bf16_supported()
 props=torch.cuda.get_device_properties(0);assert 'A100' in props.name and 38*1024**3<props.total_memory<42*1024**3
 rows=[r for r in freeze['rows'] if r['reader']==reader];assert len(rows)=={'01_budget_crossover':180,'02_geometry_mechanism':96,'03_systems_profile':15}[study]
 output.mkdir(parents=True,exist_ok=False)
 put(output/'RUN_START.json',{'reader':reader,'study':study,'expected_inputs':len(rows),'input_freeze_sha256':sha(prepared/study/'FREEZE.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'execution_freeze_sha256':sha(ROOT/'EXECUTION_FREEZE.json'),'epoch':time.time()})
 pin=read(LEGACY/f'environment/{reader}_SNAPSHOT.json');model_id=read(LEGACY/'PROTOCOL.json')['models'][reader]
 path=snapshot_download(model_id,revision=pin['revision'],allow_patterns=[r['path'] for r in pin['files']],max_workers=2)
 path=materialize(path,work/'materialized_snapshot',pin['files'],verify_files)
 processor=AutoProcessor.from_pretrained(path,local_files_only=True,trust_remote_code=False,use_fast=True)
 model=AutoModelForImageTextToText.from_pretrained(path,local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,attn_implementation='sdpa',use_safetensors=True).to('cuda:0').eval()
 profile=study==STUDIES[2];cap=1 if profile else 64
 generation=GenerationConfig.from_dict(model.generation_config.to_dict());generation.update(do_sample=False,num_beams=1,use_cache=True,max_new_tokens=cap,return_dict_in_generate=True,output_scores=False,disable_compile=True)
 random.seed(SEEDS['inference']);np.random.seed(SEEDS['inference']);torch.manual_seed(SEEDS['inference']);torch.cuda.manual_seed_all(SEEDS['inference'])
 env=environment();env.update({'revision':pin['revision'],'generation':generation.to_dict(),'gpu_total_memory':props.total_memory,'attention':'sdpa','dtype':'bfloat16','compile_enabled':False,'cudnn_benchmark':torch.backends.cudnn.benchmark,'tf32_matmul':torch.backends.cuda.matmul.allow_tf32})
 put(output/'ENVIRONMENT.json',env)
 ordered=sorted(rows,key=lambda r:digest(f"{SEEDS['order']}|{reader}|{r['case_id']}|{r['arm']}"))
 if profile:
  schedule=[]
  for phase,repetitions in [('warmup',3),('measured',10)]:
   for rep in range(repetitions):
    for regime in sorted(['short','medium','long'],key=lambda s:digest(f"{SEEDS['order']}|{rep}|{s}")):
     rr=sorted([r for r in rows if r['case_id'].endswith('-'+regime)],key=lambda r:r['arm']);offset=rep%5;rr=rr[offset:]+rr[:offset]
     schedule.extend((r,phase,rep) for r in rr)
 else:schedule=[(r,'quality',0) for r in ordered]
 put(output/'ORDER.json',[{'row':r,'phase':phase,'repetition':rep} for r,phase,rep in schedule])
 total_forwards=0
 for index,(row,phase,rep) in enumerate(schedule):
  folder=prepared/row['path'];req=read(folder/'REQUEST.json');m=read(folder/'MEASUREMENT.json')
  name=f"{index:04}--{row['case_id']}--{row['arm']}";dest=output/name;dest.mkdir()
  put(dest/'START.json',{'index':index,'row':row,'phase':phase,'repetition':rep,'cap':cap,'input_freeze_sha256':sha(prepared/study/'FREEZE.json')})
  class Journal:
   def __init__(self):self.values=[];self.first=None
   def put(self,value):
    v=value.detach().cpu().tolist();self.values.append(v)
    if len(self.values)==2:torch.cuda.synchronize();self.first=time.perf_counter()
    if not profile:
     with (dest/'TOKENS.jsonl').open('ab') as f:f.write(json.dumps(v).encode()+b'\n');f.flush();os.fsync(f.fileno())
   def end(self):pass
  journal=Journal();timing={};hooks=[];forward_starts=[];forward_times=[]
  if profile:
   c=read(prepared/STUDIES[0]/'cases'/(row['case_id']+'.json'))
   gc.collect();torch.cuda.synchronize();torch.cuda.empty_cache();torch.cuda.synchronize()
   baseline_alloc=torch.cuda.memory_allocated();baseline_reserved=torch.cuda.memory_reserved();torch.cuda.reset_peak_memory_stats()
   pipeline_start=time.perf_counter();memory,images=build_representation(req,c,processor);render_end=time.perf_counter()
   rendered=chat(processor,memory,req['question'],images);batch=processor(text=[rendered],images=images or None,return_tensors='pt',padding=False);processor_end=time.perf_counter()
   # Validate before timing invocation in a separate precheck below, not in timed path.
   def pre(module,args):torch.cuda.synchronize();forward_starts.append(time.perf_counter())
   def post(module,args,out):torch.cuda.synchronize();forward_times.append(time.perf_counter()-forward_starts[-1])
   hooks=[model.register_forward_pre_hook(pre),model.register_forward_hook(post)]
  else:
   images=[Image.open(folder/n).convert('RGB') for n in req['images']];batch=processor(text=[m['rendered_chat']],images=images or None,return_tensors='pt',padding=False);tensor_check(batch,m)
  device={k:v.to('cuda:0') for k,v in batch.items()};torch.cuda.synchronize();model_start=time.perf_counter()
  with torch.inference_mode():generated=model.generate(**device,generation_config=generation,streamer=journal)
  torch.cuda.synchronize();ended=time.perf_counter()
  if profile:
   peak_alloc=torch.cuda.max_memory_allocated();peak_reserved=torch.cuda.max_memory_reserved()
   for h in hooks:h.remove()
   assert len(forward_times)==1,'Fixed-one-token profile used unexpected forward count'
   total_forwards+=len(forward_times)
   timing={'render_or_pack_s':render_end-pipeline_start,'processor_s':processor_end-render_end,'prefill_including_vision_s':forward_times[0],'model_ttft_s':journal.first-model_start,'pipeline_ttft_s':journal.first-pipeline_start,'end_to_end_one_token_s':ended-pipeline_start,'model_generate_s':ended-model_start,'peak_allocated_bytes':peak_alloc,'peak_reserved_bytes':peak_reserved,'baseline_allocated_bytes':baseline_alloc,'baseline_reserved_bytes':baseline_reserved,'top_level_forward_passes':len(forward_times)}
   # Post-generation integrity failures invalidate the entire stage, never rerun.
   # Same code/input prechecked by CPU; verify again outside timed interval.
   assert memory==req['memory'] and rendered==m['rendered_chat'];tensor_check(batch,m)
   with (dest/'TOKENS.jsonl').open('x') as f:
    for v in journal.values:f.write(json.dumps(v)+'\n')
  ids=generated.sequences[0,len(m['input_token_ids']):].detach().cpu().tolist()
  assert len(ids)==1 if profile else 0<len(ids)<=64
  raw={'generated_token_ids':ids,'prediction':processor.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False),'decoded_with_special_tokens':processor.tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)}
  put(dest/'RAW.json',raw);put(dest/'COMPLETE.json',{'raw_sha256':sha(dest/'RAW.json'),'journal_sha256':sha(dest/'TOKENS.jsonl'),'generation_s':ended-model_start,'generated_tokens':len(ids),'cap_hit':len(ids)==cap,'timing':timing,'phase':phase,'repetition':rep})
  for im in images:im.close()
  del generated,device,batch,images,journal
  print(study,reader,index+1,'/',len(schedule),flush=True)
 put(output/'RUN_COMPLETE.json',{'status':'complete-unverified','generation_invocations':len(schedule),'quality_calls':0 if profile else len(schedule),'systems_forward_passes':total_forwards,'scoring_enabled':False,'epoch':time.time()})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=pathlib.Path,required=True);p.add_argument('--reader',choices=READERS,required=True);p.add_argument('--study',choices=STUDIES,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--work',type=pathlib.Path,required=True);a=p.parse_args();run(a.prepared,a.reader,a.study,a.output,a.work)
