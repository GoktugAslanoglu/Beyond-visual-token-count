"""Deterministic tests using synthetic fixtures only; no model outputs."""
import itertools,sys,pathlib,json
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from paired_stats import exact_signflip,exact_q,holm,bootstrap
from cases import retain,crossover,geometry
from common import LEGACY,plan
from prepare import scaled_images
from audit_inputs import independent_render
from tokenizers import Tokenizer
def test_signflip_enumeration():
 for d in [[1,1,-1],[2,1,0,-2],[0,0],[-1]*6]:
  brute=sum(abs(sum(v*s for v,s in zip(d,ss)))>=abs(sum(d)) for ss in itertools.product([-1,1],repeat=len(d)))/2**len(d)
  assert exact_signflip(d)==brute
def test_q_enumeration():
 for x in [[[1,0,0],[1,1,0],[0,0,0]],[[1,1,1]],[[1,0,0]]*5]:
  opts=[list(set(itertools.permutations(row))) for row in x];obs=sum(v*v for v in np.array(x).sum(axis=0));poss=list(itertools.product(*opts))
  p=sum(sum(v*v for v in np.array(z).sum(axis=0))>=obs for z in poss)/len(poss)
  assert abs(exact_q(x)['p']-p)<1e-15
def test_holm_known_and_bootstrap_deterministic():
 ts=[{'p':.001},{'p':.02},{'p':.04}];holm(ts)
 assert [t['holm_p'] for t in ts]==[.003,.04,.04]
 assert bootstrap([0,1,-1,2],123)==bootstrap([0,1,-1,2],123)
 assert bootstrap([0]*30,123)==[0.,0.]
def test_packer_budget_complete_deterministic():
 records=['Record A: 1111111','Record B: 2222222','Record C: 3333333']
 fits=lambda s:len(s)<=36
 a,ix=retain(records,'test',fits);b,jx=retain(records,'test',fits)
 assert (a,ix)==(b,jx) and fits(a) and a=='\n'.join(records[i] for i in ix)
 assert retain(records,'test',lambda s:False)==('',[])
 assert retain(records,'test',lambda s:True)[0]=='\n'.join(records)
def test_all_sources_and_scale_geometry():
 tok=Tokenizer.from_file(str(LEGACY/'assets/reference_tokenizer.json'));tok.no_padding();tok.no_truncation();count=lambda s:len(tok.encode(s,add_special_tokens=False).ids)
 answers=[]
 for i in range(30):
  cc=crossover(i,count);assert len({c['reference'] for c in cc})==1;answers.append(cc[0]['reference'])
  for c in cc:
   assert c['memory'].count(c['reference'])==1 and c['reference'] not in c['question']
   assert len(c['records'])==len(set(c['records']))
 assert len(set(answers))==30
 for i in range(32):
  c=geometry(i,count);g=plan(c['memory'],'L3_fullwidth_wordwrap')
  for scale in [.55,.75,1.]:
   actual=scaled_images(g,868,scale);expected=independent_render(g,868,scale)
   assert len(actual)==4
   for a,b in zip(actual,expected):assert a.size==(868,868) and a.tobytes()==b.tobytes();a.close();b.close()
