"""Validation-only alternatives; legacy models remain unchanged for comparison."""
from collections import defaultdict
import math
import numpy as np
from .models import Content, MatrixFactorization


class ProfileContent(Content):
    """Cosine profiles with train/support-only weights and explicit signed calibration."""
    def __init__(self, mode='rating', relevance=0.7):
        """mode: rating/liked/centered; relevance: frozen positive-rating cutoff for liked."""
        if mode not in ('rating', 'liked', 'centered'):
            raise ValueError('Unknown profile mode')
        self.mode, self.relevance = mode, relevance

    def score(self, support, candidates):
        """support=(item,rating), candidates=independent catalog pool, no labels accepted.

        centered weights subtract support-user mean; signed cosine maps [-1,1] to [0,1].
        No usable liked/centered history returns NaN, never secretly switches profiles.
        """
        if self.mode == 'rating':
            return super().score(support, candidates)
        mean = float(np.mean([r for _, r in support])) if support else 0
        profile = defaultdict(float)
        for item, rating in support:
            weight = (rating if rating >= self.relevance else 0) if self.mode == 'liked' else rating-mean
            for token, value in self.vectors.get(item, {}).items():
                profile[token] += weight*value
        norm = math.sqrt(sum(v*v for v in profile.values()))
        if norm < 1e-12:
            return np.full(len(candidates), np.nan)
        values = np.array([sum(profile[t]*v for t,v in self.vectors.get(i,{}).items())/norm
                           if self.vectors.get(i) else np.nan for i in candidates])
        return (values+1)/2 if self.mode == 'centered' else values


class BiasedMatrixFactorization(MatrixFactorization):
    """SGD MF with train global mean, learned user/item biases and regularized factors."""
    def fit(self, rows):
        """Minimize sum of per-observation squared residual plus L2 on p,q,bu,bi.

        Same parameters as legacy MF. Bias parameters use the same regularization.
        Mean is frozen from train; zero-mean small factor initialization models residuals.
        """
        if not rows:
            raise ValueError('No train ratings')
        self.users = {u:n for n,u in enumerate(sorted({u for u,_,_ in rows}))}
        self.items = {i:n for n,i in enumerate(sorted({i for _,i,_ in rows}))}
        self.mean = float(np.mean([r for _,_,r in rows]))
        rng = np.random.default_rng(self.seed)
        self.P = rng.normal(0,.05,(len(self.users),self.factors))
        self.Q = rng.normal(0,.05,(len(self.items),self.factors))
        self.user_bias = np.zeros(len(self.users))
        self.item_bias = np.zeros(len(self.items))
        indexed=[(self.users[u],self.items[i],float(r)) for u,i,r in rows]
        self.losses=[]
        for _ in range(self.epochs):
            for n in rng.permutation(len(indexed)):
                u,i,rating=indexed[n]
                p,q=self.P[u].copy(),self.Q[i].copy()
                error=rating-(self.mean+self.user_bias[u]+self.item_bias[i]+p@q)
                self.P[u]+=self.lr*(error*q-self.reg*p)
                self.Q[i]+=self.lr*(error*p-self.reg*q)
                self.user_bias[u]+=self.lr*(error-self.reg*self.user_bias[u])
                self.item_bias[i]+=self.lr*(error-self.reg*self.item_bias[i])
            loss=sum((r-self.mean-self.user_bias[u]-self.item_bias[i]-self.P[u]@self.Q[i])**2+
                     self.reg*(self.P[u]@self.P[u]+self.Q[i]@self.Q[i]+self.user_bias[u]**2+self.item_bias[i]**2)
                     for u,i,r in indexed)/len(indexed)
            if not np.isfinite(loss):
                raise FloatingPointError('Biased MF diverged')
            self.losses.append(float(loss))
        return self

    def score(self, user, candidates):
        """Existing-user rating predictions; return NaN for unknown users/items."""
        if user not in self.users:
            return np.full(len(candidates),np.nan)
        u=self.users[user]
        return self.score_vector(np.r_[self.P[u],self.user_bias[u]],candidates)

    def score_vector(self, vector, candidates):
        """vector concatenates new user latent coordinates and bias; item state is fixed."""
        return np.array([float(np.clip(self.mean+vector[-1]+self.item_bias[self.items[i]]+
                                      vector[:-1]@self.Q[self.items[i]],0,1))
                         if i in self.items else np.nan for i in candidates])

    def fold_in(self, support):
        """Joint ridge solve for new user factors/bias, using known-factor support only.

        Residual y removes train mean and fixed item bias. n*lambda matches per-edge L2.
        Does not mutate learned item factors, biases or mean.
        """
        known=[(i,r) for i,r in support if i in self.items]
        if not known:
            return None
        design=np.array([np.r_[self.Q[self.items[i]],1] for i,_ in known])
        y=np.array([r-self.mean-self.item_bias[self.items[i]] for i,r in known])
        return np.linalg.solve(design.T@design+len(known)*self.reg*np.eye(self.factors+1),design.T@y)


def make_mf(parameters, seed=12):
    """Build selected MF without training. parameters includes kind='legacy'/'biased'."""
    parameters=dict(parameters)
    kind=parameters.pop('kind')
    cls={'legacy':MatrixFactorization,'biased':BiasedMatrixFactorization}[kind]
    return cls(**parameters,seed=seed)
