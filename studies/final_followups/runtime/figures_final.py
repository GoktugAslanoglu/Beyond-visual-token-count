"""Generate scientific figures only from complete audited analyses."""
import argparse,pathlib
from common import read,STUDIES,READERS
def plot(folder,study):
 import numpy as np,matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 a=read(folder/'analysis.json');assert a['status']=='passed'
 plt.rcParams.update({'font.size':9,'pdf.fonttype':42})
 def save(fig,name):
  fig.tight_layout();fig.savefig(folder/(name+'.pdf'));fig.savefig(folder/(name+'.png'),dpi=180);plt.close(fig)
 if study==STUDIES[0]:
  fig,axes=plt.subplots(1,3,figsize=(10.8,3.2),sharey=True)
  for ax,reader in zip(axes,READERS):
   r=a['readers'][reader]
   for arm,label,color in [('text','Budgeted text','#2166ac'),('optical','Efficient optical','#b35806')]:
    cells=[r['table'][s][arm] for s in ['short','medium','long']];ax.plot([c['normalized_source_length_mean'] for c in cells],[100*c['accuracy'] for c in cells],'-o',label=label,color=color)
   ax.axvline(1,color='#666',linestyle=':',linewidth=1);ax.set_title(reader);ax.set_ylim(-3,103);ax.set_xlabel('Source / available text budget');ax.grid(alpha=.15)
  axes[0].set_ylabel('Native retrieval accuracy (%)');axes[0].legend();save(fig,'budget_crossover')
 elif study==STUDIES[1]:
  fig,ax=plt.subplots(figsize=(5,3.4))
  for reader,color in zip(READERS,['#2166ac','#b35806','#008577']):
   y=[a['readers'][reader]['table'][f'scale_{s:.2f}']['accuracy']*100 for s in [.55,.75,1.]]
   ax.plot([.55,.75,1.],y,'-o',label=reader,color=color)
  ax.set_xticks([.55,.75,1.]);ax.set_ylim(-3,103);ax.set_xlabel('Uniform rendered text-block scale');ax.set_ylabel('Canonical exact match (%)');ax.legend();ax.grid(alpha=.15);save(fig,'geometry_scale')
 else:
  for field,title,name in [('prefill_including_vision_s','Combined prefill incl. vision (s)','systems_prefill'),('pipeline_ttft_s','Pipeline time to first token (s)','systems_ttft'),('peak_allocated_bytes','Peak allocated GPU memory (GiB)','systems_memory')]:
   fig,axes=plt.subplots(2,3,figsize=(10.8,6),sharex='col')
   for j,reader in enumerate(READERS):
    for i,(view,arms) in enumerate([('Same source',['A_full_text','A_optical_C2','A_optical_C4']),('Fixed budget',['B_text','B_optical'])]):
     ax=axes[i,j]
     for arm in arms:
      cells=sorted([c for c in a['cells'] if c['reader']==reader and c['arm']==arm],key=lambda c:c['accounting']['source_native_tokens']);factor=1024**3 if field.endswith('bytes') else 1
      x=[c['accounting']['source_native_tokens'] for c in cells];y=[c['timing'][field]['median']/factor for c in cells];lo=[c['timing'][field]['q25']/factor for c in cells];hi=[c['timing'][field]['q75']/factor for c in cells]
      ax.plot(x,y,'-o',label=arm);ax.fill_between(x,lo,hi,alpha=.12)
     ax.set_title(reader+' — '+view);ax.grid(alpha=.15);ax.legend(fontsize=7);ax.set_xlabel('Full source-native tokens')
     if j==0:ax.set_ylabel(title)
   save(fig,name)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',type=pathlib.Path,required=True);p.add_argument('--study',choices=STUDIES,required=True);a=p.parse_args();plot(a.folder,a.study)
