# AGENTS.md — 2026 Machine Learning Term Project (Team 12)

> **Authority:** Professor Ok-Ran Jeong, *Machine Learning Term Project Specification*, Fall 2026, pages 2–9. This file translates the slides into verifiable engineering tasks. **[REQUIRED]** means explicitly stated in the slides; **[RECOMMENDED]** is our quality-control implementation choice; **[UNCONFIRMED]** needs user/professor confirmation. Never present a recommendation as a professor requirement.

## 0. Non-negotiable working rules
1. Read `AGENTS.md`, `PROJECT_DECISIONS.md`, `REQUIREMENTS_TRACEABILITY.md`, and the original professor PDF (if available) before implementation. If PDF absent, do not claim direct PDF verification.
2. Do not invent dataset names, download links, data schemas, metrics, measured results, individual contributions, GitHub URL, experiment outcomes, or citations. Mark unresolved items `TBD` and ask for decisions.
3. **Updated decision gate (v3):** User has selected the perfume domain and proposed Fragrantica + Atrafshan for development, Laure Richis for external testing, Parfumo for auxiliary validation, and Content-Based + Collaborative → Hybrid plus Knowledge-Based recommendation. Do not re-open unrelated domain searches by default. This is **user-proposed, not team-final-approved**. Run Phase 0 and quantitative feasibility/licensing checks first; request team approval and resolution of blocking issues before large-scale domain implementation. Scaffolding, audit scripts, tests, and proposal drafts are allowed.
4. Preserve evidence: reproducible commands, dataset provenance and licenses, split rules, random seeds, environment, logs, plots, tables, and measured results. Never fake experimental evidence.
5. Prevent data leakage: preprocessing/fit only on training data; use a genuinely separate dataset for external testing, not just a random split renamed as another dataset. Document user/item overlap and cold-start limitations.
6. Every deliverable must be auditable against `REQUIREMENTS_TRACEABILITY.md`; do not declare completion without actual evidence and executed checks.
7. Cite third-party copied/adapted code in nearby comments and `REFERENCES.md` (source URL, author if available, access date, license, scope of reuse). Uncited borrowed code is prohibited.
8. Explain all modules/classes/libraries/functions/methods **and their parameters** not taught/used in class, with accessible `METHODS_EXPLAINED.md` entries and useful docstrings. When unsure whether taught, explain it.
9. Source code must contain meaningful comments and error handling; avoid opaque, unexplainable libraries. The team must be able to explain its own algorithms and results.
10. Avoid destructive commands, secrets in Git, unsupported claims of published GitHub links, or commits/pushes without user approval.

## 1. Professor's explicit scope — slides 2–4
- **[REQUIRED, p2]** Build a recommendation system for a specific product/service domain. Examples (not prescribed): movies, music, friends, dating, food, experts, stores/restaurants, clinics/hospitals, targeted marketing.
- **[REQUIRED, p2]** Use **at least two distinct categories** from: (A) memory-based collaborative filtering, (B) model-based collaborative filtering, (C) content-based filtering, (D) hybrid filtering. Slide wording: “Use (2 of 4 of)”. Implement two clearly defensible categories; do not double-count two variants within one category. If choosing hybrid, document its constituent models and justify why it qualifies as a distinct evaluated approach. **[RECOMMENDED]** Independently evaluate at least two base methods and any hybrid, to avoid ambiguous counting.
- **[RECOMMENDED, p2]** Incorporate applicable learned/new ML concepts (e.g. kNN, decision tree, clustering, association rules, vector space model, gradient descent, regularization, loss functions). These are examples/encouragement, not mandatory checkboxes.
- **[REQUIRED, p3]** Use **at least two datasets**: one to build the model, another (or more) to test the model in related domains. Public or self-created datasets permitted. Clearly identify actual distinct source datasets, not only partitions of one file.
- **[OPTIONAL, p4]** Matrix factorization references are hints, not mandated implementation.

## 2. Proposal — slide 5
- **[REQUIRED]** Due **October 23, 2026**. Deliver **Word format (.docx)**.
- **[REQUIRED]** Include (1) objective including application domain, (2) datasets to use, (3) filtering methods to use.
- **[OPTIONAL]** Include planned machine-learning models.
- **[RECOMMENDED]** Add brief dataset source/provenance, dataset roles, testing protocol, feasibility/risks; distinguish additions from required fields.
- Never present an unapproved proposal or placeholder as final.

## 3. Final submission — slides 6–7
- **[REQUIRED]** Due **Monday, November 9, 2026**. Prepare PPT plus source code, Word material, and outputs (plots and code execution results). Slide 7 says “Source Codes & Word” without specifying a standalone Word report's exact structure; **[UNCONFIRMED]** clarify Word artifact expectations with professor. As a safe precaution, prepare an explanatory Word report while keeping this uncertainty explicit.
- **[REQUIRED] PPT: End-to-End Process:** business objective; data exploration including dataset descriptions; data preprocessing; modeling/training; evaluation **and explanation of outcomes even if unsuccessful**.
- **[REQUIRED] PPT: Learning Experience:** difficulties and solutions; what to do differently with more time / on redo; what **each individual** learned (collect authentic first-person inputs, never invent).
- **[REQUIRED] PPT: Teamwork data:** tasks per member and contribution percentage per member; percentages must be team-confirmed. **[RECOMMENDED]** total = 100%.
- **[REQUIRED] PPT: Open-Source SW:** full software architecture description and actual GitHub URL; do not fabricate URL or assert repo is public before verification.
- **[REQUIRED]** Good source-code comments; third-party code citations; explanations of unfamiliar components and parameters; plots and actual execution results.

## 4. Presentation — slide 8
- **[REQUIRED]** November 10 (Tuesday) and 12 (Thursday), 2026; exact team date **[UNCONFIRMED]**.
- **[REQUIRED]** 10-minute presentation + 3-minute Q&A per team. **[RECOMMENDED]** Rehearse with timing, prepare Q&A on dataset distinction, leakage, filtering taxonomy, evaluation, failures, contributions, and references.

## 5. Team — slide 9
- **[SOURCE FACT]** Team 12: 김동은, 박찬민, 이호찬. Do not assume who is leader, responsibilities, or percentages.

## 6. Implementation quality bar (recommendations, not slide requirements)
- Data contracts: document input schema, ratings/interactions/metadata, missingness, duplicates, sparsity, license and access method for each dataset.
- Cross-dataset testing: state whether same users/items exist across datasets. For incompatible domains/IDs, specify a defensible transfer, common-item alignment, content-based generalization, or independently fit representation; **do not** call a fresh model trained on test dataset an external evaluation of the original model. If external test is infeasible, report limitation and request approval of alternate dataset/domain.
- Baselines: popularity and/or random (seeded) baselines as applicable; avoid claiming professor mandated them.
- For ranking: consider Precision@K, Recall@K, NDCG@K, coverage; for explicit ratings: MAE/RMSE. Choose only metrics compatible with actual ground truth and task, and justify. Document candidate universe, negative sampling if any, seen-item exclusion, denominator, and cold-start handling.
- Deterministic preprocessing and experiments with fixed seeds; train/validation/test separation within development dataset plus external test dataset held out for final assessment.
- Make a `src/` package, `tests/`, `configs/`, `scripts/`, `reports/`, `outputs/`, `data/README.md`, `requirements.txt`, `README.md`, `REFERENCES.md`, `METHODS_EXPLAINED.md`, `PROJECT_DECISIONS.md`, `REQUIREMENTS_TRACEABILITY.md`.
- Do not commit private/large datasets without permission. Provide download instructions and hashes where feasible. A command should reproduce figures/tables from real data; tests must pass locally or failure must be documented.
- Use clear figure titles, axis labels, units, data source and dataset role; record failures as honestly as successes.

## 7. Required workflow and checkpoints
**Phase 0 — Inspect:** list repository state, professor PDF, existing files, environment, team decisions. Output a gap report with explicit vs recommended requirements.

**Phase 1 — Perfume feasibility gate (v3):** audit the user-selected four perfume datasets and evaluate true cross-dataset feasibility, rating overlap, sparse interactions, compute/time, explainability, licenses and risks. Do not propose unrelated domains unless this plan is blocked. Request team confirmation and approvals before large-scale implementation.

**Phase 2 — Proposal:** after approval, draft `proposal.docx` satisfying slide 5, verify no placeholders, and provide a requirement crosswalk. User approves before submission.

**Phase 3 — Data:** obtain authorized datasets, record provenance, separate training and external test datasets, inspect and clean without leakage, make exploratory outputs.

**Phase 4 — Models:** implement and explain >=2 filtering categories; train, validate, tune without external-test leakage; add baseline; log configurations and parameters.

**Phase 5 — Evaluation:** run actual evaluation on development holdout and independent external dataset; compare methods and explain strengths, failures, uncertainty, cold-start and distribution shift; save real plots/results.

**Phase 6 — Deliverables:** create slide deck and Word document, include architecture diagram, actual GitHub URL (only once known), documented code, references, outputs, individually verified learning reflections and contribution percentages.

**Phase 7 — Verification:** execute checks; audit every line of traceability; ensure proposal due date, final deadline, presentation length; explicitly list unresolved items and evidence paths.

## 8. Completion response format
Report: (1) completed items with file paths, (2) commands actually run and results, (3) requirement audit PASS/FAIL/BLOCKED with evidence, (4) user decisions needed, (5) next action. Never state full professor compliance while any required item is BLOCKED.

## 8A. Additional professor clarification (reported by student; verify with professor if needed)
- **[PROFESSOR VERBAL CLARIFICATION]** The development and external test datasets need not have identical feature sets. Identify genuinely comparable shared features, harmonize names, units, missing values and category vocabulary, and construct a common feature representation. Fit vocabulary/vectorizer/scaler and tune all hyperparameters on development data only; transform external data without fitting it. Report feature coverage and domain shift.
- **[PROFESSOR VERBAL CLARIFICATION]** Implement **hybrid filtering** and incorporate at least one technique not taught in class. This supersedes the earlier unconstrained choice of two categories. Use a clearly specified hybrid of distinct base recommenders; document and evaluate its components and the combined output, and explain the newly learned method, its parameters, rationale, and evidence. Confirm which techniques were actually taught with team members before claiming a technique is new.
- A hybrid of content-based and collaborative filtering requires actual user-item interactions for the collaborative component. Aggregate product ratings and rating counts are NOT user-item rating records. If only item metadata and aggregate ratings are available, do not fabricate users or label popularity-weighted content similarity as collaborative filtering. A content + popularity/quality reranker may be called hybrid only with a transparent definition and professor approval of its category.
- Do not choose a cross-dataset test protocol until actual feature overlap, entity matching, and evaluation ground truth are checked. If the external dataset has no user-level ground truth, do not claim measured personalized recommendation accuracy; instead define defensible content retrieval/consistency metrics and limitations.


## 9. v3 user-selected perfume design and external-test protocol (2026-10-16)
- **Source of decision:** user-provided project plan, recorded in `PROJECT_DECISIONS.md`; do not confuse with requirements explicitly in professor slides. Read that file as the authoritative *proposed design*.
- **Development:** `fra_cleaned.csv` (Fragrantica, item metadata) + `atrafshan_data.json` (Atrafshan, real user-item ratings). **External:** Laure Richis/Basenotes `perfumes.json`, `reviews.json`, `brand.json`, `notes.json`, `category.json`, `season.json`, `users.json`. **Auxiliary only:** `parfumo_data_clean.csv` for independent metadata consistency checks.
- **Recommendation methods:** Content-Based (notes/accords), Item-Based or similarly defensible CF (individual ratings), normalized weighted Hybrid (validate α only on development validation), plus separate constraint/rule-based Knowledge-Based Recommendation (user-selected fragrance family, season, and price only if available). Evaluate component models independently.
- **Preprocessing:** nested Persian JSON→DataFrame/CSV, rating 0 meaning audit, missingness, brand+name normalization with concentration/version collision checks, Laure numeric FK mapping, TF-IDF/multi-hot, sparse user-item matrix, privacy redaction. Document steps and real statistics.
- **External test counts are NOT known:** the 39,699 Laure perfumes, 6,288 ratings, 2,694 rated perfumes, and 156 users with >=5 reviews are **raw totals**. Compute rated-item intersection, surviving interactions, per-user surviving histories, and support/held-out eligible users before promising evaluation. Catalog-level overlap is not evaluation overlap.
- **Strict holdout:** external *answer/held-out ratings* MUST NEVER be used to fit/tune models, feature transformers, hyperparameters, popularity, user profiles, or recommendation scores. External *support ratings* may be provided only as per-user input for a frozen recommender at evaluation time. Never refit model on all Laure ratings or claim that it evaluates the original Atrafshan model. Document any fold-in method and item coverage.
- **Metrics:** Precision@K/Recall@K/NDCG@K on a clearly specified candidate universe; MAE/RMSE only for meaningful rating predictions. Unknown ratings are not negatives by default. External user IDs do not transfer; CF needs explicit new-user fold-in or must be marked non-evaluable.
- **Licensing:** independently audit dataset repository and original site permissions; never assume a public repository grants re-use or redistribution. Do not upload raw personal user fields.
- **Execution order:** Phase 0 inspect → Phase 1 compute overlap/eligible external test sample and licensing gaps → obtain team confirmation → proposal → preprocess → baselines/base models/hybrid/knowledge-based → internal validation → one-time frozen external test → deliverables.


## 10. Final proposal alignment and 3/4/5 interaction experiment (2026-10-22, v4)
**Source priority:** professor PDF for written requirements; student-reported verbal clarification for additional requirements; the attached FINAL proposal for the promised project design; this document for implementation safeguards. When they conflict, flag the conflict instead of silently rewriting the proposal. The proposal is a planned design, not evidence that dataset counts or evaluation are validated.

1. **Three distinct thresholds, not a range filter:** Compare minimum **3, 4, and 5 valid scent ratings per user** in Atrafshan. Count unique valid user–item interactions *after* checking zero-rating semantics, duplicates and cross-catalog item alignment. Do not confuse total reviews with eligible model interactions. A previously discussed 177 users for the >=5 subset is an unverified user observation, **not** a measured fact to hard-code; older proposal counts (291) are also not ground truth.
2. **Fair comparison:** Freeze the same validation users, validation interactions, candidate universe, relevance rule, seeds, and metric definitions for all three thresholds. Prefer a common >=5 eligible evaluation cohort; in threshold=3/4 training arms, add eligible lower-activity users only to the training pool, without changing the common evaluation labels. The 3/4-only user cohorts may be evaluated separately as *coverage/cold-start* analyses, never mixed into the main head-to-head score. Explicitly report whether each threshold changes the number of usable items, connected components, and ratings.
3. **Split feasibility:** Before running, construct a leakage-free deterministic train/validation/internal-test assignment with sufficient training ratings for each evaluation user. A user with only three ratings cannot automatically supply one train + one validation + one test while retaining sufficient history for stable matrix factorization; if infeasible, restrict their role to additional training data or choose a documented evaluation protocol. Never discard/duplicate labels to force a split. Persist split manifests, user counts, and seed. **Choose the threshold using internal validation only**, never internal test or Basenotes external test.
4. **MF is the core CF model, not item-kNN:** Implement explicit-rating **model-based matrix factorization** trained with gradient descent/SGD and L2 regularization as proposal §3.2. User and item latent vectors and any biases must be trained on development train interactions only; evaluate on held-out interactions. User/item kNN is optional comparison and **cannot silently replace MF**. Keep the actual optimization objective, gradient update, bias treatment, normalization and random seed documented. Use fixed learned item factors for new-user regularized fold-in from external support ratings only; only overlapping **Atrafshan-trained** items have valid MF factors. Distinguish content-catalog matches from MF-factor matches.
5. **Content and hybrid:** Fragrantica notes/accords (TF-IDF and/or multi-hot, cosine), training-only vocabulary/IDF fitting, user preference profiles from known support/train ratings only. Define common score calibration using development train/validation (never external), alpha weighting and fallback when one component cannot score. Report pure content, pure MF, hybrid and baseline metrics separately; hybrid must genuinely combine both when both are available.
6. **Knowledge-based is CORE:** Implement actual hard/soft rules for selected scent families/notes, record exact rule definitions and constraint satisfaction. Season/price must remain disabled unless reliable, legally usable metadata is present in the **development/inference catalog**. Do not source their implementation solely from Basenotes external-test metadata or imply these filters already work. Evaluate rule satisfaction independently from rating prediction.
7. **External testing and frozen evaluation:** After fixing all models, thresholds, mappings, α, candidate sets, positive definitions, metric code and split policy from development data, evaluate Basenotes/Laure **once** as a held-out external assessment. External support ratings can be read only at inference for that user's profile/fold-in. External held-out rating **values and preference labels** are inaccessible to scoring/tuning; item IDs are used only by the evaluation harness to score outputs, not by the recommender. Prevent the evaluation harness from exposing answer items as candidate-only positives. Document external catalog features available at inference separately from rating ground truth. If feature availability or overlap makes a method unevaluable, report N/A/BLOCKED instead of silently changing models.
8. **Metrics:** For top-K ranking use fixed, explicitly described candidate pools, exclusion of known support/train items, relevance threshold chosen on development, Precision@K/Recall@K/NDCG@K and coverage. Unobserved does not mean disliked. For RMSE/MAE ensure rating-scale mapping and explicit predictions; explain that cross-dataset score semantics may differ. Report confidence intervals or per-user spread where practical; do not present unsupported significance claims.
9. **Code quality and provenance:** tests must cover zero-sentinel policy, no test leakage, threshold cohorts, common validation equality, EDT/EDP collisions, FK joins, reproducibility, cold-start fallbacks and external fold-in invariants. Produce real EDA tables, matching audit (accepted/rejected/ambiguous), metrics CSV, plots and error analysis. Keep original data private/unchanged; no GitHub push without permission. All reports must distinguish planned, observed and blocked.
10. **Execution checkpoint:** The user explicitly asks Codex to develop the project, so after inspection/feasibility **proceed autonomously with non-destructive, locally executable development** using available files. Stop and ask only for genuinely blocking missing raw data, legal/permission issues, team-only inputs, or choices with material tradeoffs. Do not hold up ordinary coding behind redundant 'proposal approval' gates; do not invent approvals.
