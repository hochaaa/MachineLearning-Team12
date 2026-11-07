"""Same user/candidate metric harness, new objective-compatible inference only.

Local reuse: V2-4 clustering, bootstrap and zero-loss Inner gates; V2-0 ranking,
metrics and perturbations. No historical file modified.
"""
from collections import defaultdict
import hashlib
import numpy as np
from .config import POLICIES,POLICY
from .fold_in import fold_in
from .training import sigmoid
from perfume.models import hybrid
from experiments.scent_v2.recommend import rank
from experiments.scent_v2.robustness import compare,variants
from experiments.scent_v2.evaluate import metrics
from experiments.scent_v2.lambda_tuning.evaluate import summarize,bootstrap_delta
from experiments.scent_v2.score_diagnostics.analysis import distribution,mean_finite


def predictions(support,candidates,content,models,pop):
    """Five Support inputs only; immutable C and distinct independently trained Qs.

    A pure MF ranks raw pair scores; A Hybrid uses fixed diagnostic sigmoid.
    Baseline/B pure MF and Hybrid use existing clip. Fallback branches unchanged.
    """
    seen={i for i,y in support};pool=sorted(set(candidates)-seen);c=content.score(support,pool);b=pop.score(pool);lookup={i:n for n,i in enumerate(pool)};result={}
    for policy,mf in models.items():
        pin=hashlib.sha256(mf.Q.tobytes()).hexdigest();p,diag=fold_in(mf,support)
        raw=np.array([float(np.einsum('i,i->',p,mf.Q[mf.items[i]]))if p is not None and i in mf.items else np.nan for i in pool])
        mapped=sigmoid(raw)if policy=='variant_a'else np.clip(raw,0,1)
        mf_rank_scores=raw if policy=='variant_a'else mapped
        h=hybrid(c,mapped,.25,b);values={'mf':mf_rank_scores,'hybrid':h}
        if policy=='baseline':values['content']=c
        for method,scores in values.items():
            order=rank(pool,scores);top=order[:5];idx=[lookup[i]for i in top];fallback=~(np.isfinite(c)&np.isfinite(mapped));finite=raw[np.isfinite(raw)]
            row=dict(top=top,top_scores=[float(scores[n])for n in idx],pool=len(pool),scorable=len(order),fallback_candidates=int(fallback.sum())if method=='hybrid'else 0,fallback_top5=int(fallback[idx].sum())if method=='hybrid'else 0,
                margin56=float(scores[lookup[order[4]]]-scores[lookup[order[5]]])if len(order)>5 else None,
                foldin=diag,known_support=diag['known_support'],factor_candidates=sum(i in mf.items for i in pool),
                clipping_frequency=float(np.mean((finite<0)|(finite>1)))if len(finite)else None,
                mf_raw_distribution=distribution(raw),mf_mapped_distribution=distribution(mapped),score_distribution=distribution(scores),
                support_mean=float(np.mean([y for i,y in support])),support_variance=float(np.var([y for i,y in support])))
            result[policy,method]=row
        assert hashlib.sha256(mf.Q.tobytes()).hexdigest()==pin
    return result


def evaluate_context(fold,outer,phase,content,models,pop,candidates):
    """Common full candidate Track A; B restricts to common factor-supported items.

    Baseline Track B keeps original factor pool. New-policy B uses that same fixed
    pool (NaN where new factor unavailable), rather than improving its candidate set.
    B_full5 uses baseline known Support==5, same users across policies.
    """
    accuracy=[];robust=[];impact=[]
    bpool=[i for i in candidates if i in models['baseline'].items]
    for u in fold['users']:
        support=fold['support'][u];known=sum(i in models['baseline'].items for i,y in support)
        for track,pool in [('A',candidates),('B_partial',bpool)]:
            pred=predictions(support,pool,content,models,pop);changes={}
            for amp in (.5,1.):
                per={key:[]for key in pred}
                for n,d,changed in variants(support,amp):
                    now=predictions(changed,pool,content,models,pop)
                    for key in pred:per[key].append(compare(pred[key],now[key]))
                for key,rows in per.items():
                    changes[key,amp]=dict(amplitude=amp,variants=len(rows),**{k:mean_finite([r[k]for r in rows])for k in ('replacement','first','set_same','order_same','jaccard','rank_move')})
            answers=fold['answers'][u] # First label access after support-only scoring.
            for scope in [track]+(['B_full5']if track=='B_partial'and known==5 else []):
                for (policy,method),r in pred.items():
                    common=dict(phase=phase,outer=outer,inner=fold['fold']if phase=='inner'else None,user=u,track=scope,policy=policy,method=method,positive_answers=sum(y>=.7 for i,y in answers))
                    acc=metrics(r['top'],answers);accuracy.append(dict(common,accuracy=acc,**r))
                    for amp in (.5,1.):robust.append(dict(common,**changes[(policy,method),amp]))
                    base=pred['baseline',method];impact.append(dict(common,**compare(base,r),baseline_ndcg=metrics(base['top'],answers)['ndcg']if acc else None,policy_ndcg=acc['ndcg']if acc else None))
    return accuracy,robust,impact


def aggregate(accuracy,robust):
    """Original equal-user aggregation per policy/method; no context pseudo-replication."""
    aa=[dict(r,**{'lambda':POLICIES[r['policy']]})for r in accuracy];rr=[dict(r,**{'lambda':POLICIES[r['policy']]})for r in robust]
    a,r=summarize(aa,rr);names={v:k for k,v in POLICIES.items()}
    for row in a+r:row['policy']=names[row.pop('lambda')]
    return a,r


def user_metric(rows,policy,track,method,key,amplitude=None):
    """Collapse all repeated contexts within each unique user before paired bootstrap."""
    by=defaultdict(list)
    for r in rows:
        if (r['policy'],r['track'],r['method'])!=(policy,track,method):continue
        if amplitude is not None and r['amplitude']!=amplitude:continue
        value=r['accuracy'][key]if r.get('accuracy')is not None else(r.get(key)if 'accuracy'not in r else None)
        if value is not None:by[r['user']].append(value)
    return {u:float(np.mean(v))for u,v in by.items()}


def comparisons(accuracy,robust,policies=('variant_a','variant_b')):
    """User-paired MF/Hybrid accuracy and stability contrasts with baseline."""
    out=[]
    for track in sorted({r['track']for r in accuracy}):
        for p in policies:
            for method in ('mf','hybrid'):
                for key,source,amp in [(k,accuracy,None)for k in ('ndcg','precision','recall','hit_rate')]+[(k,robust,a)for a in (.5,1.)for k in ('replacement','first')]:
                    left=user_metric(source,p,track,method,key,amp);right=user_metric(source,'baseline',track,method,key,amp)
                    if left:out.append(dict(track=track,policy=p,method=method,metric=key,amplitude=amp,**bootstrap_delta(left,right)))
    return out


def compatibility(accuracy,training):
    """Preregistered numeric compatibility checks, only Inner support + Train diagnostics.

    A is rank-compatible if usable-pair solves succeed; its uncalibrated fixed
    sigmoid Hybrid remains diagnostic-only and is not an adoption candidate.
    B's .05 RMSE/clipping and 10x norm tolerances are project guardrails, not proof.
    """
    result={};base=[r for r in accuracy if r['track']=='A'and r['policy']=='baseline'and r['method']=='mf']
    base_rmse=mean_finite([r['foldin']['support_rmse']for r in base]);base_clip=mean_finite([r['clipping_frequency']for r in base]);base_norm=mean_finite([r['foldin']['P_norm']for r in base])
    for p in ('variant_a','variant_b'):
        rows=[r for r in accuracy if r['track']=='A'and r['policy']==p and r['method']=='mf'];eligible=[r for r in rows if r['foldin']['support_pairs']>0]
        solve_fraction=sum(r['foldin']['status']=='ok'for r in eligible)/len(eligible)if eligible else 1.
        sr=mean_finite([r['foldin']['support_rmse']for r in rows]);clip=mean_finite([r['clipping_frequency']for r in rows]);norm=mean_finite([r['foldin']['P_norm']for r in rows])
        gates=dict(finite_training=all(t['finite']for t in training if t['variant']==p))
        if p=='variant_a':gates.update(known_pair_solve_fraction=solve_fraction>=.99,transform_calibrated_for_adoption=False)
        else:
            ts=[t for t in training if t['variant']==p]
            gates.update(train_ridge_rmse_not_divergent=all(t['train_ridge_rmse']<=t['baseline_train_ridge_rmse']+.05 for t in ts),support_rmse_not_divergent=sr is not None and base_rmse is not None and sr<=base_rmse+.05,clipping_not_divergent=clip is not None and base_clip is not None and clip<=base_clip+.05,P_norm_not_divergent=norm is not None and base_norm is not None and norm<=10*max(base_norm,1e-12),Q_norm_not_divergent=all(t['history'][-1]['Q_norm']<=10*t['baseline_Q_norm']for t in ts))
        result[p]=dict(gates=gates,passed=all(gates.values()),solve_success_fraction=solve_fraction,support_rmse=sr,baseline_support_rmse=base_rmse,raw_outside01_fraction=clip,baseline_raw_outside01_fraction=base_clip,P_norm=norm)
    return result


def select_inner(accuracy,robust,compat):
    """Inner TrackA Hybrid only. No Outer values accepted; fixed zero-loss gates."""
    if any(r['phase']!='inner'for r in accuracy+robust)or len({r['outer']for r in accuracy+robust})!=1:raise ValueError('One Outer Inner only')
    aa,rr=aggregate(accuracy,robust);a={r['policy']:r for r in aa if r['track']=='A'and r['method']=='hybrid'};r={(x['policy'],x['amplitude']):x for x in rr if x['track']=='A'and x['method']=='hybrid'};evidence=[];tol=1e-12
    for p in ('variant_a','variant_b'):
        delta=bootstrap_delta(user_metric(accuracy,p,'A','hybrid','ndcg'),user_metric(accuracy,'baseline','A','hybrid','ndcg'))
        gates=dict(ndcg_increases=a[p]['ndcg']>a['baseline']['ndcg']+tol,paired95_lower_positive=delta['low']>0,coverage_not_worse=a[p]['coverage_items']>=a['baseline']['coverage_items'],top1_not_worse=a[p]['top1_slot_share']<=a['baseline']['top1_slot_share']+tol,top5_not_worse=a[p]['top5_slot_share']<=a['baseline']['top5_slot_share']+tol,foldin_compatibility=compat[p]['passed'])
        for amp in (.5,1.):
            for k in ('replacement','replacement_p90'):gates[f'{k}_{amp}_not_worse']=r[p,amp][k]<=r['baseline',amp][k]+tol
            gates[f'first_{amp}_not_worse']=r[p,amp]['first']>=r['baseline',amp]['first']-tol
        evidence.append(dict(policy=p,accepted=all(gates.values()),gates=gates,ndcg=a[p]['ndcg'],paired_ndcg=delta,compatibility=compat[p]))
    good=[x for x in evidence if x['accepted']];selected='baseline'
    if good:
        best=max(x['ndcg']for x in good);selected=next(p for p in ('variant_a','variant_b')if any(x['policy']==p and x['ndcg']>=best-tol for x in good))
    return dict(selected_policy=selected,candidates=evidence)
