# V2-1 functions and parameters

- `config`: LAMBDAS fixes three inference values; TRAIN_REG=.01 is separate.
  POLICY fixes all settings, six-fit limit and selection gates before execution.
- `evaluate.view(mf,fold_lambda)`: types.SimpleNamespace shares Q/items/factors;
  only the view.reg is the inference lambda. Underlying mf.reg and Q do not change.
  Existing V2-0 fold_in uses explicit np.einsum Gram/RHS sums and np.linalg.solve.
- `summarize(accuracy,robust)`: imports unchanged V2-0 aggregates, groups lambda,
  averages repeated user contexts before accuracy/robustness. Catalog concentration
  uses all recommendation slots; users and contexts have separate counts.
- `bootstrap_delta(left,right,repetitions=20000,seed=12)`: dictionaries indexed by
  matching private user key; paired mean differences, default_rng resampling,
  percentile95 interval and negative/equal/positive user counts.
- `metric_map(rows,lam,track,method,key,amplitude=None)`: extracts mean per-user
  NDCG/Recall or perturbation metrics, clustering repeated inner contexts.
- `comparisons(accuracy,robust)`: contrasts .1-.01/1-.01/1-.1 for MF/MF+fallback/
  Hybrid, both tracks and full-five subset. Uses only supplied phase records.
- `select_inner(accuracy,robust)`: rejects non-inner/multiple-outer records,
  applies the predeclared gates to Track A Hybrid only. Returns lambda, gate
  evidence and reason; accepts no outer performance argument.
- `run.make_inner(outer,candidates)`: uses only outer.train, hash-order eligibility,
  alternating two user folds and original support rule. No outer answer access.
- `evaluate_context(fold,outer_id,phase,lam,content,mf,pop,candidates)`: shared-Q
  view, unchanged five-support scoring then perturbations, then metric answers.
  Returns private per-context accuracy, robustness and support/clipping/margins.
- `main()`: checks baseline hashes, guards data access/writes, writes policy,
  counts original MF.fit calls via sys.setprofile (limit6), saves inner evidence,
  locks all choices before allowing V2-0 outer data, verifies and reuses outer Q,
  checks .01 prediction/robustness parity, writes new-only evidence. JSON/CSV
  writers use exclusive creation. Guard is process-local, not an OS sandbox.
- Tests: unittest synthetic fixed Q/no SGD; explicit ridge, n=known, no known
  support fallback, boundary ratings, same-Q views, unchanged Content, inner user
  boundaries, deterministic identities, selection rejection/acceptance and hashes.

Repeated inner contexts are a statistical dependency, not independent samples.
No old Test is reused; outer results cannot change the locked selection. This
experiment does not claim a lambda improvement without held-out corroboration.
