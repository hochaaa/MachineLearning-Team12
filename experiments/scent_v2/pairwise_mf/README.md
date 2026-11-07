# V2-7 observed Pairwise MF

New objective experiment; Frozen/service/V2-0–6 untouched. Only observed unequal
rating pairs, all pairs once (no gap weighting/unobserved negative sampling).
Baseline Q/IDF reused; A/B independently initialized from seed12 in each Inner.
No sharing of newly fitted factors across folds. Up to12 Inner +3 selected Outer
real-data fits; actual fit-entry markers persist even on failure. Baseline fits0.
Synthetic training tests are counted separately (6 calls before real run, including
2 in the first failed test run and4 in successful deterministic regression).

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m unittest discover -s experiments/scent_v2/pairwise_mf/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m experiments.scent_v2.pairwise_mf.run
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m experiments.scent_v2.pairwise_mf.reporting
```

Local authorized data and previous artifacts required; not a public runtime bundle.
Existing output directory => STOP; no overwrite/automatic refit. No installs/Git or
server operations. Original final Validation/Internal/External labels inaccessible.

## Fixed objectives and inference

A: sum pair softplus + .01(sumP²+sumQ²). Per-pair simultaneous SGD step .01,
global decay distributed as 2*lr*.01/n_pairs per event. Only pair-participant users
and items obtain factors. Train RMSE for A is an uncalibrated diagnostic, not a
rating objective. Compared with baseline's event-weighted penalty, .01 has a
different effective meaning; update counts differ because pair counts differ.

A new-user inference minimizes sum Support pair softplus+.01*p² with Q fixed;
Newton50, backtracking20, tol1e-8, damping1e-10. Only known-factor Support pairs.
No pairs, optimization failure, zero vector => missing MF, original Hybrid fallback.
Pure A ranks raw. Hybrid A sigmoid(raw) is fixed, uncalibrated and diagnostic-only.
It cannot establish model adoption, even if an exploratory Hybrid metric improves.
This extra eligibility gate is declared before training, not after outcomes.

B: mean(.5 rating error²+.5*.01*(Pu²+Qi²))+.1 mean(pair softplus).
Original rating SGD pass then pair pass scaled .1*n_ratings/n_pairs each epoch;
160 epochs, factors4, seed12, lr.01, no beta/learning-rate search. Ridge fold-in .01
and original clip for pure MF/Hybrid. Event-weighted objective and pass order are
explicit; this is not equal compute or identical regularization to pure A/baseline.

B compatibility: Train ridge RMSE and Support RMSE increase<=.05 normalized;
raw outside[0,1] fraction increase<=.05; P/Q norm<=10x baseline; finite numerics.
These project guardrails are not proof of calibrated probabilities. Baseline Train
ridge reconstruction uses all known Train observations per user, not unavailable
old fitted P; new fitted-P RMSE is reported separately. No answers used in checks.

## Inner selection and interpretation

Per Outer Inner TrackA Hybrid NDCG mean increase and paired95 lower>0; no Coverage
loss, Top1/Top5 concentration increase. Both perturbation amplitudes: mean/P90
replacement increase<=0, first retention decrease<=0 (tol1e-12). Compatibility must
pass. Best accepted NDCG, tie A thenB, none baseline. Lock before Outer access.
Only baseline/selected Outer models evaluated; unselected A/B Outer not fitted.
B candidate pool is original baseline factor-supported pool shared across arms;
missing new factors remain missing, never removed to improve the denominator.

20k user bootstrap seed12, contexts first averaged within user. No-positive users
excluded conditional accuracy but counted for coverage/robustness. Historic Outer
reuse, multiple comparisons, small positive sample, pair imbalance and score-scale
assumptions preclude independent confirmatory claims. Private per-user/factor files
stay local; no data/model redistribution. Next steps require separate design.

Local reuse attribution: V2-0 original rating simultaneous update, ridge/rank/metrics;
V2-1 user-cluster aggregation/bootstrap; V2-4 zero-loss selection architecture.
No third-party implementation copied. See METHODS_EXPLAINED.md.
