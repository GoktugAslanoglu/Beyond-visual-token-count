"""Append-only Colab GPU supervisor with priority gates and failure exports."""
import pathlib,sys,subprocess,time,json,traceback,zipfile,os,signal
from common import *
def archive(folder,destination):
 with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file() and not any(x in p.relative_to(folder).parts for x in ['environment','assets','materialized_snapshot','__pycache__']):z.write(p,p.relative_to(folder).as_posix())
def run(study,reader,prepared,drive):
 verify_source();verify_files(ROOT,read(ROOT/'EXECUTION_FREEZE.json')['files']);drive.mkdir(parents=True,exist_ok=True)
 if study==STUDIES[2]:
  gate=read(drive/'CROSSOVER_AUDIT_RELEASE.json');assert gate['status']=='passed' and gate['rows']==540 and gate['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
 if study==STUDIES[1]:
  gate=read(drive/'SYSTEMS_AUDIT_RELEASE.json');assert gate['status']=='passed' and gate['generation_invocations']==585 and gate['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
 key=study+'_'+reader;ledger=drive/'RUN_LEDGER';ledger.mkdir(exist_ok=True);entry=ledger/(key+'.json')
 if entry.exists():raise RuntimeError('This stage already has an attempt; do not rerun. Return its checkpoint for audit.')
 active=ledger/'ACTIVE.json'
 with active.open('x') as f:json.dump({'stage':key,'epoch':time.time()},f)
 work=pathlib.Path('<RUNTIME_ROOT>/content/final-round-'+key);work.mkdir(exist_ok=False)
 put(entry,{'status':'started','epoch':time.time(),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'execution_freeze_sha256':sha(ROOT/'EXECUTION_FREEZE.json')})
 code=None;process=None
 try:
  with (work/'PRIVATE_RUN.log').open('x') as log:
   process=subprocess.Popen([sys.executable,str(ROOT/'runtime/gpu_colab.py'),'child',study,reader,str(prepared),str(work)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while process.poll() is None:
    time.sleep(15)
    tail=(work/'PRIVATE_RUN.log').read_text(errors='replace').splitlines()
    if tail:print(tail[-1],flush=True)
   code=process.returncode
  if code:raise RuntimeError('Stage failed. Do not rerun; return the saved checkpoint.')
 finally:
  if process is not None and process.poll() is None:
   os.killpg(process.pid,signal.SIGTERM)
   try:process.wait(timeout=20)
   except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=20)
  # Completion record is a new file; the original start record is preserved.
  put(ledger/(key+'_END.json'),{'exit_code':code,'status':'complete-unverified' if code==0 else 'failed-or-interrupted','epoch':time.time()})
  dest=drive/f'FINAL_{key}_{time.time_ns()}.zip'
  archive(work,dest);print('Saved checkpoint:',dest,flush=True)
  active.unlink()
 print('Return checkpoint for audit. Accuracy is not computed here.',flush=True)
def child(study,reader,prepared,work):
 from environment_setup import setup
 python=setup('GPU',work/'environment')
 subprocess.run([str(python),'-B',str(ROOT/'runtime/gpu_final.py'),'--study',study,'--reader',reader,'--prepared',str(prepared),'--work',str(work),'--output',str(work/'output')],check=True)
if __name__=='__main__':
 if sys.argv[1]=='child':child(sys.argv[2],sys.argv[3],pathlib.Path(sys.argv[4]),pathlib.Path(sys.argv[5]))
 else:run(sys.argv[2],sys.argv[3],pathlib.Path(sys.argv[4]),pathlib.Path(sys.argv[5]))
