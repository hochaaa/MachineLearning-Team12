"""Validated new-user ridge inference. No item state changes."""
import numpy as np

def validate_support(support,catalog=None,required=None):
    """Reject duplicates, nonfinite/out-of-range values; stable sort assures order invariance."""
    if required is not None and len(support)!=required:raise ValueError(f'Exactly {required} ratings required')
    if not support:raise ValueError('At least one rating required')
    if len({i for i,_ in support})!=len(support):raise ValueError('Duplicate perfume')
    for i,r in support:
        if catalog is not None and i not in catalog:raise ValueError('Unknown perfume')
        if isinstance(r,bool) or not isinstance(r,(int,float)) or not np.isfinite(r) or not 0<=r<=1:raise ValueError('Ratings must be finite normalized numbers in [0,1]')
    return sorted(support)

def fold_in(model,support,regularization=None):
    """Joint bias/factor ridge, n*lambda; caller validates catalog identity first."""
    support=validate_support(support);known=[(i,r) for i,r in support if i in model.items]
    if not known:return None
    biased=hasattr(model,'bu');q=np.array([model.Q[model.items[i]] for i,_ in known]);y=np.array([r for _,r in known])
    if biased:
        y-=model.mean+np.array([model.bi[model.items[i]] for i,_ in known]);q=np.c_[q,np.ones(len(q))]
    reg=regularization if regularization is not None else (model.config['regularization'] if hasattr(model,'config') else model.reg)
    if reg<=0:raise ValueError('Positive ridge required')
    return np.linalg.solve(q.T@q+len(known)*reg*np.eye(q.shape[1]),q.T@y)

def score_vector(model,vector,pool):
    if vector is None:return np.full(len(pool),np.nan)
    if not hasattr(model,'bu'):return model.score_vector(vector,pool)
    return np.array([float(np.clip(model.mean+model.bi[model.items[i]]+vector[-1]+vector[:-1]@model.Q[model.items[i]],0,1)) if i in model.items else np.nan for i in pool])
