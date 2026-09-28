"""Portable repository-shaped source/input bundle; no weights or approval."""
import argparse
from pathlib import Path
import zipfile
from experiment_common import ROOT,REPO,read,sha,verify_freeze,put

def main(dest):
    f=verify_freeze();prefix=ROOT.relative_to(REPO)
    inventory=[(ROOT/r['path'],(prefix/r['path']).as_posix(),r['sha256']) for r in f['files']]
    inventory += [(REPO/r['path'],r['path'],r['sha256']) for r in f['dependencies']]
    inventory += [(ROOT/'FREEZE.json',(prefix/'FREEZE.json').as_posix(),sha(ROOT/'FREEZE.json'))]
    assert len({name for _,name,_ in inventory})==len(inventory)
    with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,name,h in inventory:
            assert sha(p)==h;z.write(p,name)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None and len(z.namelist())==len(inventory)
        import hashlib
        for _,name,h in inventory:assert hashlib.sha256(z.read(name)).hexdigest()==h
    print('Portable archive verified: '+str(dest))
    print('SHA256 '+sha(dest))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT.parent/'final_experiment_launch.zip');a=p.parse_args();main(a.output)
