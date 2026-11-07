"""Pairwise Support-only convex fold-in with immutable item factors."""
import hashlib
import numpy as np
from .config import POLICY
from .training import sigmoid
from .pairwise_data import build_pairs


def loss_grad_hessian(p,diffs,reg=.01):
    """sum softplus(-D p)+reg*p²; D rows are known-factor Support differences."""
    z=np.einsum('ni,i->n',diffs,p);s=sigmoid(-z)
    loss=float(np.logaddexp(0.,-z).sum()+reg*np.sum(p*p))
    grad=-np.einsum('n,ni->i',s,diffs)+2*reg*p
    H=np.einsum('n,ni,nj->ij',s*(1-s),diffs,diffs)+2*reg*np.eye(len(p))
    return loss,grad,H


def fold_in(mf,support):
    """Exactly five normalized distinct Support ratings; no labels or user history.

    A: known-factor strict pair differences, fixed Newton50/backtracking20/λ.01.
    Unavailable/no pairs/nonconvergence/zero vector => None + explicit reason.
    B/baseline: original Ridge .01. Q byte hash is checked around inference.
    """
    if len(support)!=5 or len({i for i,y in support})!=5:raise ValueError('Exactly five Support required')
    if any(not np.isfinite(y)or not 0<=y<=1 for i,y in support):raise ValueError('Normalized finite ratings')
    pin=hashlib.sha256(mf.Q.tobytes()).hexdigest();known=[(i,y)for i,y in support if i in mf.items]
    pairs,_=build_pairs([('support',i,y)for i,y in known])
    diag=dict(known_support=len(known),support_pairs=len(pairs),status='ok',iterations=0,gradient_norm=None,zero_vector=False)
    if getattr(mf,'variant','baseline')!='variant_a':
        from experiments.scent_v2.recommend import fold_in as ridge
        p=ridge(mf,support);diag['status']='ok'if p is not None else 'no_known_support'
    elif not pairs:p=None;diag['status']='no_known_support'if not known else 'no_support_pairs'
    else:
        D=np.array([mf.Q[mf.items[i]]-mf.Q[mf.items[j]]for u,i,j in pairs]);p=np.zeros(mf.factors);converged=False
        for n in range(POLICY['foldin_iterations']):
            loss,g,H=loss_grad_hessian(p,D);norm=float(np.linalg.norm(g));diag.update(iterations=n+1,gradient_norm=norm)
            if norm<=POLICY['foldin_tolerance']:converged=True;break
            try:step=np.linalg.solve(H+POLICY['foldin_damping']*np.eye(mf.factors),g)
            except np.linalg.LinAlgError:p=None;diag['status']='solve_failed';break
            slope=float(np.einsum('i,i->',g,step));accepted=False
            for b in range(POLICY['foldin_backtracking']):
                rate=.5**b;candidate=p-rate*step
                if loss_grad_hessian(candidate,D)[0]<=loss-1e-4*rate*slope:p=candidate;accepted=True;break
            if not accepted:p=None;diag['status']='line_search_failed';break
        if p is not None and not converged:
            diag['gradient_norm']=float(np.linalg.norm(loss_grad_hessian(p,D)[1]));converged=diag['gradient_norm']<=POLICY['foldin_tolerance']
        if p is not None and not converged:p=None;diag['status']='not_converged'
        if p is not None and np.linalg.norm(p)<1e-12:p=None;diag.update(status='zero_vector',zero_vector=True)
    if p is not None and not np.isfinite(p).all():raise FloatingPointError('Nonfinite fold-in vector')
    assert hashlib.sha256(mf.Q.tobytes()).hexdigest()==pin
    diag['P_norm']=float(np.linalg.norm(p))if p is not None else None
    diag['support_rmse']=float(np.sqrt(np.mean([(float(np.einsum('i,i->',p,mf.Q[mf.items[i]]))-y)**2 for i,y in known])))if p is not None and known else None
    return p,diag
