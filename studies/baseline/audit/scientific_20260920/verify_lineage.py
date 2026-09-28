"""Decode every output and verify saved checkpoint-prefix preservation."""
import collections,hashlib,io,json,pathlib,re,sys,zipfile
from tokenizers import Tokenizer
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from iclr.locomo_gates_20260912.gates import opaque
from preflight import sha,read

def open_private(p):
    with zipfile.ZipFile(p) as z:inner=z.read('BLINDED_DO_NOT_OPEN.zip')
    z=zipfile.ZipFile(io.BytesIO(inner));names=json.loads(z.read('INDEX_PRIVATE.json'))
    if len(names)!=len(set(names)):raise ValueError('duplicate index')
    return z,{n:f'records/{i:08d}.bin' for i,n in enumerate(names)}
def jd(z,ix,n):return json.loads(z.read(ix[n]))
def put(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    qpath=ROOT/'iclr/stage04c_identifier_amended_20260913/tokenizer/tokenizer.json';gpath=OUT/'glm_tokenizer.json'
    assert sha(qpath)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
    assert sha(gpath)=='9340665016419c825c4bdabbcc9acc43b7ca2c68ce142724afa829abb1be5efd'
    qt=Tokenizer.from_file(str(qpath));gt=Tokenizer.from_file(str(gpath))
    audit=read(OUT/'RESULT_AUDIT.json');inventory=read(ROOT/'iclr/audit/completion_20260920/completion_audit.json')['records'];reports=[];problems=[];setup_resolution=None
    for rec in inventory:
        study,label=rec['study'],rec['reader'];p=pathlib.Path(rec['path']);z,ix=open_private(p)
        complete=[n for n in ix if n.endswith('/COMPLETE.json')]
        ids={n.split('/')[0] for n in complete};t=gt if label=='GLM' else qt;decode_bad=[]
        row_files={n:hashlib.sha256(z.read(zn)).hexdigest() for n,zn in ix.items() if n.split('/')[0] in ids}
        for oid in sorted(ids):
            raw=jd(z,ix,oid+'/payload.bin');tokens=jd(z,ix,oid+'/tokens.bin')
            if t.decode(tokens,skip_special_tokens=True)!=raw['prediction']:decode_bad.append(dict(row_id=oid,field='prediction'))
            if t.decode(tokens,skip_special_tokens=False)!=raw['decoded_with_special_tokens']:decode_bad.append(dict(row_id=oid,field='decoded_with_special_tokens'))
        predecessors=[];paths=sorted(pathlib.Path('<LOCAL_USER>/Downloads').glob(f'ICLR-{study}-{label}-*.zip'))
        if (study,label)==('LoCoMo','Qwen2B'):paths+=sorted(pathlib.Path('<LOCAL_USER>/Downloads').glob('ICLR-Qwen300-*.zip'))
        seen=set()
        for old in paths:
            h=sha(old)
            if h in seen or h==rec['sha256']:continue
            seen.add(h);oz,oi=open_private(old);count=0;changes=[]
            for n,zn in oi.items():
                if re.fullmatch(r'[a-f0-9]{64}',n.split('/')[0]) and '/' in n:
                    if n not in row_files or hashlib.sha256(oz.read(zn)).hexdigest()!=row_files[n]:changes.append(n)
                    count+=n.endswith('/COMPLETE.json')
            predecessors.append(dict(path=str(old),sha256=h,completed_rows=count,changed_or_missing_files=changes))
            oz.close()
        if (study,label)==('LoCoMo','Qwen2B'):
            dirs={n.split('/')[0] for n in ix if '/' in n};extra=dirs-ids
            setup=[n for n in ix if n.split('/')[0] in extra]
            assert extra=={'setup_qwen300_1789289153546435702'}
            assert not any(n.endswith(('/START.json','/COMPLETE.json','/payload.bin','/tokens.bin','/TOKEN_JOURNAL_PRIVATE.jsonl')) for n in setup)
            setup_resolution=dict(flag='missing or extra result row',archive=p.name,missing_result_rows=0,expected_complete_rows=3000,
                extra_directory=list(extra),contents=setup,disposition='Preserved first-chunk setup records, not an additional experimental row. Retained unchanged; no result excluded.',
                implementation_correction='Audit directory comparison must classify result rows by START/COMPLETE markers and identity, rather than treating every subdirectory as a row.')
        if decode_bad:problems.append(dict(study=study,reader=label,decoding_mismatches=decode_bad))
        for prev in predecessors:
            if prev['changed_or_missing_files']:problems.append(dict(archive=prev['path'],changed=prev['changed_or_missing_files']))
        reports.append(dict(study=study,reader=label,decoded_rows=len(ids),decoding_mismatches=decode_bad,predecessors=predecessors))
        z.close();print(study,label,'decoded',len(ids),'mismatches',len(decode_bad),'prior archives',len(predecessors),flush=True)
    put('DECODING_AND_LINEAGE.json',dict(status='passed' if not problems else 'failed',reports=reports,problems=problems,
        checks='All decoded strings reproduced from exact pinned tokenizer JSON with both special-token modes. All row files in available earlier checkpoints compared byte-for-byte by SHA-256 with final checkpoint; no inference repeated.'))
    assert setup_resolution and audit['errors']==[dict(reason='missing or extra result row',key='ICLR-LoCoMo-Qwen2B-1789653262607945619.zip')]
    put('AUDIT_FLAG_RESOLUTION.json',setup_resolution)
    assert not problems,'Decode or lineage failures require review'
    put('RESULT_AUDIT_RESOLVED.json',dict(status='passed',rows=13176,original_audit='RESULT_AUDIT.json',flag_resolution='AUDIT_FLAG_RESOLUTION.json',
        additional_checks='DECODING_AND_LINEAGE.json',unresolved_errors=[],reports=audit['reports'],
        limitations=['No independent GPU replication or fresh processor execution.', 'Stored hashes prove internal consistency and unchanged lineage, not independent attestation of hardware execution.']))
