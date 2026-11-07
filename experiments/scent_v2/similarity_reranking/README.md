# V2-30 Support-aware Similarity Reranking

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.similarity_reranking.test_reranking -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.similarity_reranking.run
```

Existing results are never overwritten: runner fails on an existing output
configuration. No installs, downloads, Git actions, or service changes required.

## Reuse and parameters

Original local `Content`, `MatrixFactorization`, `hybrid`, V26 `ridge`, `folds`,
`developer_cohort`, `rank`, `user_metrics`/`summarize` remain unchanged. V29 signed
profiles are NOT recalculated or rerun; only its compatible NPZ loader and verified
all50 developer item state are reused. No third-party implementation copied.

- `config.json` fixes all13 policies before evaluation: baseline lambda0,
  Max/Top2 x full/top50 x lambda .05/.10/.20. MF factors4/epochs160/lr.01/L2.01/
  seed12 unchanged. No PN: negative Support is sparse and it is lower priority.
- `SimilarityIndex(content,ids)` builds one479x479 cosine matrix for a train-only
  vocabulary/IDF model. Sparse unit vectors become deterministic dense features;
  norms are checked/re-normalized. Zero-feature rows stay missing (NaN). Matrix
  is immutable and reused across all users/lambdas. No ratings/answers in fit.
- `SimilarityIndex.signals(support,pool)` requires5 distinct catalog items with
  normalized finite ratings0..1. At least one valid positive Support>=.7 is
  required; otherwise both signals are missing -> exact original Hybrid.
  Max is the maximum cosine over positive Support only. Top2 takes the two
  highest `rating*cosine` contributions across all feature-valid Support, averages
  them with denominator2 (zero padding if necessary). It never divides by a tiny
  sum of weights, so low similarity is not inflated. Featureless targets stay NaN.
- `cache_support(support,candidates,c,m,b,index)` computes original Content,
  Support-only Ridge MF clipped[0,1], original Hybrid H(alpha.25) and Max/Top2
  arrays once per user; cached arrays are read-only. Support is excluded.
- `rerank(spec,x,k=5)` preserves H where S is missing or below fixed .05. Else
  score=(1-lambda)*H+lambda*S. Both signals/H are already[0,1]; no fitted
  normalization or answer calibration. `full` scores all474 unseen candidates.
  `top50` selects original Hybrid Top50 before applying any similarity, reranks
  strictly within that list, and leaves outsiders' scores/order unchanged. It
  cannot rescue positives beyond original Top50. `k` is output length, not an
  oracle selector. Deterministic rank ties use ascending original item ID.
- `predict(spec,support,candidates,c,m,b,index=None)` returns `(Top IDs,scores)`.
  Pass a cached SimilarityIndex for repeated requests. No user history/held-out
  argument. `spec` is saved in NPZ metadata, including signal/mode/lambda.
- `run.main` uses exact developer50 checksum, 40train/10evaluation per fold,
  Support5 and relevance>=.7. Evaluated users' entire histories excluded from
  their fold fit. Each MF/TF-IDF fit once per fold (5 each). Only5 cosine matrices
  and50 Support caches for all13 policies. No reserved25 labels decoded. Unknown
  ratings are not negative labels. The V24 result directory is denied by guard.
- Model selection: mean of5 positive-user fold NDCG means, then mean Recall,
  then mean HitRate; strict improvement over Hybrid needed. Ties prefer smaller
  lambda/top50/Max. Pooled-user metrics are separate. No-positive users omitted
  from ranking averages, included in exposure counts. The same development
  cohort has been repeatedly used; this is not independent final validation.
- `paired_summary(recs,base)` and baseline-Top50 answer subgroups are evaluation
  diagnostics only. They report gains/losses without personal IDs, never choose
  a per-user policy. Positive-user Top50 subgroup and Top50-only subgroup differ.
- `save_model(path,c,m,b,candidates,spec)` stores selected policy, item Q,
  vocabulary/IDF/candidate vectors/popularity, preserving vector token order for
  exact floating-point roundtrip. `load_model(path)` reuses V29's item-only loader
  with allow_pickle=False, not a refit. No P/users/ratings exported. Full config
  is embedded in metadata; keep matching V30 source/config for reproduction.
- The final50-user artifact is reused from V29 ONLY AFTER V30 selection, with
  matching source checksum, exact MF config, verified SHA256 and reserved-user
  exclusion evidence. It is never used for any CV scoring (that would leak).
  No additional final fit or serving-model replacement occurs.
- `guard()` permits only original Train/candidates/catalog, V25 split checksum
  and V29 final-artifact provenance. Other old result/model reads, writes outside
  V30 output, network and process actions denied. New code and outputs stay in
  their own directories. Frozen19+manifest and input/model hashes checked pre/post.
