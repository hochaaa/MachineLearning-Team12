"""Metric-only stability/uncertainty analysis. No scoring model or tuning."""
import numpy as np


def paired_counts(pairs):
    """pairs: numeric baseline/selected metrics, no IDs or raw ratings."""
    valid=[p for p in pairs if p['baseline_ndcg'] is not None]
    return dict(positive_users=len(valid),improved=sum(p['delta']>1e-12 for p in valid),worsened=sum(p['delta']< -1e-12 for p in valid),tied=sum(abs(p['delta'])<=1e-12 for p in valid),hit_gained=sum(p['selected_hit']>p['baseline_hit'] for p in valid),hit_lost=sum(p['selected_hit']<p['baseline_hit'] for p in valid),baseline_hit_users=sum(p['baseline_hit'] for p in valid),selected_hit_users=sum(p['selected_hit'] for p in valid))


def fold_mean_delta(pairs,removed=()):
    """Recompute macro-fold delta with correct denominators after row exclusion."""
    keep=[p for n,p in enumerate(pairs) if n not in set(removed) and p['delta'] is not None];folds=sorted({p['fold'] for p in pairs});means=[]
    for f in folds:
        values=[p['delta'] for p in keep if p['fold']==f]
        if not values:raise ValueError('Cannot remove entire positive fold')
        means.append(float(np.mean(values)))
    return float(np.mean(means))


def stability(pairs,seed=12,draws=20000):
    """Fixed paired descriptive bootstrap and leave-one-out; no model selection.

    Developer bootstrap resamples positive users within each fold, then averages
    fold means. It ignores training-fold dependence/selection bias; descriptive
    conditional uncertainty only, NOT an independent significance test.
    """
    valid_indices=[n for n,p in enumerate(pairs) if p['delta'] is not None];net=fold_mean_delta(pairs);folds=sorted({p['fold'] for p in pairs});weights={f:1/(len(folds)*sum(p['delta'] is not None and p['fold']==f for p in pairs)) for f in folds}
    contributions={n:p['delta']*weights[p['fold']] for n,p in enumerate(pairs) if p['delta'] is not None};positives=sorted((x for x in contributions.values() if x>0),reverse=True);positive_sum=sum(positives);largest=sorted((n for n in valid_indices if contributions[n]>0),key=lambda n:contributions[n],reverse=True)[:2]
    loo=[fold_mean_delta(pairs,[n]) for n in valid_indices];rng=np.random.default_rng(seed);boot=np.zeros(draws)
    for f in folds:
        delta=np.asarray([p['delta'] for p in pairs if p['fold']==f and p['delta'] is not None]);boot+=delta[rng.integers(0,len(delta),(draws,len(delta)))].mean(axis=1)/len(folds)
    numeric_rows=[dict(p,macro_delta_contribution=contributions.get(n),leave_one_out_macro_delta=fold_mean_delta(pairs,[n]) if n in contributions else None) for n,p in enumerate(pairs)]
    return dict(paired=paired_counts(pairs),per_user_metrics_no_identifiers=numeric_rows,macro_ndcg_delta=net,concentration=dict(positive_contribution_total=positive_sum,negative_contribution_total=sum(x for x in contributions.values() if x<0),largest1_positive_share=positives[0]/positive_sum if positive_sum else None,largest2_positive_share=sum(positives[:2])/positive_sum if positive_sum else None,largest1_share_of_net=positives[0]/net if positives and net else None,largest2_share_of_net=sum(positives[:2])/net if positives and net else None,minimum_leave_one_out_delta=min(loo),maximum_leave_one_out_delta=max(loo),any_single_exclusion_eliminates_improvement=any(x<=1e-12 for x in loo),remove_largest2_positive_contributors_delta=fold_mean_delta(pairs,largest)),paired_stratified_bootstrap=dict(seed=seed,draws=draws,delta=net,low95=float(np.quantile(boot,.025)),high95=float(np.quantile(boot,.975)),interpretation='Descriptive conditional on reused developer selection; not selection-adjusted; overlapping training folds not accounted for'))


def final_uncertainty(pairs,seed=12,draws=20000):
    """Single heldout cohort paired-user bootstrap, positive users only."""
    delta=np.asarray([p['delta'] for p in pairs if p['delta'] is not None]);rng=np.random.default_rng(seed)
    if not len(delta):return dict(status='NOT_EVALUATED_NO_POSITIVES')
    means=delta[rng.integers(0,len(delta),(draws,len(delta)))].mean(axis=1)
    return dict(users=len(delta),seed=seed,draws=draws,delta=float(delta.mean()),low95=float(np.quantile(means,.025)),high95=float(np.quantile(means,.975)),caveat='Small historical reused cohort; conditional on fixed models, cannot repair historical test exposure')
