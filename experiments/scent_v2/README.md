# V2-0: five-support unseen-user baseline

This isolated experiment retrains the **V1 algorithm settings**, not the Frozen
model, on each of three user-disjoint folds. It never changes the service.
Only the old Train, fixed candidate IDs and Fragrantica catalog are model inputs.
Old validation/internal/external answers and old model/runtime assets are blocked
by the runner's data-access audit hook. Private outputs stay under ignored outputs/.

With the project's existing NumPy environment, from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m unittest discover -s experiments/scent_v2/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m experiments.scent_v2.run
```

Run the tests **before** training. The runner refuses an existing baseline output;
do not delete it to retune or silently rerun. Three SGD fits, no search, are used.
User order SHA256 `12:user:{user}`; support order SHA256
`12:support:{user}:{item}` over in-catalog items. Five support values are normalized
0..1 (equivalent to UI values /10). Remaining observed ratings are answers.

Track A uses 479 IDs minus five seen. Pure MF excludes nonfinite scores; a separate
MF+Content-then-popularity fallback is reported. Hybrid uses original component
fallback. Track B_partial uses fold-trained IDs; B_full5 further conditions on all
five inputs having factors. Answers outside these pools remain Recall/IDCG misses.
Track B users/candidates differ from A; do not compare them as identical settings.

Metrics are positive-user conditional macro means; coverage/concentration include
all cohort users. Top1/top5 concentration are shares of recommendation slots for
the most frequent one/five items; HHI sums squared item slot shares. B coverage/479
is only a reference-catalog proportion, not a common B candidate denominator.
Robustness is variant-then-user macro, includes users without positive answers.
Bootstrap uses 20,000 paired user resamples, seed12; overlapping fold training
means intervals are conditional/descriptive, not independent external evidence.

No borrowed third-party source code is introduced: original project implementations
are imported. NumPy usage and all new module parameters are explained in
METHODS_EXPLAINED.md here. No global documentation or legacy file is changed.
