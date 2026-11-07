"""Observational feature/product preference analysis, not a recommendation model."""
from collections import Counter
import json,math
from pathlib import Path
import numpy as np
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())
CHANNELS=['Top','Middle','Base','accords']


def label(value):
    if value is None:return 'UNOBSERVED'
    if value>=CONFIG['positive']:return 'POSITIVE'
    if value<=CONFIG['negative']:return 'NEGATIVE'
    return 'NEUTRAL'


def flatten(features):return {f'{field}:{t}' for field in CHANNELS for t in features[field]}


def preferences(history,features):
    """Whole-product labels -> per-channel annotation patterns, posthoc only."""
    pos=[i for i,r in history.items() if label(r)=='POSITIVE'];neg=[i for i,r in history.items() if label(r)=='NEGATIVE'];result={}
    for ch in CHANNELS:
        pp=[features[i][ch] for i in pos];nn=[features[i][ch] for i in neg];P=set().union(*pp) if pp else set();N=set().union(*nn) if nn else set();union=P|N
        result[ch]=dict(positive_feature_union=sorted(P),negative_feature_union=sorted(N),positive_common_to_all=sorted(set.intersection(*pp)) if len(pp)>=2 else [],negative_common_to_all=sorted(set.intersection(*nn)) if len(nn)>=2 else [],positive_common_evaluable=len(pp)>=2 and all(pp),negative_common_evaluable=len(nn)>=2 and all(nn),overlap_features=sorted(P&N),both_polarities_evaluable=bool(P and N),overlap_jaccard=len(P&N)/len(union) if P and N else None)
    nonnested=any(features[a]['accords']-features[b]['accords'] and features[b]['accords']-features[a]['accords'] for n,a in enumerate(pos) for b in pos[n+1:])
    return dict(ratings=len(history),positive_items=len(pos),negative_items=len(neg),neutral_items=len(history)-len(pos)-len(neg),compound_mainaccord_product_proxy=bool(nonnested),channels=result)


def pair_analysis(alias_a,alias_b,hist_a,hist_b,features,fold_a,fold_b):
    """Exact co-rated products distinguish evidence from feature-only proxies."""
    common=set(hist_a)&set(hist_b);mutual=sorted(i for i in common if label(hist_a[i])==label(hist_b[i])=='POSITIVE');opposite=sorted(i for i in common if {label(hist_a[i]),label(hist_b[i])}=={'POSITIVE','NEGATIVE'})
    pa=set().union(*(features[i]['accords'] for i,r in hist_a.items() if label(r)=='POSITIVE'));pb=set().union(*(features[i]['accords'] for i,r in hist_b.items() if label(r)=='POSITIVE'))
    evaluable=len(common)>=2 and bool(mutual);status='CONFIRMED_PRODUCT_PARTIAL_PREFERENCE_DIFFERENCE' if evaluable and opposite else 'NO_OPPOSITION_OBSERVED_IN_SHARED_PRODUCTS' if evaluable else 'INSUFFICIENT_EVIDENCE'
    common_accords=set().union(*(features[i]['accords'] for i in mutual)) if mutual else set();extra={i:sorted(features[i]['accords']-common_accords) for i in opposite}
    return dict(user_A=alias_a,user_B=alias_b,common_rated_products=len(common),mutual_positive_products=len(mutual),opposed_exact_products=len(opposite),common_positive_product_ids=mutual,opposed_product_ids=opposite,shared_positive_accord_annotations=sorted(pa&pb),rating_gap_mean=float(np.mean([abs(hist_a[i]-hist_b[i]) for i in common])) if common else None,rating_gap_max=max((abs(hist_a[i]-hist_b[i]) for i in common),default=None),status=status,strict_evaluable=evaluable,opposition_has_extra_accord_annotations=any(extra.values()),opposition_extra_accords=extra,different_evaluation_folds=fold_a!=fold_b,A_can_be_in_B_train=fold_a!=fold_b,B_can_be_in_A_train=fold_a!=fold_b,causal_transfer_identified=False)


def max_similarity(matrix,items,anchors,pool):
    known=[items[i] for i in anchors if i in items and np.isfinite(matrix[items[i],items[i]])];cols=[items[i] for i in pool]
    if not known:return np.full(len(pool),np.nan)
    valid=np.asarray([np.isfinite(matrix[n,n]) for n in cols]);value=np.max(np.nan_to_num(matrix[known][:,cols],nan=0),axis=0);value[~valid]=np.nan;return value


def suspected(positive_similarity,negative_similarity):
    if not np.isfinite(positive_similarity) or not np.isfinite(negative_similarity):return None
    return bool(negative_similarity>positive_similarity+1e-12)


def component_alignment(mrank,crank,mfinite,cfinite):
    if not mfinite and not cfinite:return 'POPULARITY_FALLBACK'
    if mfinite and not cfinite:return 'MF_ONLY_AVAILABLE'
    if cfinite and not mfinite:return 'CONTENT_ONLY_AVAILABLE'
    if mrank<=5 and crank>5:return 'MF_ALIGNED'
    if crank<=5 and mrank>5:return 'CONTENT_ALIGNED'
    if mrank<=5 and crank<=5:return 'BOTH_TOP5'
    return 'MIXED_NEITHER_COMPONENT_TOP5'


def summarize_recommendations(rows):
    n=len(rows);known=[r for r in rows if r['heldout_class']!='UNOBSERVED'];eligible=[r for r in rows if r['suspected_conflict'] is not None];negative=sum(r['heldout_class']=='NEGATIVE' for r in rows);conflicts=sum(r['suspected_conflict'] is True for r in eligible)
    categories=Counter(r['heldout_class'] for r in rows);alignment={}
    for kind in sorted({r['component_alignment'] for r in rows}):
        group=[r for r in rows if r['component_alignment']==kind];rated=[r for r in group if r['heldout_class']!='UNOBSERVED'];alignment[kind]=dict(slots=len(group),observed=len(rated),confirmed_negative=sum(r['heldout_class']=='NEGATIVE' for r in rated),confirmed_positive=sum(r['heldout_class']=='POSITIVE' for r in rated))
    return dict(slots=n,observed_rated_slots=len(known),unknown_slots=categories['UNOBSERVED'],positive_slots=categories['POSITIVE'],negative_slots=negative,neutral_slots=categories['NEUTRAL'],confirmed_negative_rate_among_observed=negative/len(known) if known else None,known_negative_slots_over_all_lower_bound=negative/n if n else None,suspected_conflict_slots=conflicts,suspicion_evaluable_slots=len(eligible),suspicion_unavailable_slots=n-len(eligible),suspected_conflict_fraction_evaluable=conflicts/len(eligible) if eligible else None,known_conflict_slots_over_all=conflicts/n if n else None,negative_and_suspected_slots=sum(r['heldout_class']=='NEGATIVE' and r['suspected_conflict'] is True for r in rows),alignment_diagnostics=alignment,structured_promoted_slots=sum(r['structured_promoted'] for r in rows),promoted_negative_slots=sum(r['structured_promoted'] and r['heldout_class']=='NEGATIVE' for r in rows))
