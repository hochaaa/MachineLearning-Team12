# STEP7: personalization feasibility and V3 design (no training)

Work is on `development-v2`. All original V1/V2 source/config/model/result/report files stay unchanged. Only this directory, ignored step7 outputs, and one new `reports/V3_PERSONALIZATION_FEASIBILITY.md` were created. No V3 recommender implementation, weight fitting, hyperparameter search, legacy validation/test access, website/server control, or Git mutation.

## Executed commands

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 web/backend/.venv/bin/python -B experiments/development_v2/diagnostics/step7/analyze_feasibility.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v2/diagnostics/step7/test_analysis.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v2/diagnostics/step7/write_plan.py
```

`analyze_feasibility.py` and report writer refuse overwriting their own completed primary outputs/report. Do not remove receipts to repeat an experiment. The design was subsequently refined to include6 known-user secondary diagnostic fits, making the proposed—not executed—budget54 primary/66 with optional seed diagnostics. The final report/blueprint is authoritative.

## Inputs and scopes

- Original V1 train330users/538items/1805ratings, original479pool, Fragrantica metadata only.
- Stored full-train V2 model.npz/model.json: numeric arrays loaded with allow_pickle=False and made read-only. No `ServiceV2` loading path is used, because that would rebuild/fill content representations; no `.fit` calls occur here.
- Existing STEP6 anonymous held-userCV summaries and ridge records. Fold Q arrays were not saved, and **STEP7 forbids retraining**. Therefore missing fold-Q statistics and fresh fold predictions remain N/A. Whole-train model sensitivities are explicitly not honest held-user CV.
- V1 protected19/freeze bytes for hash checks; old forbidden data/results are stat-only. No legacy validation/Test ground-truth files are read.

`sys.setprofile(prevent_training)` aborts project `fit/train_mf` calls. The7 synthetic sanity tests include a dummy-call guard test that aborts before execution; it is not model training. Open-event checks deny forbidden legacy input paths. No monkeypatch mutates original model classes.

## Functions and parameter meanings

All new analysis utilities were implemented directly; NumPy/stdlib dependencies are reused, not copied. Reference documentation: https://numpy.org/doc/ and https://docs.python.org/3/library/ (not browsed this step). `failure_diagnosis` supplies original read-only guards/hashes/rank metrics; `foldin_v2` supplies existing frozen-setting ridge inference.

- `save(name,value)` / `table(name,rows)`: write new aggregates only under outputs/development_v2/diagnostics/step7; existing output refusal. `describe(values)` returns population mean/std and quartiles, `histogram(values)` counts observations, `gini(values)` measures nonnegative frequency inequality.
- `deny(event,args)`: open-event allow/deny checks, no legacy validation/Test source allowed. `prevent_training(frame,event,arg)`: block project learning calls. `protected_snapshot()` extends the prior source/model protection to older diagnostic source.
- `data_analysis(train,catalog)`: observed interaction counts, degree/rating distributions, same/near-same users, high>=.7/low<=.3 rates, note/accord coverage, brand diversity, pairwise note/accord Jaccard distance, bipartite connected components and co-observation counts. Outputs only aggregates, never user IDs or original rating rows. Empty profile comparisons are not user satisfaction metrics.
- `load_fixed_model()`: read numeric existing weights with unchanged config/mappings into a read-only namespace. No model fitting/constructor training.
- `model_analysis(model,meta,train,pool,h,items)`: decompose stored known-user scores into item bias and p·q; same-user seen exclusions, bias-only vs full Top10/rank changes, inter-user Jaccard, degree associations, factor norms, final-state gradients. Gradient RMS/absolute bias gradients have different units and are not learning-speed ratios.
- `input_sensitivity(model,meta,pool)`:5 synthetic support-rating scenarios on the same3 public items, fixed original ridge1.0; no heldout/accuracy. Thus input response is not new-user performance evidence.
- `planned_split_counts(train,pool,seed=20261109)`: no factor training; hash-user outer3/inner2 blueprint, assume all observed fit items would receive factors. Require3known support and at least4total candidate interactions, keep unseen-factor heldout labels. Record only feasibility counts/positive denominators, not prediction metrics. New479fixed protocol differs from old fold-restricted candidate pools.
- `write_plan.read(name)` / `mdtable(rows,keys)` / `main()`: read aggregate outputs and format the one new feasibility/design report plus blueprint JSON. The six policies are a proposed future budget, not a runnable model/implemented config search.
- `test_analysis`: synthetic tests of summaries, complete-graph density, stable blueprint counts, forbidden-path/training guard checks. Tests never open validation/Test data.

For arrays: `np.mean/std/quantile` use numeric aggregate values, std ddof0. `np.linalg.norm/svd/solve` describe factor geometry and invoke the original ridge formula only. `spearman` uses average ranks for ties. Namespaces separate user/item graph nodes. Inputs use normalized0–1; explicit website0–10 is divided by10 in the planned inference contract.

## Privacy, reproduction and interpretation

Report contains aggregate statistics only. Weight mappings and anonymous per-request diagnostics remain ignored/private and are not public Git assets. Original raw records are not copied. Snapshot outputs contain paths/hashes, not user histories. The final verification also checks previous STEP6 result and report hashes at finalization.

0.87% is the average across142 stored held-user requests of candidate SD(pq)/SD(item bias); it is not a personal contribution percentage. Full-train known-user figures are a different model/cohort. Smaller latent amplitude can still move ranks. Single synthetic support-item sensitivity is illustrative only. A new split seed over reused train does not create an independent generalization test.

V3 priorities,6candidate policies, stopping/guardrail rules and fit54/66 budget are proposals requiring user approval. Do not start fitting V3, add source to Git, connect the website, or consume legacy validation/Test without a new authorized task.
