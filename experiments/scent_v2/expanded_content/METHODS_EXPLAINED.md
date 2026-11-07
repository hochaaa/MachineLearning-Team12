# V2-18 methods and parameters

Local supplement; root METHODS_EXPLAINED.md is preserved. No fitting is performed.

## Mathematical conventions

Each note token is `note:` plus existing project normalization. Projection keeps only frozen IDF keys, assigns binary-TF times fixed IDF and L2-normalizes; OOV tokens are dropped. New data never updates vocabulary/IDF. Original item vectors are retained. Profile sums unit vectors with max(0,rating/10) weights; candidate score is cosine. Exactly five unique finite ratings in [0,10] are required; seen items are excluded. Sort is descending score then ascending canonical ID. Zero/unknown profiles are unscorable, not fabricated fallback.

NDCG uses binary relevance at normalized rating≥.7, logarithmic rank discount and ideal DCG from all held-out positives. Precision denominator5, Recall denominator all positives; summarize averages accuracy over positive-answer users, exposure over generated lists. Unknown ratings are not verified dislikes. No new-cohort accuracy is evaluated with fewer than3 eligible users (reporting safeguard, not statistical sufficiency guarantee).

## Module/function API inventory

Parameters below retain code names. `self` is the instance; `cls` is the test class. Test methods take fixtures only and check the stated invariant; they do not fit models.

### `acquire_scento.py`

Download version-pinned public CC-BY metadata only; never transmit local ratings.

- `fetch(url)`: Read-only public HTTPS GET with fixed limits; no credentials, IDs or ratings.
- `main()`: Pin current public commit, check license and source policy BEFORE data download.

### `catalog.py`

Only the independently licensed snapshot supplies new inference metadata.

- `concentration(value)`: Normalize explicit declared form, preserving named variants; no missing inference.
- `licensed_match(brand, name, form, rows)`: Full identity exact match; explicitly named Absolu variant exception only.
- `build(existing_vectors, idf, old_catalog, original_products)`: Return isolated catalog, source mapping and gates; no unlicensed notes loaded.

### `evaluation.py`

Answer harness separated from scoring; no fit, tuning or synthetic ground truth.

- `user_metrics(top, answers)`: Same binary positive>=.7; P denominator5; R/IDCG use all observed positives.
- `summarize(records, universe, new_ids=())`: Positive-user conditional accuracy, ALL-user exposure/coverage/concentration.
- `label_blind_split(history, user, seed=12)`: Require>=6 unique available items; split by ID hashes, not labels/scores.

### `models.py`

Support-only cosine profile, exact original weighting, immutable legacy features.

- `canonical_id(brand, name, concentration)`: Concentration-preserving experiment ID; never replace source or legacy URL IDs.
- `project(tokens, idf)`: Binary TF / frozen IDF / L2, no fit, no synonym or accord inference.
- `ContentExperiment(see constructor)`: Read-only sparse vectors; scoring receives support and catalog candidates only.
- `permission_allows(entry)`: Require a documented LOCAL_RESEARCH approval per source product before use.  The caller/reviewer supplies evidence; this checks completeness, not legal truth. VERIFIED metadata alone or a generic user click is not a usage grant. No new metadata is approved by this source code itself.
- `candidate_gate(row, vector, permission, existing_keys)`: Identity+concentration+notes+nonzero+no duplicate+usage; PARTIAL not auto-excluded.
- `__init__(self, vectors)`: See parameter names and adjacent implementation comments in this module.
- `score(self, support, candidates)`: Exactly five unique finite [0,1] input ratings; never accepts answers.  Same sum(max(0,r)*x)/norm and cosine as original Content.score. Seen input IDs excluded. All-zero/unavailable profile returns NO_USABLE_PROFILE. Unobserved candidates are ranked for retrieval, never labeled negatives.

### `policy.py`

Predeclared V2-18 policy; never revise after viewing new-user answers/results.


### `report.py`

A–O report from executed local artifacts; append presentation evidence only.

- `main()`: Create actual measured report and five append-only sections; never invent accuracy.

### `run.py`

Version-locked Content experiment; no MF/IDF fits and no service mutation.

- `write_json(name, data)`: Create only new local outputs; private cases never contain original user IDs.
- `write_csv(name, rows)`: Nonempty aggregate/model tables; no original user identity columns.
- `density(vectors)`: Actual sparse counts by channel, with no family inference.
- `score_statistics(values)`: Descriptive candidate-score distribution; no fitting/calibration.
- `top_diagnostics(top, vectors, metadata, new_ids)`: Mean pairwise cosine and brand diversity within a generated Top5.
- `main()`: --csv approved local original; all model/feature/search choices are predeclared.

### `tests/test_licensed_run.py`

Post-run source isolation and actual catalog boundary checks; no new scoring data.

- `LicensedTests(see constructor)`: See parameter names and adjacent implementation comments in this module.
- `SourceIsolationTest(see constructor)`: See parameter names and adjacent implementation comments in this module.
- `test_01_unknown_concentration_not_imputed(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_02_edt_edp_not_merged(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_03_explicit_absolu_only(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_04_duplicate_provider_records_not_first_wins(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_05_snapshot_and_license(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_06_actual_candidates_and_legacy_preserved(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_07_no_family_accord_inference(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_08_actual_small_cohort_not_evaluated(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_09_regression_track_A(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_10_split_poisoned_answer_unread_by_scorer(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_11_no_fits_and_actual_input_exclusion(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_12_unlicensed_note_files_are_not_opened_by_catalog_builder(self)`: Synthetic invariant/regression assertion; no external side effects.
- `Poison(see constructor)`: See parameter names and adjacent implementation comments in this module.
- `guarded(path, *args, **kwargs)`: See parameter names and adjacent implementation comments in this module.
- `__float__(self)`: See parameter names and adjacent implementation comments in this module.
- `__lt__(self, other)`: See parameter names and adjacent implementation comments in this module.
- `__ge__(self, other)`: See parameter names and adjacent implementation comments in this module.

### `tests/test_models.py`

Synthetic Content preflight; fixtures are never real rating data.

- `vectors()`: See parameter names and adjacent implementation comments in this module.
- `permission()`: See parameter names and adjacent implementation comments in this module.
- `candidate(**kw)`: See parameter names and adjacent implementation comments in this module.
- `ModelTests(see constructor)`: See parameter names and adjacent implementation comments in this module.
- `test_01_legacy_vector_preservation(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_02_ids_no_collision(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_03_duplicate_gate(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_04_identity_required(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_05_idf_immutable(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_06_original_math_parity(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_07_new_projection(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_08_oov(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_09_zero_excluded(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_10_notes_accords_distinct(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_11_support5(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_12_heldout_not_in_scoring(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_13_split_by_ids(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_14_seen_excluded(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_15_top5(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_16_score_bounds(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_17_determinism(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_18_new_old_exposure(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_19_usage_not_metadata_status(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_20_all_zero_profile(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_21_no_unknown_support_fallback(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_22_invalid_ratings(self)`: Synthetic invariant/regression assertion; no external side effects.
- `test_23_new5_supported_in_expanded_fixture(self)`: Synthetic invariant/regression assertion; no external side effects.

### `verify.py`

Read-only post-run audit; --snapshot is the pre-task path-to-SHA256 JSON.

- `digest(path)`: path: regular local file; return SHA256 without modifying its payload.
- `main()`: See parameter names and adjacent implementation comments in this module.

## Infrastructure parameters

`Path` denotes a local file path. Read-only source manifests supply schema and hashes; output creation uses exclusive mode to avoid overwriting old results. SHA256 detects changed bytes, not correctness or permission. `json` serializes explicit audit artifacts; `csv.DictWriter` writes named columns. `argparse` exposes local paths only. `unittest.mock.patch.object(...fit...)` raises on attempted fits. `statistics` supplies descriptive mean/median/population spread, not significance. Public-source acquisition uses fixed GitHub URLs and a size bound; no private rows are transmitted. Verification uses read-only Git branch/HEAD/status commands.

See policy.py for all fixed choices and REFERENCES.md for attribution.
