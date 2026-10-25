"""Frozen new-user inference boundary; this module has no raw review loader."""
from .models import hybrid
import numpy as np


def recommend_new_user(support, candidates, content, mf, baseline, alpha, k=10):
    """Infer using support only, full predeclared candidates, frozen factors and alpha.

    support: (trained catalog item, normalized rating), no held-out record accepted.
    candidates: catalog-level pool, constructed independently of answer item IDs.
    content/mf/baseline: fitted development objects. alpha: frozen dev-validation weight.
    Returns rankings, never refits objects. Missing factors use content/popularity fallback.
    """
    seen = {i for i, _ in support}
    pool = [i for i in candidates if i not in seen]
    vector = mf.fold_in(support)
    m = mf.score_vector(vector, pool) if vector is not None else np.full(len(pool), np.nan)
    c, b = content.score(support, pool), baseline.score(pool)
    values = hybrid(c, m, alpha, b)
    return [pool[n] for n in sorted(range(len(pool)), key=lambda n: (-values[n], pool[n]))][:k]
