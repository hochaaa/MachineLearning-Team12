> 이 문서는 개발 당시의 이력입니다. 현재 프로젝트 소개와 발표 결과는 README.md 및 docs/results/를 참고하세요.

# REQUIREMENTS_TRACEABILITY.md

Legend: **R** explicitly required; **O** optional/encouraged; **Q** unresolved interpretation; **I** recommended implementation. Initial status = OPEN. Update status only with actual file paths and verified evidence.

| ID | Type | Slide | Acceptance criterion | Evidence path | Status |
|---|---|---:|---|---|---|
| R01 | R | 2 | Recommendation system for defined product/service domain | src/perfume/models.py; scripts/demo.py; outputs/demo.json | PASS |
| R02 | R | 2 | At least two distinct filtering categories among memory CF, model CF, content, hybrid | src/perfume/models.py; outputs/validation/metrics.csv (Content, model-based MF, Hybrid) | PASS |
| O01 | O | 2 | Appropriate mix of ML techniques where useful | METHODS_EXPLAINED.md; outputs/validation/training_loss.json | PASS |
| R03 | R | 3 | At least two actual datasets, one for model building, another for testing in related domains | outputs/final/external_metrics.csv; external_feasibility.json; 35 new users, fixed matched catalog; scope/scale limitations in reports/MODEL_IMPROVEMENT.md | PASS |
| O02 | O | 4 | Matrix factorization reference considered if relevant | MatrixFactorization implementation and explanation; no external implementation copied | PASS |
| R04 | R | 5 | Proposal .docx by Oct 23 | Existing Word proposal content read; actual submission by Oct23 not verified | BLOCKED |
| R05 | R | 5 | Proposal objective and domain | Team12_Proposal_Perfume_Recommendation.docx §1, text verified | PASS |
| R06 | R | 5 | Proposal datasets | Team12_Proposal_Perfume_Recommendation.docx §2, text verified; counts are plans | PASS |
| R07 | R | 5 | Proposal filtering methods | Team12_Proposal_Perfume_Recommendation.docx §3, text verified | PASS |
| O03 | O | 5 | Proposal ML models (optional) | Team12_Proposal_Perfume_Recommendation.docx §4 | PASS |
| R08 | R | 6 | Final PPT business objective | reports/drafts/Team12_Development_Review_v2.pptx objective; final deck pending test and team inputs | BLOCKED |
| R09 | R | 6 | PPT data exploration and dataset description | PPT draft and outputs/audit; final deck not approved | BLOCKED |
| R10 | R | 6 | PPT data preprocessing | PPT draft; src/perfume/data.py; final matching review pending | BLOCKED |
| R11 | R | 6 | PPT model training | PPT draft; real validation training; final policy not fixed | BLOCKED |
| R12 | R | 6 | PPT model evaluation and analysis, including unsuccessful results | PPT draft; validation results only; internal/external test pending | BLOCKED |
| R13 | R | 6 | PPT difficulties and solutions | reports/STATUS.md; draft notes on sparse MF; final team learning confirmation pending | BLOCKED |
| R14 | R | 6 | PPT what to do differently / more time | PPT draft notes; team-confirmed redo reflection pending | BLOCKED |
| R15 | R | 6 | PPT each member's actual learning | TBD authentic individual learning; do not invent | BLOCKED |
| R16 | R | 6 | PPT individual task assignments | TBD team-confirmed individual assignments | BLOCKED |
| R17 | R | 6 | PPT individual contribution percentages | TBD team-confirmed contribution percentages | BLOCKED |
| R18 | R | 6 | PPT entire software architecture | reports/STATUS.md architecture; draft PPT module flow; final review pending | BLOCKED |
| R19 | R | 6 | PPT verified GitHub URL | Not a Git repository; verified Team12 GitHub URL absent; no push performed | BLOCKED |
| R20 | R | 7 | Source code with meaningful comments | src/perfume/*.py; tests/test_core.py | PASS |
| R21 | R | 7 | Third-party borrowed code cited; plagiarism prevention | REFERENCES.md; original recommender implementation; nearby artifact API comment | PASS |
| R22 | R | 7 | Explanation of every not-taught module/class/library/function/method and parameters | METHODS_EXPLAINED.md; reports/API_REFERENCE.md; course scope/team explainability review pending | BLOCKED |
| R23 | R | 7 | Real plots and code execution outputs | outputs/figures/*.svg/*.png; outputs/validation/metrics.csv; outputs/tests.log | PASS |
| R24 | R | 7 | Source codes and Word material prepared | Source and reports/drafts Word material exist; final Word scope/test evidence pending | BLOCKED |
| R25 | R | 7 | Final package by Nov 9 | Partial outputs exist; Nov9 final package not complete | BLOCKED |
| R26 | R | 8 | Presentation Nov 10 or 12, exact team slot confirmed | Exact team presentation slot TBD (Nov10 or Nov12) | BLOCKED |
| R27 | R | 8 | 10-minute presentation plus 3-minute Q&A | 10-slide draft speaker timing plan; no 10min rehearsal or Q&A verification | BLOCKED |
| R28 | R | 9 | Correct Team 12 member names | professor_spec.pdf p9; unchanged proposal; reports/drafts/Team12_Development_Report.docx | PASS |
| Q01 | Q | 7 | Clarify exact purpose/structure of final Word document | Professor confirmation of final Word purpose/structure pending | BLOCKED |
| I01 | I | — | Cross-dataset evaluation leakage/overlap documented | outputs/final/freeze.json; external_manifest.json; evaluation_complete.json; reports/MODEL_IMPROVEMENT.md (matched-item scope) | PASS |
| I02 | I | — | Reproducible environment, seeds, commands and tests | configs/improvement.json; outputs/improvement/search.log; tests.log (19 PASS); outputs/final/integrity_check.json | PASS |
| I03 | I | — | Appropriate baselines and justified metrics | reports/ZERO_POLICY.md; outputs/validation/metrics.csv; METHODS_EXPLAINED.md | PASS |

**Important:** Slides do **not** specify a numerical scoring rubric, point weights, mandatory model accuracy threshold, mandatory app UI, or required deep learning. Do not invent them.


## Additional verbal professor requirements (student-reported, 2026-10-16)
| ID | Source | Requirement | Evidence | Status |
|---|---|---|---|---|
| V01 | Professor verbal clarification | Harmonize only shared features of development and external test datasets; report mapping, missingness, leakage controls | outputs/final/external_feasibility.json shared_feature_audit; frozen vocabulary; matched-catalog inference only, unseen-item transfer N/A | PASS |
| V02 | Professor verbal clarification | Implement hybrid filtering with documented constituent approaches and measured comparisons | outputs/improvement/validation_metrics.csv; outputs/final/internal_metrics.csv; external_metrics.csv; fixed hybrid and component comparisons | PASS |
| V03 | Professor verbal clarification | Include at least one technique not taught in class; explain method and parameters | Knowledge rules implemented/explained; team must confirm not taught in class | BLOCKED |


## v3 향수 프로젝트 사용자 설계 및 평가 검증 추적 (2026-10-16)
> 아래 항목은 교수님 원본 슬라이드의 신규 필수 조건이 아니라 사용자 설계를 구현·검증하기 위한 **I(권장/설계상 필수)** 항목이다. 설계 문서에 기재됐다는 사실은 실행 검증 PASS를 의미하지 않는다.

| ID | Type | 검증 기준 | 증거 경로 | Status |
|---|---|---|---|---|
| P01 | I | Fragrantica `fra_cleaned.csv` 실제 스키마/결측률/콘텐츠 컬럼 확인 | outputs/audit/summary.json; src/perfume/data.py; data/README.md | PASS |
| P02 | I | Atrafshan JSON→정규화 DataFrame/CSV 변환, 페르시아어 컬럼, 평점 0 의미, 실제 개별 평점 확인 | outputs/audit/zero_joint_distribution.json; PROJECT_DECISIONS.md §9; exclude as approved analysis assumption, semantic meaning remains unresolved | PASS |
| P03 | I | Fragrantica↔Atrafshan 브랜드+향수명 매칭, 농도/버전 충돌, 연결된 평가 수 | outputs/audit/atrafshan_matching.csv; conservative exact matches; semantic/manual collision review pending | BLOCKED |
| P04 | I | Content-Based/CF/Hybrid/Knowledge-Based 각 방법의 구현·개별 비교·규칙 설명 | src/perfume/models.py; improvements.py; outputs/final component metrics; prior knowledge_rules.csv; no new rule tuning | PASS |
| P05 | I | Atrafshan 내부 train/validation/test 분리와 누수 방지, baseline, ranking 지표·후보군 정의 | Original split preserved; outputs/final/internal_metrics.csv; one-attempt ledger; ranking definitions unchanged | PASS |
| P06 | I | Laure 전체가 아닌 **평점 존재 2,694개 아이템** 중 매칭된 수, 남는 평점 수, support+held-out 가능 사용자 수 실측 | outputs/final/external_feasibility.json: rated source/factor/candidate overlap; 35 users, support122/answer140 | PASS |
| P07 | I | 외부 support/held-out 분리; held-out 정답의 fit/tune/profile/score 접근 금지 테스트 | src/perfume/frozen.py score_frozen; external_protocol.py; tests; outputs/final/external_manifest.json and integrity_check.json | PASS |
| P08 | I | 신규 사용자 Item-CF fold-in/콜드스타트 폴백의 외부 적용 타당성 확인 | v4 MF replaces v3 ItemCF example; actual new-user fixed-factor ridge fold-in; external component results | PASS |
| P09 | I | 외부 Precision@K/Recall@K/NDCG@K 후보군·정답·coverage·미평가 처리 정의 | configs/improvement.json external_protocol frozen pretest; outputs/final/external_metrics.csv; ordinal mapping assumption, MAE/RMSE N/A | PASS |
| P10 | I | Parfumo 노트/어코드 교차 출처 일관성 검증; 개인화 성능으로 오인 금지 | Parfumo auxiliary analysis not run; never substituted for personalized external evaluation | BLOCKED |
| P11 | I | 원본 사이트 이용약관/저장소 라이선스·재배포/개인정보 사용권 감사 | PROJECT_DECISIONS.md §8 user permission confirmation; REFERENCES.md independent evidence limits; no redistribution | PASS |
| P12 | I | 교수의 수업 외 추천 기법 인정 및 팀 최종 결정 확인 | TBD team final choice and course-external method confirmation | BLOCKED |

**누수 검사 필수:** 외부 정답 평점이 전처리 fit, α·K 선택, 인기순위 계산, 사용자 프로필, 추천 점수 산출, 학습 손실에 들어가면 FAIL. 외부 support만 고정 모델의 신규 사용자 입력으로 허용.


## v4 최신 제안서/사용자 결정 추가 추적 (2026-10-22)
| ID | Type | Acceptance criterion | Evidence path | Status |
|---|---|---|---|---|
| P13 | I | 최소 유효 평점 3/4/5 기준 각각 사용자·향수·평점·매칭 수 실측 | outputs/audit/threshold_counts.csv; reports/ZERO_POLICY.md (both provisional zero scenarios) | PASS |
| P14 | I | 세 기준 공통 validation cohort/labels/candidates, 독립된 train 확장, 시드 및 split manifest 검증 | outputs/validation/split_manifest.json; training_counts.csv; outputs/verification.json | PASS |
| P15 | I | 세 기준 내부 validation 추천 지표 비교로 최종 기준 선택; 내부/외부 test 기반 선택 금지 | outputs/improvement/selection.json chosen threshold3 by common validation only; freeze pretest; no reselection | PASS |
| P16 | I | 코어 CF는 L2 regularized matrix factorization + SGD; user/item kNN은 선택적 비교 | src/perfume/models.py MatrixFactorization; outputs/validation/training_loss.json; synthetic tests | PASS |
| P17 | I | 외부 신규 사용자 MF fold-in 시 support와 개발 학습된 item factor만 사용 | Frozen Atrafshan-trained factors; external support122 all factor-eligible; external_manifest factor hash unchanged | PASS |
| P18 | I | Knowledge-Based는 코어 구현; 노트/어코드 제약, 조건 충족률, 시즌·가격 필드 검증 | outputs/validation/knowledge_rules.csv; outputs/demo.json; season/price disabled | PASS |
| P19 | I | 교수 원본 PDF와 최신 최종 Word 제안서 읽기, 설계 불일치 보고 | reports/STATUS.md; professor PDF pp2–9 and final proposal read; v3 ItemCF superseded by v4 MF | PASS |
| P20 | I | 데이터 미존재 시에도 실행 가능한 audit/ETL/테스트 scaffold 작성, 숫자 날조 금지 | All original datasets exist; src/perfume; scripts/audit.py; tests/test_core.py (missing-data branch not applicable) | PASS |

**2026-10-22 execution audit:** PASS describes only the row criterion and cited local evidence. Draft deliverables and validation sensitivity do not establish final compliance. No internal/external test was run. Zero policy, final submission and authentic team inputs remain BLOCKED.

**2026-10-22 follow-up:** zero-excluded primary analysis is an approved analytical assumption, not a sentinel finding. Validation-only improvement, frozen internal/external one-time assessments and 19 tests are complete. Earlier NOT EXECUTED/BLOCKED notes above are historical; latest evidence is reports/MODEL_IMPROVEMENT.md. Final package/team evidence remains BLOCKED.
