# V2-32 background restoration (no algorithm changes)

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.background_data_recovery.test_recovery -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.background_data_recovery.run
```

Existing outputs are exclusively created, never overwritten. Re-running the
completed experiment stops on experiment_config.json. No installs/Git/service
changes, no final25 assessment or V24/V31 final-result reads.

## Exact local reuse and parameters

- `developer_data` (V25) reproduces original background255/895 and developer50/659
  using the original canonical string IDs, normalized source and original role/
  Support hashes. Both background and developer checksums must match V25.25
  reserved users' rating substrings are skipped BEFORE numeric decoding (251
  skipped records); only their IDs participate in exclusion. The mixed source
  file bytes are parsed for identities, not used as numeric reserved labels.
- `validate_data(background,cohort,reserved,candidates)`: rejects any background/
  developer/reserved overlap, duplicate user-item pair, invalid normalized value
  or Support/heldout collision. No repair/deletion/remapping to pass validation.
  Reuses unchanged V26 folds. Combined train order is original background order
  followed by existing fold Train order, fixed and deterministic.
- Original `MatrixFactorization` factors4,160epochs,lr.01,L2.01,seed12, SGD and
  Support-only Ridge unchanged. Fit once/fold on background255+developer40,
  excluding eval10 and reserved25. Two models share the SAME Q/Content/popularity
  and user score cache, no fit per model and no Q imported from another model.
- Content uses the original binary-TF smoothed IDF, train-item vocabulary fit and
  L2 feature normalization. Adding background expands training document coverage
  as required by the same train-only protocol. IDF/popularity also change with
  training scope; before/after differences cannot be attributed solely to MF.
- `SimilarityIndex`, `cache_support`, `rerank`, `predict` (V30) reused unchanged.
  A = Hybrid Content.25/MF.75 with original clipping/component fallback.
  B = same H + Max cosine of positive Support>=.7, weight.20, Hybrid-only Top50,
  same weak-signal .05/missing-positive fallback. Top2 may be calculated by the
  reused cache but is never evaluated or selected here. No alternate lambda/K.
- `user_metrics`/`summarize` unchanged, binary relevance>=.7. Support excluded from
  fixed479, sorted IDs break ties. NDCG/Recall/HitRate@5 averaged over positive-
  answer users then equally over5folds. Other users count for exposure only.
  `counts_coverage(rows,candidates,positive_items)` includes zero-count candidates
  and uses occurrence-weighted user-item positives, not catalog-only overlap.
- Recall@20/50/100 is metric-only. B's Top50/Top100 membership equals A by design:
  B only reorders inside first50; Recall@50/100 equality is expected, not a bug.
  Ranking all items occurs before answer access, so labels cannot choose Top50.
- Selection fixed before fits: B only if mean NDCG strictly exceeds A, otherwise
  A; Recall/HitRate secondary, ties retain A. Historical40-user aggregate metrics
  are reference only, not the decision baseline. No conditional per-user policy.
- `stability` reuses V31 pure statistics helpers (no V31 result files): paired
  user metrics, macro-fold contributions, descriptive within-fold bootstrap
  20,000 draws/seed12/quantiles.025,.975, and evaluation-row exclusions. It is not
  selection-adjusted and ignores training-fold dependence. Not independent
  generalization or significance evidence. No raw IDs/item histories exported.

## Stored model: five fold states, NOT an ensemble or full305-user refit

`pack_state(c,m,b,candidates)` retains only fixed Q/item IDs/vocabulary/IDF/
features/popularity/token order; user P/mapping/ratings omitted. `save_bank` writes
all five already-trained states plus globally selected policy to best_model.npz.
MF fits remain exactly5. No extra final training is hidden in serialization.

`load_model(path,fold=1)` loads one stored state; fold1 default was fixed before
results, NOT picked for high accuracy. For reproducing CV, use each user's
original evaluation fold. Evaluating on another fold could include that user's
ratings in training and is forbidden. Never combine or select fold scores per
user. There is no ensemble or full305-user deployment model in this archive.

Example inference from the selected stored policy, using SYNTHETIC input only:

```python
from experiments.scent_v2.background_data_recovery.core import load_model, predict
c, m, b, meta = load_model('outputs/scent_v2/background_data_recovery/best_model.npz', fold=1)
ids = sorted(c.vectors)
support = list(zip(ids[:5], [.9, .1, .7, .3, .5]))
top_ids, scores = predict(meta['policy'], support, ids, c, m, b)
```

All five folds and BOTH A/B policies must roundtrip exactly (IDs/order/scores).
Existing service is not connected or changed. Full305-user refit is not performed.

`guard()` allows only original Train/catalog/candidates, V25 split metadata and
V30 aggregate reference/proof. Denies all V24/V31 output/private-label/model reads,
other old outputs, network/process actions and writes outside V32 output.
Pre/post SHA256 checks protect Frozen19, manifest, data, V30 and service sources.
No third-party implementation copied; all reuse is from local modules above.
