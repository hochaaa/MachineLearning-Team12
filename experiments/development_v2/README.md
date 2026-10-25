# Development V2 — independent experimental recommender

Frozen V1 is unchanged. Work is allowed only on `development-v2`; this directory never connects to the V1 website. The selected V2 challenger improved train-internal known-user CV but **did not improve reused validation or support-3 new-user CV**. Keep V1 as the website/default model. No independent V2 test-generalization claim is supported.

## Inputs and access rules

Existing Python3.12.14 + NumPy2.3.5 environment; no additional installation used. Only:

- `outputs/validation/train_exclude_3.json`: unchanged V1 train, 330users/538items/1805ratings.
- `outputs/improvement/candidates.json`: unchanged479pool.
- `Term-project-datasets/fra_cleaned.csv`: public-catalog metadata read locally; no new vocabulary fit on labels.
- `outputs/improvement/validation.json`: **only after** CV selection lock, one final comparison.

Do not open legacy test answers/results, raw user reviews, or old split_manifest containing test answers. `data.py` is allowlisted, and `run_experiments.py` installs an open-event deny policy. V1 freeze/protected19 are read for hash verification only; V1 model weights are not restored into the V2 search. Models of the V1 equations are separately fitted on the current permitted train/fold for controls.

## Reproduction and saved outputs

From project root, commands actually used:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B -m unittest discover -s experiments/development_v2/tests -v
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B experiments/development_v2/run_experiments.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B experiments/development_v2/check_runtime.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B experiments/development_v2/recommend_v2.py --demo mixed --condition woody
```

The experiment is already complete. `run_started.json` and the exclusive validation ledger **refuse re-running/overwriting this attempt**. Do not delete receipts to resume tuning. Reproduction requires a separate authorized fresh V2 output location and the original permitted inputs; never overwrite existing V1 artifacts. Default source constants are predeclared in `config.py`; changes after viewing validation need a new approved study, not a continuation of this result.

No results/model are Git-added. `outputs/development_v2/` stays ignored. Reports also remain ignored under the existing policy.

## Model and pipeline

- Content: nine isolated ablations, baseline binary TF-IDF, split accord/note, position channels, neutral/centered profiles. Train-only IDF per fold.
- MF: V1 f4/160 baseline, biased f2/4/8/16 × L2.01/.1. Nested train-only stopping selects epochs, not outer CV/legacy validation.
- Hybrid: top2 content/top2 bias models, linear/minmax/weightedRRF/history rules; only train CV chooses the primary recipe and fixed second challenger.
- New user: whole-user exclusion, exactly3 support, >=1 heldout, only fold-trained factors from original479intersection. Three ridge strengths selected inside this training-only user CV.
- Final selected challenger: neutral profile, accord/note .5/.5; biasedMF f8/lr.01/L2.01, actual full-train30epochs; RRF alpha_content.25, offset60; fold-in lambda1.0.
- Core normalized rating scale is **0..1**. UI0..10 conversion is not silently assumed. `--support` accepts a new JSON array `[[perfume_id,0.9], ...]` of exactly3 distinct allowed IDs. Legacy dataset/answer directories are forbidden as CLI support. Demo values are synthetic, not actual user ratings.

Example other behavioral cases: `--demo high`, `low`, `equal`, `zeros`; conditions `none/woody/floral/rose`. CLI outputs Top5 public perfume IDs/names/scores, model-version marker, condition satisfaction, fallback counters and timing. Scores are not probabilities. Inputs and candidates remain frozen479, filters are metadata hard rules after fusion. No V1 website change or backend/server control occurs.

## Results and interpretation

| Protocol (different cohorts/pools) | V1 Hybrid | V2 Hybrid |
|---|---:|---:|
| known-user train-CV fold-mean NDCG@10 | .033573 | .038087 |
| reused legacy validation | .043185 | .032808 |
| train-only new-user support3 CV | .047663 | .032505 |

Known CV has187users per fold (positive155/154/154), candidate479. New-user CV retains142different held users total (positive133), candidate pools424/423/433. Legacy validation has168users,137positive. These protocols are not interchangeable and no test was evaluated. Bootstrap uncertainty and selection bias prevent significance claims. Reused validation was opened once after locking selection; secondary scored higher than primary there but was **not** substituted.

Canonical evidence: `outputs/development_v2/experiments/{run_started,selection_locked,legacy_validation_started,run_complete}.json`, `metrics/*.csv`, `diagnostics/*.json`, model bundle `models/{model.npz,model.json,content_recipe.json}`. Input/source hashes and run time are recorded. Model metadata contains private pseudonymous mappings and must stay ignored. `model.npz` is numeric only, loaded with allow_pickle=False; content vectors are deterministically rebuilt from the hashed unchanged train metadata/recipe, not external data. No pickle or third-party model service is used.

25 unit tests passed; standalone20 valid scenarios and8 invalid requests passed, factor immutability, input-order/reload parity and rule checks passed. Synthetic behavior is not a user satisfaction study. Memory/latency are local whole-process observations, not production benchmarks.

Three minimal reports: `reports/V2_IMPLEMENTATION_AUDIT.md`, `V2_EXPERIMENT_RESULTS.md`, `V2_FINAL_COMPARISON.md`. New module/class/function parameters and formulas are in local `METHODS_EXPLAINED.md`; V1 root methods/references stay unchanged. New algorithms were implemented directly, no external implementation was copied. Dependencies reuse NumPy/stdlib and original project primitives; documentation URLs are conceptual references, not newly browsed license evidence.
