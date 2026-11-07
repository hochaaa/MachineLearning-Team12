# V2-31 fixed-model validation (no new recommendation model)

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.final_validation.test_validation -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.final_validation.run
```

Completed outputs cannot be overwritten. The exclusive protocol lock and final
open marker prevent automatic reruns. Do not remove them to retry the final test.
No packages installed or old files changed. No new model/scoring function, search,
service change or Git action. Two policies only: original H, and fixed V30 Max
Similarity lambda.20 strictly within H Top50, including all original fallbacks.

## Evidence and data boundary

- V30's config, source SHA256 recorded at its completion, model SHA256 and selected
  metadata checked before reconstruction. `locked_protocol.json` records fixed
  policy/source/model hashes BEFORE reserved labels are decoded. `check_lock`
  checks those hashes again before and after the final run.
- Original `developer_cohort` decodes only50 developers, not25 reserved or255
  background users. Five original folds, MF160epochs/factors4/lr.01/L2.01/seed12,
  train40/eval10, exact previous Support5/answers, candidates479, relevance>=.7.
  Every evaluated user's entire history excluded from its MF/TF-IDF fold fit.
- V30 has only aggregate CV metrics, not per-user predictions or trained fold
  state. Reconstruct exactly5 MF/TF-IDF fold fits to recover numeric per-user
  changes. Only the two fixed policies evaluated. Fold NDCG/Recall/HitRate must
  reproduce old results within1e-12 before any reserved numeric labels open.
- V30 `SimilarityIndex`, `cache_support`, `rerank`, item-only `load_model` are
  reused without modifications. Max/Top50/Fallback equations are unchanged.
  Existing saved synthetic IDs and scores replay EXACTLY. No claim of bitwise
  comparison with historical per-user CV outputs, because those were not saved.
- `reserved_tokens(path,candidates,reserved)` parses original source identities
  and opaque rating strings. Reserved25 membership and Support order use the
  exact V24 identity hashes. It does not decode any reserved rating. `decode`
  alone converts tokens into normalized finite numeric values.
- `open_gate(lock)` checks fixed policy and completed stability/audit outputs,
  then exclusively creates V31 `final_opened_once.json`. Only afterwards are
  reserved Support ratings decoded. All25 users x2 fixed-model predictions
  complete BEFORE decoding any of their held-out labels. Their answers enter
  only the existing metric harness. This is one new V31 assessment; V24's old
  one-time marker is preserved and its private final manifest is never read.
- Both final models reuse exactly the same V30 item-only state (trained50
  developers/659 ratings, zero overlap with25 eval users). No final fit. The255
  background users from original Train are not used. Thus CV train40 versus
  final train50 and different evaluation users cannot be compared as the same
  experiment. Historical V24 final training had a different, larger scope.
- The25 users were already evaluated in V24. Code/logs support direct exclusion
  during V25-30, but absence of indirect human/historical influence cannot be
  proved. This is REUSED HISTORICAL USER-DISJOINT HOLDOUT, not pristine independent
  generalization evidence. Old V24 metric values are not needed or read here.

## Metric analysis methods and parameters

- `paired_counts(pairs)`: numeric baseline/selected NDCG+hit metrics only; no
  user/item IDs or raw ratings. Accuracy excludes users with no positive answer.
- `fold_mean_delta(pairs,removed=())`: arithmetic mean of fold means. On removal,
  recomputes that fold's positive-user denominator. This is **metric exclusion**,
  not leave-one-out retraining or a change to the evaluation/model policy.
- `stability(pairs,seed=12,draws=20000)`: positive/negative contributions use
  1/(5 * positive_users_in_fold), so they sum to macro-fold NDCG difference.
  Largest1/2 shares are reported against both positive gains and NET change;
  these are different denominators. Also reports all one-user exclusions and
  exclusion of the two largest positive contributors. No tuning follows.
- Developer paired bootstrap resamples positive users within each fold, then
  averages fold means, using NumPy Generator(seed12),20,000 draws, quantiles
  .025/.975. Descriptive conditional interval: does not account for repeated
  model selection or overlap of training folds; not a formal significance test.
- `final_uncertainty(pairs,seed=12,draws=20000)`: paired positive-user bootstrap
  for the single25-user historical cohort, same quantiles. This cannot repair
  historical exposure or small-sample limitations. No-positive users remain
  in exposure/coverage counts. No unknown rating treated as a dislike.
- `guard()`: output writes only in V31; allows limited original Train/catalog,
  V30 state and historical status metadata reads; denies old V24 metric/private
  final data, other model/result reads and network/process mutations. Pre/post
  hashes separately verify Frozen19, manifest, inputs, V30 and service sources.

No third-party implementation copied. All reuse is from local modules cited
above; analysis.py contains only evaluation bookkeeping/statistics, not a new
recommendation model. Per-user numeric diagnostics are local mode0600 and contain
no personal identifiers, item histories, input ratings or persistent user hashes.
