"""Data quality only, never recommendation accuracy."""
from collections import Counter,defaultdict
import json,hashlib
import numpy as np
from .profiling import basic,stats


def js(p,q):
    p=np.array(p,dtype=float);q=np.array(q,dtype=float);p=p/p.sum();q=q/q.sum();m=(p+q)/2
    def kl(x):mask=x>0;return float(np.sum(x[mask]*np.log2(x[mask]/m[mask])))
    return .5*(kl(p)+kl(q))


def distribution_difference(a,b,grid):
    av=np.asarray(a);bv=np.asarray(b);p=np.array([np.count_nonzero(np.isclose(av,x))for x in grid],dtype=float);q=np.array([np.count_nonzero(np.isclose(bv,x))for x in grid],dtype=float);pc=np.cumsum(p/p.sum());qc=np.cumsum(q/q.sum());step=float(grid[1]-grid[0])if len(grid)>1 else 1.
    return dict(JS_divergence_bits=js(p,q),histogram_KS=float(np.max(np.abs(pc-qc))),histogram_Wasserstein1=float(np.sum(np.abs(pc-qc))*step))


def validate(ratings,users,candidates,realIDs):
    ids=[r['synthetic_user_id']for r in users];pairs=[(r['synthetic_user_id'],r['perfume_id'])for r in ratings];y=np.array([r['rating']for r in ratings]);known=set(ids)
    checks=dict(users_unique=len(ids)==len(set(ids)),ID_no_collision=not(set(ids)&set(realIDs)),synthetic_namespace=all(i.startswith('synthetic_v210_user_')for i in ids),items_valid=all(r['perfume_id']in set(candidates)for r in ratings),users_valid=all(r['synthetic_user_id']in known for r in ratings),pairs_unique=len(pairs)==len(set(pairs)),finite=bool(np.isfinite(y).all()),range_0_10=bool(((y>=0)&(y<=10)).all()),half_step=bool(np.isclose(y*2,np.round(y*2)).all()),user_counts_match=all(sum(r['synthetic_user_id']==u['synthetic_user_id']for r in ratings)==u['rating_count']for u in users))
    return checks


def evaluate(real,ratings,users,audit,X,candidates,realIDs,tops):
    realvalues=[y*10 for u,i,y in real];synrows=[(r['synthetic_user_id'],r['perfume_id'],r['rating']/10)for r in ratings];profiles={};diffs={};realprofile=basic(real,candidates);realactivity=list(Counter(u for u,i,y in real).values());rc=Counter(i for u,i,y in real)
    for cohort in ('combined','activity_matched','support_target_enriched'):
        rows=synrows if cohort=='combined'else [r for r,source in zip(synrows,ratings)if source['cohort']==cohort];profile=basic(rows,candidates);profiles[cohort]=profile;values=[y*10 for u,i,y in rows];activity=list(Counter(u for u,i,y in rows).values());sc=Counter(i for u,i,y in rows)
        diffs[cohort]=dict(rating=distribution_difference(realvalues,values,np.arange(0,10.01,.5)),activity=distribution_difference(realactivity,activity,np.arange(0,21)),item_frequency_JS_bits=js([rc[i]for i in candidates],[sc[i]for i in candidates]),positive_fraction_delta=profile['positive_fraction']-realprofile['positive_fraction'],low_fraction_delta=profile['low_fraction']-realprofile['low_fraction'])
    # Synthetic-only ground truth diagnostics; never real-user predictive evidence.
    by=defaultdict(list);lookup={i:n for n,i in enumerate(candidates)}
    for r,a in zip(ratings,audit):by[r['synthetic_user_id']].append((r,a))
    contrast=[];similar=[];dissimilar=[];identical=[];zero_var=0
    for uid,rows in by.items():
        ys=np.array([r['rating']for r,a in rows]);aff=np.array([a['latent_affinity']for r,a in rows]);med=float(np.median(aff));hi=ys[aff>med];lo=ys[aff<med]
        if len(hi)and len(lo):contrast.append(float(hi.mean()-lo.mean()))
        zero_var+=np.var(ys)==0
        for n,(r,a)in enumerate(rows):
            for s,b in rows[n+1:]:
                sim=float(np.einsum('i,i->',X[lookup[r['perfume_id']]],X[lookup[s['perfume_id']]]));d=abs(r['rating']-s['rating'])
                if sim>=.5:similar.append(d)
                if sim<=.1:dissimilar.append(d)
                if sim>=1-1e-10:identical.append(float(d==0))
    predictor=np.array([a['no_noise_latent']for a in audit]);target=np.array([r['rating']for r in ratings]);corr=float(np.corrcoef(predictor,target)[0,1]);rng=np.random.default_rng(12);jac=[]
    for _ in range(10000):
        i,j=rng.choice(len(tops),2,replace=False);jac.append(len(tops[i]&tops[j])/len(tops[i]|tops[j]))
    checks=validate(ratings,users,candidates,realIDs);tastes=[u['preference_vector_json']for u in users]
    return dict(hard_checks=checks,hard_checks_PASS=all(checks.values()),real_reference=realprofile,synthetic_profiles=profiles,distribution_differences=diffs,
        structure=dict(affinity_high_minus_low_rating=stats(contrast),similar_abs_rating_difference=stats(similar),dissimilar_abs_rating_difference=stats(dissimilar),identical_feature_pair_same_rating_fraction=float(np.mean(identical))if identical else None,identical_feature_pairs=len(identical),users_zero_rating_variance=zero_var,zero_variance_fraction=zero_var/len(users),unique_taste_vectors=len(set(tastes)),generator_latent_affinity_Top5_pair_Jaccard_sampled_mean=float(np.mean(jac)),sampled_user_pairs=10000,generator_known_no_noise_linear_R2=corr*corr),
        warnings=['Marginal rating match is calibrated by construction, not independent validation.','85% history enrichment intentionally violates observed user activity.','Feature stress preference is an assumption if real structure evidence is inconclusive.','Smoothing generates interactions for previously unrated candidates: extrapolation, not observed preferences.','Latent affinity Top5 is generator diagnostics, not a recommender output or accuracy.'],recommendation_accuracy_measured=False,recommender_fit_calls=0)
