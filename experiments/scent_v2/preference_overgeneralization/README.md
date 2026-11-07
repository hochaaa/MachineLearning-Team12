# V2-35 preference overgeneralization: observation only

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.preference_overgeneralization.test_analysis -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.preference_overgeneralization.run
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.preference_overgeneralization.feature_traces
```

No fits, policy changes, algorithm/parameter/model selection, service/Git/install
or external data actions. Existing outputs are exclusively created, not overwritten.
Do not delete existing files to automatically retry the completed analysis.

## Replay and label boundary

V33 best_model.npz is the ONLY model loaded:5 original40-train/10-eval states.
V34 prepared305 and V32 background models are denied. V26 developer_cohort reads
only50 developer labels, skips25 reserved and255 background numeric labels.
Same Support5/candidate479/relevance.7/metric code. A user's original evaluation
fold is always used. All50 x2 recommendations/scores/ranks complete BEFORE the
posthoc preference/heldout analysis. No answers enter original scorer APIs.
Original MF.fit/Content.fit are patched to fail during replay, proving no refits.
Stored Q/structural matrix bytes must remain unchanged. Baseline and Structured
NDCG/Recall/HitRate reproduce V33 within1e-12, with no newly selected model.

## Operational definitions fixed in analysis_config.json

- Positive>=.7, negative<=.3, middle(.3,.7) NEUTRAL, missing UNOBSERVED. Below.7 is
  not automatically negative. Old zero-excluded training source is unchanged.
- `preferences(history,features)` is posthoc on whole-product ratings. MainAccord
  sets remain separate from Top/Middle/Base note phrases. "Compound preference"
  is a proxy:>=2 positive products whose Accord sets each have a feature absent
  in the other. A single complex perfume does not count. This is NOT proof of
  isolated woody/floral/musky liking. Channel unions/intersections/Jaccards record
  positive/negative overlap; missing polarity/channel is N/A, not zero evidence.
- Full history (Support+answers) and Support-only patterns are stored separately.
  Common-to-all features require>=2 feature-valid products; per-feature overlap
  denominator includes users with both known positive and negative annotations.
  Raw metadata interpretation can include a phrase absent from a fold vocabulary;
  actual structural score uses the frozen trained matrix, never the raw feature
  union as a new scoring input.
- `pair_analysis(...)`: every unordered pair (1225) records exact co-rated count,
  mutual-positive products, opposite labels on the SAME other product and shared
  positive Accord annotations. Strict evaluability requires>=2 common products
  and>=1 same-product mutual positive. Missing co-ratings -> INSUFFICIENT_EVIDENCE,
  not identical preferences or no conflict. Opposed product extra Accords are
  annotations, not isolated disliked-family truth. Different products' ratings
  cannot establish user disagreement. Cross-fold source users can occur in a
  recipient's40-user Train; same-fold peers are excluded from that Train.
- `max_similarity(matrix,items,anchors,pool)` is diagnostic only: reuse frozen
  per-channel matrix for positive anchors and separately negative anchors. Negative
  similarities NEVER enter recommendation scores. `suspected(pos,neg)` returns
  neg>pos+1e-12 only if both anchors available, otherwise N/A. D is a risk signal,
  E is confirmed observed negative Top5. Unknowns never become errors.
- Original Content adds positive rating weights, MF Ridge uses ALL Support values
  including low ratings. Structured Max uses positive anchors only. Do not claim
  all negative preferences are ignored or apply double negative penalties blindly.
- MF/content component-only ranks are descriptive references with original
  missing-value fallbacks, not new evaluated models. A component is aligned when
  its rank<=5 and the other's rank>5. Both/mixed/fallback cases separate. Numeric
  contributions .75MF/.25Content are contributions to original H (not post-rerank
  total); available-component fallback has share1. MF share undefined if H=0.
- Structured promotion means final rank improves relative to H, especially6..50
  entering Top5. The original V30 reranker returns full ranks for inspection; its
  first5 IDs/scores must EXACTLY equal V33 original predict() results. No new model.
- `summarize_recommendations(rows)`: slot denominator250/model. Confirmed negative
  fraction among observed-rated slots is conditional; negative/all250 is only a
  known-negative lower bound. Suspicion denominator is slots with BOTH valid
  positive/negative Support anchors; unavailable slots counted separately.
  Repeated same product across users/models is not an independent observation.
- `feature_traces` reads completed CSVs and developer labels, performs NO model
  inference. It finds weaker chains: exact shared-positive and opposed co-rated
  product, source in recipient Train, recommendation sharing extra Accord
  annotations. These do not establish recipient dislike of the recommendation.
  Physical rating/error and MF transfer causality remain unproved.

Temporary U01..U50 aliases permit case linkage; original IDs, hashes or their
mapping are NEVER exported. No original full rating rows or numeric heldout
ratings are written: recommendation labels only. Derived per-person analysis is
local mode0600, not a claim of irreversible anonymization or public release.
Case1 is explicitly weak/feature-only if no negative Top5 chain exists. Case2/3
require an observed negative removed/promoted; absent cases are NOT fabricated.

Original `fragrantica`/`structural_phrases`, V26 folds, V33 loaders/component scores,
V30 rank/rerank and existing metrics reused without changes. No third-party code
copied. New functions are observational bookkeeping only. No causal claims or
recommendation accuracy improvement claims follow from this analysis.
