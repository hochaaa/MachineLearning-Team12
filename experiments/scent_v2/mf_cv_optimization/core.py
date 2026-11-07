"""Exact50-user subset and support-only ridge variants; no final label decoding."""
import json,math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline,hybrid
from experiments.scent_v2.mf_accuracy_optimization.core import read_identities,digest,validate_train
from experiments.scent_v2.recommend import rank
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/scent_v2/mf_cv_optimization'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def developer_cohort(path,candidates):
    """Decode only50 developer labels, not255 background or25 reserved users."""
    raw=read_identities(path);pool=set(candidates);counts=Counter(u for u,i,t in raw);available=Counter(u for u,i,t in raw if i in pool)
    eligible=sorted((u for u,n in counts.items() if n>=6 and available[u]>=5),key=lambda u:digest('12:v224:role:'+u))
    n=math.ceil(len(eligible)/3);reserved=set(eligible[:n]);users=eligible[n:];histories=defaultdict(list)
    for u,i,t in raw:
        if u not in set(users):continue
        value=json.loads(t)
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not 0<=value<=1:raise ValueError('Invalid developer rating')
        histories[u].append((i,float(value)))
    cohort=[]
    for u in users:
        ids=sorted((i for i,r in histories[u] if i in pool),key=lambda i:digest('12:v224:support:'+u+':'+i));seen=set(ids[:5]);s=sorted((i,r) for i,r in histories[u] if i in seen);a=sorted((i,r) for i,r in histories[u] if i not in seen)
        if len(s)!=5 or not a or seen&{i for i,r in a}:raise ValueError('Invalid support/heldout')
        cohort.append(dict(user=u,support=s,answers=a))
    return cohort,reserved,dict(developer_users=len(users),developer_ratings=sum(map(len,histories.values())),reserved_users=len(reserved),reserved_rating_tokens_decoded=0,background_rating_tokens_decoded=0,developer_split_sha256=digest(json.dumps(cohort,sort_keys=True)))


def folds(cohort):
    """User SHA order then round-robin; every user evaluated once, never in own fit."""
    ordered=sorted(cohort,key=lambda r:digest('12:v226:fold:'+r['user']));result=[]
    for n in range(5):
        evaluation=ordered[n::5];excluded={r['user'] for r in evaluation};train=[(r['user'],i,y) for r in ordered if r['user'] not in excluded for i,y in r['support']+r['answers']]
        validate_train(train,excluded)
        result.append(dict(fold=n+1,train=train,evaluation=evaluation))
    return result


def ridge(mf,support,scale=1.,center=False):
    """Known Support Q only; n*lambda*scale; optional Support-only intercept mu."""
    if len(support)!=5 or len({i for i,y in support})!=5:raise ValueError('Five unique support')
    if not all(np.isfinite(y) and 0<=y<=1 for i,y in support):raise ValueError('Rating range')
    if scale<=0:raise ValueError('Positive ridge scale')
    known=[(i,y) for i,y in support if i in mf.items]
    if not known:return None,0.
    mu=float(np.mean([y for i,y in support])) if center else 0.
    q=np.asarray([mf.Q[mf.items[i]] for i,y in known],float);y=np.asarray([y-mu for i,y in known],float)
    p=np.linalg.solve(np.einsum('ni,nj->ij',q,q)+len(known)*mf.reg*scale*np.eye(mf.factors),np.einsum('ni,n->i',q,y))
    if not np.isfinite(p).all():raise ValueError('Nonfinite ridge')
    return p,mu


def user_scores(spec,support,candidates,content,mf,pop,shared=None):
    """No answer argument; unchanged clipped MF scale and original hybrid fallback."""
    pool=sorted(set(candidates)-{i for i,y in support})
    c,b=shared if shared is not None else (content.score(support,pool),pop.score(pool))
    p,mu=ridge(mf,support,spec['ridge_scale'],spec['center'])
    m=np.asarray([float(np.clip(mu+np.einsum('i,i->',p,mf.Q[mf.items[i]]),0,1)) if p is not None and i in mf.items else np.nan for i in pool])
    values=hybrid(c,m,spec['alpha'],b);top=rank(pool,values)[:5]
    if len(top)!=len(set(top)) or set(top)&{i for i,y in support}:raise ValueError('Top5 invalid')
    return top


def evaluate_fold(spec,fold,candidates,content,mf,pop,shared):
    records=[]
    for row in fold['evaluation']:
        top=user_scores(spec,row['support'],candidates,content,mf,pop,shared[row['user']])
        answers=row['answers'];records.append(dict(top=top,answers=answers,accuracy=user_metrics(top,answers)))
    return summarize(records,candidates),records
