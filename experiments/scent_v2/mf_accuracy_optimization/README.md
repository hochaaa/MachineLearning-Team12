# V2-25 MF accuracy optimization

Reuses original MF/Content/fold-in/clipping/fallback and V2-24 model serialization loader. No UI/service/Frozen/data edits, network, installs or Git actions. Only the developer cohort is reused; **every V2-24 output file** is denied during the run. Original Train records are scanned for ID/item first; reserved25-user rating tokens are skipped before numeric decoding/validation. Their labels are never reconstructed or scored.

Same developer conditions: train255users/895ratings, development50users/250Support/409held-out, candidate479-minusSupport, relevance≥.7; accuracy mean over48positive users, coverage over50. Train-only IDF fitted once. Same C/MF arrays shared read-only for all alphas. No score normalization or posthoc calibration. alpha0 preserves original missing-component fallback, not strict pure-MF exclusion.

Predeclared5 MF fits:4factors with reg.005/.01/.02,8/16factors with reg.01; lr.01/epochs160/seed12. Baseline config gets6 alphas; others probe0/.25 and only promising developer endpoints get interior weights. Actual18 comparisons. Highest developer NDCG selected; ties favor original MF, then alpha closest.25 and smaller/simple settings. Independent evaluation NOT_EVALUATED because the only prior final has already been opened and is forbidden here.

```sh
# Pre-fit tests only (no MF fits).
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/mf_accuracy_optimization/tests -p test_mf.py -v
# One limited training/search run; completed output refuses overwrite/refit.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.mf_accuracy_optimization.run
# Post-run tests from V25 outputs, no final evaluation replay.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/mf_accuracy_optimization/tests -v
# Saved model inference; JSON contains5 {"product_id":"...","rating":7.5} records.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.mf_accuracy_optimization.predict --model outputs/scent_v2/mf_accuracy_optimization/best_model.npz --support "$LOCAL_SUPPORT_JSON"
```

Existing local Python and private original inputs required; no packages installed or public data bundle generated. best_model is trained on895 nondeveloper/nonreserved rows and is a developer-selected experiment artifact, not a deployed full-data replacement. Contains only item factors/IDF/features/popularity/settings, no P/user mappings/history. Outputs are private and not for Git upload.

APIs: `read_identities(path)` returns opaque tokens; `developer_data(path,candidates)` decodes retained labels only. `cache_scores(cohort,candidates,content,mf,pop)` computes shared clipped MF/cosine once per fit; `measure(alpha,cache,cohort,candidates)` uses original hybrid+ranking+metric. `tie_key(index,alpha)` is fixed selection priority. `save_model(content,mf,pop,candidates,selection)` creates an exclusive NPZ; existing V24 `load_model` reconstructs objects without reading any V24 output. `guard()` uses process-local Python audit hooks, not OS sandbox. Test fixture labels/arrays never merge into actual training.

Libraries are existing NumPy, JSON/CSV, hashlib, pathlib, math, unittest/mock. The ID-first JSON parser is a project-original implementation for the fixed array-of-triples source schema, not a third-party parser. Algorithm code reused from `src/perfume/models.py`, `experiments/scent_v2/recommend.py`, `accuracy_optimization/core.py` and `expanded_content/evaluation.py`; no external code borrowed. Bootstrap uses paired48developer users20000times/seed12, unadjusted exploratory interval after selection, not independent significance.
