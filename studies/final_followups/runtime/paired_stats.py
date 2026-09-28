"""Exact small-sample paired tests; no SciPy/asymptotic dependency."""
import math
from collections import defaultdict
import numpy as np
def holm(tests):
 last=0.
 for rank,t in enumerate(sorted(tests,key=lambda t:t['p'])):
  last=max(last,min(1.,(len(tests)-rank)*t['p']));t['holm_p']=last;t['reject_005']=last<=.05
 return tests
def exact_signflip(d):
 # Exact two-sided distribution of signed integer magnitudes, conditional on
 # magnitudes; symmetry/exchangeability is an explicit null assumption.
 d=[int(x) for x in d];dist={0:1};n=0
 for v in d:
  if not v:continue
  n+=1;new=defaultdict(int)
  for total,w in dist.items():new[total+abs(v)]+=w;new[total-abs(v)]+=w
  dist=dict(new)
 return sum(w for k,w in dist.items() if abs(k)>=abs(sum(d)))/(2**n)
def paired(a,b,seed): # a - b
 a=np.asarray(a,int);b=np.asarray(b,int);d=a-b
 return {'effect':float(d.mean()),'ci95':bootstrap(d,seed),'gains':int(sum(d>0)),'losses':int(sum(d<0)),'p':exact_signflip(d)}
def bootstrap(d,seed):
 d=np.asarray(d);rng=np.random.default_rng(seed);means=d[rng.integers(0,len(d),(50000,len(d)))].mean(axis=1)
 return [float(v) for v in np.quantile(means,[.025,.975])]
def exact_q(matrix):
 x=np.asarray(matrix,int);assert x.ndim==2 and x.shape[1]==3 and np.isin(x,[0,1]).all()
 totals=x.sum(axis=1);columns=x.sum(axis=0);T=int(x.sum());den=3*T-int((totals**2).sum())
 if den==0:return {'Q':0.,'p':1.,'informative_cases':0}
 q=lambda cols:2*(3*sum(int(c)**2 for c in cols)-T*T)/den
 # Condition on each case's number of successes. Uniformly permute labels
 # within case; exact DP over first two column totals, third determined by T.
 dp={(0,0):1};ways=1;partial=0
 for t in totals:
  options={0:[(0,0)],1:[(1,0),(0,1),(0,0)],2:[(1,1),(1,0),(0,1)],3:[(1,1)]}[int(t)]
  nxt=defaultdict(int)
  for (a,b),w in dp.items():
   for da,db in options:nxt[a+da,b+db]+=w
  dp=nxt;ways*=len(options);partial+=int(t)
 obs=sum(int(c)**2 for c in columns)
 exceed=sum(w for (a,b),w in dp.items() if a*a+b*b+(T-a-b)**2>=obs)
 return {'Q':float(q(columns)),'p':exceed/ways,'informative_cases':int(sum((totals>0)&(totals<3))),'permutation_outcomes':ways}
