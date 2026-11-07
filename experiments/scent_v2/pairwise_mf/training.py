"""Transparent observed-pair SGD; original baseline implementation unchanged.

Local reuse: original MatrixFactorization simultaneous copied-vector rating update.
No external code copied. New objectives/regularization explicitly differ below.
"""
from types import SimpleNamespace
import numpy as np
from .config import POLICY
from .pairwise_data import build_pairs


def sigmoid(x):
    """Stable logistic via logaddexp; accepts finite scalar/array, no overflow."""
    x=np.asarray(x,dtype=np.float64);out=np.full(x.shape,np.nan);mask=np.isfinite(x)
    out[mask]=np.exp(-np.logaddexp(0.,-x[mask]));return out


def pair_loss_gradient(p,qi,qj):
    """One observed high/low pair; return stable softplus and simultaneous gradients."""
    diff=qi-qj;d=float(np.einsum('i,i->',p,diff));s=float(sigmoid(-d))
    return float(np.logaddexp(0.,-d)),-s*diff,-s*p,s*p


def objectives(P,Q,ratings,pairs,variant):
    """Logged exact objective, separate train fit and pair discrimination diagnostics.

    Ratings/pairs are integer-index arrays from Train only. B regularization is
    event-weighted like original SGD; A global penalty is sum-based, as requested.
    """
    u,i,y=ratings;pu,qi=P[u],Q[i];pred=np.einsum('ni,ni->n',pu,qi);err=pred-y
    if len(pairs):
        a,b,c=pairs.T;d=np.einsum('ni,ni->n',P[a],Q[b]-Q[c]);pl=float(np.mean(np.logaddexp(0.,-d)));pa=float(np.mean(d>0))
    else:pl=0.;pa=None
    rmse=float(np.sqrt(np.mean(err*err)))if len(y)else None
    rating=float(np.mean(.5*err*err));reg=POLICY['regularization']
    if variant=='variant_a':penalty=reg*(float(np.sum(P*P))+float(np.sum(Q*Q)));total=len(pairs)*pl+penalty
    else:penalty=.5*reg*float(np.mean(np.sum(pu*pu,axis=1)+np.sum(qi*qi,axis=1)));total=rating+penalty+POLICY['beta']*pl
    return dict(objective=total,rating_loss=rating,pairwise_loss=pl,pairwise_sum=len(pairs)*pl,pairwise_accuracy=pa,regularization_loss=penalty,train_rating_rmse=rmse,Q_norm=float(np.linalg.norm(Q)),P_norm=float(np.linalg.norm(P)))


def fit(rows,excluded_users,variant):
    """Train from scratch: normalized Train triples, rejected eval users, A/B policy.

    A uses only users/items with observed unequal pairs; B retains all rating items.
    No existing Q or heldout ratings are accepted. No fit caching is performed.
    """
    if variant not in ('variant_a','variant_b'):raise ValueError('Unknown variant')
    pairs,stats=build_pairs(rows,excluded_users)
    if not pairs:raise ValueError('No observed unequal training pairs')
    us=sorted({u for u,i,j in pairs}if variant=='variant_a'else{u for u,i,r in rows});it=sorted({i for u,a,b in pairs for i in(a,b)}if variant=='variant_a'else{i for u,i,r in rows})
    users={u:n for n,u in enumerate(us)};items={i:n for n,i in enumerate(it)}
    rng=np.random.default_rng(POLICY['seed']);P=rng.uniform(0,.2,(len(us),4));Q=rng.uniform(0,.2,(len(it),4))
    arr=np.array([(users[u],items[i],items[j])for u,i,j in pairs],dtype=int)
    rated=[(users[u],items[i],y)for u,i,y in rows if u in users and i in items]
    r=np.array(rated);ratings=(r[:,0].astype(int),r[:,1].astype(int),r[:,2]);lr=.01;reg=.01;history=[]
    history.append(dict(epoch=0,**objectives(P,Q,ratings,arr,variant)))
    for epoch in range(160):
        if variant=='variant_b':
            for n in rng.permutation(len(rated)):
                u,i,y=rated[n];p,q=P[u].copy(),Q[i].copy();err=y-float(np.einsum('i,i->',p,q))
                P[u]+=lr*(err*q-reg*p);Q[i]+=lr*(err*p-reg*q)
        scale=1. if variant=='variant_a'else POLICY['beta']*len(rated)/len(arr)
        for n in rng.permutation(len(arr)):
            u,i,j=arr[n];p,qi,qj=P[u].copy(),Q[i].copy(),Q[j].copy();loss,gp,gi,gj=pair_loss_gradient(p,qi,qj)
            if variant=='variant_a':
                # Distribute global lambda||P,Q||² over n_pair stochastic steps.
                shrink=1-2*lr*reg/len(arr);P*=shrink;Q*=shrink
            P[u]-=lr*scale*gp;Q[i]-=lr*scale*gi;Q[j]-=lr*scale*gj
        if not np.isfinite(P).all()or not np.isfinite(Q).all():raise FloatingPointError('Nonfinite training factors')
        history.append(dict(epoch=epoch+1,**objectives(P,Q,ratings,arr,variant)))
    Q.flags.writeable=False
    return SimpleNamespace(Q=Q,P=P,items=items,users=users,factors=4,reg=.01,variant=variant),dict(pair_statistics=stats,history=history,variant=variant,finite=True)
