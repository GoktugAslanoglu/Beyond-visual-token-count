"""Fresh sources using the byte-unchanged audited crossover generator."""
import argparse
import importlib.util
import sys
from experiment_common import ROOT, REPO, LEGACY, CONFIG, put, sha

def generator_module(seed):
    runtime=REPO/'final_iclr/final_followups/runtime';sys.path.insert(0,str(runtime))
    spec=importlib.util.spec_from_file_location('final_experiment_source_adapter',runtime/'cases.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Rebind only this module's mapping: historical common.SEEDS remains unchanged.
    module.SEEDS=dict(module.SEEDS,crossover=seed)
    return module

def make_cases(split):
    from tokenizers import Tokenizer
    seed_key={'dev':'development','eval':'evaluation','smoke':'smoke'}[split]
    count_key={'dev':'n_development','eval':'n_eval','smoke':'n_smoke'}[split]
    tokenizer=Tokenizer.from_file(str(LEGACY/'assets/reference_tokenizer.json'))
    tokenizer.no_padding();tokenizer.no_truncation()
    count=lambda text:len(tokenizer.encode(text,add_special_tokens=False).ids)
    generator=generator_module(CONFIG['seeds'][seed_key]);result=[]
    for index in range(CONFIG[count_key]):
        case=generator.crossover(index,count)[2]
        assert case['regime']=='long'
        assert abs(case['source_tokens_reference']-CONFIG['source_tokens'])<=CONFIG['source_token_tolerance']
        case.update(id=f'final-{split}-{index:03}',base_id=f'final-{split}-{index:03}',split=split)
        result.append(case)
    return result

def build(split):
    folder=ROOT/'cases'/split
    if folder.exists(): raise FileExistsError('Immutable case set already exists')
    cases=make_cases(split)
    for case in cases: put(folder/(case['id']+'.json'),case)
    put(folder/'INDEX.json',{'split':split,'cases':[{'id':c['id'],'sha256':sha(folder/(c['id']+'.json'))} for c in cases],'weights_loaded':False,'model_calls':0})
    return cases

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['dev','eval','smoke'],required=True)
    a=p.parse_args();print(f'Built {len(build(a.split))} {a.split} sources; no inference.')
