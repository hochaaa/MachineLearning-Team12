"""Candidate-score-only normalization/rank fusion, never label-dependent calibration."""
import numpy as np

def normalize_scores(values):
    """User's current unseen candidate finite scores only; constant→.5, missing→NaN."""
    a=np.array(values,dtype=float);finite=np.isfinite(a)
    if finite.any():
        lo,hi=a[finite].min(),a[finite].max();a[finite]=(a[finite]-lo)/(hi-lo) if hi-lo>1e-12 else .5
    return a

def rank_scores(values,pool):
    """Weighted reciprocal rank with offset60; stable canonical ID ties."""
    result=np.full(len(pool),np.nan);order=sorted((n for n,x in enumerate(values) if np.isfinite(x)),key=lambda n:(-values[n],pool[n]))
    for rank,n in enumerate(order,1):result[n]=61/(60+rank)
    return result

def combine(c,m,b,pool,config,history_n):
    """Both components→fusion; one→component; neither→explicit train popularity."""
    c=np.array(c,dtype=float);m=np.array(m,dtype=float);method=config['method'];alpha=config['alpha']
    if method=='minmax':c,m=normalize_scores(c),normalize_scores(m)
    if method=='rrf':c,m=rank_scores(c,pool),rank_scores(m,pool)
    if method=='history':alpha=3/(3+history_n) # .5 for actual 3-support requests.
    validc,validm=np.isfinite(c),np.isfinite(m)
    score=np.where(validc&validm,alpha*c+(1-alpha)*m,np.where(validc,c,np.where(validm,m,b)))
    return score,{'component_fallback':int(np.sum(validc^validm)),'popularity_fallback':int(np.sum(~validc&~validm)),'candidate_scores':len(pool),'alpha':alpha}

def ranked(pool,scores,k=10):
    return [pool[n] for n in sorted(range(len(pool)),key=lambda n:(-float(scores[n]) if np.isfinite(scores[n]) else float('inf'),pool[n])) if np.isfinite(scores[n])][:k]
