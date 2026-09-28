"""Independent reconciliation of manuscript values and per-output results."""
from pathlib import Path
from collections import defaultdict,Counter
import json,re,hashlib,math,csv
import numpy as np
P=Path(__file__).resolve().parent;R=P.parent;V=P/'verification'
def disk(p):
 s=str(p).replace('\\','/')
 for old,new in [('final_iclr/submission_2027/','paper/'),('final_iclr/','studies/'),('iclr/','baseline/')]:
  if s.startswith(old):s=new+s[len(old):];break
 return R/s
def j(p):return json.loads(disk(p).read_text(encoding='utf8'))
def lines(p):return [json.loads(s) for s in disk(p).read_text(encoding='utf8').splitlines() if s.strip()]
def at(v,ks):
 for k in ks:v=v[k]
 return v
checks=[]
def check(name,observed,expected,tol=1e-10):
 ok=math.isclose(float(observed),float(expected),abs_tol=tol,rel_tol=tol) if isinstance(expected,(int,float)) else observed==expected
 checks.append(dict(check=name,observed=observed,expected=expected,passed=bool(ok)))
 return ok
ledger=json.loads((V/'number_ledger.json').read_text())
cache={}
for key,entry in ledger.items():
 f=entry['source'];cache.setdefault(f,j(f));v=at(cache[f],entry['json_path'])
 check('ledger:'+key,format(v*entry['multiplier'],entry['format']),entry['display'])
refs=[]
for f in [P/'main.tex',P/'appendix.tex']+list(P.glob('table_*.tex')):
 for m in re.finditer(r'\\nval\{([^}]+)\}',f.read_text(encoding='utf8')):
  check('reference:'+f.name+':'+m[1],m[1] in ledger,True);refs.append(dict(file=f.name,key=m[1]))
for e in json.loads((V/'evidence_manifest.json').read_text()):check('hash:'+e['alias'],hashlib.sha256(disk(e['path']).read_bytes()).hexdigest(),e['sha256'])

# Recompute all historical means from the authoritative per-output scoring export.
orig=j('baseline/audit/scientific_20260920/ANALYSIS.json');old=lines('baseline/audit/scientific_20260920/scored_rows.jsonl')
check('original_rows',len(old),13176)
groups=defaultdict(list)
for x in old:groups[(x['study'],x['reader'],x['condition'])].append(x)
for (study,reader,arm),xs in groups.items():
 a=orig[study][reader]['arms'][arm];check('n:'+str((study,reader,arm)),len(xs),a['n'])
 if study=='LoCoMo':
  cl=defaultdict(list)
  for x in xs:cl[x['cluster']].append(x['score']['canonical']['f1'])
  v=np.mean([np.mean(z) for z in cl.values()]);check('clusters:'+reader+arm,len(cl),10)
  check('macro_f1:'+reader+arm,v,a['conversation_macro_f1'])
 elif study=='Identifier':check('original_id_em:'+reader+arm,np.mean([x['score']['canonical']['exact_match'] for x in xs]),a['exact_match'])
 else:check('ruler_native:'+reader+arm,np.mean([x['score']['native']['answer_containment_fraction'] for x in xs]),a['scoped_native_fraction'])

layout=j('studies/identifier_followup_results/analysis.json');lr=lines('studies/identifier_followup_results/rows.jsonl')
for r,v in layout['readers'].items():
 for a,t in v['arms'].items():
  xs=[x for x in lr if x['reader']==r and x['arm']==a]
  check('layout_count:'+r+a,sum(x['scores']['canonical']['exact_match'] for x in xs),t['correct']);check('layout_n:'+r+a,len(xs),t['n'])

def exact_mcnemar(g,l):
 n=g+l
 return min(1.,2*sum(math.comb(n,k) for k in range(min(g,l)+1))/2**n) if n else 1.
def holm(ps):
 idx=np.argsort(ps);ans=[0]*len(ps);last=0
 for i,k in enumerate(idx):last=max(last,min(1.,(len(ps)-i)*ps[k]));ans[k]=last
 return ans
budget=j('studies/final_followups/01_budget_crossover/analysis.json');br=lines('studies/final_followups/01_budget_crossover/rows.jsonl')
scale=j('studies/final_followups/02_geometry_mechanism/analysis.json');sr=lines('studies/final_followups/02_geometry_mechanism/rows.jsonl')
for study,data,rows,metric in [('budget',budget,br,'containment'),('scale',scale,sr,'em')]:
 for r,v in data['readers'].items():
  for a,t in v['table'].items():
   if study=='budget':
    for arm,cell in t.items():
     xs=[x for x in rows if x['reader']==r and x['regime']==a and x['arm']==arm]
     check(study+':count:'+r+a+arm,sum(x['scores'][metric] for x in xs),cell['correct']);check(study+':n:'+r+a+arm,len(xs),cell['n'])
   else:
    xs=[x for x in rows if x['reader']==r and x['arm']==a]
    check(study+':count:'+r+a,sum(x['scores'][metric] for x in xs),t['correct']);check(study+':caps:'+r+a,sum(x['cap_hit'] for x in xs),t['cap_hits'])
for x in br:
 check('budget_constraint:'+x['reader']+x['case_id']+x['arm'],x['accounting']['total_input_tokens']<=x['diagnostics']['B'],True)
 if x['arm']=='text':check('target_survival_equals_success:'+x['reader']+x['case_id'],int(x['diagnostics']['target_record_retained']),x['scores']['containment'])
 else:check('full_optical_coverage:'+x['reader']+x['case_id'],x['accounting']['retained_source_native_tokens'],x['accounting']['source_native_tokens'])
for study,data in [('layout',layout),('budget',budget)]:
 ps=[];expected=[]
 for r,v in data['readers'].items():
  t=v['primary'] if study=='layout' else v['secondary_long'];p=exact_mcnemar(t['gains'],t['losses']);check(study+':exact_p:'+r,p,t['p']);ps.append(p);expected.append(t['holm_p'])
 for i,(a,b) in enumerate(zip(holm(ps),expected)):check(study+':holm:'+str(i),a,b)
ps=[];expected=[]
for r,v in scale['readers'].items():
 for t in v['secondary']:
  p=exact_mcnemar(t['gains'],t['losses']);check('scale_exact_p:'+r+t['comparison'],p,t['p']);ps.append(p);expected.append(t['holm_p'])
for i,(a,b) in enumerate(zip(holm(ps),expected)):check('scale_secondary_holm:'+str(i),a,b)

# Recompute every summary statistic in the systems analysis, including unprinted diagnostics.
sys=j('studies/final_followups/03_systems_profile/analysis.json');rr=lines('studies/final_followups/03_systems_profile/rows.jsonl')
for c in sys['cells']:
 xs=[x for x in rr if (x['reader'],x['case_id'],x['arm'])==(c['reader'],c['case_id'],c['arm']) and x['phase']=='measured']
 check('system_n:'+str((c['reader'],c['case_id'],c['arm'])),len(xs),10)
 for m,v in c['timing'].items():
  a=np.array([x['timing'][m] for x in xs]);derived={'median':np.median(a),'q25':np.quantile(a,.25),'q75':np.quantile(a,.75),'min':min(a),'max':max(a),'n':len(a)}
  for stat,val in derived.items():check('systems:'+str((c['reader'],c['case_id'],c['arm'],m,stat)),val,v[stat])

# Cap reconstruction from original full-arm questions plus the saved rerun scores.
cap=j('studies/locomo_cap_followup/results/cap_analysis.json');cr=j('studies/locomo_cap_followup/results/cap_rows.json')
for r,c in cap['readers'].items():
 updates={x['case_id']:x for x in cr if x['reader']==r};cl=defaultdict(list)
 for x in old:
  if x['study']=='LoCoMo' and x['reader']==r and x['condition']=='full_optical_c2':cl[x['cluster']].append(updates.get(x['item_id'],{}).get('new_f1',x['score']['canonical']['f1']))
 check('cap_reconstruction:'+r,np.mean([np.mean(v) for v in cl.values()]),c['full_500_conversation_macro_sensitivity']);check('cap_n:'+r,len(updates),c['fixed_capped_n'])

# Independent recomputation of the descriptive summaries added at meta-review.
extra=json.loads((P/'evidence/derived.json').read_text())
for name,record in extra['provenance'].items():
 check('derived_input_hash:'+name,hashlib.sha256(disk(record['path']).read_bytes()).hexdigest(),record['sha256'])
for reader,arms in extra['rates'].items():
 for arm,expected in arms.items():
  obs=[v for v in old if (v['study'],v['reader'],v['condition'])==('RULER',reader,arm)]
  density=np.array([v['source_text_tokens']/v['vision_tokens'] for v in obs])
  actual={'n':len(obs),'S':np.median([v['source_text_tokens'] for v in obs]),'V':np.median([v['vision_tokens'] for v in obs]),'H':np.median([v['total_input_tokens']-v['vision_tokens'] for v in obs]),'T':np.median([v['total_input_tokens'] for v in obs]),'Cmin':density.min(),'Cmed':np.median(density),'Cmax':density.max()}
  for field,value in actual.items():check('realized_rate:'+reader+arm+field,float(value),expected[field])
for reader,entry in extra['budget'].items():
 pairs=defaultdict(dict)
 for v in br:
  if v['reader']==reader and v['regime']=='long':pairs[v['base_id']][v['arm']]=v['scores']['containment']
 check('long_pairs:'+reader,len(pairs),30)
 for field,pair in [('gains',(0,1)),('losses',(1,0))]:
  check('long_discordance:'+reader+field,sum((v['text'],v['optical'])==pair for v in pairs.values()),entry['long'][field])
for reader,arms in extra['incremental'].items():
 for arm,expected in arms.items():
  vals=np.array([v['timing']['peak_allocated_bytes']-v['timing']['baseline_allocated_bytes'] for v in rr if v['reader']==reader and v['arm']==arm and v['case_id'].endswith('long') and v['phase']=='measured'])
  for field,value in {'n':len(vals),'median':np.median(vals),'q25':np.percentile(vals,25),'q75':np.percentile(vals,75)}.items():check('incremental_memory:'+reader+arm+field,float(value),expected[field])
audit=json.loads((V/'meta_geometry_input_check.json').read_text())
check('metadata_comparison_count',len(audit['records']),extra['layout']['pairs'])
check('metadata_comparison_expected',audit['pairs'],144)
check('metadata_comparison_status',audit['status'],'passed')
check('metadata_same_source',audit['same_source_strings'],True)

# Independently reconcile every compact-control count and input diagnostic from preserved scored rows.
compact=j('studies/final_experiment/analysis/RESULTS.json')
cc=j('studies/final_experiment/config.json')
cx=j('studies/final_experiment/outputs/scored/scores.json')['rows']
check('compact_total_outputs',len(cx),cc['held_out_calls'])
cp=defaultdict(dict)
for row in cx:
 check('compact_unique:'+row['case_id']+row['arm'],row['arm'] not in cp[row['case_id']],True)
 cp[row['case_id']][row['arm']]=row
 check('compact_budget:'+row['case_id']+row['arm'],row['total_input_tokens']<=cc['B'],True)
 check('compact_em_agreement:'+row['case_id']+row['arm'],row['success'],row['canonical_em'])
 check('compact_literal_agreement:'+row['case_id']+row['arm'],row['success'],row['literal_em'])
check('compact_pairs',len(cp),cc['n_eval'])
for arm,expected in compact['arms'].items():
 xs=[x for x in cx if x['arm']==arm]
 for field,val in [('n',len(xs)),('successes',sum(x['success'] for x in xs)),('included_n',sum(x['target_included'] for x in xs)),('included_successes',sum(x['success'] for x in xs if x['target_included'])),('omitted_successes',sum(x['success'] for x in xs if not x['target_included'])),('cap_hits',sum(x['cap_hit'] for x in xs))]:check('compact:'+arm+field,val,expected[field])
 for metric,summary in expected['input_diagnostics'].items():
  vals=[(x['records_retained']/x['source_records'] if metric=='record_fraction' else x['stored_native_tokens']/x['source_native_tokens'] if metric=='serialized_native_size_ratio' else x['source_native_tokens']/cc['B'] if metric=='source_to_total_budget_ratio' else x[metric]) for x in xs]
  for field,val in [('mean',np.mean(vals)),('min',min(vals)),('max',max(vals))]:check('compact_input:'+arm+metric+field,val,summary[field])
 for pos,expected_pos in expected['positions'].items():
  ys=[x for x in xs if x['position']==pos]
  for field,val in [('n',len(ys)),('successes',sum(x['success'] for x in ys)),('included',sum(x['target_included'] for x in ys))]:check('compact_position:'+arm+pos+field,val,expected_pos[field])
g=sum(v['optical']['success']==1 and v['compact_text']['success']==0 for v in cp.values())
l=sum(v['optical']['success']==0 and v['compact_text']['success']==1 for v in cp.values())
for field,val in [('gains',g),('losses',l),('ties',len(cp)-g-l),('effect',(g-l)/len(cp)),('p',exact_mcnemar(g,l))]:check('compact_primary:'+field,val,compact['primary'][field])
cd=j('paper/evidence/compact_derived.json')
check('compact_capacity_gain',np.mean([v['compact_text']['records_retained']/v['hash_text']['records_retained']-1 for v in cp.values()]),cd['capacity_gain'])
for path,h in cd['provenance'].items():check('compact_provenance:'+path,hashlib.sha256(disk(path).read_bytes()).hexdigest(),h)
assert json.loads((R/'studies/final_experiment/audit/RESULT_CROSSCHECK.json').read_text(encoding='utf8'))['status']=='passed'

# Literal numerical parameters and prose approximations have explicit supporting artifacts.
support={
 '0':['original/Identifier/*/compressed exact_match; layout original EM; conceptual boundary'],
 '0.55':['studies/final_followups/02_geometry_mechanism/analysis.json: scale_0.55'],
 '0.75':['scale_0.75; baseline/protocol.json: external.retriever.b; layout readable threshold'],
 '0.8':['baseline/protocol.json: controlled.c_targets[0]'],
 '1':['normalization boundary/one-token profile; protocol and mathematical definition'],
 '1.00':['scale_1.00'],
 '1.5':['baseline/protocol.json: external.retriever.k1; or rounded finite-budget regime'],
 '2':['controlled.c_targets; page counts; factor levels; independent instances; mathematical permutation statement'],
 '3':['number of readers/scale levels; prespecified three-point equivalence/materiality; frozen testing families'],
 '4':['controlled.c_targets; pages; distractors; motif size; factor instances'],
 '5':['five-record geometry cases = one target + four distractors'],
 '6':['six RULER task configurations; six primary original tests; abstract rounded minimum H1 effect 6.0488355'],
 '8':['baseline/protocol.json: controlled.payload_lengths[0]; retrieved renderer source font'],
 '8.1':['original/RULER/Qwen9B/arms/optical_c4_p4/scoped_native_fraction *100 rounded to one decimal'],
 '10':['LoCoMo cluster count; target balance; measured repetitions; glyph threshold; execution-freeze entries'],
 '11':['controlled scale early/middle target-position counts in source manifest (11/11/10)'],
 '12':['layout PROTOCOL.json: dev_cases; ExactStrip baseline count in DEVELOPMENT_REAUDIT.json'],
 '13':['completion/preservation_checks/historical_files_unchanged'],
 '14':['DEVELOPMENT_REAUDIT.json: ExactStrip success count'],
 '16':['baseline/protocol.json: external.retriever.top_k; layout min em pixels'],
 '18':['DEVELOPMENT_REAUDIT.json: ExactStrip development sample size'],
 '19':['GLM LONG retained targets and correct text answers; budget analysis and scored rows'],
 '20':['studies/audits/ruler_extraction_classifications.json: frozen audit sample size'],
 '24':['controlled.payload_lengths[1]; renderer margin; layout bootstrap stratum count'],
 '30':['budget.n_base_cases; RULER per-task n; GLM budget LONG effect *100'],
 '32':['scale.n_cases; original identifier distractor factor'],
 '36':['layout PROTOCOL.json dev_calls; readable threshold .75 * 48'],
 '42':['layout PROTOCOL.json raw_control_em_threshold .875 * 48'],
 '45':['systems.cells length'],
 '48':['layout arm n; original factor cells'],
 '50':['budget target insertion percentage'],
 '64':['layout PROTOCOL.json max_new_tokens; final native REQUEST.json max_new_tokens'],
 '72':['minimum original RULER C0.8 72.3888889 rounded to integer'],
 '84':['maximum original RULER C0.8 83.7222222 rounded to integer'],
 '90':['budget target insertion percentage'],
 '95':['prespecified pointwise confidence level'],
 '96':['original Identifier arm n; baseline/protocol.json external.max_new_tokens'],
 '103':['completion preservation_checks SOURCE_FREEZE files_verified'],
 '105':['original LoCoMo category 1 inventory'],
 '108':['original LoCoMo category 2 inventory; original geometry sampled rerender count'],
 '121':['cap.readers.Qwen9B.fixed_capped_n'],
 '122':['final input SOURCE_RECONSTRUCTION_CHECK.json exact_case_dictionary_matches'],
 '126':['cap.readers.Qwen2B.fixed_capped_n'],
 '128':['baseline/v2/PROTOCOL_AMENDMENT.md RULER max_new_tokens; saved output configs'],
 '135':['systems.warmups'],
 '180':['original RULER arm n'],
 '247':['sum cap fixed_capped_n'],
 '256':['studies/identifier_followup/CAP_PROTOCOL.json'],
 '287':['original LoCoMo category 4 inventory'],
 '288':['scale.verified_rows'],
 '382':['studies/audits/identifier_output_audit.json canonical_response_counts'],
 '384':['identifier_output_audit.json all_compressed_glm_n'],
 '450':['systems.measured'],
 '500':['original LoCoMo arm n'],
 '540':['budget.verified_rows'],
 '576':['layout.verified_rows'],
 '585':['systems.generation_invocations and top_level_forward_passes'],
 '828':['completion.quality_outputs.total'],
 '868':['final geometry REQUEST.json image canvas for GLM'],
 '873':['final native NATIVE_INPUT_AUDIT.json native_tensor_rechecks'],
 '1008':['final geometry REQUEST.json image canvas for Qwen'],
 '1152':['96 cases * 4 compressed arms * 3 readers; checked original scored_rows'],
 '1372':['baseline/PROTOCOL.md retrieved-optical canvas; processor input records'],
 '1728':['layout DEEP_INPUT_CHECKS.json exact_pixel_pages'],
 '2016':['original FINAL_VERIFICATION.json study_counts.Identifier'],
 '2048':['budget PROTOCOL.md frozen reference SHORT source length'],
 '2160':['original FINAL_VERIFICATION.json study_counts.RULER'],
 '2340':['final NATIVE_INPUT_AUDIT.json pixel_exact_pages'],
 '3240':['systems FIGURE_AND_NUMBER_AUDIT.json independent_summary_checks'],
 '3348':['original GEOMETRY_AND_METHOD_DIAGNOSTICS.json complete_source_coverage_and_bbox_checks'],
 '320':['build_assets.py Figure 1 matched-page crop height; asset construction'],
 '360':['build_assets.py Figure 1 matched-page crop uses 360 x 320 pixels; figure asset construction, not a measured result'],
 '77.9':['baseline/audit/scientific_20260920/GEOMETRY_AND_METHOD_DIAGNOSTICS.json RULER optical_c2_p4 median_max_text_width_fraction * 100, rounded'],
 '12.3':['same audit Identifier optical_c2_p4 median_max_text_width_fraction * 100, rounded'],
 '8.4':['same audit Qwen RULER optical_c2_p4 glyph_range lower endpoint rounded'],
 '9.0':['same audit Qwen RULER optical_c2_p4 glyph_range upper endpoint rounded'],
 '4.1':['same audit Qwen Identifier optical_c2_p4 glyph_range lower endpoint rounded'],
 '4.5':['same audit Qwen Identifier optical_c2_p4 glyph_range upper endpoint rounded'],
 '6.9':['same audit GLM RULER optical_c2_p4 glyph_range lower endpoint rounded'],
 '7.8':['same audit GLM RULER optical_c2_p4 glyph_range upper endpoint rounded'],
 '3.5':['same audit GLM Identifier optical_c2_p4 glyph_range lower endpoint rounded'],
 '3.8':['same audit GLM Identifier optical_c2_p4 glyph_range upper endpoint rounded'],
 '3844':['GLM native vision_tokens in budget rows and layout DEEP_INPUT_CHECKS'],
 '3916':['GLM native budget rows diagnostics.B'],
 '4096':['Qwen native vision_tokens in budget rows and layout DEEP_INPUT_CHECKS'],
 '4173':['Qwen native budget rows diagnostics.B'],
 '6144':['budget PROTOCOL.md frozen reference MEDIUM source length'],
 '8192':['layout PROTOCOL.json source_tokens; RULER reference generation length; budget LONG design'],
 '9000':['original FINAL_VERIFICATION.json study_counts.LoCoMo'],
 '10000':['layout DEEP_INPUT_CHECKS.json Qwen readable vision count'],
 '13176':['original FINAL_VERIFICATION.json mandatory_unique_rows'],
 '13456':['layout DEEP_INPUT_CHECKS.json GLM readable vision count'],
 '48941':['original INPUT_AUDIT.json checked_file_references'],
 '50000':['original ANALYSIS.json bootstrap_replicates; frozen follow-up analysis protocols'],
 '0.72656':['DEVELOPMENT_REAUDIT.json ExactStrip exact McNemar p rounded to five decimals'],
}
support.update({'40':['compact config source_token_tolerance'],'53':['compact protocol empty-query optical scaffold'],'150':['compact config n_eval'],'0.05':['compact config alpha']})
literal=[];unclassified=[]
for file in ['main.tex','appendix.tex']:
 for lineno,line in enumerate((P/file).read_text(encoding='utf8').splitlines(),1):
  # Exclude file paths, labels, model names, formatting parameters, identifiers and hashes.
  if line.lstrip().startswith('%') or lineno<16 and file=='main.tex':continue
  s=re.sub(r'\\(?:nval|path|texttt|label|ref|citep|citet|includegraphics|input)\{[^}]*\}','',line)
  s=re.sub(r'Qwen(?:3\.5-[29]B|[29]B)|GLM-4\.6V-Flash|BF16|A100 40GB|SHA-?256|\bF1\b|\bH[123]\b|\bC[24]\b|k_1|[a-f0-9]{32,}', '',s)
  for m in re.finditer(r'(?<![A-Za-z0-9])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![A-Za-z0-9])',s):
   v=m[0].replace(',','');item=dict(file=file,line=lineno,literal=m[0],support=support.get(v))
   if 'Chapter~10' in line and v=='10':item['support']=['Cover and Thomas, second edition, Chapter 10; bibliographic chapter number, not experimental count']
   elif ('\\frac{1}{C}' in line or 'x<1' in line or 'x>1' in line or '$\\rho<1$' in line) and v=='1':item['support']=['Operational mathematical definition or normalized-capacity boundary; not a measured result']
   literal.append(item)
   if v not in support:unclassified.append(item)
(V/'literal_number_register.json').write_text(json.dumps(literal,indent=2),encoding='utf8')
fail=[x for x in checks if not x['passed']]
report=dict(status='passed' if not fail and not unclassified else 'needs-review',checks=len(checks),failed=fail,unclassified_literals=unclassified,ledger_entries=len(ledger),numeric_macro_occurrences=len(refs),literal_occurrences=len(literal),scope='All generated values resolved independently from authoritative JSON; result aggregates independently recomputed from preserved scored rows; literal design/rounding values mapped to explicit protocol or metadata evidence. Bibliographic/identifier/format numbers are separate from scientific measurements.')
(V/'NUMBER_CONSISTENCY_AUDIT.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(V/'number_checks.json').write_text(json.dumps(checks,indent=2,default=lambda x:float(x)),encoding='utf8')
print(json.dumps(report,indent=2))
