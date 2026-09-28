"""Frozen primary test; no secondary hypothesis testing or outcome-dependent choices."""
import argparse
from pathlib import Path
import numpy as np
import math
from experiment_common import ROOT, CONFIG, read, put, sha, verify_freeze
from analysis_utils import exact_mcnemar, stratified_paired_bootstrap, stratified_conservative_ci

def analyze_rows(rows):
    assert len(rows)==CONFIG['held_out_calls']
    cells={}
    for row in rows:
        assert row['arm'] in CONFIG['arms']
        assert row['position'] in ('early','middle','late')
        assert type(row['success']) is int and row['success'] in (0,1)
        for field in ('target_included','cap_hit','abstention'):
            assert type(row[field]) is bool
        for field in ('canonical_em','literal_em'):
            assert type(row[field]) is int and row[field] in (0,1)
        assert isinstance(row['cer'],(int,float)) and not isinstance(row['cer'],bool) and math.isfinite(row['cer']) and row['cer']>=0
        for field in ('source_native_tokens','stored_native_tokens','total_input_tokens','vision_tokens','nonvision_input_tokens','records_retained','source_records'):
            assert type(row[field]) is int and row[field]>=0
        assert row['source_native_tokens']>0 and row['source_records']>0
        assert row['records_retained']<=row['source_records']
        assert row['vision_tokens']+row['nonvision_input_tokens']==row['total_input_tokens']<=CONFIG['B']
        key=(row['case_id'],row['arm']);assert key not in cells;cells[key]=row
    ids=sorted({r['case_id'] for r in rows});assert len(ids)==CONFIG['n_eval']
    for cid in ids:
        assert {arm for c,arm in cells if c==cid}==set(CONFIG['arms'])
        assert len({cells[cid,arm]['position'] for arm in CONFIG['arms']})==1
    strata=[cells[cid,'optical']['position'] for cid in ids]
    assert all(strata.count(s)==50 for s in ('early','middle','late'))
    x={arm:np.array([cells[cid,arm]['success'] for cid in ids],int) for arm in CONFIG['arms']}
    a,b=x['optical'],x['compact_text'];d=a-b
    gain=int((d>0).sum());loss=int((d<0).sum());p=exact_mcnemar(gain,loss)
    classification=('optical_superiority' if d.mean()>0 else 'compact_text_superiority') if p<=.05 else 'inconclusive'
    summary={}
    for arm in CONFIG['arms']:
        rs=[cells[cid,arm] for cid in ids];included=[r for r in rs if r['target_included']];omitted=[r for r in rs if not r['target_included']]
        summary[arm]={'n':len(rs),'successes':int(x[arm].sum()),'accuracy':float(x[arm].mean()),
                      'included_n':len(included),'included_successes':sum(r['success'] for r in included),
                      'omitted_n':len(omitted),'omitted_successes':sum(r['success'] for r in omitted),
                      'conditional_recovery':sum(r['success'] for r in included)/len(included) if included else None,
                      'omitted_success_rate':sum(r['success'] for r in omitted)/len(omitted) if omitted else None,
                      'canonical_em':sum(r['canonical_em'] for r in rs)/len(rs),
                      'literal_em':sum(r['literal_em'] for r in rs)/len(rs),
                      'mean_cer':sum(r['cer'] for r in rs)/len(rs),
                      'cap_hits':sum(r['cap_hit'] for r in rs),'abstentions':sum(r['abstention'] for r in rs)}
    for arm in CONFIG['arms']:
        rs=[cells[cid,arm] for cid in ids]
        metrics={k:[r[k] for r in rs] for k in ('source_native_tokens','stored_native_tokens','total_input_tokens','vision_tokens','nonvision_input_tokens','records_retained','source_records')}
        metrics.update(record_fraction=[r['records_retained']/r['source_records'] for r in rs],
                       serialized_native_size_ratio=[r['stored_native_tokens']/r['source_native_tokens'] for r in rs],
                       source_to_total_budget_ratio=[r['source_native_tokens']/CONFIG['B'] for r in rs])
        summary[arm]['input_diagnostics']={k:{'mean':float(np.mean(v)),'min':float(min(v)),'max':float(max(v))} for k,v in metrics.items()}
        summary[arm]['positions']={pos:{'n':50,'successes':sum(r['success'] for r in rs if r['position']==pos),
                                         'included':sum(r['target_included'] for r in rs if r['position']==pos)}
                                   for pos in ('early','middle','late')}
    return {'status':'complete','primary':{'contrast':'optical-minus-compact_text','n':len(ids),
        'effect':float(d.mean()),'gains':gain,'losses':loss,'ties':len(ids)-gain-loss,'p':p,
        'alpha':.05,'test':'exact-two-sided-McNemar','multiplicity':'one confirmatory contrast',
        'bootstrap':stratified_paired_bootstrap(a,b,strata,seed=CONFIG['seeds']['bootstrap'],resamples=50000),
        'conservative_ci':stratified_conservative_ci(a,b,strata),'classification':classification},
        'arms':summary,'descriptive_differences':{
            'optical_minus_hash_text':float((x['optical']-x['hash_text']).mean()),
            'compact_minus_hash_text':float((x['compact_text']-x['hash_text']).mean())},
        'practical_collapse_flag':int(a.sum())<=15 and int(b.sum())<=15,
        'interpretation_file':'CLAIM_MATRIX.md','no_equivalence_test':True}

def main(scores, output):
    verify_freeze();blob=read(scores);assert blob['freeze_sha256']==sha(ROOT/'FREEZE.json')
    assert blob['audit_sha256']==sha(ROOT/'audit/RESULT_AUDIT.json')
    assert read(ROOT/'audit/RESULT_AUDIT.json')['status']=='passed'
    expected={(v['case_id'],v['arm']) for v in read(ROOT/'manifest.json')['rows']}
    assert {(v['case_id'],v['arm']) for v in blob['rows']}==expected
    result=analyze_rows(blob['rows']);result['scores_sha256']=sha(scores);result['freeze_sha256']=sha(ROOT/'FREEZE.json')
    put(output,result);print('Frozen analysis complete.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scores',type=Path,default=ROOT/'outputs/scored/scores.json');p.add_argument('--output',type=Path,default=ROOT/'analysis/RESULTS.json');a=p.parse_args();main(a.scores,a.output)
