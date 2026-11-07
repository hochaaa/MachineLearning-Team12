"""Portable paths and fixed collection policy, separate from frozen service."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/scent_v2/real_user_dataset'
DATA=OUT/'data'
CANDIDATES=ROOT/'outputs/improvement/candidates.json'
CATALOG=ROOT/'Term-project-datasets/fra_cleaned.csv'
LEGACY=ROOT/'outputs/validation/train_exclude_3.json'
HEAD='d92c59a379a278a94bf4ca149674abb841746d69'
CONSENT_VERSION='team12-local-collection-2026-10-29-v1'
POLICY=dict(seed=12,development_fraction=.60,port=8014,bind='127.0.0.1',candidate_count=479,rating_min=0,rating_max=10,rating_step=.5,max_batch=479,max_reason=300,source='real_user_collection',support=5,relevance_raw=7,top_k=5,consent_version=CONSENT_VERSION,mode='local_only_operator_review_before_external_participation')
