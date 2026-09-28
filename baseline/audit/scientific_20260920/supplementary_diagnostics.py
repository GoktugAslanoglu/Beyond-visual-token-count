"""Post-unblinding descriptive tables, kept outside the six primary tests."""
import collections,csv,json,pathlib
import numpy as np
OUT=pathlib.Path(__file__).resolve().parent
rows=[json.loads(x) for x in (OUT/'scored_rows.jsonl').read_text(encoding='utf-8').splitlines()]
groups=collections.defaultdict(list)
for r in rows:
 if r['study']=='Identifier':
  f={k:v for k,v in r['factors'].items() if k!='instance'}
  groups[(r['reader'],r['condition'],tuple(sorted(f.items())))].append(r)
table=[]
for (reader,arm,fs),rs in sorted(groups.items()):
 assert len(rs)==2
 table.append(dict(reader=reader,condition=arm,**dict(fs),n=2,exact_match=float(np.mean([r['score']['canonical']['exact_match'] for r in rs])),cer=float(np.mean([r['score']['canonical']['cer'] for r in rs]))))
with (OUT/'identifier_joint_factor_cells.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
rng=np.random.default_rng(2026090505);out={'role':'post-unblinding secondary descriptive diagnostics; not additional confirmatory tests','RULER':{},'identifier_compressed_answer_containment':{}}
for reader in ['Qwen2B','Qwen9B','GLM']:
 rr=[r for r in rows if r['study']=='RULER' and r['reader']==reader];tasks=sorted({r['task_id'] for r in rr});arms=sorted({r['condition'] for r in rr})
 lookup={(r['task_id'],r['item_id'],r['condition']):r for r in rr};weights={t:rng.multinomial(30,[1/30]*30,size=50000)/30 for t in tasks}
 contrasts={}
 for arm in arms:
  if arm=='full_raw':continue
  boot=[];effects=[]
  for t in tasks:
   ids=sorted({r['item_id'] for r in rr if r['task_id']==t});d=np.array([lookup[t,i,arm]['score']['native']['answer_containment_fraction']-lookup[t,i,'full_raw']['score']['native']['answer_containment_fraction'] for i in ids]);effects.append(float(d.mean()));boot.append(weights[t]@d)
  b=np.mean(boot,axis=0)
  contrasts[arm+' minus raw']={'effect':float(np.mean(effects)),'ci95':list(map(float,np.quantile(b,[.025,.975]))),'task_effects':dict(zip(tasks,effects)),'leave_one_task_out_effects':[float(np.mean(np.delete(effects,i))) for i in range(6)]}
 out['RULER'][reader]=contrasts
 rr=[r for r in rows if r['study']=='Identifier' and r['reader']==reader and r['condition'] in ['optical_c2_p2','optical_c2_p4','optical_c4_p2','optical_c4_p4']]
 out['identifier_compressed_answer_containment'][reader]={'n':len(rr),'reference_anywhere_in_raw_output':sum(r['reference'] in r['prediction'] for r in rr),'canonical_exact_match':sum(r['score']['canonical']['exact_match'] for r in rr)}
(OUT/'SUPPLEMENTARY_DIAGNOSTICS.json').write_text(json.dumps(out,indent=2)+'\n')
print('Exported',len(table),'joint factor cells, 9 RULER paired contrasts, and 1152 identifier formatting checks')
