"""Download only pinned wheels/assets; isolated Python 3.13 environments."""
import json,pathlib,subprocess,sys,time,urllib.parse,urllib.request,venv
import hashlib
D=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def download(url,p,ref):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  if sha(p)!=ref['sha256'] or p.stat().st_size!=ref['bytes']:raise RuntimeError('Cached file differs')
  return
 partial=p.with_name(p.name+'.partial')
 if partial.exists():raise RuntimeError('Partial download preserved; review before resuming')
 with urllib.request.urlopen(url,timeout=120) as src,partial.open('xb') as out:
  for b in iter(lambda:src.read(1024*1024),b''):out.write(b)
 if partial.stat().st_size!=ref['bytes'] or sha(partial)!=ref['sha256']:raise RuntimeError('Downloaded bytes do not match pin')
 partial.rename(p)
def setup(mode,work):
 if sys.version_info[:2]!=(3,13):raise RuntimeError('Use Colab Python 3.13; do not silently change the pinned environment')
 work.mkdir(parents=True,exist_ok=True);pool=work/'wheels';pool.mkdir(exist_ok=True)
 inv=read(D/f'environment/{mode}_WHEELS.json');inv=inv['files'] if mode=='GPU' else inv
 for r in inv:
  fn=pathlib.Path(r['path']).name if mode=='GPU' else r['filename'];name,version=fn.split('-')[:2]
  if name in ['torch','torchvision']:url='https://download.pytorch.org/whl/'+('cu128' if mode=='GPU' else 'cpu')+'/'+urllib.parse.quote(fn)
  else:
   with urllib.request.urlopen('https://pypi.org/pypi/'+name+'/'+version+'/json',timeout=120) as f:meta=json.load(f)
   found=[x for x in meta['urls'] if x['filename']==fn and x['digests']['sha256']==r['sha256']]
   if len(found)!=1:raise RuntimeError('Pinned wheel unavailable: '+fn)
   url=found[0]['url']
  download(url,pool/fn,r)
 env=work/'env';python=env/'bin/python'
 if not python.exists():venv.EnvBuilder(with_pip=False).create(env)
 subprocess.run([sys.executable,'-m','pip','--python',str(python),'install','--no-index','--find-links',str(pool),'--require-hashes','-r',str(D/f'environment/{mode}.lock.txt')],check=True)
 subprocess.run([sys.executable,'-m','pip','--python',str(python),'check'],check=True)
 return python
def assets(work,models):
 target=work/'assets'
 for r in read(D/'environment/ASSET_PINS.json'):
  if r['model'] not in models:continue
  url=r.get('url') or 'https://huggingface.co/'+r['model']+'/resolve/'+r['revision']+'/'+r['file']
  download(url,target/r['model'].replace('/','--')/r['file'],r)
 return target
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['CPU','GPU']);p.add_argument('work',type=pathlib.Path);a=p.parse_args();print(setup(a.mode,a.work))
