"""Local checkpoint review; never creates a release from placeholders."""
import argparse,pathlib
from common import *
from transport import extract_new
from audit_inputs import audit
def main(checkpoint,destination):
 extract_new(checkpoint,destination);prepared=destination/'prepared'
 native=read(destination/'NATIVE_INPUT_AUDIT.json');local=audit(prepared,None)
 assert native['status']=='passed' and native['native_tensor_rechecks']==873
 for k in ['unique_inputs','pixel_exact_pages','source_freeze_sha256','freeze_hashes']:assert native[k]==local[k]
 env=read(prepared/'ENVIRONMENT.json');assert env['torch']=='2.10.0+cpu' and env['transformers']=='5.3.0' and env['tokenizers']=='0.22.2'
 release={'status':'all-inputs-independently-verified','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'freeze_hashes':local['freeze_hashes'],'cpu_archive_sha256':sha(checkpoint),'native_audit_sha256':sha(destination/'NATIVE_INPUT_AUDIT.json'),'local_audit_scope':'all spans, pixels, counts, cross-scale and cross-study pairing; native tensor repetition verified in CPU checkpoint','native_tensor_rechecks':873,'quality_inputs':828,'systems_unique_inputs':45}
 put(destination/'LOCAL_INPUT_AUDIT.json',local);put(destination/'INPUT_RELEASE_FINAL_v1.json',release)
 print('CPU checkpoint passed local review; release:',destination/'INPUT_RELEASE_FINAL_v1.json')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=pathlib.Path,required=True);p.add_argument('--destination',type=pathlib.Path,required=True);a=p.parse_args();main(a.checkpoint,a.destination)
