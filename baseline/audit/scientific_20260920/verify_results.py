"""Independent per-row audit of immutable inputs/results. No inference or repairs."""
import collections, datetime, hashlib, importlib.util, io, json, math, pathlib, re, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from iclr.blinded_confirmatory_20260912.boundary import require_scientific_freeze
from iclr.locomo_gates_20260912.gates import canonical,opaque
from iclr.locomo_stage_20260912.semantic import check_payload
from iclr.v2.runtime import scoring
from iclr.v2.vendor import locomo_metrics as oracle
from preflight import sha,ref,read

def digest(b):return hashlib.sha256(b).hexdigest()
def put(name,x):
    with (OUT/name).open('w',encoding='utf-8') as f:json.dump(x,f,indent=2,ensure_ascii=False)
def lines(p):return [json.loads(s) for s in pathlib.Path(p).read_text(encoding='utf-8').splitlines()]
def jbytes(b):return json.loads(b)
errors=[];checked={};inputs={};references={};sources={};budgets={};input_reports={}
def ensure(v,reason,key=''):
    if not v:errors.append(dict(reason=reason,key=key))
def checked_local(r):
    p=ROOT/r['path'];key=('local',str(p))
    if key not in checked:
        b=p.read_bytes();checked[key]=(len(b),digest(b))
    ensure(checked[key]==(r['bytes'],r['sha256']),'local reference hash',r['path'])
    return p
def checked_zip(z,r):
    key=(z.filename,r['path'])
    b=z.read(r['path'])
    if key not in checked:checked[key]=(len(b),digest(b))
    ensure(checked[key]==(r['bytes'],r['sha256']),'archive input hash',r['path'])
    return b
def measure(m,key,images):
    ensure(m['total_input_tokens']==len(m['input_token_ids'])==m['vision_tokens']+m['nonvision_input_tokens'],'input count',key)
    ensure(m['fits_context_with_128_output_reserve'] and m['total_input_tokens']+128<=m['native_context_limit'],'context reserve',key)
    ensure(sum(m['vision_tokens_per_page'])==m['vision_tokens'],'vision sum',key)
    ensure([math.prod(g)//m['merge_size']**2 for g in m['image_grid_thw']]==m['vision_tokens_per_page'],'grid count',key)
    ensure(len(images)==len(m['image_grid_thw']),'page count',key)
    if m.get('rendered_chat_sha256'):ensure(digest(m['rendered_chat'].encode())==m['rendered_chat_sha256'],'chat hash',key)
    budgets[key]=dict(total_input_tokens=m['total_input_tokens'],vision_tokens=m['vision_tokens'],source_text_tokens=m['source_text_tokens'],pages=len(images),compression=m.get('source_to_vision_ratio'))
    inputs[key]=m['input_token_ids']
def key(row):return (row['model_id'],row['item_id'],row['condition'])

if __name__=='__main__':
    require_scientific_freeze(ROOT,ref(OUT/'UNBLINDING_RELEASE.json'))
    print('Release gate passed; beginning full inputs and outputs audit',flush=True)
    manifests={};public=read(ROOT/'iclr/audit/completion_20260920/completion_audit.json')['records']
    q={r['item_id']:r for r in lines(ROOT/'iclr/data/external500/questions.private.jsonl')}
    qi={r['item_id']:r for r in lines(ROOT/'iclr/v2/data_cpu_v2/locomo_inputs.jsonl')}
    support={r['item_id']:r for r in lines(ROOT/'iclr/v2/data_cpu_v2/locomo_support.private.jsonl')}
    lm=read(ROOT/'iclr/locomo_stage_bound_20260912/RUN_MANIFEST.json')
    loc_seal='9150ea8735e97b4691eda4059f41fd120f981cfec3687b036ca4dd7d23ea7498'
    with zipfile.ZipFile(ROOT/'iclr/locomo_gates_20260912/LoCoMo-AllReaders-Inputs-UNSEALED.zip') as z:
        ensure(len(z.namelist())==len(set(z.namelist())),'duplicate LoCoMo input archive members')
        seen=set()
        for r in lm['rows']:
            k=key(r);request=read(checked_local(r['request']));model,item,arm=k
            pk=(model,item)
            if pk not in seen:
                env=jbytes(checked_zip(z,request['cpu_provenance']));p=env['payload']
                ensure(digest(canonical(p))==env['sha256'],'CPU provenance envelope',str(pk))
                try:check_payload(p,qi[item])
                except Exception as e:errors.append(dict(reason='LoCoMo semantic controls',key=str(pk),exception=type(e).__name__))
                for ca in ['retrieved_text_matched_selected']:
                    tr=p['controls'][ca]
                    ensure(tr['prefix_length']==max(c['prefix_length'] for c in tr['candidate_counts'] if c['total_input_tokens']<=tr['target']),'matched longest prefix',str(pk)+ca)
                seen.add(pk)
            m=jbytes(checked_zip(z,request['measurement']))
            for im in request['images']:
                ik=(z.filename,im['path'])
                if ik not in checked:checked_zip(z,im)
            measure(m,k,request['images'])
            references[k]=dict(reference=q[item]['reference'],category=q[item]['category'],cluster=q[item]['cluster_id'],support=support[item])
        input_reports['LoCoMo']=dict(rows=len(lm['rows']),question_reader_pairs=len(seen),clusters=len({r['cluster_id'] for r in q.values()}))
    for label,model in [('Qwen2B','Qwen/Qwen3.5-2B'),('Qwen9B','Qwen/Qwen3.5-9B'),('GLM','zai-org/GLM-4.6V-Flash')]:
        manifests['LoCoMo',label]=(lm,[r for r in lm['rows'] if r['model_id']==model],loc_seal)
    print('LoCoMo all 9000 input conditions checked',flush=True)
    cases={}
    for p in (ROOT/'iclr/pre_gpu_cpu_20260913/identifier_checkpoint/inputs/cases').glob('*.candidate.json'):
        c=read(p);cases[c['id']]=c
        ensure(abs(c['source_tokens']-8192)<=32,'identifier source length',c['id'])
        target={'early':.1,'middle':.5,'late':.9}[c['factors']['position']]
        ensure(abs(c['target_relative_position']-target)<=.02,'identifier target position',c['id'])
        ensure(sum(c['memory'].startswith(c['reference'],i) for i in range(len(c['memory'])))==1,'identifier target unique',c['id'])
        ensure(c['reference'] not in c['question'],'identifier answer leaks to question',c['id'])
        ensure(len(c['reference'])==c['factors']['length'],'identifier length factor',c['id'])
    cells=collections.Counter(tuple((k,v) for k,v in sorted(c['factors'].items()) if k!='instance') for c in cases.values())
    ensure(len(cases)==96 and len(cells)==48 and set(cells.values())=={2},'identifier factorial balance')
    for label,folder in [('Qwen2B','identifier_gpu_20260916'),('Qwen9B','identifier_qwen9b_20260917'),('GLM','identifier_glm_20260917')]:
        mp=ROOT/'iclr'/folder/'RUN_MANIFEST.json';m=read(mp);manifests['Identifier',label]=(m,m['rows'],sha(mp))
        for r in m['rows']:
            k=key(r);c=cases[r['item_id']];req=read(checked_local(r['request']));transport=read(checked_local(r['transport']))
            meas=read(checked_local(transport['measurement']))
            measure(meas,k,transport['images'])
            ensure(req['memory']==c['memory'] and req['question']==c['question'],'identifier identical canonical source',str(k))
            ensure(req['source_sha256']==digest(c['memory'].encode()),'identifier source digest',str(k))
            ensure(req['structurally_feasible'] and req['max_new_tokens']==64 and req['seed']==2026090506,'identifier settings',str(k))
            if r['condition']!='full_raw':
                ensure(req['relative_error']<=.1,'identifier optical budget',str(k))
                ensure(len(transport['images'])==int(r['condition'][-1]),'identifier page design',str(k))
            for im in transport['images']:checked_local(im)
            references[k]=dict(reference=c['reference'],factors=c['factors'])
    input_reports['Identifier']=dict(rows=2016,cases=96,factor_cells=48)
    print('Identifier all 2016 input conditions checked',flush=True)
    with zipfile.ZipFile(ROOT/'iclr/ruler_cpu5_20260917/ICLR-RULER-Merged-Checkpoint-A-E.zip') as z:
        rc={}
        for name in z.namelist():
            if name.startswith('generation/') and name.endswith('/CASES.jsonl'):
                for c in map(json.loads,z.read(name).decode().splitlines()):
                    rc[c['item_id']]=c
                    native=c['prompt_prefix']+c['memory']+c['prompt_suffix']
                    ensure(native==c['upstream']['input']+c['upstream']['answer_prefix'],'native RULER reconstruction',c['item_id'])
                    ensure(digest(native.encode())==c['native_prompt_sha256'],'RULER prompt digest',c['item_id'])
        for label,mkey in [('Qwen2B','qwen2b'),('Qwen9B','qwen9b'),('GLM','glm')]:
            mp=ROOT/f'iclr/ruler_gpu_20260919/RUN_MANIFEST_{mkey}.json';m=read(mp);manifests['RULER',label]=(m,m['rows'],sha(mp))
            for r in m['rows']:
                k=key(r);c=rc[r['item_id']]
                for rr in r['sealed_request_files']:checked_zip(z,rr)
                req=jbytes(checked_zip(z,r['request']));tr=r['transport'];meas=jbytes(checked_zip(z,tr['measurement']))
                measure(meas,k,tr['images'])
                ensure(req['structurally_feasible'],'RULER structural feasibility',str(k))
                if r['condition']!='full_raw':
                    ensure(req['relative_error']<=.1 and len(tr['images'])==4,'RULER budget/pages',str(k))
                references[k]=dict(reference=dict(task_id=c['task_id'],answers=c['reference']),task_id=c['task_id'],source_memory_sha256=c['memory_sha256'])
        input_reports['RULER']=dict(rows=2160,cases=len(rc),task_counts=dict(collections.Counter(c['task_id'] for c in rc.values())))
    print('RULER all 2160 input conditions checked',flush=True)
    put('INPUT_AUDIT.json',dict(status='passed' if not errors else 'failed',reports=input_reports,checked_file_references=len(checked),errors=errors))
    if errors:raise RuntimeError('Input audit failures; no outcome analysis performed')
    all_rows=[];result_reports=[]
    for record in public:
        study,label=record['study'],record['reader'];manifest,rows,seal=manifests[study,label]
        path=pathlib.Path(record['path']);ensure(sha(path)==record['sha256'],'outer archive changed',path.name)
        with zipfile.ZipFile(path) as outer:
            ensure(len(outer.namelist())==len(set(outer.namelist())),'duplicate outer archive',path.name)
            blob=outer.read('BLINDED_DO_NOT_OPEN.zip')
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names=jbytes(z.read('INDEX_PRIVATE.json'))
            ensure(len(names)==len(set(names)),'duplicate private index',path.name)
            ensure(set(z.namelist())=={'INDEX_PRIVATE.json'}|{f'records/{i:08d}.bin' for i in range(len(names))},'private archive inventory',path.name)
            index={n:f'records/{i:08d}.bin' for i,n in enumerate(names)}
            def data(n):return z.read(index[n])
            def jr(n):return jbytes(data(n))
            ensure(jr('MANIFEST_BINDING.json')=={'manifest_sha256':seal},'result manifest binding',path.name)
            dirs={n.split('/')[0] for n in names if '/' in n}
            expected={opaque(r) for r in rows}
            ensure(dirs==expected,'missing or extra result row',path.name)
            envs=[jr(n) for n in names if n.startswith('environment-') and n.endswith('.json')]
            approvals=[jr(n) for n in names if n.startswith('approval-') and n.endswith('.json')]
            cap={'LoCoMo':96,'Identifier':64,'RULER':128}[study]
            for e in envs:
                g=e['generation']
                ensure(e['torch']=='2.10.0+cu128' and e['transformers']=='5.3.0','runtime versions',path.name)
                ensure(g['max_new_tokens']==cap and g['do_sample'] is False and g['num_beams']==1,'generation settings',path.name)
            eos=set()
            for e in envs:
                v=e['generation'].get('eos_token_id');eos.update(v if isinstance(v,list) else [v])
            before=len(errors);terminations=collections.Counter();journal_ok=0;parity=0
            for r in rows:
                k=key(r);oid=opaque(r);start=jr(oid+'/START.json');done=jr(oid+'/COMPLETE.json')
                ensure(start=={'row_id':oid,'request_sha256':r['request_sha256']},'result start binding',str(k))
                ensure(done['row_id']==oid and done['request_sha256']==r['request_sha256'],'result complete binding',str(k))
                ensure({pathlib.PurePosixPath(rr['path']).name for rr in done['files']}=={'payload.bin','tokens.bin'},'result required files',str(k))
                for rr in done['files']:
                    n=rr['path'].removeprefix('BLINDED_DO_NOT_OPEN/');b=data(n)
                    ensure(n.startswith(oid+'/') and len(b)==rr['bytes'] and digest(b)==rr['sha256'],'result byte integrity',str(k))
                raw=jr(oid+'/payload.bin');tokens=jr(oid+'/tokens.bin');detail=jr(oid+'/DETAILS.json')
                ensure(raw['generated_token_ids']==tokens,'generated token agreement',str(k))
                journal=[jbytes(line) for line in data(oid+'/TOKEN_JOURNAL_PRIVATE.jsonl').splitlines()]
                ensure(journal[0]==[inputs[k]],'actual input journal agreement',str(k))
                generated=[v for part in journal[1:] for v in part]
                ensure(generated==tokens,'output journal agreement',str(k))
                journal_ok+=generated==tokens and journal[0]==[inputs[k]]
                ensure(len(tokens)<=cap and detail['total_input_tokens']==len(inputs[k]),'generation cap and input count',str(k))
                termination='eos' if tokens and tokens[-1] in eos else 'cap' if len(tokens)==cap else 'other'
                terminations[termination]+=1
                meta=references[k];task={'LoCoMo':'locomo','Identifier':'controlled','RULER':'ruler'}[study]
                scored=scoring.score(raw['prediction'],meta['reference'],task,meta.get('category'))
                if study=='LoCoMo':
                    fn=oracle.f1 if meta['category']==1 else oracle.f1_score
                    ensure(abs(fn(raw['prediction'],meta['reference'])-scored['native']['f1'])<1e-12,'official LoCoMo metric parity',str(k));parity+=1
                if study=='RULER':
                    native_raw=scoring.ruler_fraction(raw['prediction'],meta['reference']['answers'])
                    processed=re.sub(r'[\x00-\x1f]','\n',raw['prediction'].strip()).strip()
                    ensure(native_raw==scoring.ruler_fraction(processed,meta['reference']['answers']),'RULER wrapper affects containment',str(k));parity+=1
                all_rows.append(dict(study=study,reader=label,model=k[0],item_id=k[1],condition=k[2],
                    **meta,**budgets[k],prediction=raw['prediction'],decoded_with_special_tokens=raw['decoded_with_special_tokens'],
                    generated_token_count=len(tokens),termination=termination,score=scored,
                    generation_s=detail['generation_s'],preprocess_s=detail['preprocess_s'],archive=path.name))
            result_reports.append(dict(study=study,reader=label,rows=len(rows),environment_records=len(envs),approval_records=len(approvals),
                exact_input_and_output_journals=journal_ok,metric_parity_rows=parity,termination=dict(terminations),errors_added=len(errors)-before))
        print('Results audited',study,label,len(rows),'new errors',len(errors)-before,flush=True)
    with (OUT/'scored_rows.jsonl').open('w',encoding='utf-8') as f:
        for r in all_rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    put('RESULT_AUDIT.json',dict(status='passed' if not errors else 'failed',rows=len(all_rows),reports=result_reports,errors=errors,
        limitation='No GPU rerun or fresh processor execution. Input tokens verified against saved CPU measurements and actual generation journals; raw decoded strings will receive separate tokenizer reproduction checks.'))
    print('Finished',len(all_rows),'rows; errors',len(errors),flush=True)
