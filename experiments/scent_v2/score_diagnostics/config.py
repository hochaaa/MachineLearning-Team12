"""Diagnostic scopes and protected input paths, fixed before inspection of results."""
from experiments.scent_v2.config import ROOT,HEAD,TRAIN,CANDIDATES,CATALOG

OUT=ROOT/'outputs/scent_v2/score_diagnostics'
BASE=ROOT/'outputs/scent_v2/baseline'
TUNING=ROOT/'outputs/scent_v2/lambda_tuning'
POLICY=dict(lambdas=[.01,.1,1.],baseline=.01,alpha=.25,k=5,seed=12,
            bootstrap=20000,expected_contexts_per_lambda=150,unique_users=75,
            new_fits=0,old_test_access=False,
            distributions=['all','own_top5','hybrid_top5'],
            correlations=['all_pairwise_finite','factor_present','no_fallback','hybrid_top20'],
            counterfactuals=['raw_MF_only','raw_Hybrid','fallback_excluded'],
            success_groups='positive-answer users only; mean repeated-context NDCG=0 versus >0',
            warning='Exploratory diagnostic only. No selection, calibration or deployment.')
