"""Shared-Q lambda inference, user-cluster statistics and inner-only selection."""
from collections import defaultdict
from types import SimpleNamespace
import numpy as np
from experiments.scent_v2.recommend import score,fold_in
from experiments.scent_v2.evaluate import aggregate as aggregate_accuracy
from experiments.scent_v2.robustness import aggregate as aggregate_robustness
from .config import LAMBDAS,POLICY


def view(mf,fold_lambda):
    """Expose identical fixed Q/items with independent inference L2, no trained P.

    mf.reg remains the training coefficient .01. The view's reg is used only by
    the existing V2-0 ridge helper; Q is shared by identity, never copied/updated.
    """
    if fold_lambda not in LAMBDAS:raise ValueError('Unregistered lambda')
    return SimpleNamespace(Q=mf.Q,items=mf.items,factors=mf.factors,reg=fold_lambda)


def summarize(accuracy,robust):
    """Summarize lambda groups; repeated inner contexts are clustered by user.

    Coverage/concentration use all recommendation contexts, accuracy/robustness
    equal-weight unique users after averaging that user's contexts. Context count
    is recorded separately, never reported as independent sample size.
    """
    acc=[];rob=[]
    for lam in sorted({r['lambda']for r in accuracy}):
        aa=[r for r in accuracy if r['lambda']==lam]
        for row in aggregate_accuracy(aa):
            group=[r for r in aa if r['track']==row['track']and r['method']==row['method']]
            positive=defaultdict(list)
            for r in group:
                if r['accuracy'] is not None:positive[r['user']].append(r['accuracy'])
            row.update(contexts=row['users'],users=len({r['user']for r in group}),
                       positive_contexts=row['positive_users'],positive_users=len(positive),
                       no_positive_users=len({r['user']for r in group})-len(positive),**{'lambda':lam})
            for key in ('ndcg','precision','recall','hit_rate'):
                row[key]=float(np.mean([np.mean([v[key]for v in vals])for vals in positive.values()]))if positive else None
            acc.append(row)
        grouped=defaultdict(list)
        for r in robust:
            if r['lambda']==lam:grouped[(r['track'],r['method'],r['amplitude'],r['user'])].append(r)
        collapsed=[]
        for (track,method,amp,user),rows in grouped.items():
            entry=dict(track=track,method=method,amplitude=amp,user=user,
                       variants=sum(r['variants']for r in rows))
            for key in ('replacement','jaccard','first','set_same','order_same','rank_move'):
                vals=[r[key]for r in rows if r[key]is not None]
                entry[key]=float(np.mean(vals))if vals else None
            collapsed.append(entry)
        for row in aggregate_robustness(collapsed):row['lambda']=lam;rob.append(row)
    return acc,rob


def bootstrap_delta(left,right,repetitions=20000,seed=12):
    """Paired user mappings. Return user mean delta, percentile CI and signs."""
    if set(left)!=set(right):raise ValueError('Lambda user cohorts differ')
    d=np.array([left[u]-right[u]for u in sorted(left)])
    if not len(d):return None
    rng=np.random.default_rng(seed)
    means=d[rng.integers(0,len(d),(repetitions,len(d)))].mean(axis=1)
    lo,hi=np.quantile(means,[.025,.975])
    return dict(users=len(d),delta=float(d.mean()),low=float(lo),high=float(hi),
                negative=int(sum(d < -1e-12)),equal=int(sum(abs(d)<=1e-12)),positive=int(sum(d>1e-12)))


def metric_map(rows,lam,track,method,key,amplitude=None):
    """Collapse repeated contexts before paired user bootstrap; never inspect answers."""
    group=defaultdict(list)
    for r in rows:
        if r['lambda']!=lam or r['track']!=track or r['method']!=method:continue
        if amplitude is not None and r['amplitude']!=amplitude:continue
        value=r['accuracy'][key]if 'accuracy'in r and r['accuracy']is not None else (r.get(key)if 'accuracy'not in r else None)
        if value is not None:group[r['user']].append(value)
    return {u:float(np.mean(v))for u,v in group.items()}


def comparisons(accuracy,robust):
    """Three predeclared lambda contrasts for every track and MF/Hybrid policy."""
    result=[]
    for track in sorted({r['track']for r in accuracy}):
        for method in ('mf','mf_fallback','hybrid'):
            if not any(r['track']==track and r['method']==method for r in accuracy):continue
            for a,b in ((.1,.01),(1.,.01),(1.,.1)):
                for key,rows,amp in [('ndcg',accuracy,None),('recall',accuracy,None)]+[(key,robust,amp)for amp in (.5,1.)for key in ('replacement','first')]:
                    d=bootstrap_delta(metric_map(rows,a,track,method,key,amp),metric_map(rows,b,track,method,key,amp))
                    if d:result.append(dict(track=track,method=method,comparison=f'{a:g}-{b:g}',metric=key,amplitude=amp,**d))
    return result


def select_inner(accuracy,robust):
    """Only inner records accepted; selection never receives any outer results.

    Conservative, zero-loss stability gates are project choices, not industry
    standards. Reject uncertain accuracy gains and default to .01.
    """
    if any(r.get('phase')!='inner'for r in accuracy+robust):raise ValueError('Selection accepts INNER records only')
    if len({r['outer']for r in accuracy+robust})!=1:raise ValueError('Select each outer fold independently')
    acc,rs=summarize(accuracy,robust);tol=POLICY['tolerance']
    aa={r['lambda']:r for r in acc if r['track']=='A'and r['method']=='hybrid'}
    rr={(r['lambda'],r['amplitude']):r for r in rs if r['track']=='A'and r['method']=='hybrid'}
    candidates=[]
    for lam in (.1,1.):
        d=bootstrap_delta(metric_map(accuracy,lam,'A','hybrid','ndcg'),metric_map(accuracy,.01,'A','hybrid','ndcg'))
        gates=dict(positive_ndcg_mean=aa[lam]['ndcg']>aa[.01]['ndcg']+tol,
                   paired_ndcg_lower95_positive=d['low']>0,
                   concentration_not_worse=aa[lam]['top5_slot_share']<=aa[.01]['top5_slot_share']+tol,
                   cohort_same=aa[lam]['users']==aa[.01]['users']and aa[lam]['positive_users']==aa[.01]['positive_users'])
        for amp in (.5,1.):
            for metric in ('replacement','replacement_p90'):
                gates[f'{metric}_{amp:g}_not_worse']=rr[lam,amp][metric]<=rr[.01,amp][metric]+tol
            gates[f'first_{amp:g}_not_worse']=rr[lam,amp]['first']>=rr[.01,amp]['first']-tol
        candidates.append(dict(**{'lambda':lam},gates=gates,accepted=all(gates.values()),ndcg=aa[lam]['ndcg'],paired_ndcg=d))
    accepted=[r for r in candidates if r['accepted']]
    selected=.01
    if accepted:
        best=max(r['ndcg']for r in accepted)
        selected=min(r['lambda']for r in accepted if r['ndcg']>=best-tol)
    return dict(selected_lambda=selected,candidates=candidates,
                reason='Passing inner accuracy+stability gates'if accepted else 'No candidate passes every preregistered gate; retain .01')
