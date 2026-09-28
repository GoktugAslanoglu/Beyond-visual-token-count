"""Seal the pre-inference package after all audits; never creates approval."""
from pathlib import Path
import datetime
import importlib.metadata
import json
import sys
from experiment_common import ROOT,REPO,LEGACY,CONFIG,read,put,sha,verify_freeze

def entry(path,base):
    return {'path':path.relative_to(base).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}

def main():
    assert not (ROOT/'FREEZE.json').exists(), 'Do not overwrite a freeze'
    assert not (ROOT/'APPROVAL.json').exists()
    assert read(ROOT/'audit/PRELAUNCH.json')['status']=='passed'
    assert (ROOT/'PROTOCOL.md').read_bytes()==(ROOT/'FINAL_EXPERIMENT_PROTOCOL.md').read_bytes()
    # Everything required for scientific and execution reproduction, but not local
    # package installs, caches, worker logs, or post-approval result directories.
    allowed_roots={'scripts','tests','environment','assets','cases','inputs','audit','preparation_history'}
    developmental={'CAPACITY_REPORT.json','QUERY_INDEPENDENT_BUDGET.json','POWER.json','capacity_probe.py','SYNTHETIC_QA.json','SYNTHETIC_QA.png','tests_final.xml','tests_final.log'}
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or '.pytest_cache' in p.parts:continue
        rel=p.relative_to(ROOT)
        include=(len(rel.parts)==1 and p.suffix in ('.md','.json')) or rel.parts[0] in allowed_roots
        include=include or (rel.parts[0]=='development' and (p.name in developmental or p.name.startswith('final-dev-')))
        if include:files.append(entry(p,ROOT))
    dependencies=[]
    for p in sorted(LEGACY.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and (p.suffix=='.py' or 'assets' in p.relative_to(LEGACY).parts or p.name=='PROTOCOL.json'):
            dependencies.append(entry(p,REPO))
    runtime=REPO/'final_iclr/final_followups/runtime'
    dependencies.extend(entry(runtime/name,REPO) for name in ('cases.py','common.py'))
    freeze={'status':'frozen-awaiting-user-approval','experiment_id':CONFIG['experiment_id'],
            'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'held_out_inference_started':False,'held_out_calls':450,'model_calls':0,
            'protocol_sha256':sha(ROOT/'PROTOCOL.md'),'manifest_sha256':sha(ROOT/'manifest.json'),
            'prelaunch_audit_path':'audit/PRELAUNCH.json','files':files,'dependencies':dependencies,
            'approval_required':True,'approval_present':False,'local_freeze_not_external_registration':True}
    put(ROOT/'FREEZE.json',freeze);verify_freeze()
    print(json.dumps({'status':freeze['status'],'files':len(files),'dependencies':len(dependencies),
                      'freeze_sha256':sha(ROOT/'FREEZE.json'),'held_out_inference_started':False}))

if __name__=='__main__':main()
