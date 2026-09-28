"""Exhaustive candidate-count conformance on the three development sources only."""
import time
from experiment_common import ROOT,CONFIG,read,put,load_processor,text_count,empty_question_counter
from storage import pack

def main():
    p=load_processor();fast=empty_question_counter(p);checks=0;started=time.perf_counter()
    def checked(memory):
        nonlocal checks
        n=fast(memory);assert n==text_count(p,memory,''), 'Native counter diverged';checks+=1;return n
    for item in read(ROOT/'cases/dev/INDEX.json')['cases']:
        c=read(ROOT/'cases/dev'/(item['id']+'.json'))
        for compact in (False,True):
            pack(c['records'],c['base_id'],checked,CONFIG['B'],128,CONFIG['seeds']['retention'],compact)
    put(ROOT/'audit/COUNTER_CONFORMANCE.json',{'status':'passed','native_candidate_counts_compared':checks,
        'differences':0,'scope':'all greedy candidates on three development sources; same native backend and literal chat bytes',
        'model_calls':0,'elapsed_s':time.perf_counter()-started})
    print('Exact native counter conformance passed on all development candidates.',flush=True)

if __name__=='__main__':main()
