"""Require every frozen cell and independently recompute scores before any claims."""
import argparse,pathlib,json,math,itertools
import numpy as np
from common import *
from paired_stats import paired,bootstrap,exact_signflip,exact_q,holm
from tokenizers import Tokenizer
def independent_score(raw,answer):
 # Independent canonicalization and dynamic-programming edit distance.
 v=raw.strip();left='<|begin_of_box|>';right='<|end_of_box|>'
 if v.startswith(left) and v.endswith(right) and v.count(left)==v.count(right)==1:v=v[len(left):-len(right)].strip()
 v=' '.join(v.split());a=' '.join(answer.split());grid=np.zeros((len(a)+1,len(v)+1),dtype=int);grid[:,0]=range(len(a)+1);grid[0,:]=range(len(v)+1)
 for i in range(1,len(a)+1):
  for j in range(1,len(v)+1):grid[i,j]=min(grid[i-1,j]+1,grid[i,j-1]+1,grid[i-1,j-1]+int(a[i-1]!=v[j-1]))
 return {'em':int(v==a),'cer':int(grid[-1,-1])/max(1,len(a)),'containment':int(answer.lower() in raw.lower()),'literal_em':int(raw==answer)}
def independently_check_signflip(d,p):
 n1=sum(abs(int(v))==1 for v in d);n2=sum(abs(int(v))==2 for v in d);threshold=abs(sum(d));ways=0
 for k in range(n1+1):
  for j in range(n2+1):
   if abs(2*k-n1+2*(2*j-n2))>=threshold:ways+=math.comb(n1,k)*math.comb(n2,j)
 assert abs(p-ways/2**(n1+n2))<1e-14
def expected_order(rows,reader,profile):
 if not profile:return [(r,'quality',0) for r in sorted(rows,key=lambda r:digest(f"{SEEDS['order']}|{reader}|{r['case_id']}|{r['arm']}"))]
 out=[]
 for phase,n in [('warmup',3),('measured',10)]:
  for rep in range(n):
   for regime in sorted(['short','medium','long'],key=lambda s:digest(f"{SEEDS['order']}|{rep}|{s}")):
    rr=sorted([r for r in rows if r['case_id'].endswith('-'+regime)],key=lambda r:r['arm']);k=rep%5
    out.extend((r,phase,rep) for r in rr[k:]+rr[:k])
 return out
def verify(prepared,outputs,study):
 verify_source();verify_files(ROOT,read(ROOT/'EXECUTION_FREEZE.json')['files'])
 f=read(prepared/study/'FREEZE.json');verify_files(prepared/study,f['files']);records=[];seen=set();profile=study==STUDIES[2]
 for output in outputs:
  start=read(output/'RUN_START.json');done=read(output/'RUN_COMPLETE.json');reader=start['reader'];assert reader in READERS and reader not in seen;seen.add(reader)
  assert start['study']==study and start['input_freeze_sha256']==sha(prepared/study/'FREEZE.json') and start['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json') and start['execution_freeze_sha256']==sha(ROOT/'EXECUTION_FREEZE.json')
  env=read(output/'ENVIRONMENT.json');pin=read(LEGACY/f'environment/{reader}_SNAPSHOT.json')
  assert env['torch']=='2.10.0+cu128' and env['transformers']=='5.3.0' and env['tokenizers']=='0.22.2' and env['revision']==pin['revision'] and 'A100' in env['gpu']
  cap=1 if profile else 64;assert env['generation']['max_new_tokens']==cap and env['generation']['do_sample']==False and env['generation']['num_beams']==1 and env['attention']=='sdpa' and env['dtype']=='bfloat16'
  want=[r for r in f['rows'] if r['reader']==reader];order=expected_order(want,reader,profile)
  assert read(output/'ORDER.json')==[{'row':r,'phase':phase,'repetition':rep} for r,phase,rep in order]
  assert done['status']=='complete-unverified' and done['generation_invocations']==len(order)
  assert done['quality_calls']==(0 if profile else len(order)) and done['systems_forward_passes']==(len(order) if profile else 0)
  folders={f"{i:04}--{r['case_id']}--{r['arm']}" for i,(r,phase,rep) in enumerate(order)}
  assert {p.name for p in output.iterdir() if p.is_dir()}==folders
  tok=Tokenizer.from_file(str(LEGACY/'assets'/('glm_tokenizer.json' if reader=='GLM' else 'reference_tokenizer.json')))
  for index,(r,phase,rep) in enumerate(order):
   folder=output/f"{index:04}--{r['case_id']}--{r['arm']}";s=read(folder/'START.json');c=read(folder/'COMPLETE.json');raw=read(folder/'RAW.json')
   assert s=={'index':index,'row':r,'phase':phase,'repetition':rep,'cap':cap,'input_freeze_sha256':sha(prepared/study/'FREEZE.json')}
   assert c['raw_sha256']==sha(folder/'RAW.json') and c['journal_sha256']==sha(folder/'TOKENS.jsonl')
   request=read(prepared/r['path']/'REQUEST.json');m=read(prepared/r['path']/'MEASUREMENT.json')
   ids=raw['generated_token_ids'];assert 0<len(ids)<=cap and c['generated_tokens']==len(ids) and c['cap_hit']==(len(ids)==cap)
   journal=[json.loads(line) for line in (folder/'TOKENS.jsonl').read_text().splitlines()]
   assert journal[0]==[m['input_token_ids']] and [x for line in journal[1:] for x in line]==ids
   assert tok.decode(ids,skip_special_tokens=True)==raw['prediction'] and tok.decode(ids,skip_special_tokens=False)==raw['decoded_with_special_tokens']
   row=dict(r,phase=phase,repetition=rep,prediction=raw['prediction'],generated_token_ids=ids,cap_hit=c['cap_hit'],accounting=request['accounting'],diagnostics=request['diagnostics'])
   if profile:
    t=c['timing'];assert t['top_level_forward_passes']==1 and all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in t.values())
    assert t['pipeline_ttft_s']<=t['end_to_end_one_token_s'] and t['prefill_including_vision_s']<=t['model_generate_s'] and t['peak_allocated_bytes']>=t['baseline_allocated_bytes']
    row['timing']=t
   else:
    case=read(prepared/study/'cases'/(r['case_id']+'.json'));scores=independent_score(raw['prediction'],case['reference']);primary=score(raw['prediction'],case['reference'],'controlled')
    assert scores['em']==primary['canonical']['exact_match'] and abs(scores['cer']-primary['canonical']['cer'])<1e-12
    if study==STUDIES[0]:assert scores['containment']==score(raw['prediction'],{'task_id':'niah_single_1','answers':[case['reference']]},'ruler')['native']['answer_containment_fraction']
    row['scores']=scores;row['base_id']=case.get('base_id',case['id']);row['regime']=case.get('regime')
   records.append(row)
 assert seen==set(READERS),'All three readers required before analysis'
 assert len(records)==(585 if profile else f['expected_unique_inputs'])
 return records
def accuracy(rows,metric):
 return {'n':len(rows),'correct':sum(r['scores'][metric] for r in rows),'accuracy':float(np.mean([r['scores'][metric] for r in rows])),'em':float(np.mean([r['scores']['em'] for r in rows])),'cer':float(np.mean([r['scores']['cer'] for r in rows])),'literal_em':float(np.mean([r['scores']['literal_em'] for r in rows])),'cap_hits':sum(r['cap_hit'] for r in rows)}
def analyze_cross(rows):
 results={};primary=[];secondary=[]
 for j,reader in enumerate(READERS):
  rr=[r for r in rows if r['reader']==reader];look={(r['base_id'],r['regime'],r['arm']):r for r in rr};ids=sorted({r['base_id'] for r in rr});vectors={};table={};delta={}
  for regime in ['short','medium','long']:
   table[regime]={}
   for arm in ['text','optical']:
    cell=[look[i,regime,arm] for i in ids];vectors[regime,arm]=np.array([r['scores']['containment'] for r in cell],int);table[regime][arm]=accuracy(cell,'containment')
    table[regime][arm]['normalized_source_length_mean']=float(np.mean([r['diagnostics']['normalized_source_length'] for r in cell]))
    table[regime][arm]['normalized_source_length_range']=[min(r['diagnostics']['normalized_source_length'] for r in cell),max(r['diagnostics']['normalized_source_length'] for r in cell)]
   delta[regime]=paired(vectors[regime,'optical'],vectors[regime,'text'],SEEDS['bootstrap']+j)
  d=(vectors['long','optical']-vectors['long','text'])-(vectors['short','optical']-vectors['short','text'])
  test={'reader':reader,'effect':float(d.mean()),'ci95':bootstrap(d,SEEDS['bootstrap']+j),'p':exact_signflip(d)};independently_check_signflip(d,test['p']);primary.append(test)
  sec=dict(delta['long'],reader=reader);secondary.append(sec);independently_check_signflip(vectors['long','optical']-vectors['long','text'],sec['p'])
  results[reader]={'table':table,'delta':delta,'primary_interaction':test,'secondary_long':sec,'descriptive_crossover':delta['short']['effect']<0<delta['long']['effect'],'both_long_collapse_flag':max(table['long'][a]['correct'] for a in ['text','optical'])<=3,'text_wins_every_length':all(delta[s]['effect']<0 for s in delta),'diagnostics':{s:{'target_survived_text':sum(look[i,s,'text']['diagnostics']['target_record_retained'] for i in ids),'n':30} for s in ['short','medium','long']}}
 holm(primary);holm(secondary)
 for r in results.values():
  r['supported_relative_improvement']=r['primary_interaction']['effect']>0 and r['primary_interaction']['holm_p']<=.05 and r['primary_interaction']['ci95'][0]>0
  r['supported_long_optical_advantage']=r['secondary_long']['effect']>0 and r['secondary_long']['holm_p']<=.05 and r['secondary_long']['ci95'][0]>0
 return {'primary_metric':'native single-answer containment','readers':results,'n_base_cases':30,'warning':'sign-flip symmetry assumption; pointwise bootstrap intervals; no general optical superiority'}
def analyze_geometry(rows):
 results={};primary=[];secondary=[];arms=['scale_0.55','scale_0.75','scale_1.00']
 for j,reader in enumerate(READERS):
  rr=[r for r in rows if r['reader']==reader];ids=sorted({r['case_id'] for r in rr});look={(r['case_id'],r['arm']):r for r in rr}
  x=np.array([[look[i,a]['scores']['em'] for a in arms] for i in ids]);q=dict(exact_q(x),reader=reader);primary.append(q);pairs=[]
  for a,b in [(2,0),(2,1),(1,0)]:
   t=dict(paired(x[:,a],x[:,b],SEEDS['bootstrap']+j),reader=reader,comparison=arms[a]+' minus '+arms[b]);independently_check_signflip(x[:,a]-x[:,b],t['p']);pairs.append(t);secondary.append(t)
  results[reader]={'table':{a:accuracy([look[i,a] for i in ids],'em') for a in arms},'primary':q,'secondary':pairs}
 holm(primary);holm(secondary)
 return {'primary_metric':'canonical EM','readers':results,'n_cases':32,'secondary_family_size':9,'warning':'Scale and occupied area covary. No glyph-only or universal monotonic law.'}
def summarize(values):
 a=np.asarray(values,float);return {'median':float(np.median(a)),'q25':float(np.quantile(a,.25)),'q75':float(np.quantile(a,.75)),'min':float(a.min()),'max':float(a.max()),'n':len(a)}
def analyze_systems(rows):
 cells=[]
 for reader in READERS:
  for case in sorted({r['case_id'] for r in rows}):
   for arm in sorted({r['arm'] for r in rows}):
    rr=[r for r in rows if r['reader']==reader and r['case_id']==case and r['arm']==arm];assert len(rr)==13
    m=[r for r in rr if r['phase']=='measured'];w=[r for r in rr if r['phase']=='warmup'];assert len(m)==10 and len(w)==3
    assert all(r['accounting']==rr[0]['accounting'] for r in rr)
    cells.append({'reader':reader,'case_id':case,'arm':arm,'accounting':rr[0]['accounting'],'timing':{k:summarize([r['timing'][k] for r in m]) for k in m[0]['timing']},'warmup_n':3})
 return {'cells':cells,'generation_invocations':585,'top_level_forward_passes':sum(r['timing']['top_level_forward_passes'] for r in rows),'warmups':135,'measured':450,'sampling':'one predetermined source per length; repeated timings are systems repetitions, not independent scientific cases','regime':'resident model, cleared allocator; combined prefill includes vision; no energy/cost/FLOPs measures'}
def report(study,a):
 lines=['# Audited final-round results','',f'Study: {study}. All frozen cells completed and passed audit.','']
 if study==STUDIES[0]:
  lines+=['| Reader | Length | Text correct /30 | Optical correct /30 |','|---|---|---:|---:|']
  for reader,r in a['readers'].items():
   for length,cell in r['table'].items():lines.append(f"| {reader} | {length} | {cell['text']['correct']} | {cell['optical']['correct']} |")
   lines+=['',f"{reader}: primary interaction {r['primary_interaction']}; secondary LONG {r['secondary_long']}; descriptive crossover {r['descriptive_crossover']}; supported LONG advantage {r['supported_long_optical_advantage']}.",'']
 elif study==STUDIES[1]:
  lines+=['| Reader | Scale | EM correct /32 | CER |','|---|---|---:|---:|']
  for reader,r in a['readers'].items():
   for arm,cell in r['table'].items():lines.append(f"| {reader} | {arm} | {cell['correct']} | {cell['cer']:.4f} |")
   lines+=['',f"{reader}: primary {r['primary']}; secondary {r['secondary']}.",'']
 else:
  lines+=['| Reader | Source | Condition | Total input | Render/pack s | Processor s | Prefill s | Pipeline TTFT s | End-to-end s | Peak allocated GiB |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
  for c in a['cells']:
   t=c['timing'];vals=[t[k]['median'] for k in ['render_or_pack_s','processor_s','prefill_including_vision_s','pipeline_ttft_s','end_to_end_one_token_s']]
   lines.append(f"| {c['reader']} | {c['case_id']} | {c['arm']} | {c['accounting']['total_input_tokens']} | "+' | '.join(f'{x:.4f}' for x in vals)+f" | {t['peak_allocated_bytes']['median']/1024**3:.3f} |")
  lines+=['','Dispersion and all input accounting are in analysis.json. One fixed source per length; no task accuracy is inferred from timing outputs.']
 lines+=['','Interpretation must follow the frozen protocol. Manuscript integration remains gated on all three audited studies.']
 return '\n'.join(lines)+'\n'
def main(prepared,outputs,study,dest):
 rows=verify(prepared,outputs,study);a=({'01_budget_crossover':analyze_cross,'02_geometry_mechanism':analyze_geometry,'03_systems_profile':analyze_systems}[study])(rows);dest.mkdir(parents=True,exist_ok=False)
 put(dest/'analysis.json',dict(a,status='passed',verified_rows=len(rows)));put(dest/'audit.json',{'status':'passed','rows':len(rows),'study':study,'input_freeze_sha256':sha(prepared/study/'FREEZE.json'),'output_complete_hashes':{str(p):sha(p/'RUN_COMPLETE.json') for p in outputs}})
 with (dest/'rows.jsonl').open('x',encoding='utf-8') as f:
  for row in rows:f.write(json.dumps(row)+'\n')
 (dest/'RESULTS.md').write_text(report(study,a),encoding='utf-8');(dest/'AUDIT.md').write_text('# Audit passed\n\nAll frozen reader/case/condition cells, model pins, generation settings, deterministic execution order, token journals, decoding and raw hashes verified. Quality scores independently recomputed; paired exact-test arithmetic cross-checked. Prepared input manifests retained. No partial dataset scored. Figure visual inspection is a separate required check.\n',encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=pathlib.Path,required=True);p.add_argument('--outputs',type=pathlib.Path,nargs='+',required=True);p.add_argument('--study',choices=STUDIES,required=True);p.add_argument('--destination',type=pathlib.Path,required=True);a=p.parse_args();main(a.prepared,a.outputs,a.study,a.destination)
