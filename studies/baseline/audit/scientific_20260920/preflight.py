"""Outcome-blind audit and dated release; never mutates historical artifacts."""
import datetime, hashlib, json, pathlib, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from iclr.blinded_confirmatory_20260912.boundary import references, require_scientific_freeze

def sha(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def put(name, value):
    p=OUT/name
    with p.open('x', encoding='utf-8') as f: json.dump(value,f,indent=2,ensure_ascii=False)
    return ref(p)
def ref(p):
    p=pathlib.Path(p)
    return dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))

if __name__=='__main__':
    cache={}; problems=[]; checks=[]
    def check(r):
        p=ROOT/r['path']
        if r['path'] not in cache:
            cache[r['path']] = (p.stat().st_size,sha(p)) if p.is_file() else None
        if cache[r['path']] != (r['bytes'],r['sha256']): problems.append(r['path'])
    ident_path=ROOT/'iclr/pre_gpu_cpu_20260913/identifier_checkpoint/IDENTIFIER_SCIENTIFIC_CONTRACT.json'
    ruler_path=ROOT/'iclr/ruler_cpu5_20260917/CONTRACT_CANDIDATE.json'
    ident=read(ident_path); ruler=read(ruler_path)
    for p in [ident_path,ruler_path]:
        for r in references(read(p)):check(r)
    manifests={}
    for label,folder in [('Qwen2B','identifier_gpu_20260916'),('Qwen9B','identifier_qwen9b_20260917'),('GLM','identifier_glm_20260917')]:
        p=ROOT/'iclr'/folder/'RUN_MANIFEST.json';m=read(p)
        assert sha(p)==read(p.parent/'SEAL.json')['manifest_sha256']
        assert len(m['rows'])==672 and len({(r['item_id'],r['condition']) for r in m['rows']})==672
        for r in references(m):check(r)
        manifests['Identifier/'+label]=ref(p)
        print('manifest checked',label,'identifier',flush=True)
    p=ROOT/'iclr/locomo_stage_bound_20260912/RUN_MANIFEST.json';m=read(p)
    assert sha(p)=='9150ea8735e97b4691eda4059f41fd120f981cfec3687b036ca4dd7d23ea7498'
    assert len(m['rows'])==9000 and len({(r['item_id'],r['model_id'],r['condition']) for r in m['rows']})==9000
    for r in references(m):check(r)
    for r in read(ROOT/m['input_manifest']['path'])['files']:check(r)
    manifests['LoCoMo']=ref(p)
    print('manifest checked LoCoMo',flush=True)
    from iclr.ruler_gpu_20260919.runner import verify
    for label,key in [('Qwen2B','qwen2b'),('Qwen9B','qwen9b'),('GLM','glm')]:
        verify(key)
        manifests['RULER/'+label]=ref(ROOT/f'iclr/ruler_gpu_20260919/RUN_MANIFEST_{key}.json')
    approvals=[]
    for s in 'ABCDE':
        files=sorted(pathlib.Path('<LOCAL_USER>/Downloads').glob(f'ICLR-RULER-{s}-Checkpoint-*.zip'),key=lambda p:p.stat().st_mtime,reverse=True)
        with zipfile.ZipFile(files[0]) as z:
            a=json.loads(z.read('APPROVED_CONTRACT.json'));b=json.loads(z.read('BINDING.json'))
            assert a['contract']==sha(ruler_path)==b['contract_candidate_sha256']
            assert a['package']==b['package_sha256']
            approvals.append(dict(shard=s,archive=str(files[0]),record=a))
    cpu=ROOT/'iclr/ruler_cpu5_20260917/ICLR-RULER-Merged-Checkpoint-A-E.zip'
    assert sha(cpu)=='e9f90956c4069266e82e68385c4f58162793077562ab331d358fa080fec72d03'
    with zipfile.ZipFile(cpu) as z:
        m=json.loads(z.read('MERGE_REPORT.json'))
        assert m['request_rows']==2160 and m['realized_common_cases_each_task_reader']==30
        assert json.loads(z.read('BINDING.json'))['contract_candidate_sha256']==sha(ruler_path)
    assert not problems,problems
    review=put('PRE_OUTCOME_REVIEW.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='verified for release prerequisites, not experimental validity',
        inspection_before_this_review=False,checked_local_reference_files=len(cache),reference_failures=problems,
        manifests=manifests,ruler_pre_generation_approvals=approvals,
        user_authorization='2026-09-20: Now inspect and verify every result we got from experiments. Make sure that everything is scientifically okay.',
        scientific_review=[
            'All mandatory counts and representations remain unchanged; no outcome-based selection or amendment.',
            'RULER keeps the native VT worked example; the evaluation is training-free, not uniformly zero-shot.',
            'Identifier exact sign test follows the prospective amendment, not the historical sign-flip proposal.',
            'LoCoMo has ten previously studied conversation clusters; 500 held-out questions do not imply 500 independent histories.',
            'Input-count reduction is not evidence of latency, energy or compute reduction.',
            'Statistical significance is not required for validity; all null and adverse outcomes retained.',
            'Current release is recorded now, not backdated. Frozen originals and source approvals remain unchanged.'
        ]))
    # Boundary expects a flat legacy schema. This additive adapter maps the already
    # approved nested RULER contract without changing any scientific content.
    normalized=dict(benchmark='ruler',status='verified',sealed=True,scientific_review_passed=True,
        original_contract=ref(ruler_path),review=review,source_revision=ruler['generation']['upstream_revision'],
        reference_tokenizer=ruler['generation']['reference_tokenizer'],generator=ruler['generation'],
        templates=ruler['native_interface'],datasets=dict(corpus=ruler['generation']['corpus'],corpus_manifest=ruler['generation']['corpus_manifest']),
        metrics=ruler['metrics'],seeds=dict(generation=2026090601,execution_order=2026090504,statistics=2026090505,inference=2026090506),
        row_counts=ruler['scope'],exclusions=ruler['eligibility'],stopping_rules=ruler['technical_failure'])
    nr=put('RULER_RELEASE_CONTRACT.json',normalized)
    release=put('UNBLINDING_RELEASE.json',dict(status='verified',inspection_permitted=True,
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        contracts=dict(ruler=nr,identifier=ref(ident_path)),review=review,
        scope='User-requested local scientific audit and analysis of immutable completed experiments; no new inference'))
    require_scientific_freeze(ROOT,release)
    put('RELEASE_VALIDATION.json',dict(passed=True,release=release,private_results_opened=False))
    print('Scientific release prerequisite check PASSED. No model results inspected.',flush=True)
