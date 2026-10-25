"""Explicit rating SGD with independently regularized biases and nested stopping."""
import numpy as np
from data import inner_stop
from perfume.models import MatrixFactorization

def edge_objective_gradient(p,q,bu,bi,r,mean,reg):
    """Half squared-error plus half per-observation L2; gradients at old state."""
    error=mean+bu+bi+p@q-r
    loss=.5*(error**2+reg*(p@p+q@q+bu*bu+bi*bi))
    return loss,(error*q+reg*p,error*p+reg*q,error+reg*bu,error+reg*bi)
class BiasMF:
    def __init__(self,config,seed=12):self.config=dict(config);self.seed=seed
    def fit(self,rows,stop_rows=()):
        c=self.config;self.users={u:n for n,u in enumerate(sorted({r[0] for r in rows}))};self.items={i:n for n,i in enumerate(sorted({r[1] for r in rows}))}
        self.mean=float(np.mean([r for _,_,r in rows]));rng=np.random.default_rng(self.seed);f=c['factors']
        self.P=rng.normal(0,.05,(len(self.users),f));self.Q=rng.normal(0,.05,(len(self.items),f));self.bu=np.zeros(len(self.users));self.bi=np.zeros(len(self.items))
        indexed=[(self.users[u],self.items[i],r) for u,i,r in rows];self.curve=[];best=float('inf');stale=0;best_state=None;self.best_epoch=c['epochs']
        for epoch in range(1,c['epochs']+1):
            for j in rng.permutation(len(indexed)):
                u,i,r=indexed[j];p=self.P[u].copy();q=self.Q[i].copy();bu=self.bu[u];bi=self.bi[i]
                _,g=edge_objective_gradient(p,q,bu,bi,r,self.mean,c['regularization']);lr=c['learning_rate']
                self.P[u]-=lr*g[0];self.Q[i]-=lr*g[1];self.bu[u]-=lr*g[2];self.bi[i]-=lr*g[3]
            if epoch%10==0 or epoch==c['epochs']:
                loss=float(np.mean([edge_objective_gradient(self.P[u],self.Q[i],self.bu[u],self.bi[i],r,self.mean,c['regularization'])[0] for u,i,r in indexed]))
                errors=[self.raw(u,i)-r for u,i,r in stop_rows if u in self.users and i in self.items];rmse=float(np.sqrt(np.mean(np.square(errors)))) if errors else None
                self.curve.append({'epoch':epoch,'train_half_regularized_loss':loss,'nested_stop_rmse':rmse,'stop_n':len(errors)})
                if not np.isfinite(loss):raise FloatingPointError('MF diverged')
                if rmse is not None:
                    if rmse<best-1e-5:best=rmse;stale=0;self.best_epoch=epoch;best_state=[x.copy() for x in [self.P,self.Q,self.bu,self.bi]]
                    else:stale+=1
                    if stale>=3:break
        if best_state is not None:self.P,self.Q,self.bu,self.bi=best_state
        return self
    def raw(self,u,i):
        if u not in self.users or i not in self.items:return float('nan')
        a,b=self.users[u],self.items[i];return float(self.mean+self.bu[a]+self.bi[b]+self.P[a]@self.Q[b])
    def score(self,u,pool):return np.array([np.clip(self.raw(u,i),0,1) for i in pool])

def train_mf(rows,config,seed=12):
    """Legacy exact baseline; bias candidates stop on a nested train-only split then refit."""
    if not config['biased']:
        m=MatrixFactorization(**{k:config[k] for k in ['factors','epochs','learning_rate','regularization']},seed=seed).fit(rows)
        m.config=dict(config);m.best_epoch=config['epochs'];m.stop_curve=[];return m
    c=dict(config);stop_curve=[]
    if c.get('early'):
        inner,stop=inner_stop(rows,seed)
        probe=BiasMF(c,seed).fit(inner,stop);c['epochs']=probe.best_epoch if stop else min(40,c['epochs']);stop_curve=probe.curve
    model=BiasMF(c,seed).fit(rows);model.stop_curve=stop_curve;model.best_epoch=c['epochs'];return model
