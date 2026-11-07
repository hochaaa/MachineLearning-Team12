# V2-7 functions, parameters, provenance

All new methods are explained for class discussion; course-external status still
needs team confirmation. Local project code reuse is attributed in module headers;
no third-party code copied, no new external source needed.

- `config`: ROOT/HEAD/TRAIN/CANDIDATES/CATALOG plus prior baseline/tuning paths;
  POLICIES identity keys; POLICY freezes objectives, scale/regularization, seed,
  optimization counts, compatibility and adoption gates. No exploration grid.
- `pairwise_data.build_pairs(rows,excluded_users=())`: normalized unique triples,
  rejects evaluation users, returns all strict directed observed pairs and per-user
  counts/distribution. Equal ratings excluded; no gap weight/unobserved items.
- `training.sigmoid(x)`: finite float64 scalar/array logistic with logaddexp; missing
  score stays NaN and is not evaluated, preventing warnings or invented predictions.
- `pair_loss_gradient(p,qi,qj)`: stable softplus(-p·(qi-qj)) and analytic simultaneous
  gradients; no regularization in this single-event helper.
- `objectives(P,Q,ratings,pairs,variant)`: integer-index Train arrays, returns exact
  declared total/rating/pair/reg losses, pair accuracy, fitted-P RMSE and norms.
- `fit(rows,excluded_users,variant)`: independent seed12 initialization, dim4,
  epochs160, lr.01; A global penalty distributed per pair; B original per-rating
  regularization plus beta.1 mean pair contribution via step-scale nR/nPairs.
  P/Q copies ensure simultaneous event update; finite checks every epoch. Q read-only.
- `fold_in.loss_grad_hessian(p,diffs,reg=.01)`: pair differences D; loss sumsoftplus
  plus L2, analytic gradient and positive-definite regularized Hessian.
- `fold_in(mf,support)`: exact5 normalized inputs; A fixed Newton/backtracking,
  B/baseline original Ridge. Returns vector or None, status/iterations/pair count,
  gradient norm/P norm/support reconstruction; Q byte hash checked. A reconstruction
  is diagnostic only because ranking does not identify an absolute rating scale.
- `evaluation.predictions(support,candidates,content,models,pop)`: support-only model
  map. Same C for all arms; pure A raw vs diagnostic sigmoid Hybrid, others clipped;
  original fallback. Scores/distributions and known factor counts per context.
- `evaluate_context(fold,outer,phase,content,models,pop,candidates)`: same folds/users/
  Support/answers; answers read only after all original/perturbed scoring. Shared
  TrackA and baseline-factor TrackB pool; baseline-defined B_full5 cohort.
- `aggregate(accuracy,robust)`: bridge policy into existing summarize, grouping by
  method and user. `user_metric(rows,policy,track,method,key,amplitude=None)` gives
  per-user context means. `comparisons(...,policies=...)` 20k/seed12 paired CIs.
- `compatibility(accuracy,training)`: Inner Support and Train diagnostics only;
  preset B RMSE/clipping/norm guards and A convergence/diagnostic-transform gate.
- `select_inner(accuracy,robust,compat)`: rejects Outer/multiple Outer cohorts,
  applies preregistered accuracy/coverage/concentration/robustness/compatibility.
- `run.main()`: exclusive outputs, Git/hash/access guard, precise new fit profiler
  and persisted start events, original-fit prohibition, independent Train loads,
  Q/mapping verification, locked selection before Outer. Original Test labels never
  read. Nested `load` transforms fixed IDF; `ridge_rmse` checks Train-only new-user
  reconstruction; `train_new` saves new Q/P/mappings and actual loss history.

Reused original SGD gradient corresponds to .5 error²+.5λ(Pu²+Qi²) per event.
Its logged loss uses MSE+λ(global norms)/n and is not identical to that event-weighted
objective. This experiment does not rewrite old loss logs or compare total losses
across different definitions as if directly commensurate.

NumPy: einsum avoids platform BLAS warning path; logaddexp stable softplus;
float64/array/where/clip/isfinite/permutation/default_rng and solve are explicit.
collections groups counts; hashlib SHA256; pathlib/json/csv local artifacts;
sys.addaudithook/setprofile process-local boundary/fit accounting (not OS sandbox);
subprocess only read-only Git before guard. No new package dependency.

- `reporting.read(name)` closes a new CSV; `table(rows,keys)` formats aggregate
  Markdown; `reporting.main()` reads only new experiment results plus original
  Inner splits for posthoc item Train-frequency groups. It creates public stripped
  training diagnostics, user-cluster fold-in summaries, paired user changes and
  descriptive strata (positive count, baseline-known Support, positive item Train
  count). Labels in strata are never scoring/selection inputs. It writes A–P report
  and five authorized presentation docs. No model operations. The original
  training_diagnostics.json includes pseudonymous per-user pair counts and remains
  local/restricted; use training_diagnostics_public.json for nonpersonal summaries.

- `reference_diagnostics.main()`: old Q plus all known Train observations to re-infer Ridge P and report Train observed-pair accuracy. Original SGD P unavailable => explicit N/A; this reference is conditional and not a like-for-like trained-P comparison. No fit or heldout evaluation.

B shares one RNG for rating and pair permutations; extra pair shuffles change subsequent rating epoch order relative to baseline. This scheduling/compute difference is disclosed and never tuned after results; do not attribute changes solely to adding a loss term.
