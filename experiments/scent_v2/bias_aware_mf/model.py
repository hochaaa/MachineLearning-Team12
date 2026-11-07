"""Local extension of perfume.improvements.BiasedMatrixFactorization's SGD recipe.

Original project algorithm reused; split factor/bias L2 and support-user shrinkage.
No external implementation or library added.
"""
import numpy as np
from perfume.models import MatrixFactorization

class BiasAwareMF(MatrixFactorization):
    """mu + bu + bi + p.q; parameters normalized0..1, mean fitted on train only."""
    def __init__(self,bias_regularization=.01,**kwargs):
        super().__init__(**kwargs)
        if bias_regularization<=0:raise ValueError('Positive bias L2 required')
        self.bias_reg=float(bias_regularization)
    def fit(self,rows):
        """rows: unique train-only(user,item,rating). Same SGD/L2 convention as legacy."""
        if not rows or len({(u,i) for u,i,r in rows})!=len(rows):raise ValueError('Nonempty unique train pairs required')
        if any(not np.isfinite(r) or not 0<=r<=1 for u,i,r in rows):raise ValueError('Expected normalized finite ratings')
        self.users={u:n for n,u in enumerate(sorted({u for u,i,r in rows}))};self.items={i:n for n,i in enumerate(sorted({i for u,i,r in rows}))}
        self.mean=float(np.mean([r for u,i,r in rows]));rng=np.random.default_rng(self.seed)
        self.P=rng.normal(0,.05,(len(self.users),self.factors));self.Q=rng.normal(0,.05,(len(self.items),self.factors));self.user_bias=np.zeros(len(self.users));self.item_bias=np.zeros(len(self.items))
        edges=[(self.users[u],self.items[i],float(r)) for u,i,r in rows];self.losses=[]
        for epoch in range(self.epochs):
            for n in rng.permutation(len(edges)):
                u,i,r=edges[n];p=self.P[u].copy();q=self.Q[i].copy()
                error=r-(self.mean+self.user_bias[u]+self.item_bias[i]+np.einsum('i,i->',p,q))
                self.P[u]+=self.lr*(error*q-self.reg*p);self.Q[i]+=self.lr*(error*p-self.reg*q)
                self.user_bias[u]+=self.lr*(error-self.bias_reg*self.user_bias[u]);self.item_bias[i]+=self.lr*(error-self.bias_reg*self.item_bias[i])
            loss=sum((r-self.mean-self.user_bias[u]-self.item_bias[i]-np.einsum('i,i->',self.P[u],self.Q[i]))**2+self.reg*(np.einsum('i,i->',self.P[u],self.P[u])+np.einsum('i,i->',self.Q[i],self.Q[i]))+self.bias_reg*(self.user_bias[u]**2+self.item_bias[i]**2) for u,i,r in edges)/len(edges)
            if not np.isfinite(loss):raise FloatingPointError('Bias MF diverged')
            self.losses.append(float(loss))
        return self
    def fold_in(self,support,bias_shrinkage=1.):
        """Solve joint latent and intercept from5 known/unknown Support only; no answers."""
        if len(support)!=5 or len({i for i,r in support})!=5:raise ValueError('Five distinct support required')
        if any(not np.isfinite(r) or not 0<=r<=1 for i,r in support) or bias_shrinkage<=0:raise ValueError('Invalid support/shrinkage')
        known=[(i,r) for i,r in support if i in self.items]
        if not known:return None
        a=np.asarray([np.r_[self.Q[self.items[i]],1.] for i,r in known],float)
        y=np.asarray([r-self.mean-self.item_bias[self.items[i]] for i,r in known],float)
        penalty=np.asarray([self.reg]*self.factors+[self.bias_reg*bias_shrinkage])*len(known)
        theta=np.linalg.solve(np.einsum('ni,nj->ij',a,a)+np.diag(penalty),np.einsum('ni,n->i',a,y))
        if not np.isfinite(theta).all():raise ValueError('Nonfinite user fold-in')
        return theta
    def score_vector(self,theta,candidates):
        """Unknown items or unusable support remain NaN; no invented item factors/bias."""
        return np.asarray([float(np.clip(self.mean+self.item_bias[self.items[i]]+theta[-1]+np.einsum('i,i->',theta[:-1],self.Q[self.items[i]]),0,1)) if theta is not None and i in self.items else np.nan for i in candidates])


def freeze_user_state(model):
    """Remove training-user state before evaluation; fix learned item state read-only."""
    for name in ('P','user_bias','users'):
        if hasattr(model,name):delattr(model,name)
    model.Q.flags.writeable=False
    if hasattr(model,'item_bias'):model.item_bias.flags.writeable=False
    return model
