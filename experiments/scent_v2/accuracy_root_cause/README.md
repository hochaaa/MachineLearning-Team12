# V2-33 diagnosis-first accuracy experiment

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.accuracy_root_cause.test_diagnostic experiments.scent_v2.accuracy_root_cause.test_models -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.accuracy_root_cause.diagnostic
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.accuracy_root_cause.run
```

Existing run outputs cannot be overwritten. First command trains nothing. The
second fits EXACTLY5 original40-user MF/TF-IDF folds and saves item state and
training-only score references. The third reuses those states, evaluates fixed
policies and checks the selected new policy with existing V32 background models;
no further MF fitting. Do not delete markers/results to automatically retry.

## Reuse and experiment boundary

Original `Content`, `MatrixFactorization`, `Baseline`, `hybrid`, V26 `folds/ridge`,
V25 `developer_data`, V30 `rerank`, V32 item-state serialization/loader, V31 pure
statistics helpers reused unchanged. No third-party implementation copied.
No old V24/V31 final results, reserved25 rating decoding/evaluation, service/Git/
package/network action. Existing background bank hash and source checksum checked.

MF factors4/160epochs/lr.01/L2.01/seed12 unchanged. No actual mapping or Fold-in bug
found, so no fabricated repair/modelA. No bias/BPR/old failed signed profile or
fixed-sigmoid/candidate-percentile search repeated. Current TF-IDF is pooled
note/accord phrases, NOT a free-text description model.

Three policies fixed before diagnostic fits in config.json: original baseline,
structured reranking and conditionally eligible Train-CDF. Weights/cutoffs stay
fixed, no inner or outer hyperparameter grid. The same repeatedly-used developer
fivefolds select the policy, so this is not nested/independent final validation.
The optional background check follows primary selection and cannot change it.

## Methods and parameters

- `stats(values)`: finite numeric n/mean/std and quantiles0/.05/.5/.95/1.
  `group_stats(rows)` reports user/item count, rating value and within-user
  variance/positivity distributions. Global developer summaries are descriptive
  only; no training weights are derived from those cross-fold summaries.
- `component_arrays(support,candidates,c,m,b)`: exact original cold-user Ridge
  from five Support ratings; raw MF, clipped MF, original Content, popularity,
  and H=hybrid(.25). No answer parameter. Original user/item maps verified by
  index bijection and direct known-rating reconstruction.
- `train_reference(rows,candidates,c,m,b)`: at most12 TRAIN users, selected by
  SHA25612:v233:reference:user, each5 available items by12:v233:support:user:item.
  Scores unseen candidate IDs with the original MF and Content. References are
  **model predictions from training users**, not heldout ratings/validation RMSE.
  Same40-user pseudoSupport contexts compare40/295-trained score distributions.
  Fold-in normal-equation residual and exact fallback probes are checked.
- Train RMSE uses real TRAIN P/Q/rating pairs, raw/clipped values; train
  prediction-rating correlation and loss trajectories are recorded. No validation
  RMSE is claimed: there is no extra inner rating split/fit. Q-only background
  archives do not recover their old training-user P.
- `structural_phrases(row)`: actual CSV Top/Middle/Base comma-separated PHRASES
  and mainaccord1..5 only, using existing normalize(). Missing/unknown/nan/none
  omitted; duplicate phrases become sets. Never infer a note stage or brand family.
- `Structured(rows,train_items,candidates)`: learn each channel vocabulary only
  from TRAIN items; transform479 candidates, multi-hot then channel L2 norm.
  Pair similarity is .25cos(Top)+.25cos(Middle)+.25cos(Base)+.25cos(accords).
  Empty channels contribute0 without rescaling weights; completely empty vectors
  remain missing. All candidates have at least accord coverage in observed run.
- `max_signal(support,pool)`: maximum structured similarity to Support>=.7 only.
  No valid positive -> missing. `score('structured',...)` uses original V30
  Hybrid-only Top50 and .20 blend; similarity below.05/missing preserves H.
  This changes note stage representation AND weighting/IDF usage; the experiment
  does not isolate which change caused the observed difference.
- `cdf(values,reference,original)`: empirical mid-CDF (left_count+right_count)/2N
  fitted on TRAIN prediction samples only. Content and RAW MF get their separate
  train references; raw MF avoids clip ties. Constant/empty reference returns
  original bounded component, missing stays missing. No candidate-per-user rank
  fit, fixed sigmoid or held-out calibration. Hybrid alpha.25/fallback unchanged.
- Calibration gate is PER FOLD: train-reference MF clipping>.01 or MF/Content
  std ratio outside[.5,2]. If false, that fold's train_cdf policy is baseline.
  No cross-fold training statistics choose the gate for a different eval fold.
  Observed gates active folds2/3/4 only. This is a preregistered diagnostic rule,
  not an accuracy-selected threshold. No stabilization bug correction is claimed.
- `run.main`: same50 developer users,40train/10evaluation, Support5,479 candidates,
  relevance>=.7, original NDCG/Recall/HitRate@5. Answer access only in harness after
  all fixed policy predictions. No-positive2 users excluded from ranking means.
  Primary criterion is arithmetic mean of5 fold means, then Recall/HitRate;
  strict baseline improvement required. All score arrays shared, MF fits not repeated.
- `stability` (V31 pure helper): paired positive-user counts, weighted contribution,
  evaluation-row exclusion and20,000 paired within-fold bootstrap draws(seed12,
  percentiles.025/.975). Not leave-one-out training. Selection bias and dependence
  between overlapping training folds are not corrected; descriptive uncertainty,
  not formal/generalization significance. Numeric user metrics have no identifiers.
- Optional background scope: reuse V32's295-user fold Q/Content/popularity,
  construct features/reference from that fold's permitted Train, evaluate ONLY
  fixed selected policy and baseline. Never compare295 performance directly to
  40-user performance as equal-scope model superiority. No new background fits.

## Stored inference

`save_states` stores five item-only states plus structured479x479 matrices,
canonical item order, training-reference arrays and per-fold calibration gates.
No P/users/raw ratings. `load_selected(path,fold=1)` restores the compatible
NPZ with allow_pickle=False. Defaultfold1 was fixed BEFORE results, not best-fold
selection. No ensemble or all50/305-user final refit/service deployment is performed.
Use a developer user's original evaluation fold for CV replay; a different fold
may have trained on their ratings and must not be used as an evaluation shortcut.

```python
from experiments.scent_v2.accuracy_root_cause.run import load_selected
from experiments.scent_v2.accuracy_root_cause.model import predict
c,m,b,structure,reference,gate,meta = load_selected('outputs/scent_v2/accuracy_root_cause/best_model.npz',fold=1)
ids = sorted(c.vectors)
support = list(zip(ids[:5],[.9,.1,.7,.3,.5]))  # synthetic, not participant input
print(predict(meta['policy'],support,ids,c,m,b,structure,reference,gate))
```

All five states and all eligible policies roundtrip identical IDs/order/scores.
`access.guard` limits reads to original Train/catalog, permitted development
artifacts; denies old finals/private files and writes outside V33. Frozen19,
manifest,75 original data/model/service/source files checked pre/post. No source
or artifact from an earlier experiment is modified.
