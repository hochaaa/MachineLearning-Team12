# V2-29 Support-only Content accuracy experiment

No serving-model changes. This is reused developer CV, not an independent test.
No third-party implementation copied; local V2-26 split/Ridge, original Content,
MF and hybrid, and expanded_content evaluation helpers are reused unchanged.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.content_accuracy.test_content -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.content_accuracy.run
```

Runner refuses existing outputs instead of overwriting results. No installation
or data download needed in this existing authorized local environment.

- `config.json`: all12 scoring policies fixed before diagnosis/evaluation: three
  original baselines and three new profiles x alphas1/.5/.25; no adaptive grid.
  MF factors4,epochs160,lr.01,L2.01,seed12 unchanged. Max6 actual MF fits:5 folds
  plus selected artifact refit50. Content fit identically once per fold plus1
  refit. No reserved25 label decoding or V2-24 result reads.
- `profile_scores(kind,support,pool,content,original=None)`: Support exactly5,
  normalized finite[0,1]. Unit TF-IDF vectors from original train-only IDF.
  `rating_weighted` uses sum(2r-1)x, making .5 neutral. Positive-negative uses
  mean(x for r>=.7) minus beta*mean(x for r<=.3), beta=.25/.50; each absent
  group contributes zero. Middle ratings do not affect this second profile.
  These thresholds are fixed normalized-scale definitions, not per-user label
  selection. Each group is computed from Support only.
- Cosine clipped to[0,1], no learned calibration: a negative cosine scores0.
  This preserves the original bounded scale for unchanged MF combination.
  All-equal Support or norm<=1e-12 uses original positive-weighted Content;
  missing vectors remain NaN. Fallback is tested even if unused in real cohort.
- `cache_support(support,candidates,c,m,b)`: one original Content computation,
  one unchanged Support Ridge/clipped MF array, one array per new profile, and
  one popularity array. Sorted479 minus Support. Arrays immutable and shared
  across all alpha comparisons; none receive answers or user IDs.
- `score_cached(spec,x)`: original hybrid bounded weighted blend and component
  fallback. Pure Content (both original/new) never receives MF fallback:
  missing Content -> train popularity only. Pure MF preserves the historical
  alpha0 hybrid's Content fallback when MF is missing, to reproduce its baseline.
- `predict(spec,support,candidates,c,m,b)`: deterministic Top5, Support excluded,
  no duplicate IDs. `rank` from the existing project determines tie order.
- `developer_cohort`/`folds`: exact previous developer checksum and Support split,
  40 train/10 evaluation users x5, eval users' entire histories excluded from fit.
  Source parser skips reserved labels without numeric decoding. Each developer
  is evaluated once; that user's labels are permitted for training other folds.
- `user_metrics`/`summarize`: original binary positive>=.7,NDCG/Recall/HitRate@5.
  No-positive users excluded from ranking averages; mean of5 fold means is the
  selection criterion. Pooled-user results are separate. Positives outside a
  candidate pool would remain in recall/IDCG denominators.
- `run.main`: stores 40-user train counts/479-candidate zero-inclusive rating
  quantiles, train occurrence of held-out positives, valid Support vector ratio,
  baseline Recall@5/10/20/50/100 and aggregate ranking categories. Answers enter
  only evaluation/diagnosis, after score caches. No per-user oracle selection.
  User and positive-item category counts have different denominators. Train-seen
  positive ratio counts user/item positive occurrences, not distinct items across
  folds; per-fold unique counts are also saved. No personal records exported.
- Selection: mean fold NDCG then mean Recall then HitRate; strict improvement
  over original Hybrid required. Ties prefer original/simpler profile, then alpha
  closest .25; stable insertion order is final tie-break. All selected/unchosen
  fold and paired-user gain/loss counts are saved; no significance claim.
- `save_model`/`load_model`: selected policy, vocabulary/IDF, candidate vectors,
  popularity and fixed Q only; no training-user P/mapping/ratings. Token order is
  preserved so float scores and Top5 roundtrip exactly. All50 final refit uses
  no reserved25 labels; synthetic input only verifies inference roundtrip.
- `guard()`: old outputs/models/final data reads denied except original Train,
  candidates and V2-25 split-checksum metadata. Writes restricted to V29 outputs;
  network/process/mutation operations denied. Source/model pre/post hashes are
  checked separately, no Git operations or old experiment reruns.
