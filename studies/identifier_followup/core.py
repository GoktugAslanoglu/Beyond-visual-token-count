"""Source-only preparation and exact source-span layout bookkeeping."""
import hashlib,itertools,json,math,pathlib,string
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont
from vendor import original_generator as old
from vendor.original_layout import layout as original_layout
D=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def put(p,v):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def schedule(split):
 out=[]
 for li,ai,si,pi in itertools.product(range(2),range(2),range(2),range(3)):
  if split=='dev' and (li+ai+si+pi)%2:continue
  for instance in ([1] if split=='dev' else [1,2]):
   out.append(dict(length=[8,24][li],alphabet=['decimal','lowercase_alphanumeric'][ai],entropy=['repeated_4char_motif','independent_characters'][si],position=['early','middle','late'][pi],distractors=4,instance=instance))
 assert len(out)==(12 if split=='dev' else 48)
 return out
def generate(index,split,count):
 c=read(D/'PROTOCOL.json');f=schedule(split)[index];seed=c['development_seed' if split=='dev' else 'evaluation_seed']
 t=old.TEMPLATES['development' if split=='dev' else 'heldout'];prng=old.rng_for(index,'payloads',seed);krng=old.rng_for(index,'keys',seed)
 alphabet=string.digits if f['alphabet']=='decimal' else string.ascii_lowercase+string.digits
 def draw():
  k=4 if f['entropy']=='repeated_4char_motif' else f['length'];v=''.join(prng.choice(alphabet) for _ in range(k));return v*(f['length']//k)
 target=draw();values=[];rejected=0
 for _ in range(4):
  v=draw()
  while v==target:
   rejected+=1
   if rejected>10000:raise ValueError('Payload collision gate')
   v=draw()
  values.append(v)
 keys=[]
 while len(keys)<5:
  k=''.join(krng.choice(string.ascii_uppercase) for _ in range(10))
  if k not in keys:keys.append(k)
 records=[t['record'].format(key=k,payload=v) for k,v in zip(keys[1:],values)];fraction=old.POSITIONS[f['position']];cut=int(4*fraction)
 before='\n'.join(records[:cut]);after='\n'.join(records[cut:]);unit=t['filler']+'\n';target_line=t['record'].format(key=keys[0],payload=target)
 def prefix(n):return (before+'\n' if before else '')+unit*n
 per=max(1,count(unit*16)/16);n=max(0,round((fraction*8192-count(prefix(0)))/per))
 for _ in range(4):n=max(0,n+round((fraction*8192-count(prefix(n)))/per))
 n=min(range(max(0,n-4),n+5),key=lambda v:(abs(count(prefix(v))-fraction*8192),v))
 head=prefix(n)+target_line+'\n'+(after+'\n' if after else '');m=max(0,round((8192-count(head))/per))
 for _ in range(4):m=max(0,m+round((8192-count(head+unit*m))/per))
 m=min(range(max(0,m-4),m+5),key=lambda v:(abs(count(head+unit*v)-8192),v))
 memory=head+unit*m;offset=len(prefix(n))+len('Record '+keys[0]+': ')
 return dict(id=f'followup-{split}-{index:03}',split=split,seed=seed,factors=f,memory=memory,question=t['question'].format(key=keys[0]),reference=target,target_key=keys[0],source_tokens=count(memory),target_relative_position=count(memory[:offset])/count(memory),target_char_offset=offset,record_count=5,rejected_payload_draws=rejected,realized_minimal_period=old.minimal_period(target))
def generate_all():
 from tokenizers import Tokenizer
 tok=Tokenizer.from_file(str(D/'assets/reference_tokenizer.json'));tok.no_padding();tok.no_truncation();count=lambda x:len(tok.encode(x,add_special_tokens=False).ids)
 for split in ['dev','eval']:
  for i in range(len(schedule(split))):
   row=generate(i,split,count);p=D/'cases'/split/(row['id']+'.json');put(p,row);old.validate(row,count)
 print('Generated and validated 12 development and 48 fresh evaluation cases; no inference.')
@lru_cache(maxsize=256)
def font():return ImageFont.truetype(str(D/'assets/DejaVuSansMono.ttf'),12)
def efficient_plan(text,layout_id,side):
 columns=2 if layout_id=='L2_twocolumn_wordwrap' else 1;word=layout_id!='L1_fullwidth_charwrap';margin=24;gap=24
 width=(side-2*margin-gap*(columns-1))/columns;fw=font().getlength('M');capacity=int(width//fw)
 if capacity<2:raise ValueError('No horizontal capacity')
 flat=text.replace('\n',' ');lines=[];start=0
 while start<len(flat):
  end=min(len(flat),start+capacity)
  if word and end<len(flat) and flat[end]!=' ':
   boundary=flat.rfind(' ',start,end)
   if boundary>start:end=boundary+1
  lines.append(dict(start=start,end=end,text=flat[start:end]));start=end
 ascent,descent=font().getmetrics();height=ascent+descent+2;bucket_count=4*columns;q,rem=divmod(len(lines),bucket_count);cursor=0;pages=[]
 for page_i in range(4):
  pl=[]
  for col in range(columns):
   bucket=page_i*columns+col;n=q+int(bucket<rem)
   for j,l in enumerate(lines[cursor:cursor+n]):
    x=margin+col*(width+gap);y=margin+ascent+j*height;b=font().getbbox(l['text'],anchor='ls');bbox=[x+b[0],y+b[1],x+b[2],y+b[3]]
    if bbox[0]<margin or bbox[2]>side-margin+1e-6 or bbox[1]<margin or bbox[3]>side-margin:raise ValueError('No vertical capacity')
    pl.append(dict(l,x=x,baseline_y=y,bbox=bbox,column=col))
   cursor+=n
  if not pl:raise ValueError('Empty page')
  pages.append(dict(page_index=page_i,source_start=pl[0]['start'],source_end=pl[-1]['end'],lines=pl,width=side,height=side))
 return pages
def plan(text,layout_id):
 if layout_id=='original':
  for side in range(1372,16381,28):
   try:_,pages=original_layout(text,D/'assets/DejaVuSansMono.ttf',12,side,side,pages=4);break
   except ValueError as e:
    if 'without clipping' not in str(e):raise
  else:raise ValueError('Original layout infeasible')
 else:
  for side in range(224,4090,28):
   try:pages=efficient_plan(text,layout_id,side);break
   except ValueError:continue
  else:raise ValueError('Efficient layout infeasible')
 cursor=0
 for p in pages:
  assert p['source_start']==cursor
  for l in p['lines']:
   assert l['start']==cursor
   expected=text[l['start']:l['end']].removesuffix('\n') if layout_id=='original' else text[l['start']:l['end']].replace('\n',' ')
   assert l['text']==expected;cursor=l['end']
  assert cursor==p['source_end']
 assert cursor==len(text)
 return dict(layout=layout_id,base_side=side,pages=pages,source_sha256=digest(text.encode()),linebreak_policy='original hard breaks' if layout_id=='original' else 'newline maps one-for-one to horizontal space; original bytes retained by exact source spans',width_utilization=max((max(l['bbox'][2] for l in p['lines'])-min(l['bbox'][0] for l in p['lines']))/side for p in pages))
def render(plan,side):
 images=[]
 for p in plan['pages']:
  im=Image.new('RGB',(plan['base_side'],plan['base_side']),'white');draw=ImageDraw.Draw(im)
  for l in p['lines']:draw.text((l['x'],l['baseline_y']),l['text'],font=font(),fill='black',anchor='ls')
  images.append(im.resize((side,side),Image.Resampling.LANCZOS));im.close()
 return images
def package_files(folder,exclude=()):return [dict(path=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.rglob('*')) if p.is_file() and p.relative_to(folder).as_posix() not in exclude and '__pycache__' not in p.parts]
def verify_files(folder,files):
 folder=pathlib.Path(folder).resolve()
 for ref in files:
  p=(folder/ref['path']).resolve()
  if not p.is_relative_to(folder) or p.stat().st_size!=ref['bytes'] or sha(p)!=ref['sha256']:raise ValueError('File integrity failure: '+ref['path'])
