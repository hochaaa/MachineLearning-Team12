# STEP6: fixed V2 Hybrid failure diagnosis

No STEP5/V1 implementation, config, weights, split, website, report or result is edited. No new model is selected. No legacy validation answers/predictions or internal/external Test files are read. Only prior aggregate metrics and train-internal reconstructions are used. Work requires `development-v2` and unchanged frozen19/manifest.

## Commands actually executed

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B experiments/development_v2/diagnostics/failure_diagnosis.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B experiments/development_v2/diagnostics/ridge_stability.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v2/diagnostics/test_diagnostics.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v2/diagnostics/write_diagnosis_report.py
```

The fixed diagnostic is already complete. Outputs are under ignored `outputs/development_v2/diagnostics/hybrid_failure_step6/`; scripts refuse to overwrite their existing primary output. Do not delete receipts or rerun to explore alternative settings. The report is `reports/V2_HYBRID_FAILURE_DIAGNOSIS.md`.

## Reconstruction, not optimization

STEP5 did not preserve CV score arrays or fold models. For known-user CV, original V1 uses160epochs and selected V2 uses20epochs from saved fold receipts. New-user CV exactly replays the old deterministic nested stopping because original fold weights/epochs were not saved; it recovers30/20/30epochs. Hybrid NDCG matches all12 STEP5 V1/V2 fold entries within1e-12. Ridge stability then uses these recovered fixed epochs with early=False. No new hyperparameter value, seed, or architecture is searched.

Both original algorithms and their score arrays are unchanged imports. A 2×2 fixed diagnostic applies Linear/RRF at alpha_content=.25 to V1 or V2 components. Counterfactual outputs are explanatory controls, **not new chosen/saved/deployed models**. New-user fold-in regularization stays V1 .01/V2 1.0. Only original train can construct support/heldout; complete held users stay outside factor learning.

## Definitions and parameters

- `avg_rank(values)` computes average-tie ranks for Spearman. Production RRF instead uses ID-resolved ordinal ranks. `spearman(c,m)` uses jointly finite scores, returns None for constant/undefined vectors.
- `rank_scores` is reused unchanged: `61/(60+rank)`. Fusion is .25Content+.75MF rank contribution; no answer-derived normalization.
- `score_stats(v)` reports finite count, mean/std/min/max, clip boundary0/1 fraction, `1-unique/finite` duplicate fraction and largest tie group fraction. All arrays are inference scores on unseen current candidates.
- `coverage(pred,pool,catalog)` counts Top10 exposures for **all scored users**, including no-positive users. Pool includes zero exposures for Gini. `top10_item_slot_share` is the share held by ten most frequently exposed products, not component overlap or per-user duplication. Hottest incidence is users receiving that item/requests. Shannon entropy is bits. Intralist diversity is mean `1-Jaccard(tokens)` over Top10 pairs.
- `cluster_bootstrap(differences,users,folds=3,seed=12,draws=3000)` resamples users as paired clusters across all folds; no-positive cells stay missing. Each draw computes fold mean deltas then the unweighted threefold mean, matching the original primary estimand. Intervals are descriptive/post-selection and do not establish generalization significance.
- `snapshot()` hashes protected19, tracked V1 and existing STEP5 source/model/result artifacts. Forbidden raw data and old V1 answer/results are compared by size/mtime only; their contents are not opened. `deny_legacy` enforces this read boundary. New outputs/diagnostic code are excluded from the before/after old-artifact set.
- `save(name,value)` / `table(name,rows)` only write new files in the diagnostic output directory and reject overwriting.
- `ridge_stability.main()` builds original `A=[q,1]`, `G=A.T@A+n*lambda*I`, checks condition number/eigenvalues/residual of `Gz=A.Ty` and fixedQ. Does not score new hypotheses or compare lambda values.
- `metric_parity()` and `test_diagnostics.py` use synthetic data only;10 tests cover formulas/aggregation, ties, Gini/entropy, primary bootstrap estimand, clipping and denied files.
- `write_diagnosis_report.py` reads diagnostic aggregates and writes one new report; no learning/evaluation/selection. Report helper `table(rows,keys)` formats measured values; `number(row,key)` parses floats.

All new algorithmic utilities are original project code. Existing `development_v2` modules and V1 `ranking_metrics/evaluate` are reused, not copied/changed. NumPy2.3.5 supplies arrays/linalg/RNG; stdlib supplies CSV/JSON/pathlib/hashlib/subprocess/unittest. Reference documentation URLs identify dependencies only: https://numpy.org/doc/ and https://docs.python.org/3/library/ . No network or installation performed.

## Privacy and interpretation

No raw user identifiers or rating rows are included in the report. Anonymous request-level diagnostic CSVs and input/source hashes remain private ignored outputs. Product frequency CSV contains public brand/perfume names, not user profiles. Sharing source does not authorize sharing data or artifacts.

Measured item-bias dominance and concentration are not complete causal proof. V2 Content spreads more, solver conditioning is good, clipping is negligible and popularity fallback is0; these findings rule out several simple explanations. Legacy validation failure mechanisms remain partly inconclusive because answers/predictions were intentionally not used. Keep all existing models/settings and wait for user approval before any next experiment or Git operation.
