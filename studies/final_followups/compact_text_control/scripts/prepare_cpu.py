"""Resource-bounded three-case CPU workers. No weights, inference imports, or output answers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from experiment_common import ROOT,CONFIG,read,put,sha

def prepare(split):
    index=read(ROOT/'cases'/split/'INDEX.json');rows=[]
    env=dict(os.environ,TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    env['PYTHONPATH']=str(ROOT/'development/pydeps')
    for i,item in enumerate(index['cases']):
        folder=ROOT/'inputs'/split/item['id']
        required=[folder/arm/name for arm in CONFIG['arms'] for name in ('REQUEST.json','MEASUREMENT.json')]
        if not all(p.is_file() for p in required):
            # CPU-only incomplete directories may contain no committed scientific
            # input. Never delete files or repair partially written data silently.
            if folder.exists():
                if any(p.is_file() for p in folder.rglob('*')):
                    raise RuntimeError('Partial CPU case contains files: inspect before repair: '+str(folder))
                for child in sorted(folder.rglob('*'),reverse=True):
                    if child.is_dir():child.rmdir()
                folder.rmdir()
            command=[sys.executable,'-u',str(ROOT/'scripts/build_conditions.py'),'--split',split,'--case-index',str(i)]
            subprocess.run(command,env=env,check=True)
        for arm in CONFIG['arms']:
            dest=folder/arm;req=read(dest/'REQUEST.json');m=read(dest/'MEASUREMENT.json')
            assert req['case_id']==item['id'] and req['arm']==arm and req['source_sha256']==item['sha256']
            assert req['B']==CONFIG['B'] and req['max_new_tokens']==CONFIG['max_new_tokens']
            assert m['total_input_tokens']<=CONFIG['B']
            assert all((dest/n).is_file() for n in req['images'])
            rows.append({'case_id':item['id'],'arm':arm,'path':dest.relative_to(ROOT).as_posix(),
                         'request_sha256':sha(dest/'REQUEST.json'),'measurement_sha256':sha(dest/'MEASUREMENT.json')})
        print(f'CPU case committed {split} {i+1}/{len(index["cases"])}',flush=True)
    manifest={'experiment_id':CONFIG['experiment_id'],'split':split,'rows':rows,'B':CONFIG['B'],
              'held_out_inference_started':False,'model_calls':0}
    put(ROOT/('manifest.json' if split=='eval' else f'manifest_{split}.json'),manifest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['dev','eval','smoke'],required=True);a=p.parse_args();prepare(a.split)
