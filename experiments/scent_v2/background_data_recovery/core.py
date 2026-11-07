"""Restore original background users; no recommendation algorithm modifications.

Local reuse: V25 developer_data, V26 folds, original MF/Content, V30 reranking.
NPZ is a fold-state bank, not an ensemble/new scoring model. No external code copied.
"""
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict
import json,math
import numpy as np
from perfume.models import Content,Baseline
from experiments.scent_v2.mf_accuracy_optimization.core import developer_data,digest
from experiments.scent_v2.mf_cv_optimization.core import ROOT,folds,validate_train
from experiments.scent_v2.similarity_reranking.core import SimilarityIndex,cache_support,rerank,predict
OUT=ROOT/'outputs/scent_v2/background_data_recovery'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def validate_data(background,cohort,reserved,candidates):
    """Reject overlap/duplicates/invalid ratings, without deleting or remapping data."""
    bg_users={u for u,i,r in background};dev_users={r['user'] for r in cohort}
    if len(dev_users)!=len(cohort) or bg_users&dev_users or bg_users&set(reserved) or dev_users&set(reserved):raise ValueError('User overlap/duplicate; stop training')
    if len({(u,i) for u,i,r in background})!=len(background):raise ValueError('Duplicate background user-item')
    if any(not isinstance(u,str) or not isinstance(i,str) or isinstance(r,bool) or not math.isfinite(r) or not 0<=r<=1 for u,i,r in background):raise ValueError('Original normalized string-ID train schema required')
    for row in cohort:
        s=row['support'];a=row['answers'];history=s+a
        if len(s)!=5 or not a or len({i for i,r in history})!=len(history) or not {i for i,r in s}<=set(candidates):raise ValueError('Invalid Support/heldout split')
        if any(not isinstance(i,str) or isinstance(r,bool) or not math.isfinite(r) or not 0<=r<=1 for i,r in history):raise ValueError('Invalid developer rating')
    result=[]
    for f in folds(cohort):
        evaluation_users={r['user'] for r in f['evaluation']};combined=list(background)+f['train'];validate_train(combined,evaluation_users|set(reserved))
        if len({(u,i) for u,i,r in combined})!=len(combined):raise ValueError('Duplicate combined edge')
        if {u for u,i,r in combined}!=bg_users|{u for u,i,r in f['train']}:raise ValueError('Invalid union')
        result.append(dict(fold=f['fold'],train=combined,evaluation=f['evaluation'],developer_train=f['train']))
    return result


def pack_state(c,m,b,candidates):
    """Snapshot item-only arrays; exclude P, user mappings and original ratings."""
    ids=sorted(candidates);tokens=sorted(c.idf)
    arrays=dict(Q=m.Q.copy(),MF_items=np.asarray(sorted(m.items,key=m.items.get)),feature_items=np.asarray(ids),tokens=np.asarray(tokens),idf=np.asarray([c.idf[t] for t in tokens]),features=np.asarray([[c.vectors[i].get(t,0.) for t in tokens] for i in ids]),popularity=np.asarray([b.counts[i] for i in ids]),popularity_maximum=np.asarray(b.maximum),token_order=np.asarray(json.dumps({i:list(c.vectors[i]) for i in ids})))
    return arrays


def save_bank(path,states,policy):
    """Store all5 folds. Policy selected globally, default fold1 predeclared."""
    values={f'fold{n}_{key}':value for n,state in enumerate(states,1) for key,value in state.items()}
    values['metadata']=np.asarray(json.dumps(dict(policy=policy,mf_config=CONFIG['mf'],folds=len(states),default_fold=1,artifact_type='CV_FOLD_BANK_NOT_ENSEMBLE_OR_ALL305_REFIT',scope='Per-fold background+developer training, no reserved users',config=CONFIG)))
    with path.open('xb') as f:np.savez_compressed(f,**values)


def load_model(path,fold=1):
    """Load one PRE-EXISTING fold state and globally selected policy, no fit.

    fold1 is a prespecified representative, not performance-selected. For CV
    reproduction load each original fold; never average the five model scores.
    """
    with np.load(path,allow_pickle=False) as z:
        meta=json.loads(str(z['metadata']))
        if not 1<=fold<=meta['folds']:raise ValueError('Invalid stored fold')
        prefix=f'fold{fold}_';get=lambda k:z[prefix+k];cfg=meta['mf_config'];m=SimpleNamespace(Q=get('Q').copy(),items={str(i):n for n,i in enumerate(get('MF_items'))},factors=cfg['factors'],reg=cfg['regularization']);m.Q.flags.writeable=False
        c=Content();tokens=list(map(str,get('tokens')));c.idf=dict(zip(tokens,map(float,get('idf'))));pos={t:n for n,t in enumerate(tokens)};order=json.loads(str(get('token_order')));c.vectors={str(i):{t:float(row[pos[t]]) for t in order[str(i)]} for i,row in zip(get('feature_items'),get('features'))}
        b=Baseline();b.counts=defaultdict(int,zip(map(str,get('feature_items')),map(int,get('popularity'))));b.maximum=float(get('popularity_maximum'))
        return c,m,b,meta
