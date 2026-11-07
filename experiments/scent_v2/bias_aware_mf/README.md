# V2-27 Bias-aware MF

Actual implementation/adaptation of local `perfume.improvements.BiasedMatrixFactorization` SGD. Factor and bias L2 separated. mu fixed to train mean; optimize squared residual with per-observation L2. Gaussian residual factor initialization0,.05 and seed12. User/item biases are both learned; item Q/bias/mu stay fixed when a new user is folded in.

Joint fold-in: design [Qknown,1], residual r−mu−b_item; regularizer n*diag(factor_L2,...,bias_L2*shrink). Estimate latent vector plus user intercept from exactly5 support only; unknown factors stay missing. Same clip[0,1], candidate exclusions, alpha and missing-component fallback as original. No label-fitted scaler. alpha0 preserves fallback and is not strict MF-only exclusion of missing items.

Same V26 CV:50 developers,5 folds,40train/10eval. Reserved25 and background255 rating tokens are not decoded. Same original Support/heldout/hash/479/relevance/metrics. No V24 output/results/models read. This is repeatedly used developer CV, not independent generalization evidence.

Actual search:5 legacy baseline fits+5 initial bias fits(factors4,latentL2.01,biasL2.01,lr.01,160epochs); support shrink.1/1/10 and alpha0/.1/.25 share those5 fixed bias models. Initial best failed the original Hybrid gate, so extra bias L2.001/.1 and8factors were NOT run. Final selected baseline refit on all50 adds1fit. Actual-data fits11; one tiny synthetic bias fit per unittest process is separate test evidence, not experimental data.

```sh
# Pre-fit focused tests (12), no real-data fits.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/bias_aware_mf/tests -p test_bias.py -v
# Completed experiment refuses overwrite/automatic repeat.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.bias_aware_mf.run
# Post-run saved-evidence tests, no CV replay.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/bias_aware_mf/tests -v
# Local inference; JSON holds5 {"product_id":"...","rating":7.5}.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.bias_aware_mf.predict --model outputs/scent_v2/bias_aware_mf/best_model.npz --support "$LOCAL_SUPPORT_JSON"
```

best_model is the unchanged baseline architecture refit on50 after developer selection because bias MF did not win; no accuracy evaluation on those same final-fit training users. A selected biased model would persist Q/item_bias/train mean only, never training P/user-bias/user-ID maps. Existing Frozen/old artifacts/service unchanged. No installs, network research, Git or UI work.

APIs: `BiasAwareMF(bias_regularization,**legacy_mf_params).fit(rows)` accepts unique normalized training triples. `fold_in(support,bias_shrinkage)` jointly solves factors/user bias; `score_vector(theta,candidates)` adds train mean/item bias and clips, with NaN for unknowns. `freeze_user_state` removes P/bu/user maps and locks item arrays before scoring. `predict(spec,support,candidates,content,mf,pop,shared)` takes no answers. Metric harness reads answers only after prediction. `save_model/load_model` use allow_pickle=False arrays and metadata. Config records the gate and selection before fitting.

NumPy/einsum/solve/random implement explicit SGD and ridge; json/csv/hashlib/pathlib record deterministic evidence; unittest/mock counts real fits and tests interfaces. Python audit hook enforces process-local read/write restrictions, not OS isolation. Local source reuse: original perfume.models Content/legacyMF/Hybrid, V26 user splits and legacy ridge, V2-18 metric harness. No externally borrowed code or new source; all unfamiliar parameters are described here and adjacent docstrings.
