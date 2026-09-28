"""CPU preparation and durable checkpoints; no GPU work from CPU notebook."""
import pathlib,sys,subprocess,time,zipfile,json,traceback,os
ROOT=pathlib.Path(__file__).resolve().parents[1];LEGACY=ROOT/'runtime/legacy'
sys.path.insert(0,str(LEGACY))
def archive(folder,destination):
 with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file() and not any(x in p.relative_to(folder).parts for x in ['environment','assets','__pycache__']):z.write(p,p.relative_to(folder).as_posix())
def cpu(drive):
 from environment_setup import setup,assets
 work=pathlib.Path('<RUNTIME_ROOT>/content/final-round-cpu');work.mkdir(exist_ok=False);drive.mkdir(parents=True,exist_ok=True)
 dest=drive/f'FINAL_CPU_{time.time_ns()}.zip'
 try:
  with (work/'CPU.log').open('x') as log:
   cmd=[sys.executable,str(ROOT/'runtime/colab_entry.py'),'child',str(work)]
   completed=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  if completed.returncode:print((work/'CPU.log').read_text()[-6000:]);raise RuntimeError('CPU preparation failed; preserve checkpoint and return for review.')
 finally:
  archive(work,dest);print('Checkpoint saved:',dest,flush=True)
 print('Return the CPU checkpoint. No model inference has occurred.',flush=True)
def child(work):
 from environment_setup import setup,assets
 python=setup('CPU',work/'environment');model_ids=list(json.loads((LEGACY/'PROTOCOL.json').read_text())['models'].values());asset=assets(work,model_ids)
 subprocess.run([str(python),'-B',str(ROOT/'runtime/prepare.py'),'--assets',str(asset),'--output',str(work/'prepared')],check=True)
 subprocess.run([str(python),'-B',str(ROOT/'runtime/audit_inputs.py'),'--prepared',str(work/'prepared'),'--assets',str(asset),'--report',str(work/'NATIVE_INPUT_AUDIT.json')],check=True)
if __name__=='__main__':
 if sys.argv[1]=='child':child(pathlib.Path(sys.argv[2]))
 else:cpu(pathlib.Path(sys.argv[2]))
