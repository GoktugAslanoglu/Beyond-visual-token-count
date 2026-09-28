"""Final-round shared invariants; historical modules remain byte-identical."""
import sys,pathlib,json,hashlib,platform,importlib.metadata,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
LEGACY=ROOT/'runtime/legacy'
sys.path.append(str(LEGACY))
from core import read,put,sha,verify_files,package_files,plan,render,font
from vendor.processor_measure import measure,SYSTEM
from vendor.scoring import score
READERS=['Qwen2B','Qwen9B','GLM']
STUDIES=['01_budget_crossover','02_geometry_mechanism','03_systems_profile']
SIDES={'Qwen2B':1008,'Qwen9B':1008,'GLM':868}
VISION={'Qwen2B':4096,'Qwen9B':4096,'GLM':3844}
SEEDS={'crossover':202609230101,'geometry':202609230102,'retention':202609230103,'order':202609230104,'bootstrap':202609230105,'inference':2026090506}
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def environment():
 import torch,transformers
 return {'python':sys.version,'platform':platform.platform(),'torch':torch.__version__,'cuda':torch.version.cuda,'transformers':transformers.__version__,'tokenizers':importlib.metadata.version('tokenizers'),'pillow':importlib.metadata.version('pillow'),'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def verify_source():
 f=read(ROOT/'SOURCE_FREEZE.json');verify_files(ROOT,f['files']);verify_files(LEGACY,read(LEGACY/'DEV_FREEZE.json')['files'])
def chat(processor,memory,question,images=None):
 content=([{'type':'text','text':'MEMORY\n'}]+[{'type':'image','image':im} for im in images]+[{'type':'text','text':'\n\nQUESTION\n'+question}]) if images else [{'type':'text','text':'MEMORY\n'+memory+'\n\nQUESTION\n'+question}]
 return processor.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':content}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
def text_count(processor,memory,question):return len(processor.tokenizer.encode(chat(processor,memory,question),add_special_tokens=False))
def tensor_check(batch,m):
 assert batch['input_ids'][0].tolist()==m['input_token_ids'],'input IDs changed'
 for k,v in m['tensor_inventory'].items():
  a=batch[k].detach().cpu().contiguous().numpy()
  assert list(a.shape)==v['shape'] and str(a.dtype)==v['dtype'] and hashlib.sha256(a.tobytes()).hexdigest()==v['sha256'],'tensor changed: '+k
