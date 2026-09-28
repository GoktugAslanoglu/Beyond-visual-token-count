"""Frozen primary analyses plus explicitly labeled descriptive diagnostics."""
import collections,csv,itertools,json,pathlib,sys
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from iclr.stage04c_identifier_amended_20260913.amendment_checks import sign_test

def put(n,d): (OUT/n).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def interval(v):return list(map(float,np.quantile(v,[.025,.975])))
def mean(v):return float(np.mean(v))
def table(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__=='__main__':
    audit=json.loads((OUT/'RESULT_AUDIT_RESOLVED.json').read_text())
    if audit['unresolved_errors']:raise RuntimeError('Resolve audit failures before interpreting results')
    rows=[json.loads(s) for s in (OUT/'scored_rows.jsonl').read_text(encoding='utf-8').splitlines()]
    rng=np.random.default_rng(2026090505); B=50000
    result=dict(statistics_seed=2026090505,bootstrap_replicates=B,LoCoMo={},Identifier={},RULER={},hypotheses=[],limitations=[
        'LoCoMo inference is conditional on ten previously studied conversation clusters; increasing question count does not increase independent clusters.',
        'LoCoMo sign-flip inference assumes exchangeability/symmetry of cluster differences under the null. No random assignment of modality was performed.',
        'Identifier sign test concerns the frequency of positive non-tied case contrasts, not the mean effect. The factorial design has only two cases per cell.',
        'RULER intervals are conditional on six task templates and a shared corpus; the benchmark is synthetic and scoped, not the full official aggregate.',
        'Token counts are not compute or energy. Generation times include synchronous output-journal I/O and are descriptive, not controlled speed comparisons.',
        'Greedy single-seed runs do not estimate variation across independent stochastic generations.',
        'Zero-shot wording is inappropriate for native RULER VT, which includes a benchmark-provided worked example.'
    ])
    summary=[];clusters=sorted({r['cluster'] for r in rows if r['study']=='LoCoMo'})
    weights=rng.multinomial(len(clusters),[1/len(clusters)]*len(clusters),size=B)/len(clusters)
    for reader in ['Qwen2B','Qwen9B','GLM']:
        rr=[r for r in rows if r['study']=='LoCoMo' and r['reader']==reader]
        arms=sorted({r['condition'] for r in rr}); cm={};per_arm={}
        for arm in arms:
            a=[r for r in rr if r['condition']==arm]
            vals=np.array([mean([r['score']['canonical']['f1'] for r in a if r['cluster']==c]) for c in clusters]);cm[arm]=vals
            per_arm[arm]=dict(n=len(a),conversation_macro_f1=mean(vals),macro_ci95=interval(weights@vals),question_micro_f1=mean([r['score']['canonical']['f1'] for r in a]),native_question_f1=mean([r['score']['native']['f1'] for r in a]),
                category_f1={str(c):mean([r['score']['canonical']['f1'] for r in a if r['category']==c]) for c in [1,2,4]},
                empty=sum(not r['prediction'].strip() for r in a),cap=sum(r['termination']=='cap' for r in a),mean_input_tokens=mean([r['total_input_tokens'] for r in a]))
            summary.append(dict(study='LoCoMo',reader=reader,condition=arm,n=len(a),metric='conversation_macro_F1',value=mean(vals),ci_low=per_arm[arm]['macro_ci95'][0],ci_high=per_arm[arm]['macro_ci95'][1]))
        contrasts={}
        for name,left,right in [('H1','retrieved_optical_8px','full_optical_c2'),('H2','retrieved_optical_8px','retrieved_text'),('selected_budget','retrieved_optical_8px','retrieved_text_matched_selected'),('full_budget','full_optical_c2','retrieved_text_matched'),('full_raw_gap','full_raw','full_optical_c2')]:
            d=cm[left]-cm[right];ci=interval(weights@d)
            contrasts[name]=dict(left=left,right=right,effect=mean(d),ci95=ci,cluster_differences=dict(zip(clusters,map(float,d))),leave_one_cluster_out=[mean(np.delete(d,i)) for i in range(len(d))])
            if name=='H1':
                signs=np.array(list(itertools.product([-1,1],repeat=len(d))))
                p=float(np.mean(signs@d/len(d)>=mean(d)-1e-12))
                result['hypotheses'].append(dict(name='H1',reader=reader,p_value=p,effect=mean(d),ci95=ci,test='exact 1024 conversation sign flips'))
            if name=='H2':contrasts[name]['equivalence_within_003']=ci[0]>=-.03 and ci[1]<=.03
        chosen=[r for r in rr if r['condition']=='retrieved_optical_8px']
        coverage={}
        for cat in ['all',1,2,4]:
            subset=[r for r in chosen if cat=='all' or r['category']==cat]
            complete=[r for r in subset if r['support']['all_annotated_support']]
            incomplete=[r for r in subset if r['support']['all_annotated_support'] is False]
            coverage[str(cat)]=dict(n=len(subset),all_support_n=len(complete),unknown_annotation_n=sum(r['support']['support_recall'] is None for r in subset),mean_support_recall=mean([r['support']['support_recall'] for r in subset if r['support']['support_recall'] is not None]),f1_all_support=mean([r['score']['canonical']['f1'] for r in complete]) if complete else None,f1_incomplete_support=mean([r['score']['canonical']['f1'] for r in incomplete]) if incomplete else None)
        result['LoCoMo'][reader]=dict(arms=per_arm,contrasts=contrasts,support_coverage=coverage)
    # Pair-preserving resampling within each two-instance factorial cell.
    ident=[r for r in rows if r['study']=='Identifier'];ids=sorted({r['item_id'] for r in ident})
    factors={r['item_id']:r['factors'] for r in ident};cells=collections.defaultdict(list)
    for i,item in enumerate(ids):cells[tuple((k,v) for k,v in sorted(factors[item].items()) if k!='instance')].append(i)
    iw=np.zeros((B,len(ids)),dtype=np.float64)
    for pair in cells.values():
        assert len(pair)==2
        w=rng.binomial(2,.5,size=B);iw[:,pair[0]]=w/len(ids);iw[:,pair[1]]=(2-w)/len(ids)
    for reader in ['Qwen2B','Qwen9B','GLM']:
        rr=[r for r in ident if r['reader']==reader];arms=sorted({r['condition'] for r in rr});lookup={(r['item_id'],r['condition']):r for r in rr};vec={};per_arm={}
        for arm in arms:
            a=[lookup[item,arm] for item in ids];v=np.array([r['score']['canonical']['exact_match'] for r in a]);vec[arm]=v;ci=interval(iw@v)
            per_arm[arm]=dict(n=len(a),exact_match=mean(v),ci95=ci,cer=mean([r['score']['canonical']['cer'] for r in a]),cap=sum(r['termination']=='cap' for r in a),empty=sum(not r['prediction'].strip() for r in a))
            summary.append(dict(study='Identifier',reader=reader,condition=arm,n=len(a),metric='canonical_EM',value=mean(v),ci_low=ci[0],ci_high=ci[1]))
        optical=['optical_c2_p2','optical_c2_p4','optical_c4_p2','optical_c4_p4']
        raw=vec['full_raw'];op=np.stack([vec[a] for a in optical],axis=1)
        st=sign_test(raw.astype(int).tolist(),op.astype(int).tolist());d=raw-op.mean(axis=1);ci=interval(iw@d)
        result['hypotheses'].append(dict(name='H3',reader=reader,p_value=st['p_value'],effect=mean(d),ci95=ci,test='exact one-sided sign test of nonzero case contrasts',positive=st['positive'],negative=st['negative'],ties=st['ties']))
        marginals={}
        for factor in ['length','alphabet','entropy','distractors','position']:
            marginals[factor]={}
            for value in sorted({factors[i][factor] for i in ids},key=str):
                ix=[j for j,i in enumerate(ids) if factors[i][factor]==value]
                marginals[factor][str(value)]={a:mean(vec[a][ix]) for a in arms}
        result['Identifier'][reader]=dict(arms=per_arm,H3=st,contrast_ci95=ci,factor_marginal_em=marginals)
    for reader in ['Qwen2B','Qwen9B','GLM']:
        rr=[r for r in rows if r['study']=='RULER' and r['reader']==reader];arms=sorted({r['condition'] for r in rr});tasks=sorted({r['task_id'] for r in rr});per_arm={}
        tw={t:rng.multinomial(30,[1/30]*30,size=B)/30 for t in tasks}
        for arm in arms:
            per_task={};boots=[];strict=[]
            for t in tasks:
                a=sorted([r for r in rr if r['condition']==arm and r['task_id']==t],key=lambda r:r['item_id']);v=np.array([r['score']['native']['answer_containment_fraction'] for r in a]);bv=tw[t]@v;boots.append(bv)
                per_task[t]=dict(n=len(a),native_score_percent=round(100*mean(v),2),fraction=mean(v),ci95=interval(bv))
                if 'exact_match' in a[0]['score']['native']:
                    per_task[t]['strict_native_em']=mean([r['score']['native']['exact_match'] for r in a]);per_task[t]['canonical_em']=mean([r['score']['canonical']['exact_match'] for r in a]);per_task[t]['canonical_cer']=mean([r['score']['canonical']['cer'] for r in a]);strict.extend(a)
            a=[r for r in rr if r['condition']==arm];value=mean([v['fraction'] for v in per_task.values()]);ci=interval(np.mean(boots,axis=0))
            # Background-stratified descriptive sensitivity: template groups share fixed source styles.
            bg={name:mean([per_task[t]['fraction'] for t in group]) for name,group in {'essay':['niah_single_2','niah_single_3','niah_multivalue'],'repeated_noise':['niah_single_1','vt'],'needle':['niah_multikey_3']}.items()}
            per_arm[arm]=dict(n=len(a),scoped_native_fraction=value,ci95=ci,tasks=per_task,background_stratified_sensitivity=bg,cap=sum(r['termination']=='cap' for r in a),empty=sum(not r['prediction'].strip() for r in a))
            summary.append(dict(study='RULER',reader=reader,condition=arm,n=len(a),metric='scoped_native_containment',value=value,ci_low=ci[0],ci_high=ci[1]))
        result['RULER'][reader]=dict(arms=per_arm)
    hs=sorted(result['hypotheses'],key=lambda x:x['p_value']);last=0
    for i,h in enumerate(hs):
        last=max(last,min(1,(len(hs)-i)*h['p_value']));h['holm_adjusted_p']=last;h['reject_at_005']=last<=.05
    put('ANALYSIS.json',result);table('condition_summary.csv',summary)
    table('hypothesis_tests.csv',[{k:h.get(k) for k in ['name','reader','test','effect','p_value','holm_adjusted_p','reject_at_005','positive','negative','ties']} for h in result['hypotheses']])
    print(json.dumps({'hypotheses':result['hypotheses'],'summary_rows':len(summary)},indent=2))
