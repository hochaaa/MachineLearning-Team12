# V2-28 BPR (local experimental model)

Run from project root, using the existing environment; no installation required:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.bpr_ranking.test_bpr -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.bpr_ranking.run
```

The runner exclusively creates outputs and refuses an existing configuration: do
not overwrite/rerun the completed run. No serving code changes are made.

## Implementation and parameters

- `config.json`: policy fixed before actual training. Four factors, 160 epochs,
  learning rate .01, global L2 .01, seed12. BPR alphas0/.1/.25/.5 share identical
  fold models and scores. One additional 8-factor configuration only if initial
  mean developer NDCG beats the baseline. Maximum17 real-data fits, including
  baseline and final refits. Synthetic tiny fits are separate from this count.
- `model.fit(rows, excluded_users, factors, epochs, learning_rate,
  regularization, seed)`: local observed-pair builder reused from
  `experiments/scent_v2/pairwise_mf/pairwise_data.py`. Only strictly unequal,
  observed ratings form pairs. Equal ratings are omitted; unknown ratings are
  never negative labels. All pair-participating item/user factors initialized
  uniformly [0,.2] with NumPy Generator. No pair means no usable BPR factor.
- `model.step(P,Q,scale,u,i,j,lr,reg,n_pairs)`: gradients use copied pre-update
  vectors. Lazy scalar decay exactly implements global L2 shrinkage per step
  `1-2*lr*reg/n_pairs`. Sum-logistic pair loss and global L2 are logged every20
  epochs; fixed160 epochs are not chosen using held-out labels.
- `pairwise_mf.fold_in.fold_in(model,support)` is reused unchanged: fixed Q,
  exactly5 distinct Support ratings, zero initial vector, convex pair logistic
  loss + .01*||p||², Newton max50, tolerance1e-8, damping1e-10, Armijo1e-4,
  backtracking max20 with step multiplier .5. Missing known unequal pairs,
  optimization failure or zero vector returns None; it never samples a vector.
- `model.scores(model,support,pool)`: sigmoid of centered raw BPR scores. Center
  is the mean prediction on known Support only. Temperature is RMS of the
  learned TRAIN pair margins, lower bounded1e-6. This bounded ranking score is
  not a calibrated rating or probability of liking. No held-out or candidate
  statistics are used to fit the transform.
- `run.bpr_top(alpha,support,candidates,c,m,b,legacy,shared)`: uses the original
  hybrid component fallback for items lacking BPR factors. If the user's entire
  pairwise Fold-in fails, uses the original Hybrid alpha.25. Thus “Pure BPR”
  means alpha0 where BPR is available, with explicit missing-data fallbacks.
  Sorted candidate479 minus Support; original deterministic rank, Top5.
- `developer_cohort`, `folds`, `user_scores`: reuse V2-26's exact developer50,
  Support5/held-out assignment and user-disjoint40/10 folds. No reserved25 rating
  token decoding. TF-IDF, popularity and item factors fitted on each40-user
  training fold only. The old frozen artifact is not used for scoring evaluation
  users, since it could contain their interactions; its algorithm is refitted.
- `user_metrics`/`summarize`: reuse existing relevance >=.7, binary NDCG@5,
  Recall@5, Hit Rate@5. No-positive users excluded from ranking metric means.
  Model selection uses arithmetic mean of5 fold means, then Recall/HitRate.
  Positives outside candidate479 remain in recall/IDCG denominators as before.
  Pooled-user metrics are reported separately, not used to change this criterion.
- `run.guard()`: denies old result/model reads outside the original training
  source, fixed candidates and V2-25 split checksum; rejects network/process
  actions and writes outside this run's output directory. Reserved identities
  are parsed to enforce exclusion but their ratings are never decoded.
- `save_model`/`load_model`: NPZ contains item factors, feature vocabulary/IDF,
  vectors, popularity and policy; no user factors, mappings or raw ratings.
  BPR selection would additionally embed a training-only legacy fallback model.
  Final refit uses all50 developers, never the reserved25. It is not evaluated
  on its own training labels or deployed into the existing service.

No third-party implementation was copied; reuse is from the existing local
project modules named above. Repeated developer CV is not independent final
validation. Selection among these candidates can overfit this small cohort.
