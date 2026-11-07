"""Fixed pilot design; data-supported vs stress assumptions are distinguished."""
from experiments.scent_v2.config import ROOT,HEAD,TRAIN,CANDIDATES,CATALOG
MANIFEST=ROOT/'outputs/scent_v2/baseline/split_manifest.private.json'
OUT=ROOT/'outputs/scent_v2/synthetic_data'
POLICY=dict(seed=12,version='v2_10_pilot_1',users=1000,activity_matched_users=150,enriched_users=850,
    enriched_ratings_min=15,enriched_ratings_max=20,
    exclusion='ALL75 existing Nested evaluation users, entire histories, not only labels; values skipped before decoding',
    generation_scope='eligible Train-only rows whose item belongs to frozen479',rating_scale='raw0-10; source normalized y*10',rating_step=.5,
    positive_raw=7.,low_raw=5.,item_shrink=10.,feature_shrink=20.,user_shrink=5.,
    selection='p_i proportional to sqrt(Train count+1); without replacement',
    stress_preference_selection_temperature=.25,preference_variance_fraction=.0625,
    matched_feature_signal='enabled only if matched-user similar/dissimilar difference CI lower>0 and n>=10; otherwise0',
    enriched_feature_signal='weak6.25% within-user variance, explicit synthetic assumption not fitted real preference',
    preference_feature_counts='each sign3-8 distinct features, random lognormal magnitudes sigma.35',
    global_feature_mixture=.15,residual_histogram_width=.5,
    marginal_rating_calibration='one fixed pass: monotone global latent rank -> empirical eligible-Train quantile -> round.5, clip0-10; matches marginal by construction',
    feature_pair_similarity_high=.5,feature_pair_similarity_low=.1,minimum_history_for_structure=5,
    structure_bootstrap=2000,feature_uncertainty='user-cluster delta-method approximate95%; fewer5 feature users=>N/A; no multiple-comparison correction',
    protected_tests='no numeric label decoding from manifest; no original Validation/Internal/External data read',
    no_recommender_fit_or_evaluation=True,synthetic_not_anonymity_or_license_guarantee=True)
