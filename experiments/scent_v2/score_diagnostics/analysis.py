"""Answer-free score reconstruction and diagnostic statistical primitives."""
from collections import defaultdict
import numpy as np
from perfume.models import hybrid
from experiments.scent_v2.recommend import fold_in,rank
from experiments.scent_v2.lambda_tuning.evaluate import view

STATS=('min','p1','p5','p25','p50','mean','p75','p95','p99','max','sd')


def distribution(values):
    """Finite values only, population SD(ddof=0); None for an empty distribution."""
    x=np.asarray(values,dtype=float);x=x[np.isfinite(x)]
    if not len(x):return dict(count=0,**{k:None for k in STATS})
    q=np.quantile(x,[0,.01,.05,.25,.5,.75,.95,.99,1])
    return dict(count=len(x),min=float(q[0]),p1=float(q[1]),p5=float(q[2]),p25=float(q[3]),
                p50=float(q[4]),mean=float(np.mean(x)),p75=float(q[5]),p95=float(q[6]),
                p99=float(q[7]),max=float(q[8]),sd=float(np.std(x)))


def mean_finite(values):
    """Ignore undefined entries, preserving None when all entries are undefined."""
    v=[float(x)for x in values if x is not None and np.isfinite(x)]
    return float(np.mean(v))if v else None


def ranks_average(x):
    """Standard average ranks for exact ties; no external statistics dependency."""
    x=np.asarray(x,dtype=float);order=np.argsort(x,kind='stable');r=np.empty(len(x));n=0
    while n<len(x):
        end=n+1
        while end<len(x)and x[order[end]]==x[order[n]]:end+=1
        r[order[n:end]]=(n+end-1)/2+1;n=end
    return r


def correlation(x,y,spearman=False):
    """Pairwise finite Pearson or average-rank Spearman; constants are undefined."""
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);mask=np.isfinite(x)&np.isfinite(y)
    x=x[mask];y=y[mask]
    if len(x)<2:return None,'insufficient',len(x)
    if np.ptp(x)==0 or np.ptp(y)==0:return None,'constant',len(x)
    if spearman:x=ranks_average(x);y=ranks_average(y)
    x=x-x.mean();y=y-y.mean();den=np.sqrt(np.sum(x*x)*np.sum(y*y))
    return float(np.sum(x*y)/den),'ok',len(x)


def reconstruct(support,candidates,content,mf,pop,lam):
    """No answers/user ID accepted. Same support, Q, clipping/fallback as V2-1.

    Returns candidate-aligned raw arrays and applied additive contributions.
    On fallback candidates .25C/.75M are NOT the applied contributions: actual
    fallback is full C, full M or train popularity, tracked separately.
    """
    seen={i for i,r in support};pool=sorted(set(candidates)-seen)
    v=fold_in(view(mf,lam),support)
    factors=np.array([i in mf.items for i in pool])
    raw=np.array([v @ mf.Q[mf.items[i]]if v is not None and i in mf.items else np.nan for i in pool])
    c=content.score(support,pool);m=np.clip(raw,0,1);b=pop.score(pool);h=hybrid(c,m,.25,b)
    both=np.isfinite(c)&np.isfinite(m);fallback=~both
    cc=np.where(both,.25*c,0.);mm=np.where(both,.75*m,0.);fb=np.where(fallback,h,0.)
    if not np.allclose(cc+mm+fb,h,atol=1e-12):raise ValueError('Contribution reconstruction failed')
    arrays=dict(content=c,mf_raw=raw,mf_clipped=m,hybrid=h,
                nominal_content=.25*c,nominal_mf=.75*m,
                applied_content=cc,applied_mf=mm,fallback_contribution=fb)
    orders={k:rank(pool,arrays[k])for k in ('content','mf_raw','mf_clipped','hybrid')}
    return dict(pool=pool,arrays=arrays,factors=factors,fallback=fallback,
                vector_norm=float(np.linalg.norm(v))if v is not None else None,
                known_support=sum(i in mf.items for i,r in support),orders=orders)


def rank_info(pool,values):
    """Full finite ranking, 5/6 margin, exact adjacent ties (all and Top5)."""
    order=rank(pool,values);lookup=dict(zip(pool,map(float,values)));scores=[lookup[i]for i in order]
    return dict(top=order[:5],order=order,margin=scores[4]-scores[5]if len(scores)>5 else None,
                adjacent_ties=sum(a==b for a,b in zip(scores,scores[1:])),
                top5_adjacent_ties=sum(a==b for a,b in zip(scores[:5],scores[1:5])))


def user_means(rows,key,condition=lambda r:True):
    """Cluster repeated contexts before averaging a diagnostic scalar."""
    values=defaultdict(list)
    for r in rows:
        if condition(r)and r.get(key)is not None:values[r['user']].append(r[key])
    return {u:mean_finite(v)for u,v in values.items()}


def scalar_summary(rows,keys,condition=lambda r:True):
    """Separate context average, user average and distribution of user averages."""
    selected=[r for r in rows if condition(r)];result={}
    for key in keys:
        users=user_means(selected,key)
        result[key]=dict(context_mean=mean_finite([r.get(key)for r in selected]),
                         user_mean=mean_finite(list(users.values())),user_distribution=distribution(list(users.values())))
    return result
