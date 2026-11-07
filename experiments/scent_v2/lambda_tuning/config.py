"""Predeclared policy; never changed based on inner or outer observations."""
from experiments.scent_v2.config import ROOT, HEAD

OUT=ROOT/'outputs/scent_v2/lambda_tuning'
BASE=ROOT/'outputs/scent_v2/baseline'
LAMBDAS=(.01,.1,1.)
TRAIN_REG=.01
POLICY=dict(lambdas=LAMBDAS, training_regularization=.01, factors=4,epochs=160,
            learning_rate=.01,seed=12,alpha=.25,support=5,k=5,relevance=.7,
            bootstrap=20000,inner_folds=2,outer_folds=3,max_new_mf_fits=6,
            inner_user_order='original SHA256 12:user:{user} order excluding outer users; alternating 2 folds',
            support_order='SHA256 12:support:{user}:{item}; first five in catalog',
            selection_track='A',selection_method='hybrid',
            selection_rule='Change from .01 only if paired NDCG lower95>0 and mean improves; '
            'neither amplitude replacement/P90 may increase, neither first-retention may decrease, '
            'top-five item slot concentration may not increase (tolerance 1e-12). '
            'Among passing candidates maximize NDCG, tie within 1e-12 choose smaller lambda. '
            'Otherwise retain .01. Recall and all other metrics are reported, not new selection gates.',
            tolerance=1e-12,baseline=.01,no_outer_reselection=True,
            fallback='unchanged V2-0 component fallback; pure MF excludes NaN',filters=False)
