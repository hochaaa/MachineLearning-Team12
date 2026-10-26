"""Fixed-factor ridge inference with separate latent and user-bias penalties."""
import numpy as np
from foldin_v2 import validate_support

def normalize_support(support,rating_scale=10):
    """Explicit UI/CLI boundary: scale10 raw ratings to normalized1; no auto inference."""
    if rating_scale not in (1,10):raise ValueError('rating_scale must be1 or10')
    for _,r in support:
        if isinstance(r,bool) or not isinstance(r,(int,float)) or not np.isfinite(r) or not 0<=r<=rating_scale:raise ValueError('Finite ratings within explicit scale required')
    ratings=np.asarray([r for _,r in support],dtype=np.float64)/rating_scale
    return [(i,float(r)) for (i,_),r in zip(support,ratings)]

def fold(model,support,policy):
    support=validate_support(support);known=[(i,r) for i,r in support if i in model.items]
    if not known:return None
    biased=hasattr(model,'bu');a=np.array([model.Q[model.items[i]] for i,_ in known]);y=np.asarray([r for _,r in known],dtype=np.float64);pen=np.full(a.shape[1],policy['fold_latent'])
    if biased:
        a=np.c_[a,np.ones(len(a))];pen=np.r_[pen,policy['fold_bias']];y-=model.mean+np.array([model.bi[model.items[i]] for i,_ in known])
    if np.any(pen<=0):raise ValueError('Positive ridge penalties required')
    return np.linalg.solve(a.T@a+len(known)*np.diag(pen),a.T@y)

def score(model,z,pool):
    if z is None:return np.full(len(pool),np.nan)
    biased=hasattr(model,'bu');out=[]
    for i in pool:
        if i not in model.items:out.append(np.nan);continue
        j=model.items[i];v=model.Q[j]@(z[:-1] if biased else z)
        if biased:v+=model.mean+model.bi[j]+z[-1]
        out.append(float(np.clip(v,0,1)))
    return np.array(out)
