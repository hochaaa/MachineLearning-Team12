"""V3 explicit-rating SGD: per-edge latent/user-bias/item-bias L2 separated."""
import numpy as np

def edge(p,q,bu,bi,r,mean,latent_l2,bias_l2):
    e=mean+bu+bi+p@q-r
    loss=.5*(e*e+latent_l2*(p@p+q@q)+bias_l2*(bu*bu+bi*bi))
    return loss,(e*q+latent_l2*p,e*p+latent_l2*q,e+bias_l2*bu,e+bias_l2*bi)

class MFV3:
    def __init__(self,config,seed=12):self.config=dict(config);self.seed=seed
    def fit(self,rows):
        c=self.config;self.users={u:n for n,u in enumerate(sorted({u for u,_,_ in rows}))};self.items={i:n for n,i in enumerate(sorted({i for _,i,_ in rows}))};self.mean=float(np.mean([r for _,_,r in rows]));rng=np.random.default_rng(self.seed)
        self.P=rng.normal(0,.05,(len(self.users),c['factors']));self.Q=rng.normal(0,.05,(len(self.items),c['factors']));self.bu=np.zeros(len(self.users));self.bi=np.zeros(len(self.items));indexed=[(self.users[u],self.items[i],r) for u,i,r in rows];self.curve=[]
        for epoch in range(1,c['epochs']+1):
            for n in rng.permutation(len(indexed)):
                u,i,r=indexed[n];p,q=self.P[u].copy(),self.Q[i].copy();_,g=edge(p,q,self.bu[u],self.bi[i],r,self.mean,c['latent_l2'],c['bias_l2']);lr=c['learning_rate'];self.P[u]-=lr*g[0];self.Q[i]-=lr*g[1];self.bu[u]-=lr*g[2];self.bi[i]-=lr*g[3]
            if epoch%10==0:
                loss=float(np.mean([edge(self.P[u],self.Q[i],self.bu[u],self.bi[i],r,self.mean,c['latent_l2'],c['bias_l2'])[0] for u,i,r in indexed]));assert np.isfinite(loss)
                self.curve.append({'epoch':epoch,'train_half_regularized_loss':loss,'P_norm':float(np.linalg.norm(self.P)),'Q_norm':float(np.linalg.norm(self.Q))})
        self.best_epoch=c['epochs'];return self
    def score(self,user,pool):
        if user not in self.users:return np.full(len(pool),np.nan)
        u=self.users[user];return np.array([float(np.clip(self.mean+self.bu[u]+self.bi[self.items[i]]+self.P[u]@self.Q[self.items[i]],0,1)) if i in self.items else np.nan for i in pool])
