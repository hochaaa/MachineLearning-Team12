# V2-21 METHODS_EXPLAINED

Local supplement; root methods and protected source unchanged.

## Libraries and design

Reuse V2-14 Store for auth/CSRF, local SQLite locking, transactions and CSV-safe atomic_write. The new root is isolated; participants use inherited fixed roles, while V2-21 evaluation rows are never exported to training. New master tables store stage-specific immutable pre ratings and exposure snapshots. No destructive migration or training API.

secrets.token_urlsafe(32) generates a256bit random deletion bearer code. hashlib.sha256 stores only its digest; high entropy makes a password stretching scheme unnecessary here. It is not an encryption or a data-use authorization. The plaintext is returned once, never in session-state/CSV. sqlite3 BEGIN IMMEDIATE serializes session/rating/deletion operations; secure_delete is enabled by inherited connections. A transaction commits raw deletion then local raw CSV views are invalidated and inherited views regenerated. Disk-I/O failure must be investigated; manual backup copies are outside automatic deletion.

datetime.date parses the actual operator retention_end. Expiry means today>end (last date retained through end of day of local operator clock). Purge runs on startup/request/CLI; no automatic OS timer was installed. Dedicated owner account plus0700/0600 restricts local raw access; not a multi-user identity control or disk encryption.

Comparison sampling uses random.Random with a SHA256 session-specificseed, sample5 without replacement from479−Support5−Top5. Each eligible item inclusion probability is5/469 conditional on those exclusions, not1/469 per exposure or an unconditional model-free effect estimate. Label/score values do not enter the sampler. Source classification is derived server-side from whether a session already exists, not a trusted client flag.

Frozen Engine inherits unchanged standalone recommendation: five normalized support, fixed item factors/ridge, alpha.25/.75, existing content profile and ID tie. No held-out or feedback is an argument. Hash-pin validation verifies runtime5. Original479 and optional497Content are distinct modes; latter unsupported.

HTTPServer binds127.0.0.1; inherited Host/Origin/X-Scent-Request+CSRF/content limits and no request logging. Static client uses textContent for user-provided strings and native form constraints backed by server validation. Strict JSON and preference validation reject booleans, NaN/Inf, range/.5-step violations. Null means unknown/not experienced, not0. csv_safe prevents formula execution in textual exports.

## Function/class inventory and parameters

### app.py

V2-14 HTTP security/parser/styles reused; new loopback app, no existing API changes.

- `Handler(constructor below)`: Reuse host/origin/CSRF/content-type/body limits and no-request-logging policy.
- `Server(constructor below)`: port loopback only; tests inject a separate Store and data root.
- `main()`: Local helper with data roles indicated by argument names and adjacent comments.
- `route(self, method)`: Local helper with data roles indicated by argument names and adjacent comments.
- `__init__(self, port, store)`: Local helper with data roles indicated by argument names and adjacent comments.

### engine.py

Read-only Frozen adapter: receives exactly five Support records, never answers.

- `Engine(constructor below)`: Load verified runtime5; existing recommend math/UI service remain unchanged.
- `concentration(name)`: Only explicit literal catalog tokens; no inferred concentrations or variants.
- `__init__(self)`: Local helper with data roles indicated by argument names and adjacent comments.
- `recommend(self, support)`: support: five canonical(product_id,rating) objects; no response-label input.

### legacy_diagnosis.py

Identity-only diagnosis of original85. No notes/scoring/fitting or retroactive consent.

- `main()`: --csv: authorized existing85 original; emit aggregate identity-review evidence only.

### report.py

Aggregate real-empty store status, protocol and A–P documentation. No model eval.

- `write(name, value)`: Create new finite audit output exclusively; no overwrite of existing studies.
- `main()`: Local helper with data roles indicated by argument names and adjacent comments.

### smoke.py

Temporary fixture-only actual Frozen HTTP/UI verification, never a real response.

- `main()`: Local helper with data roles indicated by argument names and adjacent comments.
- `request(path, data=None, method=None)`: Local helper with data roles indicated by argument names and adjacent comments.

### storage.py

V2-14 auth/SQLite/CSV reused in a NEW directory; immutable V2-21 stage records.

- `policy_ready(policy, fixture=False)`: Actual operator must provide retention/deletion/access; never invent approval.
- `preference(status, value)`: Non-experience MUST have null, not zero. Real experienced zero is valid.
- `EvaluationStore(constructor below)`: root NEW data path; engine Frozen-only; policy actual operator settings or pending.
- `__init__(self, root, engine, policy=None, fixture=False)`: Local helper with data roles indicated by argument names and adjacent comments.
- `register_evaluation(self, consent, version)`: Participant consent plus exact operator-policy snapshot; does not claim rights.
- `identity(self, c, token, csrf=None)`: Authenticate inherited opaque cookie; no direct-identifying fields collected.
- `state(self, token)`: Local helper with data roles indicated by argument names and adjacent comments.
- `save_rating(self, token, csrf, row)`: Exact product identity validation; before/after-source is server-derived, immutable.
- `session_view(self, c, s)`: Own exposure only; support IDs but never held-out values sent to client scorer.
- `recommend(self, token, csrf)`: First immutable session per participant; label-blind5 support, score API only5.
- `feedback(self, token, csrf, sid, pid, status, rating, comparison=False)`: Store post-exposure response; null unknown/never-experienced, never offline labels.
- `_delete_user(self, uid)`: Delete participant-linked raw rows transactionally; rebuild only NEW exports.
- `withdraw_evaluation(self, token, csrf)`: Same-browser withdrawal is also supported; delete code survives cookie loss.
- `delete_by_code(self, code)`: A 256-bit random bearer code authorizes deletion; hash-only lookup, no identity.
- `purge_expired(self, today=None)`: At startup/each request: erase raw rows after their consent retention end.
- `export_evaluation(self)`: CLI-only private CSV snapshots; no HTTP download, no auth secrets exported.
- `analyses(self)`: Counts only for Offline pending; feedback denominators explicit and no trained claim.

### tests/test_evaluation.py

Isolated temporary test-fixture DBs, no real respondents or fake accuracy evidence.

- `FakeEngine(constructor below)`: Local helper with data roles indicated by argument names and adjacent comments.
- `StoreTests(constructor below)`: Local helper with data roles indicated by argument names and adjacent comments.
- `ActualFrozenTests(constructor below)`: Local helper with data roles indicated by argument names and adjacent comments.
- `DeletionPolicyTests(constructor below)`: Local helper with data roles indicated by argument names and adjacent comments.
- `__init__(self)`: Local helper with data roles indicated by argument names and adjacent comments.
- `recommend(self, support)`: Local helper with data roles indicated by argument names and adjacent comments.
- `setUp(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `tearDown(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `rating(self, i, y=7)`: Local helper with data roles indicated by argument names and adjacent comments.
- `session(self)`: Local helper with data roles indicated by argument names and adjacent comments.
- `test01_store_real_zero(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test02_halfstep(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test03_support_insufficient(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test04_heldout_not_in_score(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test05_no_training(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test06_top5(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test07_support_exclusion(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test08_never_experienced_null(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test09_unknown_null(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test10_post_separated(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test11_comparison_sample(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test12_model_versions(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test13_dedup_sessions(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test14_no_direct_identity_fields(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test15_export_csv(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test16_old_db_preserved(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test17_services(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test18_frozen19(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test19_v216to20(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `check_prefix(self, prefixes)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test20_determinism(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test21_unknown_product_no_fuzzy(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test22_concentration_mismatch(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test23_concentration_no_inference(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test24_duplicate_ratings(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test25_pending_policy_blocks_registration(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test26_test_policy_not_real(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test27_no_fake_offline_accuracy(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test28_withdraw(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test29_foreign_session_denied(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test30_support_cannot_be_feedback(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `setUpClass(cls)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test31_actual_load479(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test32_actual_results_parity(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test33_actual_repeat(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test34_reject497(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test35_deletion_hash_only_and_once(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test36_delete_code_cascade_and_csv(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test37_expiration(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test38_invalid_code(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.
- `test39_expired_policy_not_ready(self)`: Test fixture assertion, separate temporary DB; no actual respondents or fits.

### verify.py

Post-run byte checks only; no real respondent creation or recommendation evaluation.

- `digest(path)`: path: local regular file; SHA256 byte identity, not permission certification.
- `main()`: --snapshot actual pre-task hash map; --ratings legacy85 hash only, no alteration.

## Parameter glossary

`root`: new private collector data directory, never old V2-14/legacy data. `engine`: real Frozen service or fixture in tests; `fixture` marks synthetic namespace only. `policy`: confirmed retention/deletion/access values, no manufactured permissions. `token/csrf`: inherited opaque browser authentication and same-session token. `consent/version`: user acknowledgement and V2-21 notice version. `row`: product-specific experience/rating data. `form/concentration`: literal source concentration or explicit unknown. `sid/pid`: own session/product IDs. `status/rating`: experience enum and nullable preference. `comparison`: whether separately recorded nonrecommendation exposure. `uid`: internal random participant, never direct identity. `today`: injectable date for expiry tests only. `code`: raw deletion bearer accepted only for a local deletion request; hash lookup. `support`: exactly five ID/raw-score inputs, no labels. `snapshot`: true pre-task path-hash audit. `ratings/csv`: authorized original85 path for hash/identity diagnosis, never V2-21 retroactive purge. `self/cls`: class/fixture instance.

Feedback analysis response denominator = returned experience statuses; exposure denominator =5×unique participant sessions. Mean preference and positive fraction exclude experienced-but-unrated and unexperienced/unknown. Offline accuracy is not computed without new data and independent membership/training-exclusion evidence. Test-fixture data are not merged into real counters.
