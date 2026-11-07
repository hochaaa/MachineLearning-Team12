"""Answer-free inference. Inputs contain five support ratings, never held-out labels."""
import math
import numpy as np
from perfume.models import hybrid


def rank(pool, scores):
    """Rank finite scores only, descending score then original item ID ascending."""
    return [pool[n] for n in sorted(range(len(pool)),
            key=lambda n: (-float(scores[n]) if np.isfinite(scores[n]) else math.inf,
                           pool[n])) if np.isfinite(scores[n])]


def fold_in(mf, support):
    """Same V1 ridge equation, explicit Gram sums for small-matrix portability.

    NumPy 2.3.5 on this host raises spurious invalid-matmul warnings for some
    finite 5x4 inputs. einsum computes the identical sums without that BLAS path.
    Parameters: fixed mf.Q/items/reg/factors and normalized support pairs only.
    Unknown items are ignored; n is the known support count, not always five.
    """
    known=[(i,r)for i,r in support if i in mf.items]
    if not known:return None
    q=np.array([mf.Q[mf.items[i]]for i,r in known],dtype=np.float64)
    y=np.array([r for i,r in known],dtype=np.float64)
    gram=np.einsum('ni,nj->ij',q,q)
    rhs=np.einsum('ni,n->i',q,y)
    vector=np.linalg.solve(gram+len(known)*mf.reg*np.eye(mf.factors),rhs)
    if not np.isfinite(vector).all():raise ValueError('Nonfinite fold-in')
    return vector


def score(support, candidates, content, mf, popularity):
    """support: exactly five distinct (ID, normalized rating) inputs, scale [0,1].

    Unknown support items are ignored by the original fold_in implementation;
    n*lambda therefore uses the actual known count. No trained P[u] is used.
    Missing pure MF scores remain NaN. MF+fallback is explicitly a separate policy.
    """
    if len(support) != 5 or len({i for i, _ in support}) != 5:
        raise ValueError('Exactly five distinct inputs required')
    if not all(np.isfinite(r) and 0 <= r <= 1 for _, r in support):
        raise ValueError('Invalid normalized support rating')
    seen = {i for i, _ in support}
    pool = sorted(set(candidates)-seen)
    vector = fold_in(mf,support)
    raw = np.array([vector @ mf.Q[mf.items[i]] if vector is not None and i in mf.items
                    else np.nan for i in pool])
    m = np.clip(raw, 0, 1)
    c, b = content.score(support, pool), popularity.score(pool)
    fallback = np.where(np.isfinite(m), m, np.where(np.isfinite(c), c, b))
    values = dict(content=c, mf=m, mf_fallback=fallback,
                  hybrid=hybrid(c, m, .25, b))
    result = {}
    for name, scores in values.items():
        ordered = rank(pool, scores)
        lookup = dict(zip(pool, map(float, scores)))
        top = ordered[:5]
        result[name] = dict(top=top, top_scores=[lookup[i] for i in top],
                            scorable=len(ordered), pool=len(pool),
                            margin56=lookup[ordered[4]]-lookup[ordered[5]] if len(ordered)>5 else None,
                            fallback_candidates=sum(not np.isfinite(m[n]) for n in range(len(pool)))
                            if name in ('hybrid','mf_fallback') else 0,
                            fallback_top5=sum(not np.isfinite(m[pool.index(i)]) for i in top)
                            if name in ('hybrid','mf_fallback') else 0)
    return dict(methods=result, known_support=sum(i in mf.items for i, _ in support),
                upper=int(np.sum(raw>1)), lower=int(np.sum(raw<0)))
