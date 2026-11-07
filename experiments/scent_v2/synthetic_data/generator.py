"""Semiparametric marginal-calibrated generator; latent taste is an assumption.

No recommender is trained or called. Real user vectors/histories are never copied.
"""
from collections import Counter,defaultdict
import json,hashlib
import numpy as np
from .config import POLICY


def standard(x):
    x=np.asarray(x,dtype=float);sd=float(x.std());return (x-x.mean())/sd if sd>1e-12 else np.zeros_like(x)


def estimate(rows,X,vocab,candidates,feature_effect,evidence):
    """All parameters from disjoint eligible, candidate-aligned Train only.

    Global/within/user/style/item effects are shrinkage estimates, not identified
    causal preferences. Feature signal in enrichment is a fixed stress assumption.
    """
    by=defaultdict(list);items=defaultdict(list);ix={i:n for n,i in enumerate(candidates)}
    for u,i,y in rows:by[u].append((i,y*10));items[i].append((u,y*10))
    real=np.array([y*10 for u,i,y in rows]);mu=float(real.mean());means={u:float(np.mean([y for i,y in h]))for u,h in by.items()};den=sum(len(h)-1 for h in by.values());within=sum(sum((y-means[u])**2 for i,y in h)for u,h in by.items())/den if den else float(real.var());within=max(within,1e-6)
    style=np.array([(sum(y for i,y in h)+5*mu)/(len(h)+5)for h in by.values()]);sigmas=[]
    for u,h in by.items():
        sse=sum((y-means[u])**2 for i,y in h);sigmas.append(np.sqrt((sse+5*within)/(len(h)-1+5)))
    logs=np.log(sigmas);b=np.array([sum(y-means[u]for u,y in items[i])/(len(items[i])+10)for i in candidates]);counts=np.array([len(items[i])for i in candidates]);p=np.sqrt(counts+1.);p/=p.sum();globalfeature=standard(np.einsum('ni,i->n',X,feature_effect));residual=[]
    for u,i,y in rows:residual.append(y*10-means[u]-b[ix[i]])
    hist=Counter(float(np.floor(v/.5)*.5+.25)for v in residual);centers=np.array(sorted(hist));prob=np.array([hist[x]for x in centers],dtype=float);prob/=prob.sum();hmean=float(np.einsum('i,i->',centers,prob));hstd=float(np.sqrt(np.einsum('i,i->',(centers-hmean)**2,prob)+.5**2/12))
    featurefreq=np.sum(X>0,axis=0).astype(float)+1;featurefreq=np.sqrt(featurefreq);featurefreq/=featurefreq.sum()
    params=dict(mu=mu,user_mean_location=float(style.mean()),user_mean_sd=float(style.std()),within_variance=within,log_noise_mean=float(logs.mean()),log_noise_sd=float(logs.std()),activity_histogram=dict(sorted(Counter(len(h)for h in by.values()).items())),matched_feature_signal_supported=bool(evidence),item_effects=b.tolist(),base_selection_probabilities=p.tolist(),real_item_counts=counts.tolist(),residual_centers=centers.tolist(),residual_probabilities=prob.tolist(),residual_mean=hmean,residual_sd=hstd,feature_selection_probabilities=featurefreq.tolist(),feature_global_score=globalfeature.tolist(),reference_ratings=sorted(real.tolist()),generator_uses_no_real_user_ID_or_vector=True)
    return params


def generate(params,X,vocab,candidates,all_real_IDs,seed=12,n_users=1000,matched=150):
    """Return entirely synthetic ratings/users/audit; exact seed reproducible.

    Marginal rank mapping to Train rating quantiles is one preregistered pass,
    not post-quality tuning. Equality of marginal ratings is by construction.
    """
    if not 0<=matched<=n_users or len(candidates)!=len(set(candidates)):raise ValueError('Invalid cohort/catalog')
    if len(vocab)<16:raise ValueError('Need at least16 generator features')
    rng=np.random.default_rng(seed);p=np.array(params['base_selection_probabilities']);b=np.array(params['item_effects']);globalf=np.array(params['feature_global_score']);fprob=np.array(params['feature_selection_probabilities']);centers=np.array(params['residual_centers']);rp=np.array(params['residual_probabilities']);acts=np.array(list(params['activity_histogram']),dtype=int);ap=np.array(list(params['activity_histogram'].values()),dtype=float);ap/=ap.sum()
    users=[];ratings=[];audit=[];latent=[];signal=[];propensities=np.zeros(len(candidates));tops=[]
    for u in range(n_users):
        uid=f'synthetic_v210_user_{u+1:06d}'
        if uid in all_real_IDs:raise ValueError('ID namespace collision')
        cohort='activity_matched'if u<matched else 'support_target_enriched';n=int(rng.choice(acts,p=ap))if u<matched else int(rng.integers(15,21));n=min(n,len(candidates));npref=int(rng.integers(3,9));nneg=int(rng.integers(3,9));chosen=rng.choice(len(vocab),npref+nneg,replace=False,p=fprob);w=np.zeros(len(vocab));w[chosen[:npref]]=rng.lognormal(0,.35,npref);w[chosen[npref:]]=-rng.lognormal(0,.35,nneg);w/=np.linalg.norm(w)
        affinity=np.clip(standard(.15*globalf+np.sqrt(1-.15**2)*standard(np.einsum('ni,i->n',X,w))),-3,3)
        enabled=cohort=='support_target_enriched'or params['matched_feature_signal_supported'];temperature=.25 if enabled else 0.;pu=p*np.exp(temperature*affinity);pu/=pu.sum();propensities+=pu
        selected=rng.choice(len(candidates),n,replace=False,p=pu);mu=float(np.clip(rng.normal(params['user_mean_location'],params['user_mean_sd']),0,10));sigma=float(rng.lognormal(params['log_noise_mean'],params['log_noise_sd']));taste_sd=.25*sigma if enabled else 0.;noise_sd=np.sqrt(max(sigma*sigma-taste_sd*taste_sd,1e-6));tops.append(set(np.argsort(-affinity,kind='stable')[:5].tolist()))
        prefs={vocab[i]:float(w[i])for i in chosen};noise=(rng.choice(centers,n,p=rp)+rng.uniform(-.25,.25,n)-params['residual_mean'])/params['residual_sd'];no_noise=mu+b[selected]+taste_sd*affinity[selected];raw=no_noise+noise_sd*noise
        supportset=set(sorted(selected,key=lambda i:hashlib.sha256(f'{seed}:future-support:{uid}:{candidates[i]}'.encode()).hexdigest())[:5])if cohort=='support_target_enriched'else set()
        users.append(dict(synthetic_user_id=uid,cohort=cohort,rating_count=n,user_bias_raw=mu,noise_sigma_raw=float(noise_sd),feature_signal_sd_raw=float(taste_sd),preference_vector_json=json.dumps(prefs,ensure_ascii=False,sort_keys=True),generator_version='v2_10_pilot_1',seed=seed,proposed_support_count=len(supportset),preference_is_synthetic_assumption=enabled and not params['matched_feature_signal_supported']))
        for k,item in enumerate(selected):
            ratings.append(dict(synthetic_user_id=uid,perfume_id=candidates[item],rating=None,generator_version='v2_10_pilot_1',seed=seed,cohort=cohort,proposed_role='support'if item in supportset else'target'if cohort=='support_target_enriched'else'activity_only'))
            audit.append(dict(synthetic_user_id=uid,perfume_id=candidates[item],latent_affinity=float(affinity[item]),feature_signal_raw=float(taste_sd*affinity[item]),no_noise_latent=float(no_noise[k]),noise_raw=float(noise_sd*noise[k]),unmapped_latent=float(raw[k])))
            latent.append(float(raw[k]));signal.append(float(no_noise[k]))
    rank=np.argsort(np.argsort(np.array(latent),kind='stable'),kind='stable');q=(rank+.5)/len(rank);mapped=np.quantile(np.array(params['reference_ratings']),q);mapped=np.clip(np.floor(mapped*2+.5)/2,0,10)
    for row,value in zip(ratings,mapped):row['rating']=float(value)
    return ratings,users,audit,propensities/n_users,tops
