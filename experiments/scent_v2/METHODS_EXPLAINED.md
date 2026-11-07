# V2-0 methods and parameters

This directory is an isolated baseline, not the pre-existing development_v2/v3.

- `config`: ROOT is inferred from this file, OUT is new output only, POLICY fixes
  seed12, support5, folds3, K5, relevance.7, alpha.25, MF4/160/.01/.01, bootstrap20000.
- `splits.digest(text)`: hashlib SHA256 bytes give stable ordering; never Python hash.
- `splits.build(rows,candidates,seed)`: ID/count eligibility, round-robin hashed
  users, hashed five candidate support, remaining answers. `validate(fold,candidates)`
  rejects train/eval users, duplicate supports, overlap and out-of-catalog inputs.
- `train.fit_fold(rows,evaluation_users,catalog)`: rejects user leakage before fit;
  original Content/SGD MF/Popularity, no saved factors. Q becomes read-only. Training
  objective, updates and n*lambda ridge remain original `src/perfume/models.py`.
- `recommend.rank(pool,scores)`: np.isfinite removes missing scores, score desc/ID asc.
  `score(support,candidates,content,mf,popularity)` accepts normalized support only,
  not user identity or answers; clips raw dot products, invokes exact original
  hybrid fallback, and emits factor/fallback/margin evidence. MF+fallback is labeled.
- `evaluate.metrics(top,answers)`: original binary ranking metrics at5 plus hit flag.
  `aggregate(records)` averages positive-user accuracy and all-user catalog/slot
  evidence. `paired(records,robustness,repetitions,seed)` resamples matched users
  using np.random.default_rng, computes mean deltas and np.quantile(.025,.975).
- `robustness.variants(support,amplitude)`: UI perturbations .5/1, reject out of
  range, no clamp. `compare(before,after)` computes overlap, set/list identity and
  common-item absolute rank movement (None for empty intersection).
  `measure(...)` averages each user's variants; `aggregate(rows)` equal-weights users
  and uses np.quantile(.9) on user replacement rates. No answer values are accepted.
- `run.install_guard()`: sys.addaudithook blocks old private data/model reads,
  writes outside OUT and process mutations. It is process-local, not an OS sandbox.
  `write_json(path,value)`/`write_csv(path,rows)` use exclusive creation. `main()`
  checks HEAD/output collision, exact split counts, counts MF.fit through sys.setprofile,
  performs three independent fits, deletes P before inference, checks Q SHA256,
  and writes all/private evidence. No choices are made from observed results.
- NumPy `solve` solves the four-dimensional ridge linear system; no inverse is
  formed. `clip` bounds dot products. `savez` serializes new Q arrays only; no old
  files are replaced. `Counter` computes recommendation frequency and HHI.
- Tests use unittest and unittest.mock, synthetic metadata and explicit Q arrays;
  no synthetic MF fit is performed. Test parameters exercise 0/1 normalized UI
  boundaries, missing factors, split invariance, metrics and leakage rejection.

`recommend.fold_in(mf,support)` uses np.einsum('ni,nj->ij') for Qs.T Qs and
np.einsum('ni,n->i') for Qs.T y, followed by the unchanged n*lambda ridge solve.
This avoids a finite-input invalid-matmul warning from the host NumPy2.3.5 small
matrix path. It changes no objective, factor, parameter or missing-input rule.
Synthetic parity to the original method is tested at atol1e-12/rtol1e-10;
new inference must pass warnings-as-errors. The first 18 ordinary tests passed
with a warning; the stricter run exposed this portability problem before any fit.

Operational interpretation: 479 is the historical catalog. Refit folds cannot
guarantee all items have factors. Public metadata can be transformed at inference;
IDF vocabulary/statistics and Popularity counts are fitted only on fold Train.
