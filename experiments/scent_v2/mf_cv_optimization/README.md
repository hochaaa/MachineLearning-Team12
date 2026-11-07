# V2-26 user-CV Fold-in experiment

Only50 original V25 developer users. The reserved25 and original255 background users have no decoded labels and no training/evaluation/tuning rows. Per-fold40train/10evaluation; same original Support5/held-out and fixed479-minusSupport/relevance.7. Each fold fits its own MF/IDF/popularity on40 users; all variants share that fold's fixed Q and Content arrays. This differs from V25's895-row background-train single split, so its old.058254 cannot be directly compared to the CV mean.

Existing4-factor SGD/reg.01/lr.01/160epoch/seed12 retained. Variants change only ridge multiplier(.5,1,2) or support-only intercept. Centering solves residual(y−mu) with mu=mean(all5 support), adds mu back before original clip[0,1]. Unknown item/support factor remains missing and original component fallback stays. alpha0 is MF with unchanged missing-component fallback, not strict exclusion of missing items.

Predeclared mean-centered gate prunes its extra lambda variants when worse than V25; actual3 new variants plus3 baselines evaluated,6 MF fits total(5fold+one all50 selected refit). 8factors intentionally not retrained after previous weak result. Select by arithmetic mean of5 positive-user fold NDCGs, ties preferV25. Pooled out-of-fold user metrics are also saved but are not the selection metric. Repeated developer-source/non-nested CV is not independent validation.

```sh
# Pre-fit synthetic tests, no MF fitting.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/mf_cv_optimization/tests -p test_cv.py -v
# Completed run refuses overwrite/repeated fits.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.mf_cv_optimization.run
# Post-run evidence tests, not CV replay.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/mf_cv_optimization/tests -v
# Saved model inference; JSON contains5 {"product_id":"...","rating":7.5}.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.mf_cv_optimization.predict --model outputs/scent_v2/mf_cv_optimization/best_model.npz --support "$LOCAL_SUPPORT_JSON"
```

Saved model refits the CV-highest setting on all50 developers; no accuracy is measured on those same users. It is not deployed. Existing V25 model/artifacts are preserved. Actual best was existingHybrid.25, not new fold-in. No change to existing service/Frozen/data, installs, external research or Git.

APIs/parameters: `developer_cohort(path,candidates)` reuses V25 ID-first parser and returns only developer ratings; `folds(cohort)` hashes users and excludes entire test histories. `ridge(mf,support,scale,center)` uses known Q only and n*reg*scale. `user_scores(spec,support,candidates,content,mf,pop,shared)` takes no answers, clips and combines with fixed alpha. `evaluate_fold` alone reads answers after inference. `save_model(path,...)` excludes P/user mapping and stores selected spec; `load_model` reused from V24 source only, never its output. Tests use synthetic fixtures/temp paths or new aggregates; no past experiment replay.

NumPy/einsum/solve computes explicit ridge, mean/std summarizes fold metrics, SHA256 makes stable identity-only orders, JSON/CSV records results, mock wraps/counts MF fit, audit hook denies old output/model reads and outside-output writes. No added package. Local original code reused from V25 read_identities/digest, original perfume.models/recommend, V2-18 metric harness and V24 NPZ loader. No externally borrowed implementation.
