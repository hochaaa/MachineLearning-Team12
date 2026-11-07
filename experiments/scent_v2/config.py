"""Immutable experiment policy. No search or post-result parameter selection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/scent_v2/baseline'
HEAD = 'd92c59a379a278a94bf4ca149674abb841746d69'
TRAIN = ROOT / 'outputs/validation/train_exclude_3.json'
CANDIDATES = ROOT / 'outputs/improvement/candidates.json'
CATALOG = ROOT / 'Term-project-datasets/fra_cleaned.csv'
POLICY = dict(seed=12, support=5, outer_folds=3, relevance=.7, k=5,
              alpha=.25, factors=4, epochs=160, learning_rate=.01,
              regularization=.01, bootstrap=20000,
              split_user_hash='12:user:{user}',
              split_support_hash='12:support:{user}:{item}',
              mf_fallback='content_then_train_popularity',
              answer_denominator='all_observed_heldout_positives_including_unscorable',
              content_fit='fold_train_item_documents_only', filters=False)
