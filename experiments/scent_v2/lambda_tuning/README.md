# V2-1: fold-in lambda only

New code/results only; Frozen V1 and existing V2-0 are read-only. No installs,
web changes, Git operations or historical validation/internal/external answers.

Run from repository root in the existing NumPy environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m unittest discover -s experiments/scent_v2/lambda_tuning/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -W error -m experiments.scent_v2.lambda_tuning.run
```

The output directory must not exist. Run tests before six new SGD fits. Do not
delete an existing output to retry/tune silently. Training L2 remains .01; only
inference lambda (.01/.1/1) differs. Each inner Q is shared by identity across all
three values; fixed V2-0 scoring/perturbations/fallback/metrics are imported.

Inner two-fold users are original hash-ordered eligible users excluding outer
users, alternating into two groups. Support is the original five hash-selected
candidate items. No preference-dependent eligibility. Q training excludes both
outer and inner evaluation users. All three outer selections are locked before
V2-0 outer artifact data can be parsed by the runner. Then outer train/config/Q
hashes and baseline predictions/robustness are checked and saved Qs reused.

Selection was declared BEFORE fits in config.py: Track A Hybrid paired NDCG gain
must have lower95>0; average replacement and user P90 at both amplitudes cannot
increase, first retention cannot decrease, top-five concentration cannot increase.
No candidate passing every gate means .01. Among passing candidates choose the
highest NDCG, tie1e-12 smaller lambda. These conservative zero-loss gates are a
project policy, not industry standards. Recall and diagnostics are reported.

Track B is diagnostic, including full-five factor-covered users separately.
Missing/unscorable positives stay misses. Accuracy averages positive users;
robustness/coverage include all users. Pooled inner contexts repeat users across
outer training sets: average within user before statistics; never call contexts
independent users. Bootstrap20000/seed12, descriptive conditional intervals;
no multiplicity correction, not external validation.

All new unfamiliar functions/parameters are explained in METHODS_EXPLAINED.md.
Original project functions are imported, no third-party implementation is copied.
