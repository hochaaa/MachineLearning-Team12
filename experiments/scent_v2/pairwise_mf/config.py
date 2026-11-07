"""Policy fixed before fitting/results, not a hyperparameter search."""
from experiments.scent_v2.config import ROOT,HEAD,TRAIN,CANDIDATES,CATALOG
OUT=ROOT/'outputs/scent_v2/pairwise_mf'
BASE=ROOT/'outputs/scent_v2/baseline'
TUNING=ROOT/'outputs/scent_v2/lambda_tuning'
POLICIES={'baseline':0.,'variant_a':1.,'variant_b':2.}
POLICY=dict(seed=12,factors=4,epochs=160,learning_rate=.01,regularization=.01,beta=.1,
    fold_lambda=.01,alpha=.25,k=5,relevance=.7,support=5,bootstrap=20000,
    max_new_fits=15,inner_fits=12,outer_selected_variant_fits_max=3,
    A_objective='sum softplus(-p(qi-qj)) + .01*(sumP2+sumQ2)',
    A_optimizer='SGD per observed pair; global reg/n_pairs distributed over steps',
    A_items='observed pair participants only; no-pair items do not get usable factors',
    B_objective='mean[.5*rating_error^2 + .5*.01*(Pu2+Qi2)] + .1*mean(pair softplus)',
    B_optimizer='original rating SGD pass then pair pass scaled beta*n_ratings/n_pairs',
    A_foldin='Support-only pair objective sumsoftplus+.01*p2; Newton/backtracking',
    foldin_iterations=50,foldin_backtracking=20,foldin_tolerance=1e-8,foldin_damping=1e-10,
    no_pair_or_failed_foldin='pure MF NaN, Hybrid original C/M/popularity fallback; never arbitrary vector',
    A_transform='fixed sigmoid(raw) for Hybrid diagnostics; pure MF ranks raw',
    A_transform_diagnostic_only=True,A_eligible_for_adoption=False,
    B_transform='original clip(raw,0,1)',
    B_compatibility_rmse_allowed_increase=.05,B_clipping_allowed_increase=.05,
    norm_ratio_divergence_limit=10.,coverage_allowed_loss=0,concentration_allowed_increase=0.,
    robustness_allowed_replacement_increase=0.,robustness_allowed_p90_increase=0.,robustness_allowed_first_decrease=0.,
    tolerance=1e-12,selection='per Outer Inner TrackA Hybrid NDCG increase and paired95 lower>0, no coverage/concentration loss, zero-loss robustness at both amplitudes and compatibility; A sigmoid diagnostic-only cannot establish adoption; best passing NDCG, ties A then B; else baseline',
    outer_evaluate='baseline and locked selection only; do not evaluate unselected variants',
    historical_outer_reuse='exploratory only; no independent confirmatory accuracy claim')
