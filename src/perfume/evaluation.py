"""Ranking evaluation: answer labels reside here, never passed to scoring models."""
import math
from collections import defaultdict
import numpy as np
from .models import hybrid


def ranking_metrics(ranked, relevant, k=10):
    """Binary Precision/Recall/NDCG@k. relevant is observed positive held-out item set.

    Precision denominator is k, including when fewer candidates are returned.
    Empty positive sets return None: report exclusion counts, do not invent relevance.
    """
    if k < 1:
        raise ValueError('k must be positive')
    if not relevant:
        return None
    hits = [int(i in relevant) for i in ranked[:k]]
    dcg = sum(h/math.log2(n+2) for n, h in enumerate(hits))
    ideal = sum(1/math.log2(n+2) for n in range(min(k, len(relevant))))
    return {'precision': sum(hits)/k, 'recall': sum(hits)/len(relevant), 'ndcg': dcg/ideal}


def score_users(train, users, candidates, content, mf, baseline, alphas):
    """Compute recommendations using ONLY train history and explicit candidate universe.

    Returns user->method->ranked IDs; this function accepts no held-out item/value input.
    """
    histories = defaultdict(list)
    for user, item, rating in train:
        histories[user].append((item, rating))
    predictions = {}
    for user in users:
        support = histories[user]
        seen = {i for i, _ in support}
        pool = [i for i in candidates if i not in seen]
        b = baseline.score(pool)
        c, m = content.score(support, pool), mf.score(user, pool)
        # Pure method: NaN items remain unscorable, no silent blending with baseline.
        scores = {'popularity': b, 'content': c, 'mf': m}
        scores.update({f'hybrid_{a:g}': hybrid(c, m, a, b) for a in alphas})
        predictions[user] = {name: [pool[n] for n in sorted(range(len(pool)),
                             key=lambda n: (-float(values[n]) if np.isfinite(values[n]) else float('inf'), pool[n]))
                             if np.isfinite(values[n])]
                             for name, values in scores.items()}
    return predictions


def evaluate(predictions, answers, k=10, relevance=0.7):
    """Aggregate rankings with held-out labels; return per-user spread and cohort accounting."""
    positives = defaultdict(set)
    for user, item, rating in answers:
        if rating >= relevance:
            positives[user].add(item)
    per_user, summaries = [], []
    for user, methods in predictions.items():
        for method, ranked in methods.items():
            metrics = ranking_metrics(ranked, positives[user], k)
            if metrics is not None:
                per_user.append({'user': user, 'method': method, **metrics, 'returned': min(k, len(ranked))})
    methods = next(iter(predictions.values())).keys() if predictions else []
    for method in methods:
        rows = [r for r in per_user if r['method'] == method]
        summary = {'method': method, 'evaluation_users': len(predictions), 'positive_users': len(rows),
                   'no_positive_users': len(predictions)-len(rows)}
        for metric in ('precision', 'recall', 'ndcg'):
            values = [r[metric] for r in rows]
            summary[metric] = float(np.mean(values)) if values else None
            summary[metric+'_sd'] = float(np.std(values)) if values else None
        summary['catalog_coverage_items'] = len({i for u in predictions for i in predictions[u][method][:k]})
        summaries.append(summary)
    return summaries, per_user


def rating_errors(rows, mf, baseline):
    """MAE/RMSE for observed labels only, reporting MF factor coverage explicitly."""
    mf_errors, mean_errors = [], []
    for user, item, rating in rows:
        pred = mf.score(user, [item])[0]
        if np.isfinite(pred):
            mf_errors.append(pred-rating)
        mean_errors.append(baseline.mean-rating)
    output = {}
    for name, errors in [('mf', mf_errors), ('global_mean', mean_errors)]:
        output[name] = {'n': len(errors), 'mae': float(np.mean(np.abs(errors))) if errors else None,
                        'rmse': float(np.sqrt(np.mean(np.square(errors)))) if errors else None}
    return output
