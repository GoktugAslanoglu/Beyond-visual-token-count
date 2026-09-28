"""Colab orchestration: CPU preparation, bounded GPU execution, durable exports."""
import argparse,datetime,json,os,pathlib,signal,subprocess,sys,time,zipfile
D=pathlib.Path(__file__).resolve().parent
def archive(folder,path,exclude=()):
 with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file() and not any(x in exclude for x in p.relative_to(folder).parts):z.write(p,p.relative_to(folder).as_posix())
def child(mode,stage,reader,work,prepared=None,selection=None,output=None):
 from environment_setup import setup,assets
 read=lambda p:json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
 python=setup(mode,work/'environment')
 if mode=='CPU':
  models=read(D/'PROTOCOL.json')['models'];wanted=[models['Qwen2B']] if stage=='dev' else list(models.values());asset=assets(work,wanted)
  args=[str(python),'-B',str(D/'prepare.py'),'--stage',stage,'--assets',str(asset),'--output',str(work/'prepared')]
  if selection:args+=['--selection',str(selection)]
 else:args=[str(python),'-B',str(D/'gpu.py'),'--prepared',str(prepared),'--reader',reader,'--output',str(output)]
 subprocess.run(args,check=True,cwd=D)
def run_cpu(stage,drive,selection=None):
 if os.environ.get('COLAB_GPU')=='1':raise RuntimeError('Switch to CPU runtime before preparation')
 work=pathlib.Path('<RUNTIME_ROOT>/content/followup-cpu-'+stage)
 if work.exists():raise RuntimeError('Existing CPU work preserved; return it for review before restarting')
 work.mkdir();drive.mkdir(parents=True,exist_ok=True);log=work/'CPU.log'
 try:
  with log.open('x') as f:
   subprocess.run([sys.executable,str(D/'colab.py'),'child','--mode','CPU','--stage',stage,'--work',str(work)]+(['--selection',str(selection)] if selection else []),cwd=D,stdout=f,stderr=subprocess.STDOUT,check=True)
 finally:
  dest=drive/f'FOLLOWUP_CPU_{stage}_{time.time_ns()}.zip';archive(work,dest,exclude=('environment','assets'));print('Saved CPU checkpoint:',dest,flush=True)
 print('Return this checkpoint for local audit before GPU inference.',flush=True)
def run_gpu(stage,reader,prepared,drive,first_cell_epoch):
 freeze=json.loads((prepared/'INPUT_FREEZE.json').read_text())
 if freeze['stage']!=stage:raise RuntimeError('Prepared checkpoint belongs to a different scientific stage')
 if stage=='cap':
  audit=json.loads((drive/'P1_AUDIT.json').read_text())
  if audit.get('status')!='passed' or audit.get('rows')!=576:raise RuntimeError('Verified identifier evaluation required before cap sensitivity')
  for prereq in ['development_Qwen2B','evaluation_Qwen2B','evaluation_Qwen9B','evaluation_GLM']:
   q=drive/'GPU_LEDGER'/(prereq+'.json')
   if not q.exists() or json.loads(q.read_text()).get('status')!='complete-unverified':raise RuntimeError('Identifier stages must finish before spending conditional cap budget')
 utc=datetime.datetime.now(datetime.timezone.utc)
 cutoff=datetime.datetime(2026,9,23,21,tzinfo=datetime.timezone.utc)
 if utc>=cutoff or (stage=='dev' and utc>=datetime.datetime(2026,9,22,21,tzinfo=datetime.timezone.utc)):raise RuntimeError('Frozen inference calendar cutoff reached')
 key=('development_Qwen2B' if stage=='dev' else ('evaluation_'+reader if stage=='eval' else 'cap_'+reader));drive.mkdir(parents=True,exist_ok=True);ledger=drive/'GPU_LEDGER';ledger.mkdir(exist_ok=True)
 lock=ledger/'ACTIVE' # One GPU job at a time; a stale lock needs review.
 entry=ledger/(key+'.json');work=pathlib.Path('<RUNTIME_ROOT>/content/followup-'+key);dest=drive/key
 started=time.time();elapsed=started-first_cell_epoch
 if elapsed<0 or elapsed>=6900:raise RuntimeError('Two-hour first-cell allowance already exhausted')
 if entry.exists() or dest.exists() or work.exists():raise RuntimeError('Stage already attempted; do not overwrite or rerun')
 lock.mkdir();work.mkdir();dest.mkdir();entry.write_text(json.dumps({'stage':key,'first_cell_epoch':first_cell_epoch,'max_seconds':7200,'status':'started'}))
 argv=[sys.executable,str(D/'colab.py'),'child','--mode','GPU','--stage',stage,'--reader',reader,'--prepared',str(prepared),'--work',str(work),'--output',str(dest/'output')]
 process=None;code=None;status='failed'
 try:
  with (dest/'PRIVATE_RUN.log').open('x') as f:
   process=subprocess.Popen(argv,cwd=D,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   try:code=process.wait(timeout=max(1,min(6900-elapsed,(cutoff-utc).total_seconds()-300)));status='complete-unverified' if code==0 else 'failed-preserved'
   except subprocess.TimeoutExpired:
    os.killpg(process.pid,signal.SIGTERM)
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    status='time-limit-preserved'
 finally:
  if process and process.poll() is None:
   os.killpg(process.pid,signal.SIGKILL);process.wait()
  end=time.time();entry.write_text(json.dumps({'stage':key,'first_cell_epoch':first_cell_epoch,'end_epoch':end,'elapsed_seconds':end-first_cell_epoch,'max_seconds':7200,'status':status,'exit_code':code}))
  checkpoint=drive/(key+'_'+str(time.time_ns())+'.zip');archive(dest,checkpoint);print('Saved private checkpoint:',checkpoint,flush=True)
  if lock.exists():lock.rmdir()
 print('Status:',status,'— return checkpoint for verification; no scores displayed.',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['child','cpu','gpu']);p.add_argument('--mode',choices=['CPU','GPU']);p.add_argument('--stage',choices=['dev','eval','cap'],required=True);p.add_argument('--reader',default='Qwen2B');p.add_argument('--work',type=pathlib.Path);p.add_argument('--prepared',type=pathlib.Path);p.add_argument('--selection',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path);p.add_argument('--drive',type=pathlib.Path);p.add_argument('--first-cell-epoch',type=float);a=p.parse_args()
 if a.command=='child':child(a.mode,a.stage,a.reader,a.work,a.prepared,a.selection,a.output)
 elif a.command=='cpu':run_cpu(a.stage,a.drive,a.selection)
 else:run_gpu(a.stage,a.reader,a.prepared,a.drive,a.first_cell_epoch)
