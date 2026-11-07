"""Metric harness only: answer values never reach recommendation functions."""
import itertools
from collections import Counter
import numpy as np
from perfume.evaluation import ranking_metrics


def metrics(top, answers):
    """Binary positives >=.7; all observed positives remain in Recall/IDCG.

    Unscorable/out-of-pool positives are misses. Empty positive sets return None.
    Unknown items are not asserted to be disliked. Precision denominator is five.
    """
    positives = {i for i, r in answers if r >= .7}
    result = ranking_metrics(top, positives, 5)
    if result is not None:
        result['hit_rate'] = float(bool(set(top)&positives))
    return result


def aggregate(records):
    """Aggregate one baseline recommendation per user; coverage uses ALL users.

    Concentration: maximum item share, top-five most frequent item share, slot HHI.
    Coverage denominator 479 is a reference catalog, including in Track B.
    """
    groups = {}
    for row in records:
        groups.setdefault((row['track'], row['method']), []).append(row)
    result = []
    for (track, method), rows in groups.items():
        positive = [r for r in rows if r['accuracy'] is not None]
        count = Counter(i for r in rows for i in r['top'])
        slots = sum(count.values())
        summary = dict(track=track, method=method, users=len(rows),
                       positive_users=len(positive), no_positive_users=len(rows)-len(positive),
                       coverage_items=len(count), coverage_fraction_479=len(count)/479,
                       top1_slot_share=max(count.values(),default=0)/slots if slots else None,
                       top5_slot_share=sum(v for _,v in count.most_common(5))/slots if slots else None,
                       slot_hhi=sum((v/slots)**2 for v in count.values()) if slots else None,
                       candidate_min=min(r['pool'] for r in rows), candidate_max=max(r['pool'] for r in rows),
                       scorable_min=min(r['scorable'] for r in rows), scorable_max=max(r['scorable'] for r in rows),
                       fallback_candidates_mean=float(np.mean([r['fallback_candidates'] for r in rows])),
                       fallback_top5_mean=float(np.mean([r['fallback_top5'] for r in rows])))
        for name in ('ndcg','precision','recall','hit_rate'):
            summary[name] = float(np.mean([r['accuracy'][name] for r in positive])) if positive else None
        result.append(summary)
    return result


def paired(records, robustness, repetitions=20000, seed=12):
    """Percentile bootstrap of paired USER differences; folds have overlapping train sets."""
    results = []
    for track in sorted({r['track'] for r in records}):
        for a,b in [('hybrid','mf'),('hybrid','content'),('mf','content')]:
            subsets = [('ndcg', [r for r in records if r['track']==track and r['accuracy'] is not None])]
            for amp in (.5,1.):
                subsets.extend((f'{name}_{amp:g}',[r for r in robustness if r['track']==track and r['amplitude']==amp])
                               for name in ('replacement','first'))
            for metric, rows in subsets:
                left = {r['user']:(r['accuracy']['ndcg'] if metric=='ndcg' else r[metric.rsplit('_',1)[0]]) for r in rows if r['method']==a}
                right = {r['user']:(r['accuracy']['ndcg'] if metric=='ndcg' else r[metric.rsplit('_',1)[0]]) for r in rows if r['method']==b}
                if set(left)!=set(right):
                    raise ValueError('Paired comparison has mismatched users')
                d = np.array([left[u]-right[u] for u in sorted(left)])
                if not len(d):continue
                rng = np.random.default_rng(seed)
                bs = d[rng.integers(0,len(d),size=(repetitions,len(d)))].mean(axis=1)
                lo,hi = np.quantile(bs,[.025,.975])
                results.append(dict(track=track, comparison=a+'-'+b, metric=metric,
                                    users=len(d), delta=float(d.mean()), low=float(lo), high=float(hi),
                                    negative=int(np.sum(d < -1e-12)), equal=int(np.sum(abs(d)<=1e-12)),
                                    positive=int(np.sum(d > 1e-12))))
    return results
