"""Shared-candidate evaluation; answer values stay outside all scoring interfaces."""
from collections import Counter,defaultdict
import time
import numpy as np
from perfume.models import Baseline
from perfume.evaluation import ranking_metrics
from content_v2 import ContentV2
from hybrid_v2 import combine,ranked
from foldin_v3 import fold,score

def avg_rank(v):
    order=np.argsort(v,kind='stable');out=np.zeros(len(v));a=0
    while a<len(v):
        b=a+1
        while b<len(v) and v[order[b]]==v[order[a]]:b+=1
        out[order[a:b]]=(a+b-1)/2+1;a=b
    return out

def corr(a,b):
    a,b=avg_rank(a),avg_rank(b)
    return float(np.corrcoef(a,b)[0,1]) if len(a)>1 and a.std()>0 and b.std()>0 else None

class ScoringContext:
    """Exact-fit-data boundary; policy differences reuse fixed component scores only."""
    def __init__(self,fit,pool,catalog,raw,supports):
        self.fit,self.pool,self.catalog,self.raw,self.supports=fit,pool,catalog,raw,supports;self.contents={};self.c_cache={};self.m_cache={};self.baseline=Baseline().fit(fit)
    def content(self,kind):
        if kind not in self.contents:
            cfg={'kind':'v1','mode':'rating'} if kind=='v1' else {'kind':'split','mode':'neutral','accord_weight':.5}
            self.contents[kind]=ContentV2(cfg).fit(self.catalog,self.raw,{i for _,i,_ in self.fit})
        return self.contents[kind]
    def predict(self,model,policy,kind='hybrid',known=False):
        predictions={};diag=[];totals=Counter();times=[]
        for u,support in sorted(self.supports.items()):
            support=sorted(support);seen={i for i,_ in support};pool=[i for i in self.pool if i not in seen];start=time.perf_counter()
            ckey=(policy['content'],u)
            if ckey not in self.c_cache:self.c_cache[ckey]=self.content(policy['content']).score(support,pool)
            c=self.c_cache[ckey];mkey=(id(model),policy['fold_latent'],policy['fold_bias'],u,known)
            if mkey not in self.m_cache:
                t=time.perf_counter();z=None if known else fold(model,support,policy);ft=time.perf_counter()-t
                m=model.score(u,pool) if known else score(model,z,pool)
                self.m_cache[mkey]=(m,z,ft)
            m,z,ft=self.m_cache[mkey];b=self.baseline.score(pool)
            s,fb=combine(c,m,b,pool,{'method':policy['fusion'],'alpha':policy['alpha']},len(support))
            if kind=='content':s=c
            if kind=='mf':s=m
            result=ranked(pool,s,10);assert len(set(result))==len(result) and set(result)<=set(pool);predictions[u]=result
            if kind=='hybrid':totals.update({k:fb[k] for k in ['component_fallback','popularity_fallback','candidate_scores']})
            d={'foldin_seconds':ft,'mf_latent_sd':None,'item_bias_sd':None,'latent_bias_sd_ratio':None,'mf_itembias_spearman':None,'mf_bias_top10_jaccard':None}
            if hasattr(model,'bu'):
                idx=[model.items[i] for i in pool if i in model.items];vec=model.P[model.users[u]] if known else z[:-1] if z is not None else None
                if vec is not None:
                    lat=model.Q[idx]@vec;bi=model.bi[idx];raw=lat+bi
                    fullids=[i for i in pool if i in model.items];bt=ranked(fullids,bi);mt=ranked(fullids,raw)
                    d.update(mf_latent_sd=float(np.std(lat)),item_bias_sd=float(np.std(bi)),latent_bias_sd_ratio=float(np.std(lat)/np.std(bi)) if np.std(bi)>0 else None,mf_itembias_spearman=corr(raw,bi),mf_bias_top10_jaccard=len(set(mt)&set(bt))/len(set(mt)|set(bt)))
            diag.append(d);times.append(time.perf_counter()-start)
        totals['popularity_fallback_fraction']=totals['popularity_fallback']/max(1,totals['candidate_scores']);totals['component_fallback_fraction']=totals['component_fallback']/max(1,totals['candidate_scores'])
        return predictions,dict(totals),diag,times

def assess(pred,answers,pool,fb=None,diagnostics=(),times=()):
    positive=defaultdict(set)
    for u,i,r in answers:
        if r>=.7:positive[u].add(i)
    per={};allcounts=Counter(i for ranking in pred.values() for i in ranking);n=len(pool);freq=np.array([allcounts[i] for i in pool],dtype=float);total=freq.sum();prob=freq[freq>0]/total if total else np.array([])
    for u,r in pred.items():
        m=ranking_metrics(r,positive[u],10)
        if m is not None:per[u]=m
    result={'evaluation_users':len(pred),'positive_users':len(per),'no_positive_users':len(pred)-len(per),'coverage':len(allcounts),'catalog_coverage':len(allcounts)/n,'top10_concentration':sum(v for _,v in allcounts.most_common(10))/total if total else None,'hottest_item_user_fraction':max(allcounts.values(),default=0)/max(1,len(pred)),'gini':float(np.sum((2*np.arange(1,n+1)-n-1)*np.sort(freq))/(n*total)) if total else None,'entropy_bits':float(-np.sum(prob*np.log2(prob))) if total else None}
    for metric in ['precision','recall','ndcg']:result[metric]=float(np.mean([m[metric] for m in per.values()])) if per else None
    pairs=[];sets=[set(v) for v in pred.values()]
    for a,x in enumerate(sets):
        for y in sets[a+1:]:pairs.append(len(x&y)/len(x|y) if x|y else 1.)
    result['interuser_top10_jaccard']=float(np.mean(pairs)) if pairs else None
    result.update(fb or {})
    for key in ['mf_latent_sd','item_bias_sd','latent_bias_sd_ratio','mf_itembias_spearman','mf_bias_top10_jaccard','foldin_seconds']:
        values=[d[key] for d in diagnostics if d.get(key) is not None];result[key]=float(np.mean(values)) if values else None
    result['scoring_seconds_mean_with_cache']=float(np.mean(times)) if len(times) else None
    return result,{u:r['ndcg'] for u,r in per.items()}

def select_policy(rows,policies,settings):
    """Inner rows only: guardrails; primary NDCG; .002 complexity tie and V1 retention."""
    def mean(name,key):return float(np.mean([r[key] for r in rows if r['policy']==name]))
    base={k:mean('V1',k) for k in ['ndcg','coverage','top10_concentration']};eligible=[];receipt=[]
    for p in policies:
        name=p['id'];s={k:mean(name,k) for k in base};ok=s['coverage']>=settings['coverage_min_ratio']*base['coverage'] and s['top10_concentration']<=base['top10_concentration']+settings['concentration_max_increase']
        receipt.append({'policy':name,**s,'guardrail_pass':ok})
        if ok:eligible.append((p,s['ndcg']))
    from v3_config import V1
    eligible.append((V1,base['ndcg']));best=max(s for p,s in eligible);near=[p for p,s in eligible if s>=best-settings['ndcg_tie']]
    chosen=sorted(near,key=lambda p:(p['factors'],-p.get('bias_l2',0),-p['fold_latent'],p['id']))[0]
    return chosen,{'chosen':chosen['id'],'baseline':base,'candidate_checks':receipt,'primary_best':best,'near_tie_policies':[p['id'] for p in near],'scope':'inner only, before all outer evaluations'}

def paired_bootstrap(rows,reference='V1H',target='Nested',seed=20261109,draws=3000):
    """User-cluster paired resampling preserving outerfold macro averaging."""
    users=sorted({u for f,m,p in rows for u in p});idx={u:n for n,u in enumerate(users)};matrix=np.full((len(users),3),np.nan)
    for f in range(3):
        a=next(p for ff,m,p in rows if ff==f and m==reference);b=next(p for ff,m,p in rows if ff==f and m==target);assert set(a)==set(b)
        for u in a:matrix[idx[u],f]=b[u]-a[u]
    rng=np.random.default_rng(seed);samples=[]
    for _ in range(draws):samples.append(float(np.mean(np.nanmean(matrix[rng.integers(len(users),size=len(users))],axis=0))))
    return {'positive_users':len(users),'fold_macro_delta':float(np.mean(np.nanmean(matrix,axis=0))),'low':float(np.quantile(samples,.025)),'high':float(np.quantile(samples,.975)),'draws':draws,'interpretation':'descriptive reused-train nested-CV workflow comparison, not independent Test significance'}
