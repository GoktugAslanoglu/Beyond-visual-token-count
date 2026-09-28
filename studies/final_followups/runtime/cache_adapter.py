"""Materialize only pinned snapshot files; retain strict hash/containment checks."""
import pathlib,hashlib,shutil,json

def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def materialize(snapshot,destination,refs,verify):
 snapshot=pathlib.Path(snapshot).resolve();destination=pathlib.Path(destination)
 if destination.exists():raise RuntimeError('Materialization attempt already exists')
 # Hugging Face snapshots/<revision> links are confined to the same repo cache.
 cache_root=snapshot.parent.parent if snapshot.parent.name=='snapshots' else snapshot
 checked=[];seen=set()
 for ref in refs:
  rel=pathlib.PurePosixPath(ref['path'])
  if rel.is_absolute() or '..' in rel.parts or ':' in ref['path'] or ref['path'] in seen:raise ValueError('Invalid pinned path')
  seen.add(ref['path']);source=(snapshot/rel).resolve()
  if not source.is_relative_to(cache_root) or not source.is_file():raise ValueError('Snapshot link escapes its repository cache')
  if source.stat().st_size!=ref['bytes'] or sha(source)!=ref['sha256']:raise ValueError('Pinned bytes differ: '+ref['path'])
  checked.append((source,rel))
 destination.mkdir(parents=True)
 for source,rel in checked:
  target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
  with source.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst,8*1024*1024)
 verify(destination,refs)
 return destination

def install(runtime,work):
 import huggingface_hub
 from core import read,verify_files
 runtime=pathlib.Path(runtime);original=huggingface_hub.snapshot_download
 def download(repo_id,*args,**kwargs):
  matches=[read(p) for p in (runtime/'environment').glob('*_SNAPSHOT.json') if read(p)['model_id']==repo_id]
  if len(matches)!=1:raise ValueError('Unpinned model request')
  pin=matches[0]
  if args or kwargs.get('revision')!=pin['revision'] or kwargs.get('allow_patterns')!=[r['path'] for r in pin['files']]:raise ValueError('Snapshot request differs from frozen pin')
  snapshot=original(repo_id,**kwargs)
  result=materialize(snapshot,pathlib.Path(work)/'materialized_snapshot',pin['files'],verify_files)
  print('Pinned snapshot copied to regular files; all hashes verified.',flush=True)
  return str(result)
 huggingface_hub.snapshot_download=download
