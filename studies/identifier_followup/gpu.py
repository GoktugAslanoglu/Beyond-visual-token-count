"""Bounded identifier inference from previously sealed CPU requests. No scores."""
import argparse,hashlib,json,os,pathlib,random,sys,time
from core import D,read,put,sha,verify_files
def run(prepared,reader,output):
 import torch,transformers,numpy as np
 from PIL import Image
 from huggingface_hub import snapshot_download
 from transformers import AutoProcessor,AutoModelForImageTextToText,GenerationConfig
 protocol=read(D/'PROTOCOL.json');dev=read(D/'DEV_FREEZE.json');verify_files(D,dev['files'])
 freeze=read(prepared/'INPUT_FREEZE.json');verify_files(prepared,freeze['files'])
 release=read(prepared/'INPUT_RELEASE.json')
 if release.get('status')!='verified-for-inference' or release['input_freeze_sha256']!=sha(prepared/'INPUT_FREEZE.json') or release['dev_freeze_sha256']!=sha(D/'DEV_FREEZE.json'):raise RuntimeError('Returned CPU checkpoint requires independent input review')
 if freeze['protocol_sha256']!=sha(D/'PROTOCOL.json') or freeze['dev_freeze_sha256']!=sha(D/'DEV_FREEZE.json') or freeze['status']!='all-inputs-verified-no-inference':raise RuntimeError('Input freeze mismatch')
 if freeze['stage']=='dev' and reader!='Qwen2B':raise RuntimeError('Development reader mismatch')
 if freeze['stage']=='eval' and not freeze.get('selection_sha256'):raise RuntimeError('Evaluation lacks development selection')
 rows=[r for r in freeze['rows'] if r['reader']==reader];expected=36 if freeze['stage']=='dev' else (192 if freeze['stage']=='eval' else {'Qwen2B':126,'Qwen9B':121}.get(reader,0))
 if freeze['stage'] not in ['dev','eval','cap']:raise RuntimeError('Unknown study stage')
 cap=256 if freeze['stage']=='cap' else 64
 if freeze['stage']=='cap' and (freeze.get('cap_protocol_sha256')!=sha(D/'CAP_PROTOCOL.json') or freeze['expected_calls']!=247):raise RuntimeError('Cap-only protocol mismatch')
 if len(rows)!=expected or len({(r['case_id'],r['arm']) for r in rows})!=expected:raise RuntimeError('Row inventory differs')
 output.mkdir(parents=True,exist_ok=False)
 put(output/'RUN_START.json',{'reader':reader,'stage':freeze['stage'],'expected_calls':expected,'input_freeze_sha256':sha(prepared/'INPUT_FREEZE.json'),'dev_freeze_sha256':sha(D/'DEV_FREEZE.json'),'protocol_sha256':sha(D/'PROTOCOL.json')})
 if torch.__version__!='2.10.0+cu128' or transformers.__version__!='5.3.0' or not torch.cuda.is_bf16_supported():raise RuntimeError('Pinned GPU environment mismatch')
 if 'A100' not in torch.cuda.get_device_name(0) or not 38*1024**3<torch.cuda.get_device_properties(0).total_memory<42*1024**3:raise RuntimeError('Use one A100 40GB')
 snap=read(D/f'environment/{reader}_SNAPSHOT.json');model_id=protocol['models'][reader]
 path=pathlib.Path(snapshot_download(model_id,revision=snap['revision'],allow_patterns=[r['path'] for r in snap['files']],max_workers=2));verify_files(path,snap['files'])
 processor=AutoProcessor.from_pretrained(path,local_files_only=True,trust_remote_code=False,use_fast=True)
 model=AutoModelForImageTextToText.from_pretrained(path,local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,attn_implementation='sdpa',use_safetensors=True).to('cuda:0').eval()
 generation=GenerationConfig.from_dict(model.generation_config.to_dict());generation.update(do_sample=False,num_beams=1,use_cache=True,max_new_tokens=cap,return_dict_in_generate=True,output_scores=False)
 seed=protocol['inference_seed'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
 put(output/'ENVIRONMENT.json',{'python':sys.version,'torch':torch.__version__,'transformers':transformers.__version__,'gpu':torch.cuda.get_device_name(0),'revision':snap['revision'],'generation':generation.to_dict()})
 rows=sorted(rows,key=lambda r:hashlib.sha256(f"{protocol['order_seed']}|{reader}|{r['case_id']}|{r['arm']}".encode()).hexdigest())
 for index,row in enumerate(rows):
  folder=prepared/row['path'];req=read(folder/'REQUEST.json');m=read(folder/'MEASUREMENT.json')
  images=[Image.open(folder/n).convert('RGB') for n in req['images']]
  batch=processor(text=[m['rendered_chat']],images=images or None,return_tensors='pt',padding=False)
  for im in images:im.close()
  if batch['input_ids'][0].tolist()!=m['input_token_ids']:raise RuntimeError('Prepared input IDs differ')
  for name,expected_tensor in m['tensor_inventory'].items():
   ar=batch[name].detach().cpu().contiguous().numpy()
   if list(ar.shape)!=expected_tensor['shape'] or str(ar.dtype)!=expected_tensor['dtype'] or hashlib.sha256(ar.tobytes()).hexdigest()!=expected_tensor['sha256']:raise RuntimeError('Prepared processor tensor differs: '+name)
  dest=output/(row['case_id']+'--'+row['arm']);dest.mkdir()
  if len(m['input_token_ids'])+cap>m['native_context_limit']:raise RuntimeError('Raised cap exceeds native context')
  put(dest/'START.json',{'row':row,'index':index,'reader':reader,'max_new_tokens':cap,'input_freeze_sha256':sha(prepared/'INPUT_FREEZE.json')})
  class Journal:
   def put(self,value):
    with (dest/'TOKENS.jsonl').open('ab') as f:f.write(json.dumps(value.detach().cpu().tolist()).encode()+b'\n');f.flush();os.fsync(f.fileno())
   def end(self):pass
  device={k:v.to('cuda:0') for k,v in batch.items()};torch.cuda.synchronize();start=time.monotonic()
  with torch.inference_mode():generated=model.generate(**device,generation_config=generation,streamer=Journal())
  torch.cuda.synchronize();elapsed=time.monotonic()-start;ids=generated.sequences[0,len(m['input_token_ids']):].detach().cpu().tolist()
  raw={'generated_token_ids':ids,'prediction':processor.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False),'decoded_with_special_tokens':processor.tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)}
  put(dest/'RAW.json',raw);put(dest/'COMPLETE.json',{'raw_sha256':sha(dest/'RAW.json'),'journal_sha256':sha(dest/'TOKENS.jsonl'),'generation_s':elapsed,'cap_hit':len(ids)==cap,'generated_tokens':len(ids)})
  print('Completed',index+1,'/',len(rows),flush=True)
 put(output/'RUN_COMPLETE.json',{'calls':len(rows),'status':'complete-unverified','scoring_enabled':False})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=pathlib.Path,required=True);p.add_argument('--reader',choices=['Qwen2B','Qwen9B','GLM'],required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();run(a.prepared,a.reader,a.output)
