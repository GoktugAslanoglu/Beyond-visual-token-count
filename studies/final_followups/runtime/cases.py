"""Answer-blind source construction and record retention; never model outputs."""
import random,string,math
from common import SEEDS,digest,LEGACY,read
from vendor import original_generator as original
def rng(seed,i,stream):return random.Random(int(digest(f'{seed}|final-round|{i}|{stream}'),16))
def crossover(index,count):
 r=rng(SEEDS['crossover'],index,'records');keys=set();values=set();records=[]
 # Single-key numeric-value retrieval derives from RULER NIAH single-answer design.
 for j in range(1600):
  key=''.join(r.choice(string.ascii_uppercase) for _ in range(10))
  while key in keys:key=''.join(r.choice(string.ascii_uppercase) for _ in range(10))
  value=str(r.randrange(1000000,10000000))
  while value in values:value=str(r.randrange(1000000,10000000))
  keys.add(key);values.add(value);records.append(f'Record {key}: {value}')
 target=records[0];key=target[7:17];answer=target.split(': ')[1];position=['early','middle','late'][index%3];fraction=original.POSITIONS[position];out=[]
 for regime,want in [('short',2048),('medium',6144),('long',8192)]:
  lo,hi=5,len(records)
  while lo<hi:
   mid=(lo+hi)//2
   if count('\n'.join(records[:mid]))<want:lo=mid+1
   else:hi=mid
  n=min([max(5,lo-1),lo],key=lambda n:(abs(count('\n'.join(records[:n]))-want),n))
  distractors=records[1:n];at=round(fraction*(n-1));lines=distractors[:at]+[target]+distractors[at:];memory='\n'.join(lines)
  assert abs(count(memory)-want)<=40
  assert memory.count(answer)==1 and memory.count(target)==1
  out.append({'id':f'cross-{index:03}-{regime}','base_id':f'cross-{index:03}','index':index,'regime':regime,'position':position,'seed':SEEDS['crossover'],'memory':memory,'records':lines,'question':f'What number is stored for record {key}? Return only the number.','reference':answer,'target_record':target,'source_tokens_reference':count(memory)})
 return out
def geometry(index,count):
 # Reuse validated five-record task construction with a new seed and a fixed schedule.
 seed=SEEDS['geometry'];length=[8,24][(index//16)%2];alpha=['decimal','lowercase_alphanumeric'][(index//8)%2];entropy=['repeated_4char_motif','independent_characters'][(index//4)%2];position=['early','middle','late'][index%3]
 r=rng(seed,index,'values');k=rng(seed,index,'keys');alphabet=string.digits if alpha=='decimal' else string.ascii_lowercase+string.digits
 def draw():
  n=4 if entropy=='repeated_4char_motif' else length;s=''.join(r.choice(alphabet) for _ in range(n));return s*(length//n)
 values=[];keys=[]
 while len(values)<5:
  v=draw()
  if v not in values:values.append(v)
 while len(keys)<5:
  v=''.join(k.choice(string.ascii_uppercase) for _ in range(10))
  if v not in keys:keys.append(v)
 template=original.TEMPLATES['heldout'];record=lambda j:template['record'].format(key=keys[j],payload=values[j]);fraction=original.POSITIONS[position];unit=template['filler']+'\n'
 cut=int(4*fraction);before='\n'.join(record(j) for j in range(1,cut+1));after='\n'.join(record(j) for j in range(cut+1,5));per=count(unit*16)/16
 prefix=lambda n:(before+'\n' if before else '')+unit*n
 n=max(0,round((fraction*8192-count(prefix(0)))/per))
 for _ in range(4):n=max(0,n+round((fraction*8192-count(prefix(n)))/per))
 n=min(range(max(0,n-4),n+5),key=lambda n:abs(count(prefix(n))-fraction*8192))
 head=prefix(n)+record(0)+'\n'+(after+'\n' if after else '');m=max(0,round((8192-count(head))/per))
 for _ in range(4):m=max(0,m+round((8192-count(head+unit*m))/per))
 m=min(range(max(0,m-4),m+5),key=lambda m:abs(count(head+unit*m)-8192));memory=head+unit*m
 question=template['question'].format(key=keys[0]);original.validate_uniqueness(memory,question,values[0],keys[0]);assert abs(count(memory)-8192)<=32
 return {'id':f'geometry-{index:03}','seed':seed,'memory':memory,'question':question,'reference':values[0],'target_key':keys[0],'factors':{'length':length,'alphabet':alpha,'entropy':entropy,'position':position,'distractors':4},'source_tokens_reference':count(memory)}
def retain(records,base_id,fits):
 # Neither query, target key, target value nor target position is available here.
 order=sorted(range(len(records)),key=lambda i:digest(f"{SEEDS['retention']}|{base_id}|{records[i]}"))
 selected=[]
 for i in order:
  trial=sorted(selected+[i]);text='\n'.join(records[j] for j in trial)
  if fits(text):selected=trial
 return '\n'.join(records[i] for i in selected),selected
