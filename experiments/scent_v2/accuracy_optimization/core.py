"""Train-only features/MF, support-only scoring; actual old-mode formulas reused."""
import hashlib,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline,hybrid
from experiments.scent_v2.recommend import fold_in,rank
from experiments.scent_v2.unified_recommender.engine import percentiles
from experiments.scent_v2.personalized_recommender.engine import preferences,rerank
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/scent_v2/accuracy_optimization'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def order(text):return hashlib.sha256(text.encode()).hexdigest()


def split(rows,candidates):
    """Train triples -> user-disjoint train/dev/final; identity-only assignment."""
    if len({(u,i) for u,i,r in rows})!=len(rows):raise ValueError('Duplicate pairs')
    histories=defaultdict(list);pool=set(candidates)
    for u,i,r in rows:
        if not np.isfinite(r) or not 0<=r<=1:raise ValueError('Invalid rating')
        histories[u].append((i,float(r)))
    eligible=sorted((u for u,h in histories.items() if len(h)>=6 and sum(i in pool for i,r in h)>=5),key=lambda u:order('12:v224:role:'+u))
    if len(eligible)<30:raise ValueError('Insufficient eval users; no fake labels')
    n=math.ceil(len(eligible)/3);final=eligible[:n];dev=eligible[n:];train=[tuple(r) for r in rows if r[0] not in set(eligible)]
    def cohort(users):
        records=[]
        for u in users:
            ids=sorted((i for i,r in histories[u] if i in pool),key=lambda i:order('12:v224:support:'+u+':'+i));seen=set(ids[:5])
            records.append(dict(user=u,support=sorted((i,r) for i,r in histories[u] if i in seen),answers=sorted((i,r) for i,r in histories[u] if i not in seen)))
        return records
    return train,cohort(dev),cohort(final)


def validate_train(rows,excluded_users):
    if {u for u,i,r in rows}&set(excluded_users):raise ValueError('Evaluation user leaked into MF/IDF fit')


def components(support,candidates,content,mf,pop):
    """Five normalized support only. Shared MF raw/clipped predictions, no answers."""
    if len(support)!=5 or len({i for i,r in support})!=5:raise ValueError('Need5support')
    if any(not np.isfinite(r) or not 0<=r<=1 for i,r in support):raise ValueError('Invalid support')
    pool=sorted(set(candidates)-{i for i,r in support});p=fold_in(mf,support)
    raw=np.asarray([np.einsum('i,i->',p,mf.Q[mf.items[i]]) if p is not None and i in mf.items else np.nan for i in pool],float)
    c=content.score(support,pool);m=np.clip(raw,0,1);b=pop.score(pool);h=hybrid(c,m,.25,b)
    return dict(pool=pool,content=c,mf=m,raw=raw,baseline=h,known=sum(i in mf.items for i,r in support))


def percent_array(values,pool):
    """No label fit; missing stays NaN, tie ranks equal within this candidate universe."""
    p=percentiles({i:float(v) for i,v in zip(pool,values) if np.isfinite(v)})
    return np.asarray([p.get(i,np.nan) for i in pool])


def profile(support,pool,content,kind):
    """Train vocabulary fixed; rating / excess-liking / centered signed cosine."""
    if kind=='rating':return content.score(support,pool)
    if kind=='liked':
        v=content.score([(i,max(0,r-.6)) for i,r in support],pool)
        return v if np.isfinite(v).any() else content.score(support,pool)
    if kind!='centered':raise ValueError('Unknown profile')
    p=defaultdict(float)
    for i,r in support:
        for t,v in content.vectors.get(i,{}).items():p[t]+=(r-.5)*v
    norm=math.sqrt(sum(w*w for w in p.values()))
    if not norm:return content.score(support,pool)
    return np.asarray([.5+.5*sum(p[t]*v for t,v in content.vectors.get(i,{}).items())/norm if content.vectors.get(i) else np.nan for i in pool])


def score_variant(spec,support,candidates,content,mf,pop,cache=None):
    """spec frozen before answers; returns rankings on common479-minusSupport."""
    x=cache or components(support,candidates,content,mf,pop);pool=x['pool'];method=spec['method']
    if method=='baseline':return rank(pool,x['baseline'])[:5]
    if method=='pure_mf':return rank(pool,x['mf'])[:5]
    if method=='v22_unified':
        c=percent_array(x['content'],pool);h=percent_array(x['baseline'],pool)
        return rank(pool,.5*c+.5*h if x['known'] else c)[:5]
    if method in ('v23_personalized','v23_personalized_mmr'):
        values,_=preferences(content.vectors,[dict(product_id=i,rating=float(r*10)) for i,r in support],pool)
        return rerank(values,content.vectors,diversity=method.endswith('_mmr'))[0]
    if method!='rank_hybrid':raise ValueError('Unknown candidate')
    c=percent_array(profile(support,pool,content,spec['profile']),pool);m=percent_array(x['raw'],pool)
    alpha=.25+.5*(1-x['known']/5) if spec['alpha']=='adaptive' else spec['alpha']
    values=hybrid(c,m,alpha,pop.score(pool))
    return rank(pool,values)[:5]


def evaluate(spec,cohort,candidates,content,mf,pop):
    records=[]
    for row in cohort:
        top=score_variant(spec,row['support'],candidates,content,mf,pop)
        answers=row['answers'] # Only metric harness sees the labels, after scoring.
        records.append(dict(top=top,answers=answers,accuracy=user_metrics(top,answers)))
    return summarize(records,candidates),records


def paired(a,b,seed=12):
    deltas=np.asarray([y['accuracy']['ndcg']-x['accuracy']['ndcg'] for x,y in zip(a,b) if x['accuracy'] is not None])
    if not len(deltas):return dict(status='NOT_EVALUATED')
    rng=np.random.default_rng(seed);means=deltas[rng.integers(0,len(deltas),(20000,len(deltas)))].mean(axis=1)
    return dict(users=len(deltas),delta=float(deltas.mean()),low95=float(np.quantile(means,.025)),high95=float(np.quantile(means,.975)),improved=int((deltas>1e-12).sum()),worsened=int((deltas< -1e-12).sum()))
