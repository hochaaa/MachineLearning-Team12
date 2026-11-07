# V2-34 — fixed Structured model generalization readiness

Current result: **GENERALIZATION_NOT_EVALUATED**. No eligible independent new
users exist in current collection stores. Synthetic test metrics are never real
accuracy. Existing Hybrid service remains unchanged.

## Completed preparation

- Fixed V33 original MF/Content/Ridge/Hybrid.25/.75; Top/Middle/Base/accord multi-hot
  channel cosine weights.25 each; positive Support>=.7, Max, weight.20, Hybrid-only
  Top50, weak signal<.05/missing fallback unchanged. Policies/source/model SHA256
  bound in locked_policy.json; no tuning or alternative model selection.
- Audited background255/895, developer50/659 and historical reserved25 as separate
  groups. Reserved25 were already evaluated in V24/V31; their numeric ratings are
  skipped here and no new evaluation is run. Namespaced IDs alone cannot prove
  that actual people differ across source datasets.
- V14/V21/V22/V23 actual collection SQLite/CSV rows are empty. Merged/training-ready
  exports have only historical330 identities, not new participants. Legacy12/85
  is historically audited, has0 exact479 matches, and remains unchanged. No
  retroactive new-consent/deletion-code requirement is applied to that old data.
- One shared model fit on permitted background255+developer50 =305users/1554
  ratings. The same Q/IDF/Content/popularity state serves BOTH algorithms. Reserved25
  and future evaluation people excluded. V33 CV train40 per fold differs from
  preparation train305; do not attach V33 CV accuracy to this new fit.
- `prepared_shared_model.npz` is a separate prepared state, not the old fivefold
  CV bank and not deployed. Actual model fit1, Content fit1. Exact restore of
  both algorithms' synthetic-input IDs/order/scores verified. No existing
  service/model/data/collection DB is changed.

Preparation commands actually used (completed outputs cannot be overwritten):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest experiments.scent_v2.structured_generalization.test_pipeline -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.structured_generalization.prepare
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.structured_generalization.audit_exports
```

## Future real data: minimum conditions

Technical eligibility: each genuinely new participant needs **at least6 distinct
exact canonical479 perfume ratings**:5 Support and>=1 heldout. All must be actual
experiences, collected BEFORE showing recommendation results. Do not substitute
recommendation feedback or fabricated likes. No positive heldout requirement
is used to recruit/select participants; users with no positive answer are omitted
from conditional ranking means and explicitly counted.

For a more informative study,30–50 new participants and10+ experienced ratings
per person are recommendations, not professor requirements or a power guarantee.
One eligible participant can run the tool but does not establish population
improvement; tiny-sample bootstrap intervals can be uninformative.

Use the existing collection schema and raw scale:

```text
user_id,perfume_id,rating
```

- Anonymous stable globally unique IDs; no email/name/phone needed.
- perfume_id must be an exact existing catalog URL, including correct product/
  concentration. Existing input template is HEADER ONLY, not fake participant data.
- rating is raw0..10 in .5 steps, normalized by/10. Genuine new-user0 is valid.
  Do not supply normalized0..1 as if it were raw0..10. Unknown experience is not0.
- Unknown products are counted as outside479 and excluded by ID-only rule, never
  fuzzy-matched. Duplicate user/item, historical ID overlap, bad scale, missing
  required columns and explicit post-recommendation sources fail closed.
- Canonical V14 CSV is directly supported. For V21 exports, verify source is
  pre_recommendation_rating and explicitly rename product_id to perfume_id without
  changing identity/value; post-exposure feedback/comparisons are not offline labels.
- Existing anonymous namespaced IDs cannot rule out the same person under a new
  alias. The data operator must verify new people/provenance; the tool never
  fabricates that verification.

Fill `provenance_template.json` ONLY with verified facts for the new dataset:
real people, no prior model selection use, pre-recommendation ratings, distinct
historical people and consent for this local evaluation. Defaults are FALSE and
are not a permission/consent approval. Provide the actual source namespace.
Keep actual raw responses/provenance private; do not upload them to Git.

## One-time evaluation (no training or tuning)

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.structured_generalization.evaluate --csv /path/to/new_ratings.csv --provenance /path/to/verified_provenance.json --run-id new_cohort_01
```

Run from the project root using the existing environment; no installation needed.
Canonical ID list can be obtained locally from `load_selected(...)[0].vectors`.
No real evaluation has been executed by this command during current preparation;
only `--help` and temporary synthetic functional tests were run.

Output is a NEW directory:
`outputs/scent_v2/structured_generalization/evaluations/new_cohort_01/`.
The root NOT_EVALUATED files preserve this preparation snapshot; actual future
comparison is in that new run's evaluation_results.json/model_comparison.csv.

The tool freezes eligibility and Support selection by IDs before label decoding,
reuses existing `real_user_dataset.support_split` hash(seed12), decodes5 Support,
produces all users' baseline/Structured predictions, and only THEN decodes answers.
Both models share the same prepared state/Support/heldout/candidate universe.
Historical330 IDs and legacy12 IDs are excluded. One-time markers contain only
participant hashes and block repeat evaluation even under a different CSV/run name.
Do not delete markers to retry or tune; use one local operator/run at a time.

NDCG/Recall/HitRate@5 reuse existing evaluation functions and binary relevance>=.7.
Positive-heldout users are the accuracy denominator; all users count for exposure.
Reported paired changes/20,000-draw bootstrap(seed12) and user-exclusion effects
are fixed-model diagnostics, not tuning. No-positive cohorts have unmeasurable
ranking accuracy. Input with no eligible users produces NOT_EVALUATED, not zeros.
Fixture mode exists only as a Python unit-test mechanism, not a CLI switch; its
metrics stay in temporary files explicitly marked SYNTHETIC_FUNCTIONAL_TEST_ONLY.

## Methods/parameters and local reuse

`lock_policy()` verifies V33 saved source/config/artifact and records the fixed
policy/source hashes. `verify_lock()` rechecks the canonical policy hash, source,
training source/candidates and prepared artifact hash before evaluation.
`audit_sources(candidates,catalog,known_users)` uses immutable read-only SQLite
counts and aggregate CSV metadata; existing Store objects are never instantiated.
`audit_exports` verifies historical merged exports by IDs, without numeric labels.

`load_csv_identities(path,candidates,forbidden_ids)` returns opaque rating tokens
and ID-only6+ eligibility/Support/heldout; it never selects users by positive labels.
`decode(tokens)` alone converts finite0..10/.5 ratings to[0,1].
`validate_provenance(path)` requires operator-supplied facts, not guessed identity.
`evaluate_csv(csv_path,provenance_path,result_dir,fixture=False,...)` never fits:
exactly two policies, then existing metric/paired bootstrap functions. Actual
person disjointness remains attested rather than inferred from opaque IDs.

`prepare` uses original V25 developer_data (reserved labels skipped), original
MF/Content/Baseline, V33 Structured/predict, V32 item-state packaging and V33 loader.
No algorithm, lambda, channel weights or fallback are changed. `support_split`
was already used for real collection evaluation, not newly tuned on answers.
NPZ stores fixed item factors/features/IDF/structure and no training P/user mapping/
raw ratings. New derived outputs are local; no Git commands or external transfer.
No third-party implementation copied; local source modules are named above.
