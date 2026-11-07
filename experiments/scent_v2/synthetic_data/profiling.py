"""Train-only aggregates; no raw user records written to public outputs."""
from collections import defaultdict,Counter
from itertools import combinations
import math
import numpy as np


def stats(values):
    x=np.asarray(values,dtype=float);x=x[np.isfinite(x)]
    if not len(x):return dict(count=0,mean=None,median=None,sd=None,min=None,max=None,p10=None,p25=None,p75=None,p90=None,p95=None)
    q=np.quantile(x,[0,.1,.25,.5,.75,.9,.95,1]);return dict(count=len(x),mean=float(x.mean()),median=float(q[3]),sd=float(x.std()),min=float(q[0]),max=float(q[7]),p10=float(q[1]),p25=float(q[2]),p75=float(q[4]),p90=float(q[5]),p95=float(q[6]))


def basic(rows,candidates):
    by=defaultdict(list);items=Counter();pairs=Counter();invalid=missing=0
    for u,i,y in rows:
        missing+=u is None or i is None or y is None
        if y is None or not np.isfinite(y)or not 0<=y<=1:invalid+=1;continue
        by[u].append(float(y*10));items[i]+=1;pairs[u,i]+=1
    ratings=[y for v in by.values()for y in v];n=len(ratings);density=n/(len(by)*len(items))if by and items else None
    return dict(users=len(by),perfumes=len(items),ratings=n,fixed_candidate_density=sum(v for i,v in items.items()if i in set(candidates))/(len(by)*len(candidates))if by and candidates else None,density=density,sparsity=1-density if density is not None else None,ratings_per_user=stats([len(v)for v in by.values()]),ratings_per_perfume=stats(list(items.values())),rating=stats(ratings),duplicates=sum(v-1 for v in pairs.values()),missing=missing,invalid=invalid,rating_unit='.5 grid compliance; raw source y/10 restored by *10',half_point_compliance=float(np.mean(np.isclose(np.array(ratings)*2,np.round(np.array(ratings)*2))))if ratings else None,
        rating_bands=dict(raw0_to3=sum(0<=y<=3 for y in ratings),raw_gt3_lt5=sum(3<y<5 for y in ratings),raw5_lt7=sum(5<=y<7 for y in ratings),raw7_to10=sum(7<=y<=10 for y in ratings)),positive_fraction=float(np.mean(np.array(ratings)>=7))if ratings else None,low_fraction=float(np.mean(np.array(ratings)<5))if ratings else None,
        user_activity_bins={'1-2':sum(len(v)<=2 for v in by.values()),'3-5':sum(3<=len(v)<=5 for v in by.values()),'6-10':sum(6<=len(v)<=10 for v in by.values()),'11-20':sum(11<=len(v)<=20 for v in by.values()),'21+':sum(len(v)>=21 for v in by.values())},
        item_frequency_bins={'1':sum(v==1 for v in items.values()),'2-5':sum(2<=v<=5 for v in items.values()),'6+':sum(v>=6 for v in items.values()),'unrated_candidates':sum(i not in items for i in candidates)},
        user_tendency_summary=dict(means=stats([np.mean(v)for v in by.values()]),SDs=stats([np.std(v)for v in by.values()]),high_fraction=stats([np.mean(np.array(v)>=7)for v in by.values()]),low_fraction=stats([np.mean(np.array(v)<5)for v in by.values()]),unstable_users_n_lt5=sum(len(v)<5 for v in by.values())))


def features(rows,catalog,candidates):
    """Original note/accord tokens, Train-only IDF; candidate metadata cooccurrence."""
    by=defaultdict(list)
    for u,i,y in rows:by[u].append((i,y*10))
    means={u:float(np.mean([y for i,y in v]))for u,v in by.items()};trainitems=sorted({i for u,i,y in rows});df=Counter(t for i in trainitems for t in catalog[i]['tokens']);vocab=sorted(df);idf={t:math.log((1+len(trainitems))/(1+df[t]))+1 for t in vocab};lookup={t:k for k,t in enumerate(vocab)};X=np.zeros((len(candidates),len(vocab)));metadata=Counter();co=Counter();observations=defaultdict(list);clusters=defaultdict(lambda:defaultdict(list));itemindex={i:n for n,i in enumerate(candidates)}
    for n,item in enumerate(candidates):
        ts=catalog[item]['tokens'];metadata.update(set(ts));co.update(combinations(sorted(set(ts)),2));vec={t:idf[t]for t in ts if t in idf};norm=math.sqrt(sum(x*x for x in vec.values()))
        for t,x in vec.items():X[n,lookup[t]]=x/norm if norm else 0
    for u,i,y in rows:
        for t in catalog[i]['tokens']:observations[t].append(y*10);clusters[t][u].append(y*10-means[u])
    statsrows=[]
    for t in sorted(metadata):
        raw=observations[t];parts=clusters[t];total=sum(len(v)for v in parts.values());center=sum(sum(v)for v in parts.values())/total if total else None;K=len(parts)
        se=math.sqrt(K/(K-1)*sum((sum(v)-center*len(v))**2 for v in parts.values()))/total if K>=5 else None
        statsrows.append(dict(feature=t,kind=t.split(':',1)[0],candidate_frequency=metadata[t],Train_rating_count=len(raw),Train_users=K,raw_mean=float(np.mean(raw))if raw and K>=5 else None,user_centered_mean=center if K>=5 else None,cluster_SE=se,approx95_low=center-1.96*se if se is not None else None,approx95_high=center+1.96*se if se is not None else None,uncertainty='insufficient_<5users'if K<5 else 'cluster_delta_normal_unadjusted',rare_metadata=metadata[t]<=5,generator_feature=t in lookup))
    effects=np.array([sum(sum(v)for v in clusters[t].values())/(sum(len(v)for v in clusters[t].values())+20)for t in vocab])
    return X,vocab,idf,statsrows,[dict(feature1=a,feature2=b,candidate_cooccurrence=n)for(a,b),n in co.most_common(100)],means,effects


def structure(rows,X,candidates):
    """Enough-history users only; paired similarity strata and split-half reliability."""
    ix={i:n for n,i in enumerate(candidates)};by=defaultdict(list)
    for u,i,y in rows:by[u].append((i,y*10))
    paired=[];high=[];low=[];halves=[];profiles=[];eligible=0
    for u,h in by.items():
        if len(h)<5:continue
        eligible+=1;hi=[];lo=[]
        for(i,a),(j,b)in combinations(h,2):
            sim=float(np.einsum('i,i->',X[ix[i]],X[ix[j]]));diff=abs(a-b)
            if sim>=.5:hi.append(diff);high.append(diff)
            if sim<=.1:lo.append(diff);low.append(diff)
        if hi and lo:paired.append(float(np.mean(lo)-np.mean(hi)))
        y=np.array([y for i,y in h]);p=np.einsum('n,ni->i',y-y.mean(),np.array([X[ix[i]]for i,a in h]));norm=np.linalg.norm(p)
        if norm>1e-12:profiles.append(p/norm)
        hs=[]
        for half in (h[::2],h[1::2]):
            v=np.array([y for i,y in half]);p=np.einsum('n,ni->i',v-v.mean(),np.array([X[ix[i]]for i,y in half]));norm=np.linalg.norm(p);hs.append(p/norm if norm>1e-12 else None)
        if all(v is not None for v in hs):halves.append(float(np.einsum('i,i->',hs[0],hs[1])))
    loCI=hiCI=None
    if paired:
        a=np.array(paired);rng=np.random.default_rng(12);boot=a[rng.integers(0,len(a),(2000,len(a)))].mean(axis=1);loCI,hiCI=map(float,np.quantile(boot,[.025,.975]))
    cos=[float(np.einsum('i,i->',a,b))for a,b in combinations(profiles,2)]
    evidence=len(paired)>=10 and loCI is not None and loCI>0
    return dict(minimum_ratings=5,eligible_users=eligible,paired_similarity_strata_users=len(paired),similar_pair_count=len(high),dissimilar_pair_count=len(low),similar_abs_rating_difference=stats(high),dissimilar_abs_rating_difference=stats(low),user_paired_dissimilar_minus_similar=stats(paired),paired_user_bootstrap95=[loCI,hiCI],matched_feature_evidence=evidence,split_half_profile_cosine=stats(halves),between_user_profile_cosine=stats(cos),cluster_conclusion='No stable number of taste clusters inferred; sparse histories/unstable split halves limit identification.')
