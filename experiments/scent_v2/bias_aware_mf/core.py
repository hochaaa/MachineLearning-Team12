"""Shared V26 user folds and metric policy; only MF training/fold-in differs."""
import json
from pathlib import Path
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline,hybrid
from experiments.scent_v2.mf_cv_optimization.core import ROOT,developer_cohort,folds,validate_train,user_scores as legacy_scores
from experiments.scent_v2.recommend import rank
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
OUT=ROOT/'outputs/scent_v2/bias_aware_mf';CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def predict(spec,support,candidates,content,mf,pop,shared=None):
    """Support-only API for both baseline and biased; same exclusions/score scale."""
    if spec['family']=='legacy':return legacy_scores(dict(alpha=spec['alpha'],ridge_scale=1.,center=False),support,candidates,content,mf,pop,shared)
    pool=sorted(set(candidates)-{i for i,r in support});c,b=shared if shared is not None else (content.score(support,pool),pop.score(pool))
    theta=mf.fold_in(support,spec['bias_shrinkage']);m=mf.score_vector(theta,pool);values=hybrid(c,m,spec['alpha'],b)
    top=rank(pool,values)[:5]
    if len(top)!=len(set(top)) or set(top)&{i for i,r in support}:raise ValueError('Invalid Top5')
    return top


def evaluate(spec,fold,candidates,c,m,b,shared):
    records=[]
    for row in fold['evaluation']:
        top=predict(spec,row['support'],candidates,c,m,b,shared[row['user']])
        answers=row['answers'];records.append(dict(top=top,answers=answers,accuracy=user_metrics(top,answers)))
    return summarize(records,candidates),records
