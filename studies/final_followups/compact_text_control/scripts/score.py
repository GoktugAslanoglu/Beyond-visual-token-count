"""Offline scoring only after complete, independently audited held-out execution."""
import argparse
from pathlib import Path
from experiment_common import ROOT, CONFIG, read, put, sha, verify_freeze
from vendor.scoring import score as historical_score

def score_answer(raw, reference):
    s=historical_score(raw, {'task_id':'niah_single_1','answers':[reference]}, 'ruler')
    return {'success':int(s['native']['answer_containment_fraction']),
            'canonical_em':int(s['canonical']['exact_match']),
            'literal_em':int(s['native']['literal_exact_match']),
            'cer':s['canonical']['cer'],
            'abstention':raw.strip().lower()=='no information available'}

def main(raw_dir, output):
    verify_freeze()
    report=read(ROOT/'audit/RESULT_AUDIT.json')
    assert report['status']=='passed' and report['raw_root']==str(raw_dir.resolve())
    assert report['freeze_sha256']==sha(ROOT/'FREEZE.json')
    rows=[]
    for record in report['records']:
        folder=raw_dir/record['path']
        assert sha(folder/'RAW.json')==record['raw_sha256']
        row=record['row']; case=read(ROOT/'cases/eval'/(row['case_id']+'.json'))
        req=read(ROOT/row['path']/'REQUEST.json'); raw=read(folder/'RAW.json')
        measurement=read(ROOT/row['path']/'MEASUREMENT.json')
        optical=read(ROOT/'inputs/eval'/row['case_id']/'optical/MEASUREMENT.json')
        rows.append({'case_id':row['case_id'],'arm':row['arm'],'position':case['position'],
                     'target_included':req['diagnostics']['target_included'],
                     'cap_hit':len(raw['generated_token_ids'])==CONFIG['max_new_tokens'],
                     'generated_tokens':len(raw['generated_token_ids']),
                     'source_native_tokens':optical['source_text_tokens'],
                     'stored_native_tokens':measurement['source_text_tokens'],
                     **{k:measurement[k] for k in ('total_input_tokens','vision_tokens','nonvision_input_tokens')},
                     **{k:req['diagnostics'][k] for k in ('records_retained','source_records')},
                     **score_answer(raw['prediction'],case['reference'])})
    assert len(rows)==CONFIG['held_out_calls']
    put(output,{'experiment_id':CONFIG['experiment_id'],'freeze_sha256':sha(ROOT/'FREEZE.json'),
                'audit_sha256':sha(ROOT/'audit/RESULT_AUDIT.json'),'rows':rows})
    print('Scored all 450 audited outputs; no model calls.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,default=ROOT/'outputs/raw')
    p.add_argument('--output',type=Path,default=ROOT/'outputs/scored/scores.json');a=p.parse_args();main(a.raw,a.output)
