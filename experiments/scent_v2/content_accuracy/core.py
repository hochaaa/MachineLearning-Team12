"""Support-only signed Content profiles, unchanged MF/Ridge and score fallback.

Original local project components are reused; no third-party code copied. All
parameters are fixed in config.json before evaluation. No answer argument exists
in profile/scoring/inference APIs.
"""
from collections import defaultdict
import math,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from perfume.models import Content,Baseline,hybrid
from experiments.scent_v2.mf_cv_optimization.core import ROOT,ridge
from experiments.scent_v2.recommend import rank
OUT=ROOT/'outputs/scent_v2/content_accuracy'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def profile_scores(kind,support,pool,content,original=None):
    """5 Support ratings [0,1], unit TF-IDF vectors, cosine clipped to [0,1].

    rating_weighted: sum (2r-1)x. positive_negative_beta: mean(x,r>=.7)
    - beta*mean(x,r<=.3). Missing vectors are omitted, never filled with notes.
    Equal ratings/near-zero norm use the original positive-weighted profile.
    """
    if len(support)!=5 or len({i for i,r in support})!=5:raise ValueError('Exactly5 distinct Support ratings')
    if any(not np.isfinite(r) or not 0<=r<=1 for i,r in support):raise ValueError('Finite normalized ratings required')
    if kind not in CONFIG['profiles']:raise ValueError('Unknown profile')
    known=[(i,r) for i,r in support if content.vectors.get(i)];v=defaultdict(float)
    positives=[i for i,r in known if r>=.7];negatives=[i for i,r in known if r<=.3]
    for i,r in known:
        if kind=='rating_weighted':w=2*r-1
        else:
            beta=float(kind.rsplit('_',1)[1]);w=(1/len(positives) if i in positives else -beta/len(negatives) if i in negatives else 0.)
        for t,x in content.vectors[i].items():v[t]+=w*x
    norm=math.sqrt(sum(x*x for x in v.values()));reason=None
    if len({r for i,r in support})==1:reason='equal_ratings'
    elif norm<=1e-12:reason='zero_profile'
    if reason:values=content.score(support,pool) if original is None else original.copy()
    else:values=np.asarray([float(np.clip(sum(v[t]*x for t,x in content.vectors.get(i,{}).items())/norm,0,1)) if content.vectors.get(i) else np.nan for i in pool])
    return values,dict(valid_support_vectors=len(known),positive_support=len(positives),negative_support=len(negatives),fallback=reason)


def cache_support(support,candidates,c,m,b):
    """Exactly one original MF/Content and each custom profile calculation per user."""
    pool=sorted(set(candidates)-{i for i,r in support});cs=c.score(support,pool);bs=b.score(pool);p,_=ridge(m,support)
    ms=np.asarray([float(np.clip(np.einsum('i,i->',p,m.Q[m.items[i]]),0,1)) if p is not None and i in m.items else np.nan for i in pool]);profiles={};diags={}
    for kind in CONFIG['profiles']:profiles[kind],diags[kind]=profile_scores(kind,support,pool,c,cs)
    for arr in [cs,bs,ms,*profiles.values()]:arr.flags.writeable=False
    return dict(pool=pool,content=cs,mf=ms,popularity=bs,profiles=profiles,profile_diagnostics=diags)


def score_cached(spec,x):
    """Original bounded hybrid or true single-component fallbacks."""
    if spec['profile']=='original':cs=x['content']
    else:cs=x['profiles'][spec['profile']]
    if spec.get('pure')=='content':return np.where(np.isfinite(cs),cs,x['popularity'])
    return hybrid(cs,x['mf'],spec['alpha'],x['popularity'])


def predict(spec,support,candidates,c,m,b):
    """Inference from saved model and Support only; excludes rated IDs."""
    x=cache_support(support,candidates,c,m,b);top=rank(x['pool'],score_cached(spec,x))[:5]
    if len(top)!=len(set(top)) or set(top)&{i for i,r in support}:raise ValueError('Invalid Top5')
    return top


def save_model(path,c,m,b,candidates,spec):
    """Save item-only state and selected scoring policy; no user factors or ratings."""
    ids=sorted(candidates);tokens=sorted(c.idf)
    meta=dict(spec=spec,mf_config=CONFIG['mf'],feature_token_order={i:list(c.vectors[i]) for i in ids},scope='V29 all50 developer refit; experimental, not service deployment')
    values=dict(Q=m.Q,MF_items=np.asarray(sorted(m.items,key=m.items.get)),feature_items=np.asarray(ids),tokens=np.asarray(tokens),idf=np.asarray([c.idf[t] for t in tokens]),features=np.asarray([[c.vectors[i].get(t,0) for t in tokens] for i in ids]),popularity=np.asarray([b.counts[i] for i in ids]),popularity_maximum=np.asarray(b.maximum),metadata=np.asarray(json.dumps(meta)))
    with path.open('xb') as f:np.savez_compressed(f,**values)


def load_model(path):
    """allow_pickle=False; fixed Q and vocabulary loaded, never refitted."""
    with np.load(path,allow_pickle=False) as v:
        meta=json.loads(str(v['metadata']));cfg=meta['mf_config'];m=SimpleNamespace(Q=v['Q'].copy(),items={str(i):n for n,i in enumerate(v['MF_items'])},factors=cfg['factors'],reg=cfg['regularization']);m.Q.flags.writeable=False
        c=Content();c.idf=dict(zip(map(str,v['tokens']),map(float,v['idf'])));c.vectors={}
        token_indices={str(t):n for n,t in enumerate(v['tokens'])}
        for i,row in zip(v['feature_items'],v['features']):
            c.vectors[str(i)]={t:float(row[token_indices[t]]) for t in meta['feature_token_order'][str(i)]}
        b=Baseline();b.counts=defaultdict(int,zip(map(str,v['feature_items']),map(int,v['popularity'])));b.maximum=float(v['popularity_maximum'])
        return c,m,b,meta
