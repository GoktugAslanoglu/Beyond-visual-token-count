"""Compact inclusion/accuracy figure from all prespecified arms, after completion."""
import argparse
from pathlib import Path
from experiment_common import ROOT, read

def main(results, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    r=read(results);assert r['status']=='complete'
    arms=['hash_text','compact_text','optical'];labels=['Original hash text','Compact hash text','Full-source optical']
    fig,ax=plt.subplots(figsize=(7,4),constrained_layout=False)
    for i,arm in enumerate(arms):
        s=r['arms'][arm];ax.bar(i,s['included_n']/s['n']*100,color='#cbd5e1',width=.66)
        ax.bar(i,s['accuracy']*100,color=['#475569','#0d9488','#4f46e5'][i],width=.42)
        ax.text(i,max(s['included_n']/s['n'],s['accuracy'])*100+2,f"{s['successes']}/{s['n']} correct\n{s['included_n']}/{s['n']} included",ha='center',fontsize=9)
    ax.set(xticks=range(3),xticklabels=labels,ylim=(0,115),ylabel='Percentage of 150 fresh cases',title='GLM LONG: inclusion and generated-answer recovery')
    ax.spines[['top','right']].set_visible(False)
    if r.get('synthetic_fixture'):ax.set_title('SYNTHETIC QA ONLY - not experiment results')
    p=r['primary'];fig.text(.01,.02,f"Primary optical-compact: {p['effect']*100:+.1f} pp; exact McNemar p={p['p']:.4g}. Pale: inclusion; solid: accuracy.",fontsize=8)
    fig.tight_layout(rect=(0,.10,1,1))
    output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(output,dpi=180);plt.close(fig)
    print(str(output))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=ROOT/'analysis/RESULTS.json');p.add_argument('--output',type=Path,default=ROOT/'figures/compact_storage.png');a=p.parse_args();main(a.results,a.output)
