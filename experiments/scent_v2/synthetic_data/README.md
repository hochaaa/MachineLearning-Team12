# V2-10 — Real-data profiling and synthetic pilot only

No recommender fit, inference, evaluation, service integration, original dataset
augmentation, Git mutation, install or upload. Original labels/models untouched.
Existing output => STOP; no overwrite or automatic quality-driven generator tuning.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m unittest discover -s experiments/scent_v2/synthetic_data/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m experiments.scent_v2.synthetic_data.run
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m experiments.scent_v2.synthetic_data.reporting
```

## Strict boundary

The original normalized Train1805 includes histories of75 previously evaluated
Nested users. Read only `users` identity arrays from the saved manifest; skip all
train/support/answer values. In the flat Train triples, check user before decoding
item or rating; skip those75 histories entirely (910 rows). Eligible895 rows/255
users are left; only candidate-aligned823 rows/254 users calibrate generation.
No original Validation/Internal/External/raw Atrafshan rating file is parsed.

The remaining activity is conditional on excluding the high-activity evaluation
cohort, NOT a population-wide claim that real users only rate1–5 items. Original
330/538/1805 are historical context, not generator statistics. Metadata CSV is
public-item feature input, not user labels. Vocabulary/IDF from eligible Train items
only; candidate metadata transformed with same original token/IDF rules.

## Purpose-separated pilot

150 activity-matched users follow eligible reference counts;850 enriched users
have15–20 histories for proposed Support5/Target roles. All synthetic IDs have a
new namespace. Enrichment is intentional, not observed long-term behavior.
The data cannot identify strong feature-consistency/clusters: only18 eligible
users have5 ratings and zero pairs have cosine>=.5 under fixed bins. Matched group
feature signal is0. Enriched group uses an explicit weak6.25% variance stress
assumption; different continuous sparse preferences, not fixed taste classes.

User style/shrunken variance, item centered effects, tempered sqrt(count+1) exposure,
empirical residual noise and weak synthetic affinity are combined. One predetermined
latent-rank->eligible-Train rating quantile map, half-point rounding and clipping
match the rating marginal BY CONSTRUCTION. Do not treat this as independent realism
validation. Parameters/seed12 fixed; two full generations hash-identical.

## Outputs and limits

REPORT/design/config/profile/quality + actual four SVGs, synthetic ratings/users
and separate generator audit. Real per-user rows/IDs never exported. Feature means
for<5 Train users suppressed in public table. Generator parameters private file
contains aggregate-derived statistics and sorted marginal ratings, no source IDs.
No DP/anonymity/redistribution guarantee is implied. Derived metadata and pilot stay
local; raw source/site permissions still apply.

Latent vectors/noise audit and proposed roles are debugging/design fields, NOT
legitimate future heldout-prediction features. Generator latent Top5 and known-signal
R² are synthetic diagnostics, not a trained recommender or real-user accuracy.
Future augmentation needs separate authorization/design and fresh independent
real-user evaluation; do not contaminate old frozen/repeated Test sets.

Local code provenance: src/perfume/data.py token parsing/normalization and smoothed
IDF equation reused without altering its files. No third-party implementation copied.

Fresh-process audit: `python -B -m experiments.scent_v2.synthetic_data.reproduce` reads saved aggregate parameters and fixed vocabulary/metadata; source IDs only,0 numeric rating decodes. It generates in memory, checks original CSV rows/hashes, writes only reproduction_check.json and refuses existing evidence. No rule refit or source overwrite.
