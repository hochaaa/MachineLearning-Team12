"""Evaluation harness alone accepts labels. No scorer receives answer IDs/values."""
from collections import defaultdict
import numpy as np
from perfume.models import Baseline
from perfume.evaluation import ranking_metrics
from hybrid_v2 import ranked,combine
from foldin_v2 import fold_in,score_vector

def evaluate_arrays(scores_by_user,answers,k=10,relevance=.7):
    """Positive-only macro metrics exactly matching V1, plus observed rating-independent coverage."""
    pos=defaultdict(set)
    for u,i,r in answers:
        if r>=relevance:pos[u].add(i)
    values=[];users=[]
    for u,ranking in scores_by_user.items():
        m=ranking_metrics(ranking,pos[u],k)
        if m is not None:values.append(m);users.append(u)
    summary={'evaluation_users':len(scores_by_user),'positive_users':len(values),'no_positive_users':len(scores_by_user)-len(values),'coverage_items':len(set(i for p in scores_by_user.values() for i in p[:k]))}
    for key in ['precision','recall','ndcg']:summary[key]=float(np.mean([r[key] for r in values])) if values else None
    return summary,{u:r['ndcg'] for u,r in zip(users,values)}

def component_scores(model,content,train,pool,supports=None,regularization=None):
    """No answer argument. All known users or provided synthetic/new-user support are scored."""
    histories=defaultdict(list)
    for u,i,r in train:histories[u].append((i,r))
    if supports is None:supports=histories
    baseline=Baseline().fit(train);out={};rawstats=[]
    for u,support in sorted(supports.items()):
        support=sorted(support);seen={i for i,_ in support};candidates=[i for i in pool if i not in seen]
        c=content.score(support,candidates) if content is not None else np.full(len(candidates),np.nan)
        if model is None:m=np.full(len(candidates),np.nan)
        elif regularization is None:m=model.score(u,candidates)
        else:m=score_vector(model,fold_in(model,support,regularization),candidates)
        b=baseline.score(candidates);out[u]=(candidates,c,m,b,len(support))
        if np.isfinite(c).any() and np.isfinite(m).any():rawstats.append({'content_sd':float(np.nanstd(c)),'mf_sd':float(np.nanstd(m)),'mf_clipped_fraction':float(np.mean((m==0)|(m==1))),'content_unique':len(set(c[np.isfinite(c)])),'mf_unique':len(set(m[np.isfinite(m)]))})
    return out,rawstats

def predictions(cache,kind='hybrid',config=None):
    """Return ranked lists and exact fallback counters; ranking IDs are never saved publicly."""
    out={};stats={'component_fallback':0,'popularity_fallback':0,'candidate_scores':0}
    for u,(pool,c,m,b,n) in cache.items():
        if kind=='hybrid':scores,s=combine(c,m,b,pool,config,n)
        else:scores={'content':c,'mf':m,'popularity':b}[kind];s={'component_fallback':0,'popularity_fallback':0,'candidate_scores':len(pool)}
        out[u]=ranked(pool,scores);assert len(out[u])==len(set(out[u])) and set(out[u])<=set(pool)
        for key in stats:stats[key]+=s[key]
    stats['popularity_fallback_fraction']=stats['popularity_fallback']/max(1,stats['candidate_scores']);stats['component_fallback_fraction']=stats['component_fallback']/max(1,stats['candidate_scores'])
    return out,stats

def paired_interval(left,right,seed=12,draws=2000):
    """Paired user-bootstrap descriptive delta interval; not independent generalization proof."""
    users=sorted(set(left)&set(right));d=np.array([right[u]-left[u] for u in users]);rng=np.random.default_rng(seed)
    if not len(d):return {'users':0,'delta':None,'low':None,'high':None}
    boot=np.array([d[rng.integers(len(d),size=len(d))].mean() for _ in range(draws)])
    return {'users':len(d),'delta':float(d.mean()),'low':float(np.quantile(boot,.025)),'high':float(np.quantile(boot,.975)),'draws':draws}
