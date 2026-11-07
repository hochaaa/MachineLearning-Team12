"""Support item-wise cosine reranking over unchanged Hybrid, not profile replacement.

Local reuse: original Content/MF/hybrid, V26 ridge/rank, V29 NPZ loader. No
third-party implementation copied. All rules and parameters fixed in config.json.
"""
import json
from pathlib import Path
import numpy as np
from perfume.models import hybrid
from experiments.scent_v2.mf_cv_optimization.core import ROOT,ridge
from experiments.scent_v2.recommend import rank
from experiments.scent_v2.content_accuracy.core import load_model
OUT=ROOT/'outputs/scent_v2/similarity_reranking'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


class SimilarityIndex:
    """One candidate-item cosine matrix per TRAIN-fitted TF-IDF model.

    ids: fixed479 (small synthetic sets allowed in tests); content: unit sparse
    vectors from existing train-only Content. Missing feature rows remain NaN.
    No answer/rating data enter construction. Matrix reused across users/policies.
    """
    def __init__(self,content,ids):
        self.ids=sorted(set(ids));self.items={i:n for n,i in enumerate(self.ids)}
        tokens=sorted(content.idf);X=np.asarray([[content.vectors.get(i,{}).get(t,0.) for t in tokens] for i in self.ids],float)
        norms=np.sqrt(np.einsum('ij,ij->i',X,X));valid=norms>1e-12
        X[valid]/=norms[valid,None]
        self.matrix=np.clip(np.einsum('it,jt->ij',X,X),0.,1.)
        self.matrix[~valid,:]=np.nan;self.matrix[:,~valid]=np.nan;self.matrix.flags.writeable=False

    def signals(self,support,pool):
        """Return bounded Max and r*cos Top2. Support ratings only, never labels.

        r normalized[0,1] multiplies cosine directly; no weight renormalization
        that could inflate weak similarities. Missing contribution pads0 for Top2.
        Both methods require a known valid positive Support item (r>=.7).
        """
        if len(support)!=5 or len({i for i,r in support})!=5:raise ValueError('Exactly5 distinct Support required')
        if any(not np.isfinite(r) or not 0<=r<=1 for i,r in support):raise ValueError('Finite normalized Support ratings required')
        if any(i not in self.items for i,r in support):raise ValueError('Support outside fixed catalog')
        columns=[self.items[i] for i in pool];valid=[(i,r) for i,r in support if np.isfinite(self.matrix[self.items[i],self.items[i]])];positive=[i for i,r in valid if r>=CONFIG['positive_threshold']]
        empty=np.full(len(pool),np.nan)
        if not positive:return dict(max=empty.copy(),top2=empty.copy()),dict(valid_support=len(valid),positive_support=0,status='no_valid_positive_support')
        maxscores=np.max(np.nan_to_num(self.matrix[[self.items[i] for i in positive]][:,columns],nan=0.),axis=0) if columns else empty.copy()
        # Explicitly avoid all-NaN reduction warnings for featureless candidates.
        valid_candidates=np.asarray([np.isfinite(self.matrix[n,n]) for n in columns],dtype=bool)
        maxscores[~valid_candidates]=np.nan
        raw=np.asarray([r*self.matrix[self.items[i],columns] for i,r in valid]);raw=np.nan_to_num(raw,nan=0.)
        if len(raw)<2:raw=np.vstack([raw,np.zeros((2-len(raw),len(pool)))])
        top2=np.sort(raw,axis=0)[-2:].mean(axis=0);top2[~valid_candidates]=np.nan
        return dict(max=maxscores,top2=top2),dict(valid_support=len(valid),positive_support=len(positive),status='ok')


def cache_support(support,candidates,c,m,b,index):
    """One unchanged H plus two similarity arrays per user, shared by12 policies."""
    pool=sorted(set(candidates)-{i for i,r in support});signals,diag=index.signals(support,pool)
    cs=c.score(support,pool);bs=b.score(pool);p,_=ridge(m,support)
    ms=np.asarray([float(np.clip(np.einsum('i,i->',p,m.Q[m.items[i]]),0,1)) if p is not None and i in m.items else np.nan for i in pool])
    h=hybrid(cs,ms,.25,bs);base_order=rank(pool,h)
    for a in [h,*signals.values()]:a.flags.writeable=False
    return dict(pool=pool,hybrid=h,signals=signals,baseline_order=base_order,diagnostic=diag)


def rerank(spec,x,k=5):
    """Answer-free full scoring or strictly Hybrid-only Top50 candidate selection.

    Returns IDs and their final scores. k permits full diagnostic rankings, not
    ground-truth candidate selection. Weak/unavailable signals preserve H exactly.
    """
    weight=spec['lambda'];scores=x['hybrid'].copy()
    if not 0<=weight<=1 or spec['mode'] not in ('full','top50'):raise ValueError('Invalid reranking policy')
    if weight:
        s=x['signals'][spec['signal']];active=np.isfinite(s)&(s>=CONFIG['signal_floor'])
        if spec['mode']=='top50':active &= np.asarray([i in set(x['baseline_order'][:50]) for i in x['pool']])
        scores[active]=(1-weight)*scores[active]+weight*s[active]
    if spec['mode']=='top50' and weight:
        chosen=x['baseline_order'][:50];lookup={i:n for n,i in enumerate(x['pool'])}
        ordered=rank(chosen,np.asarray([scores[lookup[i]] for i in chosen]))+x['baseline_order'][50:]
    else:ordered=rank(x['pool'],scores)
    lookup=dict(zip(x['pool'],map(float,scores)));top=ordered[:k]
    if len(top)!=len(set(top)):raise ValueError('Duplicate rank IDs')
    return top,[lookup[i] for i in top]


def predict(spec,support,candidates,c,m,b,index=None):
    """Saved model inference; excludes Support, deterministic ties by original ID."""
    index=index or SimilarityIndex(c,candidates);x=cache_support(support,candidates,c,m,b,index);top,scores=rerank(spec,x)
    if set(top)&{i for i,r in support}:raise ValueError('Support in recommendations')
    return top,scores


def save_model(path,c,m,b,candidates,spec):
    """Item-only state plus exact selected policy; preserves vector token order."""
    ids=sorted(candidates);tokens=sorted(c.idf)
    meta=dict(spec=spec,mf_config=CONFIG['mf'],feature_token_order={i:list(c.vectors[i]) for i in ids},scope='V30 selected reranking on verified V29 all50 developer item state; experimental, not service',reranking_config=CONFIG)
    values=dict(Q=m.Q,MF_items=np.asarray(sorted(m.items,key=m.items.get)),feature_items=np.asarray(ids),tokens=np.asarray(tokens),idf=np.asarray([c.idf[t] for t in tokens]),features=np.asarray([[c.vectors[i].get(t,0) for t in tokens] for i in ids]),popularity=np.asarray([b.counts[i] for i in ids]),popularity_maximum=np.asarray(b.maximum),metadata=np.asarray(json.dumps(meta)))
    with path.open('xb') as f:np.savez_compressed(f,**values)


def specs():
    result={'hybrid_baseline':dict(signal='none',mode='full',**{'lambda':0.})}
    for signal in CONFIG['signals']:
        for mode in CONFIG['modes']:
            for w in CONFIG['lambdas']:result[f'{signal}_{mode}_l{w:g}']=dict(signal=signal,mode=mode,**{'lambda':w})
    return result
