"""Observed-pair BPR SGD. Reuses local V2-7 pairing and convex Fold-in.

No third-party implementation copied. Parameters: factors = latent dimension;
epochs = pair passes; learning_rate = SGD step; regularization = global L2;
seed = initialization/order seed. Training accepts only train triples and rejects
excluded users. Item factors are immutable at inference, user factors not exported.
"""
from types import SimpleNamespace
import math
import numpy as np
from experiments.scent_v2.pairwise_mf.pairwise_data import build_pairs
from experiments.scent_v2.pairwise_mf.fold_in import fold_in


def step(P,Q,scale,u,i,j,lr,reg,n_pairs):
    """Lazy exact global decay, equivalent to shrinking every factor each step.

    All gradients use PRE-update actual factors; scale defers global shrinkage.
    """
    p=scale*P[u].copy(); qi=scale*Q[i].copy(); qj=scale*Q[j].copy()
    diff=qi-qj; gap=float(np.einsum('i,i->',p,diff))
    # sigmoid(-gap), branch avoids overflow for large finite margins.
    s=math.exp(-gap)/(1+math.exp(-gap)) if gap>=0 else 1/(1+math.exp(gap))
    scale*=1-2*lr*reg/n_pairs
    P[u]+=lr*s*diff/scale; Q[i]+=lr*s*p/scale; Q[j]-=lr*s*p/scale
    return scale


def fit(rows,excluded_users=(),factors=4,epochs=160,learning_rate=.01,regularization=.01,seed=12):
    """Pair-only model; no held-out input or unknown-item negative generation."""
    if factors<1 or epochs<1 or learning_rate<=0 or regularization<=0:raise ValueError('Positive training parameters required')
    pairs,stats=build_pairs(rows,excluded_users)
    if not pairs:raise ValueError('No unequal observed train pairs')
    users={u:n for n,u in enumerate(sorted({u for u,i,j in pairs}))}
    items={i:n for n,i in enumerate(sorted({i for u,a,b in pairs for i in (a,b)}))}
    arr=np.asarray([(users[u],items[i],items[j]) for u,i,j in pairs],int)
    rng=np.random.default_rng(seed);P=rng.uniform(0,.2,(len(users),factors));Q=rng.uniform(0,.2,(len(items),factors));scale=1.;history=[]
    def diagnostics(epoch):
        p=scale*P;q=scale*Q;u,i,j=arr.T;gaps=np.einsum('ni,ni->n',p[u],q[i]-q[j]);penalty=regularization*(np.sum(p*p)+np.sum(q*q))
        history.append(dict(epoch=epoch,objective=float(np.logaddexp(0.,-gaps).sum()+penalty),pair_accuracy=float(np.mean(gaps>0))))
        return gaps
    diagnostics(0)
    for epoch in range(epochs):
        for n in rng.permutation(len(arr)):
            u,i,j=arr[n];scale=step(P,Q,scale,u,i,j,learning_rate,regularization,len(arr))
        if (epoch+1)%20==0 or epoch+1==epochs:diagnostics(epoch+1)
    gaps=diagnostics(epochs) if history[-1]['epoch']!=epochs else np.einsum('ni,ni->n',(scale*P)[arr[:,0]],(scale*Q)[arr[:,1]]-(scale*Q)[arr[:,2]])
    Q=scale*Q
    if not np.isfinite(Q).all() or not np.isfinite(P).all():raise FloatingPointError('Nonfinite BPR factors')
    Q.flags.writeable=False;stats.pop('user_pair_counts_private')
    model=SimpleNamespace(Q=Q,items=items,factors=factors,reg=regularization,variant='variant_a',temperature=max(float(np.sqrt(np.mean(gaps*gaps))),1e-6))
    return model,dict(pair_statistics=stats,history=history,train_temperature=model.temperature)


def scores(model,support,pool):
    """Fixed-Q Support-only Fold-in; sigmoid calibration uses TRAIN temperature.

    Return None for explicit whole-user legacy Hybrid fallback. Missing item
    factors remain NaN and use the unchanged component fallback, never fake Q.
    """
    p,diag=fold_in(model,support)
    if p is None:return None,diag
    center=float(np.mean([np.einsum('i,i->',p,model.Q[model.items[i]]) for i,y in support if i in model.items]))
    raw=np.asarray([float(np.einsum('i,i->',p,model.Q[model.items[i]])) if i in model.items else np.nan for i in pool])
    result=np.full(raw.shape,np.nan);valid=np.isfinite(raw)
    result[valid]=np.exp(-np.logaddexp(0.,-(raw[valid]-center)/model.temperature))
    return result,diag
