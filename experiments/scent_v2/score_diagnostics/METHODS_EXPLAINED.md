# V2-2 methods

- `config.POLICY`: three diagnostic lambdas, baseline.01, alpha.25, K5, seed12,
  bootstrap20000, scopes and counterfactual labels; no tuning/selection function.
- `analysis.distribution(values)`: finite min/P1/P5/P25/P50/mean/P75/P95/P99/max
  and population SD, undefined fields None for no finite values.
- `mean_finite(values)`: mean defined values only; no zero filling.
- `ranks_average(x)`: stable sort and average ranks for exactly tied scores.
- `correlation(x,y,spearman=False)`: paired finite Pearson or average-rank Pearson;
  returns coefficient/reason/sample count; constants/insufficient pairs undefined.
- `reconstruct(support,candidates,content,mf,pop,lam)`: unchanged five-support ridge,
  clipped MF and hybrid fallback; no answers/user argument. Returns aligned arrays,
  factor/fallback flags, vector norm and rankings. Actual applied components sum
  to H; nominal .25C/.75M are also retained, but NOT applied to fallback candidates.
- `rank_info(pool,values)`: finite ranking score-desc/ID-asc, 5/6 margin and adjacent
  ties. `user_means(rows,key,condition)` clusters repeated contexts. `scalar_summary`
  separates context mean, user mean and user-mean distribution (utility).
- `run.save_json(name,value)`/`save_csv(name,rows)`: exclusive creation under new
  OUT; mixed-schema CSV union keys, private data never transmitted.
- `guard_install()`: process-local audit hook prevents old test/model reads,
  protected writes and process changes. Only V2-1 INNER artifact inputs allowed.
- `main()`: verifies baseline hashes/Q/train boundaries, restores IDF vectors and
  train counts without any fit, counts/rejects fit calls using sys.setprofile,
  replays six Qs x25users x3lambdas, checks V2-1 parity, records diagnostics,
  then reads local INNER labels for post-hoc success groups. No outer preferences.
- Pooled score distribution concatenates context candidates. Context macro averages
  context distribution summaries. User macro first concatenates that user's two
  context arrays, computes their distribution, then equal-weights75 users.
- Candidate-context statistics are different from distinct item/user counts.
  Correlation averages omit undefined contexts/users and report invalid counts.
- Counterfactual raw-H uses the identical formula/fallback with unclipped M; values
  may exceed[0,1]. Fallback exclusion only changes the pool; retained scores are
  unchanged. Neither virtual policy is evaluated for recommendation accuracy.
- Applied variance identity: Var(H)=Var(Capplied)+Var(Mapplied)+Var(Fallback)+
  2*sum(pairwise covariances). Covariance shares can be negative, not causal effects.
- `bootstrap_delta` is imported unmodified from V2-1: matched per-user contrasts,
  20000 resamples/seed12/percentile95. Only a few prespecified scalar contrasts are
  bootstrapped; exploratory multiple hypotheses are not significance guarantees.
- Success groups use user mean observed INNER NDCG: >0/0/no-positive separately.
  Counts/Support norm/correlation/margins/concentration are descriptive, not tuning.
- NumPy np.savez_compressed stores local arrays; separate private JSON maps rows to
  original candidate IDs. NumPy quantile/std use finite values with stated scopes.

Original project code is imported unchanged; no third-party source is copied.

`supplement.main()` reads only the newly generated V2-2 arrays/metadata, never
old labels or models. It writes two additional exclusive outputs: variance and
score-fraction decomposition restricted to trained/nonfallback candidates, and
an exact fixed-candidate fallback invariance check. This avoids conflating the
zero-filled applied component's all-candidate variance with known-item variation.
It also counts context-level changes of norm/raw means between fixed lambdas.
No model fit, policy change, counterfactual accuracy or selection is performed.
