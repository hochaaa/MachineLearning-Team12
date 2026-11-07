"""Fit each fold independently by reusing unmodified original algorithm code."""
import hashlib
import json
import numpy as np
from perfume.models import Content, MatrixFactorization, Baseline
from .config import POLICY


def fit_fold(rows, evaluation_users, catalog):
    """Reject evaluation users before any fit. No answers accepted by this API.

    Return frozen-in-memory models and training evidence. Three real MF fits
    are performed by the runner; neither old weights nor fit caches are loaded.
    """
    if {u for u, _, _ in rows} & set(evaluation_users):
        raise ValueError('Evaluation ratings reached fit boundary')
    content = Content().fit(catalog, {i for _, i, _ in rows})
    popularity = Baseline().fit(rows)
    mf = MatrixFactorization(factors=4, epochs=160, learning_rate=.01,
                            regularization=.01, seed=12).fit(rows)
    if not np.isfinite(mf.Q).all() or not np.isfinite(mf.P).all():
        raise ValueError('Nonfinite training factors')
    mf.Q.flags.writeable = False
    evidence = dict(users=len(mf.users), items=len(mf.items), ratings=len(rows),
                    evaluation_user_training_ratings=0,
                    train_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                    q_sha256=hashlib.sha256(mf.Q.tobytes()).hexdigest(),
                    loss_first=mf.losses[0], loss_last=mf.losses[-1],
                    policy=POLICY, actual_mf_fits=1)
    return content, mf, popularity, evidence
