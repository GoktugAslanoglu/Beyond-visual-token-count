"""Generate numeric LaTeX, vector figures and evidence ledger from audited JSON."""
from pathlib import Path
import json, hashlib, shutil, csv, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch
from PIL import Image

OUT=Path(__file__).resolve().parent; ROOT=OUT.parent
FILES={
 'original':'baseline/audit/scientific_20260920/ANALYSIS.json',
 'layout':'studies/identifier_followup_results/analysis.json',
 'cap':'studies/locomo_cap_followup/results/cap_analysis.json',
 'budget':'studies/final_followups/01_budget_crossover/analysis.json',
 'scale':'studies/final_followups/02_geometry_mechanism/analysis.json',
 'systems':'studies/final_followups/03_systems_profile/analysis.json',
 'sensitivity':'studies/audits/locomo_cluster_sensitivity.json',
 'completion':'studies/final_followups/FINAL_COMPLETION_AUDIT.json',
 'compact':'studies/final_experiment/analysis/RESULTS.json',
 'compact_config':'studies/final_experiment/config.json',
}
D={k:json.loads((ROOT/v).read_text(encoding='utf8')) for k,v in FILES.items()}
# Descriptive additions use preserved observations, never fresh inference.
def read_rows(path):
 return [json.loads(x) for x in (ROOT/path).read_text(encoding='utf8').splitlines() if x.strip()]
derived_inputs={
 'original_rows':'baseline/audit/scientific_20260920/scored_rows.jsonl',
 'budget_rows':'studies/final_followups/01_budget_crossover/rows.jsonl',
 'systems_rows':'studies/final_followups/03_systems_profile/rows.jsonl',
 'layout_check':'paper/verification/meta_geometry_input_check.json'}
original_rows=read_rows(derived_inputs['original_rows'])
budget_rows=read_rows(derived_inputs['budget_rows'])
systems_rows=read_rows(derived_inputs['systems_rows'])
derived={'provenance':{k:{'path':v,'sha256':hashlib.sha256((ROOT/v).read_bytes()).hexdigest()} for k,v in derived_inputs.items()},'rates':{},'budget':{},'incremental':{}}
for reader in ['Qwen2B','Qwen9B','GLM']:
 derived['rates'][reader]={}
 for arm in ['optical_c0p8_p4','optical_c2_p4','optical_c4_p4']:
  rr=[v for v in original_rows if v['study']=='RULER' and v['reader']==reader and v['condition']==arm]
  ce=[v['source_text_tokens']/v['vision_tokens'] for v in rr]
  derived['rates'][reader][arm]={'n':len(rr),'S':float(np.median([v['source_text_tokens'] for v in rr])),'V':float(np.median([v['vision_tokens'] for v in rr])),'H':float(np.median([v['total_input_tokens']-v['vision_tokens'] for v in rr])),'T':float(np.median([v['total_input_tokens'] for v in rr])),'Cmin':min(ce),'Cmed':float(np.median(ce)),'Cmax':max(ce)}
 pairs={}
 for v in budget_rows:
  if v['reader']==reader and v['regime']=='long':pairs.setdefault(v['base_id'],{})[v['arm']]=v['scores']['containment']
 derived['budget'][reader]={'long':{'gains':sum(v['optical']==1 and v['text']==0 for v in pairs.values()),'losses':sum(v['optical']==0 and v['text']==1 for v in pairs.values())}}
 derived['incremental'][reader]={}
 for arm in ['A_full_text','A_optical_C2','A_optical_C4','B_text','B_optical']:
  vals=[v['timing']['peak_allocated_bytes']-v['timing']['baseline_allocated_bytes'] for v in systems_rows if v['reader']==reader and v['case_id'].endswith('long') and v['arm']==arm and v['phase']=='measured']
  derived['incremental'][reader][arm]={'n':len(vals),'median':float(np.median(vals)),'q25':float(np.quantile(vals,.25)),'q75':float(np.quantile(vals,.75))}
derived['layout']={'pairs':json.loads((ROOT/derived_inputs['layout_check']).read_text(encoding='utf8'))['pairs']}
FILES['derived']='paper/evidence/derived.json'
(ROOT/FILES['derived']).write_text(json.dumps(derived,indent=2),encoding='utf8')
D['derived']=derived
READERS=['Qwen2B','Qwen9B','GLM'];COLORS=['#27699c','#d17b25','#268475']
ledger={}; figures={}
def get(src,keys):
 v=D[src]
 for k in keys:v=v[k]
 return v
def num(name,src,keys,scale=1,fmt='.2f'):
 v=get(src,keys); shown=format(v*scale,fmt)
 ledger[name]=dict(source=FILES[src],json_path=keys,raw=v,multiplier=scale,format=fmt,display=shown)
 return r'\nval{'+name+'}'
def nv(name):return r'\nval{'+name+'}'
def esc(s):return str(s).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def tabfile(name,cols,header,rows):
 text=r'\begin{tabular}{'+cols+'}\n'+r'\toprule'+'\n'+header+r'\\'+'\n'+r'\midrule'+'\n'
 text+='\n'.join(' & '.join(row)+r'\\' for row in rows)+'\n'+r'\bottomrule\end{tabular}'+'\n'
 (OUT/(name+'.tex')).write_text(text,encoding='utf8')

# Native-rate and memory summaries newly exposed in the manuscript.
num('derived.layout.pairs','derived',['layout','pairs'],1,'.0f')
rate_arms=['optical_c0p8_p4','optical_c2_p4','optical_c4_p4']
for r in READERS:
 for a in rate_arms:
  for f in ['n','S','V','H','T','Cmin','Cmed','Cmax']:
   num(f'derived.rates.{r}.{a}.{f}','derived',['rates',r,a,f],1,'.3f' if f.startswith('C') else '.0f')
 for f in ['gains','losses']:num(f'derived.budget.{r}.long.{f}','derived',['budget',r,'long',f],1,'.0f')
 for a in D['derived']['incremental'][r]:
  for f in ['median','q25','q75']:num(f'derived.incremental.{r}.{a}.{f}','derived',['incremental',r,a,f],1/2**30,'.3f')
assert D['derived']['rates']['Qwen2B']==D['derived']['rates']['Qwen9B']
tabfile('table_ruler_rates_compact','lrrr','Reader & Nominal $C=0.8$ & $C=2$ & $C=4$',[[label]+[nv(f'derived.rates.{r}.{a}.Cmed') for a in rate_arms] for label,r in [('Qwen2B / Qwen9B','Qwen2B'),('GLM','GLM')]])
rows=[]
for r in READERS:
 for a,c in zip(rate_arms,['0.8','2','4']):
  prefix=f'derived.rates.{r}.{a}.'
  rows.append([r,c]+[nv(prefix+f) for f in ['S','V','H','T']]+[nv(prefix+'Cmed')+' ['+nv(prefix+'Cmin')+', '+nv(prefix+'Cmax')+']'])
tabfile('table_ruler_rates_full','llrrrrr','Reader & $C$ & Source & Vision & Nonvision & Total & $C_{\\rm eff}$ median [range]',rows)
rows=[]
for a,label in [('A_full_text','A: text'),('A_optical_C2','A: C2'),('A_optical_C4','A: C4'),('B_text','B: text'),('B_optical','B: optical')]:
 rows.append([label]+[nv(f'derived.incremental.{r}.{a}.median')+' ['+nv(f'derived.incremental.{r}.{a}.q25')+', '+nv(f'derived.incremental.{r}.{a}.q75')+']' for r in READERS])
tabfile('table_systems_incremental','lrrr','LONG arm & Qwen2B & Qwen9B & GLM',rows)

# All recurring numerical values in prose and tables are referenced by key.
for r in READERS:
 for a,v in D['original']['LoCoMo'][r]['arms'].items():
  for field in ['conversation_macro_f1','question_micro_f1','mean_input_tokens','cap']:
   num(f'loc.{r}.{a}.{field}','original',['LoCoMo',r,'arms',a,field],100 if 'f1' in field else 1,'.2f' if 'f1' in field or 'tokens' in field else '.0f')
 for c,v in D['original']['LoCoMo'][r]['contrasts'].items():
  for field,keys in [('effect',['effect']),('lo',['ci95',0]),('hi',['ci95',1])]:num(f'loc.{r}.{c}.{field}','original',['LoCoMo',r,'contrasts',c]+keys,100)
 for a,v in D['original']['RULER'][r]['arms'].items():
  num(f'ruler.{r}.{a}','original',['RULER',r,'arms',a,'scoped_native_fraction'],100)
 for a,v in D['original']['Identifier'][r]['arms'].items():
  num(f'id.{r}.{a}','original',['Identifier',r,'arms',a,'exact_match'],v['n'],'.0f')
 for a,v in D['layout']['readers'][r]['arms'].items():
  num(f'layout.{r}.{a}','layout',['readers',r,'arms',a,'correct'],1,'.0f')
 for field,keys,sc,fmt in [('effect',['effect'],100,'.2f'),('lo',['paired_ci95',0],100,'.2f'),('hi',['paired_ci95',1],100,'.2f'),('p',['p'],1,'.6g'),('holm',['holm_p'],1,'.6g'),('gain',['gains'],1,'.0f'),('loss',['losses'],1,'.0f')]:num(f'layout.{r}.{field}','layout',['readers',r,'primary']+keys,sc,fmt)
 for length in ['short','medium','long']:
  for arm in ['text','optical']:
   num(f'budget.{r}.{length}.{arm}','budget',['readers',r,'table',length,arm,'correct'],1,'.0f')
  for field,keys in [('effect',['effect']),('lo',['ci95',0]),('hi',['ci95',1])]:num(f'budget.{r}.{length}.{field}','budget',['readers',r,'delta',length]+keys,100)
 for test in ['primary_interaction','secondary_long']:
  for field,keys,sc in [('effect',['effect'],100),('lo',['ci95',0],100),('hi',['ci95',1],100),('holm',['holm_p'],1)]:num(f'budget.{r}.{test}.{field}','budget',['readers',r,test]+keys,sc,'.4f' if field=='holm' else '.2f')
 for s in ['0.55','0.75','1.00']:
  for f in ['correct','cer','cap_hits']:num(f'scale.{r}.{s}.{f}','scale',['readers',r,'table','scale_'+s,f],1,'.3f' if f=='cer' else '.0f')
 num(f'scale.{r}.holm','scale',['readers',r,'primary','holm_p'],1,'.4f')
 num(f'scale.{r}.Q','scale',['readers',r,'primary','Q'],1,'.4f')
 for i,v in enumerate(D['scale']['readers'][r]['secondary']):
  for f,keys,sc,fmt in [('effect',['effect'],100,'.3f'),('lo',['ci95',0],100,'.3f'),('hi',['ci95',1],100,'.3f'),('p',['p'],1,'.6f'),('holm',['holm_p'],1,'.6f'),('gains',['gains'],1,'.0f'),('losses',['losses'],1,'.0f')]:num(f'scale.{r}.{i}.{f}','scale',['readers',r,'secondary',i]+keys,sc,fmt)
for i,h in enumerate(D['original']['hypotheses']):num(f'loc.{h["reader"]}.{h["name"]}.holm','original',['hypotheses',i,'holm_adjusted_p'],1,'.6g')
for r in ['Qwen2B','Qwen9B']:
 for f in ['fixed_capped_n','still_capped_256','full_500_conversation_macro_old','full_500_conversation_macro_sensitivity','macro_change']:
  num(f'cap.{r}.{f}','cap',['readers',r,f],100 if 'macro' in f else 1,'.4f' if 'macro' in f else '.0f')
 for i,k in enumerate(['lo','hi']):num(f'cap.{r}.{k}','cap',['readers',r,'paired_conversation_bootstrap_ci95',i],100,'.4f')

rows=[]
for label,arm in [('Full text','full_raw'),('Full optical','full_optical_c2'),('Retrieved text','retrieved_text'),('Retrieved optical','retrieved_optical_8px'),('Text, full-optical budget','retrieved_text_matched'),('Text, selected-optical budget','retrieved_text_matched_selected')]:rows.append([label]+[nv(f'loc.{r}.{arm}.conversation_macro_f1') for r in READERS])
tabfile('table_locomo','lrrr','Representation & Qwen2B & Qwen9B & GLM',rows)
rows=[]
for r in READERS:
 rows.append([r]+[nv(f'budget.{r}.{l}.text')+' / '+nv(f'budget.{r}.{l}.optical') for l in ['short','medium','long']]+[nv(f'budget.{r}.primary_interaction.effect'),nv(f'budget.{r}.primary_interaction.holm')])
tabfile('table_budget','lrrrrr','Reader & SHORT & MEDIUM & LONG & Interaction (pp) & Adj. $p$',rows)
rows=[]
for label,arm in [('Full text','full_raw'),('Original layout','original_c2_p4'),('Full-width layout','efficient_c2_p4'),('Enlarged-image control','readable_p4')]:rows.append([label]+[nv(f'layout.{r}.{arm}') for r in READERS])
tabfile('table_layout','lrrr','Representation & Qwen2B & Qwen9B & GLM',rows)

# Exhaustive secondary statistics, generated from the same authoritative objects.
rows=[]
for r in READERS:
 for i,v in enumerate(D['scale']['readers'][r]['secondary']):
  pair=v['comparison'].replace('scale_','').replace(' minus ','--')
  rows.append([r,pair,nv(f'scale.{r}.{i}.effect'), '['+nv(f'scale.{r}.{i}.lo')+', '+nv(f'scale.{r}.{i}.hi')+']', nv(f'scale.{r}.{i}.gains')+'/'+nv(f'scale.{r}.{i}.losses'),nv(f'scale.{r}.{i}.holm')])
tabfile('table_scale_secondary','llrrrr','Reader & Scales & $\Delta$ (pp) & 95\% interval & Gain/loss & Adj. $p$',rows)
rows=[]
for r in READERS:
 rows.append([r]+[nv(f'scale.{r}.{s}.correct')+' / '+nv(f'scale.{r}.{s}.cer')+' / '+nv(f'scale.{r}.{s}.cap_hits') for s in ['0.55','0.75','1.00']]+[nv(f'scale.{r}.Q'),nv(f'scale.{r}.holm')])
tabfile('table_scale_all','lrrrrr','Reader & 0.55 & 0.75 & 1.00 & $Q$ & Adj. $p$',rows)
rows=[]
for r in READERS:
 for a,v in D['original']['RULER'][r]['arms'].items():
  vals=[]
  for t,tv in v['tasks'].items():vals.append(num(f'rulertask.{r}.{a}.{t}','original',['RULER',r,'arms',a,'tasks',t,'fraction'],100))
  rows.append([r,{'full_raw':'Text','optical_c0p8_p4':'0.8','optical_c2_p4':'2','optical_c4_p4':'4'}[a]]+vals)
tabfile('table_ruler_tasks','llrrrrrr','Reader & $C$ & MK3 & MV & S1 & S2 & S3 & VT',rows)
rows=[]
for a in D['original']['Identifier']['Qwen2B']['arms']:rows.append([esc(a)]+[nv(f'id.{r}.{a}') for r in READERS])
tabfile('table_identifier_original','lrrr','Arm & Qwen2B & Qwen9B & GLM',rows)
rows=[]
for r in READERS:
 for c in ['H1','H2','selected_budget','full_budget']:
  rows.append([r,esc(c),nv(f'loc.{r}.{c}.effect'),'['+nv(f'loc.{r}.{c}.lo')+', '+nv(f'loc.{r}.{c}.hi')+']'])
tabfile('table_locomo_contrasts','llrr','Reader & Contrast & Difference (F1 points) & 95\% interval',rows)
rows=[]
for i,v in enumerate(D['sensitivity']['rows']):
 vals=[v['reader'],v['hypothesis']]
 for f in ['positive','negative','ties','sign_p_greater']:
  vals.append(num(f'sens.{i}.{f}','sensitivity',['rows',i,f],1,'.4f' if 'p_' in f else '.0f'))
 vals.append('['+num(f'sens.{i}.lo','sensitivity',['rows',i,'descriptive_t_ci95',0],100)+', '+num(f'sens.{i}.hi','sensitivity',['rows',i,'descriptive_t_ci95',1],100)+']')
 rows.append(vals)
tabfile('table_sensitivity','llrrrrr','Reader & Contrast & $+$ & $-$ & Ties & Sign $p_+$ & $t$ interval (pp)',rows)
rows=[]
for r in READERS:
 for l in ['short','medium','long']:
  rows.append([r,l.upper()]+[num(f'bd.{r}.{l}.{m}','budget',['readers',r,'table',l,'text',m],1,'.4f') for m in ['normalized_source_length_mean']]+[nv(f'budget.{r}.{l}.effect'),'['+nv(f'budget.{r}.{l}.lo')+', '+nv(f'budget.{r}.{l}.hi')+']',num(f'bd.{r}.{l}.surv','budget',['readers',r,'diagnostics',l,'target_survived_text'],1,'.0f')])
tabfile('table_budget_diagnostics','llrrrr','Reader & Length & Source/capacity & $\Delta$ (pp) & 95\% interval & Target retained',rows)

# All systems cells: separate compact tables for accounting, latency, memory, and TTFT.
sys=D['systems']['cells'];arm_names={'A_full_text':'A: text','A_optical_C2':'A: C2','A_optical_C4':'A: C4','B_text':'B: text','B_optical':'B: optical'}
order={r:i for i,r in enumerate(READERS)}; lens=['short','medium','long']
indices=sorted(range(len(sys)),key=lambda i:(order[sys[i]['reader']],lens.index(sys[i]['case_id'].split('-')[-1]),list(arm_names).index(sys[i]['arm'])))
def systab(name,metrics,unit,caption):
 rows=[]
 for i in indices:
  c=sys[i];row=[c['reader'],c['case_id'].split('-')[-1][0].upper(),arm_names[c['arm']]]
  for met in metrics:
   if met in c['accounting']:
    row.append('--' if c['accounting'][met] is None else num(f'sys.{i}.{met}','systems',['cells',i,'accounting',met],1,'.3f' if met=='realized_C' else '.0f'))
   else:
    sc=1/2**30 if 'bytes' in met else 1
    row.append(num(f'sys.{i}.{met}.median','systems',['cells',i,'timing',met,'median'],sc,'.3f')+' ['+num(f'sys.{i}.{met}.q25','systems',['cells',i,'timing',met,'q25'],sc,'.3f')+', '+num(f'sys.{i}.{met}.q75','systems',['cells',i,'timing',met,'q75'],sc,'.3f')+']')
  rows.append(row)
 col='lll'+'r'*len(metrics)
 h='Reader & Len. & Arm & '+caption
 txt=r'\begingroup\setlength{\tabcolsep}{4pt}\small\begin{longtable}{'+col+'}\n'+r'\caption{'+unit+r'}\\\toprule'+'\n'+h+r'\\\midrule\endfirsthead'+'\n'+r'\toprule '+h+r'\\\midrule\endhead'+'\n'
 txt+='\n'.join(' & '.join(v)+r'\\' for v in rows)+r'\bottomrule\end{longtable}\endgroup'+'\n'
 (OUT/(name+'.tex')).write_text(txt,encoding='utf8')
systab('table_systems_accounting',['source_native_tokens','retained_source_native_tokens','vision_tokens','text_input_tokens','total_input_tokens','realized_C'],'Complete native token accounting. A: same source; B: fixed budget. S/M/L: SHORT/MEDIUM/LONG. Nonvision includes scaffolding; it is not added again to the total.','Source & Retained & Vision & Nonvision & Total & $C$')
systab('table_systems_latency',['render_or_pack_s','processor_s','prefill_including_vision_s'],'Complete preprocessing and combined-prefill timings (seconds). Entries are median [Q1, Q3] over ten executions of the predetermined case.','Render/pack & Processor & Prefill incl. vision')
systab('table_systems_ttft',['model_ttft_s','pipeline_ttft_s','end_to_end_one_token_s'],'Time to first token (TTFT) and one-token end-to-end time (seconds), median [Q1, Q3].','Model TTFT & Pipeline TTFT & End to end')
systab('table_systems_memory',['peak_allocated_bytes','peak_reserved_bytes','baseline_allocated_bytes'],'Total allocated and reserved peaks and resident allocation baseline (GiB), median [Q1, Q3].','Allocated peak & Reserved peak & Allocated baseline')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#6b7280','axes.linewidth':.6,'grid.color':'#dde2e5','grid.linewidth':.5,'pdf.fonttype':42,'ps.fonttype':42,'savefig.facecolor':'white'})
def save(fig,name,desc):
 fig.savefig(OUT/'figures'/f'{name}.pdf',bbox_inches='tight',pad_inches=.025,metadata={'Creator':'Matplotlib','Author':''})
 fig.savefig(OUT/'figures'/f'{name}.png',dpi=230,bbox_inches='tight',pad_inches=.025)
 plt.close(fig);figures[name]=desc
def style(ax,ylabel=None):
 ax.grid(axis='y');ax.set_axisbelow(True)
 if ylabel:ax.set_ylabel(ylabel)

# Figure 1: the geometry intervention is the centerpiece; coverage is a separate study.
fig=plt.figure(figsize=(7.05,3.18))
gs=fig.add_gridspec(2,2,height_ratios=[.66,2.0],width_ratios=[1.1,1],wspace=.36,hspace=.26)
ax=fig.add_subplot(gs[0,:]);ax.axis('off')
ax.text(0,.99,'a  Two stages of usable context',fontweight='bold',fontsize=8,va='top')
stages=[('Source\nrecords','#f0f2f5'),('Represent source\nunder budget B','#eaf1f7'),('Target span\nincluded?','#f5eee3'),('Fixed reader\nrecovers answer?','#e7f2ee')]
for i,(label,color) in enumerate(stages):
 x=.016+i*.25
 ax.add_patch(FancyBboxPatch((x,.10),.204,.58,boxstyle='round,pad=0.012,rounding_size=0.024',facecolor=color,edgecolor='#697581',linewidth=.65))
 ax.text(x+.102,.39,label,ha='center',va='center',fontsize=7.2)
 if i<3:ax.add_patch(FancyArrowPatch((x+.218,.39),(x+.245,.39),arrowstyle='-|>',mutation_scale=8,lw=.7,color='#68727d'))
ax.set_xlim(0,1);ax.set_ylim(0,1)
ax=fig.add_subplot(gs[1,0]);ax.axis('off');ax.set_title('b  Qwen9B: matched native allocation',loc='left',fontweight='bold',fontsize=8)
evalroot=ROOT/'studies/checkpoints/cpu_eval_1789993635114781407/prepared'
found=[]
for arm in ['original_c2_p4','efficient_c2_p4']:
 candidates=sorted(p for p in evalroot.rglob('page_000.png') if 'Qwen9B' in p.parts and arm in p.parts)
 if not candidates:raise RuntimeError('Cannot locate original audited layout render '+arm)
 found.append(candidates[0])
for i,p in enumerate(found):
 inset=ax.inset_axes([.015+i*.50,.35,.47,.51]);inset.imshow(Image.open(p).crop((0,0,360,320)));inset.set_xticks([]);inset.set_yticks([])
 for sp in inset.spines.values():sp.set_visible(True);sp.set_color('#adb5bd')
 ax.text(.25+i*.50,.29,['Original','Full-width'][i],ha='center',fontsize=7.5)
 correct=D['layout']['readers']['Qwen9B']['arms'][['original_c2_p4','efficient_c2_p4'][i]]['correct']
 ax.text(.25+i*.50,.17,f'{correct}/48 exact',ha='center',fontsize=10,fontweight='bold',color=COLORS[1])
ax.text(.5,.015,'Same source, counts, IDs; different image tensors\nSame 360 x 320 px crop; 4,096 vision tokens each',ha='center',va='bottom',fontsize=6.5)
ax=fig.add_subplot(gs[1,1]);b=D['budget']['readers']['GLM'];ax.set_title('c  GLM: one hash-retention policy',loc='left',fontweight='bold',fontsize=8)
included=[b['diagnostics']['long']['target_survived_text'],30]
recovered=[b['table']['long'][arm]['correct'] for arm in ['text','optical']]
for y,inc,rec,c in zip([1,0],included,recovered,[COLORS[0],COLORS[2]]):
 ax.barh(y,inc,height=.48,color=c,alpha=.22,edgecolor=c,lw=.8,zorder=2)
 ax.barh(y,rec,height=.24,color=c,zorder=3)
 ax.text(inc+.8,y+.14,f'{inc}/30 included',fontsize=7,color=c,va='center')
 ax.text(rec+.8,y-.14,f'{rec}/30 correct',fontsize=7,color=c,va='center',fontweight='bold')
ax.set_yticks([1,0],['Retained\ntext','Full-source\noptical'],fontsize=7);ax.set_xlim(0,49);ax.set_xticks([0,10,20,30]);ax.set_ylim(-.62,1.55)
style(ax);ax.set_xlabel('LONG cases / 30',fontsize=7)
ax.text(.99,.025,'Common total-input ceiling',transform=ax.transAxes,ha='right',fontsize=6.5,color='#555')
save(fig,'figure1',{'sources':['budget','layout'],'render_examples':[p.relative_to(ROOT).as_posix() for p in found],'crop_xyxy':[0,0,360,320],'note':'Panel a schematic; b first Qwen9B held-out case selected by identifier, with aggregate paired layout outcomes; c GLM LONG inclusion and answer success under one retention policy. Distinct studies/readers.'})

fig,axs=plt.subplots(1,2,figsize=(7.05,2.38),gridspec_kw={'width_ratios':[1,1.15]})
for r,c in zip(READERS,COLORS):
 ar=D['original']['RULER'][r]['arms'];ks=['optical_c0p8_p4','optical_c2_p4','optical_c4_p4'];y=np.array([ar[k]['scoped_native_fraction']*100 for k in ks]);lo=np.array([ar[k]['ci95'][0]*100 for k in ks]);hi=np.array([ar[k]['ci95'][1]*100 for k in ks])
 axs[0].plot([.8,2,4],y,'o-',color=c,label=r,lw=1.6,ms=4);axs[0].fill_between([.8,2,4],lo,hi,color=c,alpha=.10)
 axs[0].axhline(ar['full_raw']['scoped_native_fraction']*100,color=c,lw=.8,ls='--')
axs[0].set_xticks([.8,2,4]);axs[0].set_ylim(0,104);style(axs[0],'Native retrieval score (%)');axs[0].set_xlabel('Nominal source / vision token ratio C');axs[0].set_title('a  Density and retrieval',loc='left',fontsize=8,fontweight='bold');axs[0].text(.02,.04,'Dashed: same-source text',transform=axs[0].transAxes,fontsize=6.5)
for i,(r,c) in enumerate(zip(READERS,COLORS)):
 for j,contrast in enumerate(['H1','H2']):
  v=D['original']['LoCoMo'][r]['contrasts'][contrast];mean=v['effect']*100;lo,hi=np.array(v['ci95'])*100
  axs[1].errorbar(mean,1-j+(1-i)*.17,xerr=[[mean-lo],[hi-mean]],fmt=['o','s','D'][i],color=c,capsize=2,ms=4,lw=1.1)
axs[1].axvline(0,color='gray',ls='--',lw=.8);axs[1].set_yticks([1,0],['Selected minus full\noptical package','Selected optical minus\nsame-evidence text'],fontsize=7)
axs[1].set_ylim(-.45,1.45);axs[1].grid(axis='x');axs[1].set_axisbelow(True);axs[1].set_xlabel('Paired difference in macro F1 (points)');axs[1].set_title('b  LoCoMo: paired package contrasts',loc='left',fontsize=8,fontweight='bold')
handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False,fontsize=7,bbox_to_anchor=(.5,-.015))
fig.tight_layout(w_pad=1.2,rect=[0,.09,1,1]);save(fig,'frontiers',{'sources':['original'],'uncertainty':'RULER pointwise task-stratified bootstrap intervals; LoCoMo preserved paired conversation-bootstrap 95% intervals for H1/H2, not intervals reconstructed from arm means.'})

fig=plt.figure(figsize=(7.05,3.28))
gs=fig.add_gridspec(2,2,width_ratios=[1.37,1],hspace=.73,wspace=.40)
axa=fig.add_subplot(gs[:,0]);axb=fig.add_subplot(gs[0,1]);axc=fig.add_subplot(gs[1,1])
positions=np.arange(4)*1.3;w=.32
for i,(r,c) in enumerate(zip(READERS,COLORS)):
 v=D['layout']['readers'][r]['arms'];counts=[v[k]['correct'] for k in ['original_c2_p4','efficient_c2_p4','readable_p4','full_raw']];xx=positions+(i-1)*w
 axa.bar(xx,np.array(counts)/48*100,w*.90,color=c,label=r,zorder=3)
 for x,n in zip(xx,counts):
  if n==0:axa.plot(x,0,'_',color=c,ms=7,mew=2,zorder=5,clip_on=False)
  axa.text(x,n/48*100+1.8,f'{n}',ha='center',va='bottom',fontsize=7,color=c,fontweight='bold')
 v=D['scale']['readers'][r]['table'];axb.plot([.55,.75,1],[v['scale_'+k]['correct']/32*100 for k in ['0.55','0.75','1.00']],'o-',color=c,lw=1.4,ms=3)
 v=D['layout']['readers'][r]['primary'];m=v['effect']*100;lo,hi=np.array(v['paired_ci95'])*100
 axc.errorbar(m,2-i,xerr=[[m-lo],[hi-m]],fmt='o',color=c,capsize=2,lw=1.2,ms=4)
axa.axvspan(1.95,4.55,color='#f3f0e8',zorder=0);axa.axvline(1.95,lw=.7,ls=':',color='gray')
axa.set_xticks(positions,['Original','Full-width','Enlarged','Full text'],fontsize=7);axa.set_xlim(-.6,4.5);axa.set_ylim(0,116)
axa.set_title('a  Layout intervention (n = 48)',loc='left',fontsize=8,fontweight='bold')
axa.text(.65,113,'Matched budget',ha='center',va='top',fontsize=7);axa.text(3.25,113,'Larger-budget references',ha='center',va='top',fontsize=7)
style(axa,'Exact retrieval (%)');axa.set_yticks([0,25,50,75,100]);axa.text(.025,.67,'Bar labels: correct / 48',transform=axa.transAxes,fontsize=7)
axb.set_xticks([.55,.75,1]);axb.set_ylim(0,52);axb.set_yticks([0,25,50]);axb.set_xlabel('Rendered-block scale',fontsize=7);axb.set_title('b  Controlled scale (n = 32)',loc='left',fontsize=8,fontweight='bold');style(axb,'Exact (%)')
axc.set_yticks([2,1,0],READERS,fontsize=7);axc.set_ylim(-.55,2.55);axc.set_xlim(0,62);axc.set_xticks([0,20,40,60]);axc.grid(axis='x');axc.set_axisbelow(True);axc.set_xlabel('Full-width minus Original (pp)',fontsize=7);axc.set_title('c  Paired layout effects (95% CI)',loc='left',fontsize=8,fontweight='bold')
handles,labels=axa.get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False,fontsize=7,bbox_to_anchor=(.50,-.055))
save(fig,'geometry',{'sources':['layout','scale'],'note':'Counts / 48; enlarged and full text are larger-budget references. Paired layout intervals are preserved from the audit. Scale uses 32 independent cases; only Qwen9B passes the corrected omnibus test.'})

fig,axs=plt.subplots(1,3,figsize=(7.05,2.78),sharey=True)
for r,ax in zip(READERS,axs):
 b=D['budget']['readers'][r];xx=np.arange(3);bw=.36
 for arm,c,offset in [('text',COLORS[0],-bw/2),('optical',COLORS[2],bw/2)]:
  yy=[b['table'][l][arm]['correct'] for l in lens];inc=[b['diagnostics'][l]['target_survived_text'] if arm=='text' else 30 for l in lens]
  ax.bar(xx+offset,np.array(inc)/30*100,width=bw*.94,color=c,alpha=.18,zorder=2)
  ax.bar(xx+offset,np.array(yy)/30*100,width=bw*.60,color=c,label='Hash-retained text' if arm=='text' else 'Full-source optical',zorder=3)
  ax.scatter(xx+offset,np.array(inc)/30*100,s=25,facecolors='white',edgecolors=c,zorder=4)
  for x,n,k in zip(xx+offset,yy,inc):ax.text(x,k/30*100+(11 if arm=='optical' else 3.1),f'{n}/{k}',ha='center',va='bottom',fontsize=6.5,color=c,fontweight='bold')
 ratios=[b['table'][l]['text']['normalized_source_length_mean'] for l in lens]
 ax.set_xticks(xx,[f'{l.upper()}\n({v:.2f}x)' for l,v in zip(lens,ratios)],fontsize=7);ax.set_xlim(-.54,2.54);ax.set_ylim(0,128);ax.set_yticks([0,25,50,75,100]);ax.set_title(r,fontweight='bold');style(ax)
axs[0].set_ylabel('Targets (%)');axs[1].set_xlabel('Discrete regime (source / text capacity)',fontsize=7)
handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=2,frameon=False,fontsize=7,bbox_to_anchor=(.5,1.01))
fig.text(.5,.01,'Hollow marker / pale bar: included. Solid bar: correct. Labels: correct / included (30 cases per regime).',ha='center',fontsize=6.7,color='#4b5563')
fig.tight_layout(w_pad=1.0,rect=[0,.06,1,.90])
save(fig,'budget',{'sources':['budget'],'note':'Per-case inclusion and correctness displayed separately. All optical targets included; text correct counts equal inclusion in every cell. Common upper bound, not equal consumed tokens. Ratios remain the frozen nominal capacity ratios.'})

fig,axs=plt.subplots(1,4,figsize=(7.05,2.23))
metrics=['end_to_end_one_token_s','prefill_including_vision_s','peak_allocated_bytes','incremental']
for ax,met,title in zip(axs,metrics,['End-to-end\nlatency','Prefill incl.\nvision','Total allocated\npeak','Allocated peak\nabove resident']):
 for i,view in enumerate(['A','B']):
  ratios=[]
  for r in READERS:
   lookup={c['arm']:c for c in sys if c['reader']==r and c['case_id'].endswith('long')}
   left,right=('A_optical_C2','A_full_text') if view=='A' else ('B_optical','B_text')
   if met=='incremental':ratios.append(D['derived']['incremental'][r][left]['median']/D['derived']['incremental'][r][right]['median'])
   else:ratios.append(lookup[left]['timing'][met]['median']/lookup[right]['timing'][met]['median'])
  ax.plot(range(3),ratios,marker=['o','s'][i],color=[COLORS[0],COLORS[2]][i],lw=1.2,label=['Same source C2','Fixed budget'][i])
 ax.axhline(1,color='gray',ls='--',lw=.7);ax.set_xticks(range(3),READERS,rotation=30,fontsize=7);ax.set_title(title,fontsize=8,fontweight='bold');style(ax);ax.set_ylim(bottom=0)
axs[0].set_ylabel('Optical / text (LONG medians)')
handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,fontsize=7,bbox_to_anchor=(.5,-.025))
fig.tight_layout(w_pad=1,rect=[0,.10,1,1]);save(fig,'systems_summary',{'sources':['systems','derived'],'note':'Ratios of medians. Last panel uses per-execution peak minus resident baseline before taking medians. End-to-end preprocessing is asymmetric: repeated text packing included, optical planning excluded. Lower resource cost does not establish better quality.'})

# Additional render examples: native images are reproduced without editing their pixels.
base=ROOT/'studies/final_followups/checkpoints/cpu_1790114103802037991/prepared/02_geometry_mechanism/inputs/Qwen9B/geometry-000'
fig,axs=plt.subplots(1,3,figsize=(6.65,2.3))
for ax,s in zip(axs,['0.55','0.75','1.00']):
 p=base/('scale_'+s)/'page_000.png';ax.imshow(Image.open(p));ax.set_title('Scale '+s,fontsize=8);ax.set_xticks([]);ax.set_yticks([])
fig.tight_layout();save(fig,'scale_examples',{'sources':['scale'],'case':'geometry-000','page':'first','reader':'Qwen9B','selection':'predeclared example'})
for n in ['systems_prefill','systems_ttft','systems_memory']:
 shutil.copy2(ROOT/'studies/final_followups/03_systems_profile/results'/f'{n}.pdf',OUT/'figures'/f'{n}.pdf')

# Compact-storage follow-up: derived fields are descriptive recomputations from scored rows.
compact_rows = json.loads((ROOT/'studies/final_experiment/outputs/scored/scores.json').read_text(encoding='utf8'))['rows']
compact_pairs = {}
for row in compact_rows: compact_pairs.setdefault(row['case_id'], {})[row['arm']] = row
compact_derived = {
 'capacity_gain': float(np.mean([v['compact_text']['records_retained']/v['hash_text']['records_retained']-1 for v in compact_pairs.values()])),
 'additional_targets': D['compact']['arms']['compact_text']['included_n']-D['compact']['arms']['hash_text']['included_n'],
 'budget_increase': D['compact_config']['B']/3916-1,
 'optical_misses': D['compact']['arms']['optical']['n']-D['compact']['arms']['optical']['successes'],
 'late_misses': D['compact']['arms']['optical']['positions']['late']['n']-D['compact']['arms']['optical']['positions']['late']['successes'],
 'provenance': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['studies/final_experiment/outputs/scored/scores.json','studies/final_experiment/analysis/RESULTS.json','studies/final_experiment/config.json']}
}
(OUT/'evidence/compact_derived.json').write_text(json.dumps(compact_derived,indent=2),encoding='utf8')
FILES['compact_derived']='paper/evidence/compact_derived.json'
D['compact_derived']=compact_derived
num('compact.n','compact',['primary','n'],1,'.0f')
num('compact.calls','compact_config',['held_out_calls'],1,'.0f')
num('compact.B','compact_config',['B'],1,',.0f')
for k,field,scale,fmt in [('effect','effect',100,'.1f'),('p','p',1e6,'.2f'),('gains','gains',1,'.0f'),('losses','losses',1,'.0f'),('ties','ties',1,'.0f')]:
 num('compact.'+k,'compact',['primary',field],scale,fmt)
for k,path in [('lo',['bootstrap','low']),('hi',['bootstrap','high']),('conservative_lo',['conservative_ci','low']),('conservative_hi',['conservative_ci','high'])]:
 num('compact.'+k,'compact',['primary']+path,100,'.2f')
for key,field,scale,fmt in [('capacity_gain','capacity_gain',100,'.2f'),('additional_targets','additional_targets',1,'.0f'),('budget_increase','budget_increase',100,'.2f'),('optical.misses','optical_misses',1,'.0f'),('optical.late_misses','late_misses',1,'.0f')]:
 num('compact.'+key,'compact_derived',[field],scale,fmt)
summary_rows=[]; input_rows=[]
for arm,label in [('hash_text','Original-format text'),('compact_text','Compact text'),('optical','Full-source optical')]:
 for field in ['successes','included_n','included_successes']:
  num(f'compact.{arm}.{field}','compact',['arms',arm,field],1,'.0f')
 num(f'compact.{arm}.records','compact',['arms',arm,'input_diagnostics','records_retained','mean'],1,'.2f')
 for field,path in [('source','source_native_tokens'),('total','total_input_tokens'),('vision','vision_tokens'),('nonvision','nonvision_input_tokens')]:
  for stat in ['mean','min','max']:
   num(f'compact.{arm}.{field}_{stat}','compact',['arms',arm,'input_diagnostics',path,stat],1,',.2f' if stat=='mean' else ',.0f')
 for pos in ['early','middle','late']:
  num(f'compact.{arm}.{pos}','compact',['arms',arm,'positions',pos,'successes'],1,'.0f')
 summary_rows.append([label,nv(f'compact.{arm}.included_n')+'/'+nv('compact.n'),nv(f'compact.{arm}.successes')+'/'+nv('compact.n'),nv(f'compact.{arm}.included_successes')+'/'+nv(f'compact.{arm}.included_n'),nv(f'compact.{arm}.records')])
 input_rows.append([label,nv(f'compact.{arm}.vision_min'),nv(f'compact.{arm}.nonvision_min')+'--'+nv(f'compact.{arm}.nonvision_max'),nv(f'compact.{arm}.total_mean'),nv(f'compact.{arm}.total_min')+'--'+nv(f'compact.{arm}.total_max')])
tabfile('table_compact_storage','lrrrr','Representation & Included & Correct & Conditional & Mean records',summary_rows)
tabfile('table_compact_inputs','lrrrr','Representation & Vision & Nonvision range & Mean total & Total range',input_rows)

# Preserve compact authoritative evidence (full raw journals stay at repository paths).
manifest=[]
for k,p in FILES.items():
 data=(ROOT/p).read_bytes();dst=OUT/'evidence'/(k+'.json');dst.write_bytes(data)
 manifest.append(dict(alias=k,path=p,sha256=hashlib.sha256(data).hexdigest(),package_path='evidence/'+dst.name))
(OUT/'verification'/'evidence_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(OUT/'verification'/'number_ledger.json').write_text(json.dumps(ledger,indent=2),encoding='utf8')
(OUT/'verification'/'figure_sources.json').write_text(json.dumps(figures,indent=2),encoding='utf8')
(OUT/'numbers.tex').write_text('% Generated from audited machine-readable analysis; do not edit.\n'+r'\newcommand{\nval}[1]{\csname n@#1\endcsname}'+'\n'+'\n'.join(r'\expandafter\def\csname n@'+k+r'\endcsname{'+v['display']+'}' for k,v in ledger.items())+'\n',encoding='utf8')
print('Generated',len(ledger),'traceable numbers and',len(figures),'new figures.')
