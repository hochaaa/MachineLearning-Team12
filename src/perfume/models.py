"""Explainable models using NumPy plus sparse dictionaries, no opaque recommender library."""
import math
from collections import Counter, defaultdict
import numpy as np


class Content:
    """Binary TF + smoothed IDF cosine, fitted only on training-item documents."""
    def fit(self, catalog, train_items):
        """catalog maps item->tokens; train_items identifies documents allowed for vocabulary/IDF."""
        ids = sorted(set(train_items))
        if not ids:
            raise ValueError('No training documents')
        df = Counter(t for item in ids for t in set(catalog[item]['tokens']))
        self.idf = {t: math.log((1 + len(ids)) / (1 + n)) + 1 for t, n in df.items()}
        self.vectors = {}
        for item, row in catalog.items():
            vector = {t: self.idf[t] for t in set(row['tokens']) if t in self.idf}
            norm = math.sqrt(sum(v*v for v in vector.values()))
            self.vectors[item] = {t: v/norm for t, v in vector.items()} if norm else {}
        return self

    def score(self, support, candidates):
        """support is (item,rating in [0,1]); use positive rating weights, no answer access.

        Empty/all-zero/no-vocabulary support returns NaN, triggering explicit fallback.
        """
        profile = defaultdict(float)
        for item, rating in support:
            for token, value in self.vectors.get(item, {}).items():
                profile[token] += max(0, rating) * value
        norm = math.sqrt(sum(v*v for v in profile.values()))
        if not norm:
            return np.full(len(candidates), np.nan)
        return np.array([sum(profile[t]*v for t, v in self.vectors.get(i, {}).items()) / norm
                         if self.vectors.get(i) else np.nan for i in candidates])


class MatrixFactorization:
    """Bias-free explicit-rating MF trained by simultaneous SGD + per-observation L2."""
    def __init__(self, factors=12, epochs=80, learning_rate=0.025, regularization=0.03, seed=12):
        """factors: latent width; epochs: shuffled passes; learning_rate: SGD step;
        regularization: per-observation L2 weight; seed: initialization/permutation RNG.
        """
        if factors < 1 or epochs < 1 or learning_rate <= 0 or regularization <= 0:
            raise ValueError('MF parameters must be positive')
        self.factors, self.epochs, self.lr, self.reg, self.seed = factors, epochs, learning_rate, regularization, seed

    def fit(self, rows):
        """Fit unique train (user,item,rating) edges, never held-out values."""
        if not rows:
            raise ValueError('No train ratings')
        self.users = {u: n for n, u in enumerate(sorted({u for u, _, _ in rows}))}
        self.items = {i: n for n, i in enumerate(sorted({i for _, i, _ in rows}))}
        rng = np.random.default_rng(self.seed)
        self.P = rng.uniform(0, 0.2, (len(self.users), self.factors))
        self.Q = rng.uniform(0, 0.2, (len(self.items), self.factors))
        indexed = [(self.users[u], self.items[i], float(r)) for u, i, r in rows]
        self.losses = []
        for _ in range(self.epochs):
            for n in rng.permutation(len(indexed)):
                u, i, rating = indexed[n]
                p, q = self.P[u].copy(), self.Q[i].copy()
                error = rating - p @ q
                self.P[u] += self.lr * (error*q - self.reg*p)
                self.Q[i] += self.lr * (error*p - self.reg*q)
            loss = sum((r-self.P[u]@self.Q[i])**2 + self.reg*(self.P[u]@self.P[u]+self.Q[i]@self.Q[i])
                       for u, i, r in indexed) / len(indexed)
            if not np.isfinite(loss):
                raise FloatingPointError('MF diverged')
            self.losses.append(float(loss))
        return self

    def score(self, user, candidates):
        """Predict existing user ratings; unseen user/item -> NaN (not fake factor)."""
        if user not in self.users:
            return np.full(len(candidates), np.nan)
        return self.score_vector(self.P[self.users[user]], candidates)

    def score_vector(self, vector, candidates):
        """Fixed-factor dot products; clip explicit predictions to declared [0,1] scale."""
        return np.array([float(np.clip(vector @ self.Q[self.items[i]], 0, 1))
                         if i in self.items else np.nan for i in candidates])

    def fold_in(self, support):
        """New user ridge solution from support only; item factors remain unchanged.

        support: (item,normalized rating). Non-trained items are ignored.
        Uses the same per-observation L2 objective, giving n*lambda regularization.
        """
        known = [(i, r) for i, r in support if i in self.items]
        if not known:
            return None
        q = np.array([self.Q[self.items[i]] for i, _ in known])
        y = np.array([r for _, r in known])
        return np.linalg.solve(q.T@q + len(known)*self.reg*np.eye(self.factors), q.T@y)


class Baseline:
    """Train-only popularity ranking and global-mean explicit rating prediction."""
    def fit(self, rows):
        """Count training observations by item; keep global mean for MAE/RMSE."""
        self.counts = Counter(i for _, i, _ in rows)
        self.mean = float(np.mean([r for _, _, r in rows]))
        self.maximum = max(self.counts.values(), default=1)
        return self

    def score(self, candidates):
        """Bounded log popularity in [0,1] for each candidate; unseen item -> 0."""
        return np.array([math.log1p(self.counts[i])/math.log1p(self.maximum) for i in candidates])


def hybrid(content, mf, alpha, fallback):
    """Weighted scores: alpha*content+(1-alpha)*MF; component fallback, then popularity.

    Cosine and clipped rating predictions share [0,1] bounds by construction; no external
    statistics are estimated. Missing values are represented by NaN, not zero.
    """
    if not 0 <= alpha <= 1:
        raise ValueError('alpha must be in [0,1]')
    c, m = np.isfinite(content), np.isfinite(mf)
    return np.where(c & m, alpha*content+(1-alpha)*mf,
                    np.where(c, content, np.where(m, mf, fallback)))


def knowledge(catalog, candidates, scores, required=(), forbidden=(), preferred=(), soft_weight=0.1,
              season=None, max_price=None):
    """Hard all-required/no-forbidden token rules, then soft preference bonus.

    required/forbidden/preferred: exact note:/accord: tokens. Soft score adds
    soft_weight * fraction of preferred tokens present. Unsupported season/price raises.
    Returns eligible (item,score,explanation) records; no eligible result is fabricated.
    """
    if season is not None or max_price is not None:
        raise ValueError('Season/price disabled: development metadata not validated')
    results = []
    for item, score in zip(candidates, scores):
        available = set(catalog[item]['tokens'])
        if set(required) <= available and not set(forbidden) & available:
            matched = sorted(set(preferred) & available)
            bonus = soft_weight * len(matched)/len(set(preferred)) if preferred else 0
            results.append((item, float(score+bonus), {'required_satisfied': True, 'preferred_matched': matched}))
    return sorted(results, key=lambda r: (-r[1], r[0]))
