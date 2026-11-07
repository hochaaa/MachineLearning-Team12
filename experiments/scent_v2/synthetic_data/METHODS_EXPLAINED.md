# V2-10 methods and parameters

Original analysis/generator code; local reuse of perfume.data.fragrantica/tokens and
existing IDF formula. No external code copied. These engineering diagnostics are not
additional professor requirements. No class contribution or novelty claims invented.

- `config`: repository-relative input paths, fixed HEAD, POLICY seed12/cohorts150+850,
  enriched15–20, parameter shrink5/10/20, selection sqrt(count+1), noise histogram.5,
  assumed feature variance6.25% and temperature.25, evidence thresholds and boundaries.
- `boundary.Cursor(text)`: position-based structural reader; `ws` skips whitespace,
  `take(char)` enforces punctuation, `string()` decodes only known key/ID positions,
  `skip()` skips quoted/nested/primitive values WITHOUT numeric decoding, `number()`
  is called only for eligible Train ratings and increments a counter.
- `evaluation_users(text)`: manifests' users fields only, rejects cohort overlap,
  returns excluded IDs in memory +aggregate counts. No support/answer numbers parsed.
- `safe_train(text,excluded)`: normalized triples, check ID before item/rating decode;
  returns safe rows/all ID set for collision checks +aggregate audit, no raw exports.
- `profiling.stats(values)`: finite scalar summary (populationSD/P10/P25/P75/P90/P95).
- `basic(rows,candidates)`: normalized triples; raw=y*10; count/density/duplicates/
  missing/invalid, ratings/activity/item frequency, tendencies. Observed-item density
  and fixed479 candidate density differ. Individual tendency stats stay in memory;
  only aggregated summaries exported.
- `features(rows,catalog,candidates)`: eligible Train-only IDF, original sparse token
  rules, candidate-normalized X; metadata frequency/cooccurrence, observed raw and
  user-centered feature effects. Public means/CI suppressed if<5 distinct users.
  Cluster delta SE uses user aggregate numerator/denominator influence, approximate
  unadjusted normal95%; descriptive association, not causal preference.
- `structure(rows,X,candidates)`: min5 histories, cosine>=.5 vs<=.1 within-user pairs;
  same-user difference bootstrap2000 seed12 requires>=10 paired users and lower>0
  for observed-feature evidence. Split-half and between-user profile cosine only;
  no clustering/count selection. Missing strata=>N/A, not absence of true taste.
- `generator.standard(x)`: center/scale candidate affinity; constant=>zero.
- `estimate(rows,X,vocab,candidates,feature_effect,evidence)`: eligible Train only;
  shrunk mean/noise/item effects, activity/frequency and residual histogram/feature
  frequency parameters. Sorted marginal ratings avoid retaining original row order.
  No real profile/user-ID copying; uncertain personal signal explicitly not estimated.
- `generate(params,X,vocab,candidates,all_real_IDs,seed=12,n_users=1000,matched=150)`:
  new namespace, continuous preferences, different purposes, without-replacement
  exposure; structured/noisy latent then ONE empirical marginal mapping/round.5/clip.
  Future Support5 chosen by IDs/hash only; no existing evaluation modified. Returns
  synthetic ratings/users/audit/mean propensities/latent-top5 sets. These top5 sets
  are generator descriptors, not recommender outputs.
- `quality.js(p,q)`: base2 Jensen–Shannon divergence, zero bins handled explicitly.
- `distribution_difference(a,b,grid)`: same-grid rating/activity JS, empirical histogram
  KS and approximate Wasserstein1 in raw units; no statistical significance claim.
- `validate(ratings,users,candidates,realIDs)`: strict counts/finite/bounds/half-step/
  unique IDs/items/pairs and actual per-user count checks. No real ratings accessed.
- `evaluate(real,ratings,users,audit,X,candidates,realIDs,tops)`: aggregate cohort-wise
  distribution comparison, noise/variance/affinity/latent diversity and known-signal
  linearR² diagnostics. Not recommendation accuracy or a privacy attack guarantee.
- `run.native(value)`: strict NumPy scalar/array conversion without hiding NaN;
  `write_json/write_csv` use exclusive create, `digest_rows` canonical SHA256.
  `main()` checks boundary/HEAD, guards accesses and recommender entry points, profiles,
  generates twice with same seed and checks all outputs, writes new directory only.
- `reporting.read/table`: closed CSV and aggregate Markdown. `chart(path,title,labels,
  series,ylabel,source)` produces labeled standalone grouped-bar SVGs. `main()` adds
  cohort-specific synthetic affinity diagnostics/report/design and five append-only
  docs, no generator adjustment/model activity.
- `SyntheticTests`: canary skip, rating bands/units, seeded generation, namespace,
  distribution metrics and invalid/duplicate handling using toy data only.

NumPy mean/std/quantile/einsum/choice/normal/lognormal/uniform and sort perform explicit
statistics/generation; no new library or opaque model. Counter/defaultdict count
metadata and scopes, json/csv/pathlib artifacts, hashlib reproducibility, html/XML-safe
SVG text. sys audit/profile are local guards (not OS sandbox); subprocess only
read-only Git before guard. All output remains local, no package/network mutation.

- `reproduce.main()`: fresh-process parameter-only replay. Cursor decodes source IDs only and skips all items/ratings, transforms fixed metadata via saved IDF, generates in memory, verifies original canonical and CSV roundtrip hashes. No estimate/refit/output dataset overwrite; one exclusive evidence JSON.
