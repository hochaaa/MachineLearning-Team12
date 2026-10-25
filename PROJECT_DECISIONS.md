# PROJECT_DECISIONS.md — 향수 추천 시스템 (2026-10-16, v3)

**상태: 사용자 제안안 기록 완료 / 팀 최종 승인·데이터 검증·이용 허가는 미완료.** 이 문서는 사용자가 명시한 설계 방향을 기록하며 구현 완료나 교수 요구사항 충족을 의미하지 않는다. Codex는 같은 도메인을 다시 탐색하도록 요구하지 말고 이 설계를 기준으로 **Phase 0 및 데이터 타당성 감사부터** 시작한다. 대규모 구현·제출 전 팀 확인을 요청한다.

## 1. 제안된 설계 결정
| 결정 | 현재 계획 | 상태 |
|---|---|---|
| 추천 도메인 | 향수 개인화 추천 시스템 | 사용자 선택, 팀 확인 대기 |
| 추천 과제 | 사용자가 선호하는 향수 Top-K 추천; 필요 시 평점 예측 보조 | 제안 |
| 콘텐츠 기반 학습 | `fra_cleaned.csv` (Fragrantica 파생) | 제안; 사용권 확인 필요 |
| 협업 필터링 학습 | `atrafshan_data.json` (Atrafshan) | 제안; 실제 평점 추출 검증 필요 |
| 하이브리드 | Content-Based + Collaborative의 점수 정규화 및 가중 결합 | 필수 방향, 결합 방식 튜닝 필요 |
| 수업 외 추천 기법 | Knowledge-Based Recommendation: 사용자 명시 조건/제약·규칙 기반 필터링 및 랭킹 | 제안; 수업 외 여부 팀 확인 |
| 독립 외부 테스트 | Laure Richis/Basenotes 파생 JSON (`perfumes.json`, `reviews.json` + lookup JSON) | 제안; 매칭 후 평가 가능 수 미확정, 사용권 확인 필요 |
| 보조 데이터 | `parfumo_data_clean.csv` (Parfumo) | 제안; 향수 특성 일관성 검증, 외부 개인화 성능 평가 대체 불가 |
| 팀 | Team 12: 김동은, 박찬민, 이호찬 | 교수 자료 확인 |
| 역할·기여율·GitHub·개별 학습 소감 | TBD | 팀 확인 필요 |
| 최종 Word 문서 범위·발표 날짜 | TBD | 교수 확인 필요 |

## 2. 데이터 출처 및 규모 (기존 로컬 조사 수치; 재실행하여 검증)
| 출처 | 파일 | 대략적 규모 | 용도 |
|---|---|---|---|
| Fragrantica | `fra_cleaned.csv` | 향수 24,063 | 향수명/브랜드/탑·미들·베이스 노트/어코드 등 콘텐츠 |
| Atrafshan | `atrafshan_data.json` | 향수 1,369; 개별 평점 6,882; 사용자 댓글 36,434 | user-item-rating 구축; 댓글은 평점과 혼동 금지 |
| Laure Richis | `perfumes.json`, `reviews.json`, `brand.json`, `notes.json`, `category.json`, `season.json`, `users.json` | 향수 39,699; 사용자 877; 평점 6,288; 평가된 향수 2,694; 5건 이상 평가 사용자 156(총 5,202건) | 독립 사용자에 대한 외부 평가 |
| Parfumo | `parfumo_data_clean.csv` | 향수 59,325 | 별도 출처의 향료/어코드 일관성 점검 |

데이터셋 URL: Fragrantica https://www.kaggle.com/datasets/olgagmiufana1/fragrantica-com-fragrance-dataset ; Atrafshan https://github.com/Kalashi-Saed-Collaborations/SentimentDrivenCommunityDetection ; Laure Richis https://github.com/animalcrossingparty/perfume/tree/master . Parfumo 원본 CSV의 정확한 다운로드 URL은 `TBD`로 두고 확인한다. 원본 사이트의 약관과 재배포·ML 사용 허가를 별도로 검토한다. Atrafshan 저장소의 학술·비상업적 사용 설명, Fragrantica/Laure의 사용권 불확실성을 기록한다. 사용권 확인 없이 데이터를 Git에 커밋·배포하지 않는다.

## 3. 전처리 계획
1. 원본은 불변으로 보관하고 JSON을 pandas DataFrame으로 정규화; Atrafshan의 중첩 구조·페르시아어 컬럼 매핑·CSV 추출 결과를 재현 가능한 스크립트로 작성하고 보고서에 기록.
2. 데이터별 스키마·결측률·중복·이상값 확인. Atrafshan의 `0` 평점이 실제 점수인지 결측 센티널인지 원본 스키마로 확인하기 전 임의 삭제/사용 금지.
3. Laure의 정수 브랜드/노트/계절/카테고리 FK를 참조 JSON으로 복원; 개인 식별·프로필 정보는 평가 데이터에서 제거/가명화.
4. 브랜드+향수명 정규화(대소문자, 악센트, 공백, 구두점)로 매칭. EDT/EDP·리뉴얼·동명 이종 제품·다대다 충돌을 수동/규칙 검증; 매칭 근거와 거절 건수 기록.
5. 학습용 향수 노트/어코드를 TF-IDF 또는 multi-hot 벡터로 변환하고 코사인 유사도 계산. vocabulary/IDF/스케일러 등은 개발 학습 데이터로만 fit.
6. Atrafshan의 실제 개별 user–perfume–rating으로 희소 행렬 생성. 사용자/아이템별 평가 수, 점수 분포, 희소도 보고. 평점 없는 댓글과 향수별 평균 평점으로 가짜 상호작용 생성 금지.
7. 지식 기반 규칙에 필요한 계절/가격 등의 필드 존재와 결측률 확인. 없는 가격을 임의 생성하지 않고 해당 조건 비활성화 또는 데이터 출처 보강.

## 4. 모델과 비교 실험
- **Content-Based**: 선호 향수/사용자 입력 향수의 특성 프로필 → 유사도 점수.
- **Collaborative**: Atrafshan의 실제 개별 평점 기반 Item-Based CF 등. 신규 사용자와 공통 아이템이 없으면 계산 불가능함을 명시.
- **Hybrid**: 개발 validation에서만 정한 α를 사용해 정규화된 두 점수의 가중합. 점수 범위·결측/콜드스타트 폴백을 문서화. 두 단일 모델과 하이브리드 성능 각각 보고.
- **Knowledge-Based**: 사용자 명시 조건(향 계열, 계절, 가격 *실제 존재할 때만*)을 필수/선호 조건으로 해석하여 규칙·제약 충족 여부와 랭킹 계산. 단순 콘텐츠 유사도와 별도 추천 논리를 명확히 구현하고 평가.
- Baseline: 인기/평균 평점 또는 무작위(시드 고정) 등 적절한 비교 기준을 추가.

## 5. 평가 설계 — **절대 누수 금지**
### 내부 평가
- Atrafshan 개별 평점을 개발 train/validation/internal test로 사용자별 분리. 각 평가 사용자가 train에 충분한 이력이 있는지 확인.
- 개발 train만으로 전처리/CF 모델 fit; validation으로 α, K, 점수 임계값 등을 결정; 내부 test는 최종 측정에만 사용.
- Precision@K, Recall@K, NDCG@K를 우선 검토. 실제 점수 예측을 구현한 경우에만 MAE/RMSE. 긍정 평점 정의·후보 집합·미평가 상품 처리·분모·seen-item 제외를 명시.
### 독립 외부 평가 (Laure Richis)
1. **먼저 외부 평가 가능 규모를 측정**: 전체 Laure 카탈로그 매칭 수가 아닌 **평점이 달린 2,694개 향수 중 매칭된 수**, 그 향수에 속한 **6,288개 평점 중 남는 수**, 그리고 **취향 입력용/정답용으로 나눌 수 있는 사용자 수**를 순서대로 계산. 학습 측 공통 아이템(Fragrantica/Atrafshan)을 각각 구분하여 기록.
2. Laure의 사용자 ID는 Atrafshan과 연결되지 않음. 사용자별 매칭 평점 일부는 **support/profile 입력**으로만, 나머지는 **held-out query/정답**으로 사용(예: 10건 중 5건/5건). 적어도 support 1건 + held-out 1건 필요; 권장 5건 이상 사용자 결과도 별도 보고. 사용자별 잔여 수 분포와 탈락 사유 제시.
3. **외부 테스트용 정답 평점은 모델 학습·튜닝·벡터라이저 fit·아이템 인기도 계산·사용자 프로필·추천 점수 산출에 절대 사용하지 않는다.** support 평점은 평가 시점에만 신규 사용자 적응 입력으로 허용; 외부 테스트에서 모델 파라미터를 재학습하거나 α/threshold를 선택하지 않는다. 평가 프로토콜 확정 후 외부 점수로 반복 튜닝 금지.
4. 신규 사용자에게 기존 Atrafshan CF의 사용자 ID를 재사용하지 않는다. support 아이템과 Atrafshan 학습 아이템 간 이웃 기반 fold-in/Item-CF 점수 등 **명시적으로 구현된** 신규 사용자 적응이 있어야 CF/Hybrid 외부 점수를 주장할 수 있다. 공통 상호작용이 부족하면 CF는 `not evaluable`로 표기하고 콘텐츠 기반 결과와 별도 보고.
5. 외부 평점은 Laure 0~9 범위; Atrafshan 평점 범위·의미가 다를 수 있으므로 내부 기준으로 정한 선호도 매핑을 사용하고 근거를 문서화. 후보군/negative sampling/positives/coverage/정확한 분모를 사전에 고정. 미평가 향수를 무조건 부정 사례로 취급하지 않는다.
6. 평가 가능 수가 적거나 매칭 오류가 많으면 **성능 수치를 꾸미지 말고 BLOCKED로 보고**, 평가 설계 또는 데이터셋 변경을 사용자에게 요청한다. Parfumo의 콘텐츠 일관성 검증을 외부 개인화 평가로 대체했다고 주장하지 않는다.
### Parfumo 보조 검증
- 브랜드+향수명 매칭된 제품의 노트/어코드 집합의 일치도·커버리지 비교; 어휘 동의어·표현 차이를 구분. 이는 추천 정확도/사용자 선호도 측정이 아님.

## 6. 미확정 검증 게이트
- [ ] Fragrantica↔Atrafshan 공통 향수 **고유** 매칭 수와 연결되는 사용자별 평점 수 확인.
- [ ] Laure **평가된 향수**↔Fragrantica/Atrafshan 매칭 수, 잔여 평점 수, support+held-out 가능 사용자 수 확인. 기존 전체 카탈로그 매칭 수(Laure↔Fragrantica 약 7,938, Laure↔Parfumo 약 9,382)는 외부 평가 가능 수를 의미하지 않음.
- [ ] 데이터 사용·재배포 조건 및 개인정보 처리 검토.
- [ ] 팀 승인, 교수의 수업 외 추천 기법 인정 범위 확인.
- [ ] 2026-10-23 Word 제안서, 2026-11-09 최종 제출, 11-10/12 발표 준비.

**금지:** 검증 전 '외부 평가 성공', '요구사항 충족', '모든 6,288개 평점 사용 가능' 등의 확정 표현.


## 7. 최종 제안서 및 최신 사용자 결정 (2026-10-22, v4)
- `Team12_Proposal_Perfume_Recommendation.docx`는 사용자가 제공한 최신 제안서다. 기존 v3 문서에 있는 '사용자 제안/팀 승인 대기' 표현은 팀 확인 상태를 뜻하며 **개발 자체를 시작하지 말라는 뜻이 아니다**. 로컬에서 가능한 구현과 감사는 즉시 진행한다.
- 제안서 §3.2에 따라 **SGD/gradient-descent + L2 matrix factorization이 코어 collaborative model**이다. 기존 §4의 'Item-Based CF 등'은 선택적 비교/폴백으로 해석하고 MF를 대체하지 않는다.
- 제안서 §2의 최소 사용자 평점 기준은 **3, 4, 5개의 세 가지 별도 실험**으로 확정. 동일한 공통 validation에서 비교하며 사용자/평점/향수 수 및 추천 성능을 기준별로 기록한다. 더 적은 평점 사용자에게 train/validation/test를 억지로 강요하지 않는다. 선택은 개발 validation으로만.
- 제안서 §3.4 **Knowledge-Based는 CORE**. 시즌/가격은 실제 개발 카탈로그에 신뢰 가능한 필드가 있을 때만.
- 제안서 표의 수치(Fragrantica 24,063, Atrafshan 5,573 valid ratings/1,748 users/1,050 perfumes, Laure 39,699 perfumes/6,288 ratings/877 users, Parfumo 59,325)는 **제안서에 기재된 추정/사전 조사 값**이며 실행으로 재확인해야 한다. 특히 이전 대화의 >=5 사용자 177명과 구 버전 291명은 서로 상충할 수 있으므로 **실제 파일을 기준으로 재산출**하고 차이를 설명한다.
- MF 신규 사용자 fold-in은 외부 support 중 Atrafshan 학습된 item-factor를 가진 아이템만 사용하며, 기존 item factor는 고정한다. 외부 held-out rating을 이용한 하이퍼파라미터 선정/학습/점수 계산 금지.
- Parfumo 원본 링크는 최종 제안서에서 'Parfumo Fragrance Dataset – mexwell (Kaggle)'로 명시되었으나 실제 다운로드 주소·사용권은 실행 시 확인.
- 최종 제출일: 2026-11-09, 발표 2026-11-10 또는 11-12; Word 제안서 마감 2026-10-23.

## 8. 실행 중 사용자 확인 및 잠정 결과 (2026-10-22)

- 사용자가 데이터 4종 사용권 확정 및 사용 가능을 명시했다. 수업 프로젝트 로컬 분석·학습을 진행한다. 재배포/원본 업로드/push 허가로 확대 해석하지 않는다. 원본 사이트 약관 독립 검증의 한계는 REFERENCES.md에 기록한다.
- 사용자는 0점 의미를 임의 확정하지 말고 원본 조사, 항목별 분포, 포함/제외 × 3/4/5 내부 validation 민감도 분석을 요청했다. 최종 정책은 BLOCKED를 유지한다.
- `reports/ZERO_POLICY.md`와 `outputs/validation/selection.json`은 **잠정** 결과. 포함 가정 >=4, 제외 가정 >=5가 validation Hybrid 기준 최선이며, 어느 것도 최종 정책 승인으로 취급하지 않는다.
- 외부 Basenotes 정확도 평가와 내부 test는 미실행. 외부 평점 값은 정책/성능 선택에 사용하지 않았다. 보수적 brand+name 정확 매칭만 사용하고 fuzzy/브랜드별칭 확장은 검토 전 미적용이다.
- 팀별 역할/기여율/소감, 수업 외 기술 여부, GitHub URL, 발표 날짜는 계속 TBD. 최종 제출 완료를 선언하지 않는다.

## 9. 사용자 승인 분석 가정과 동결 평가 (2026-10-22)

- 사용자가 **0 제외를 주 분석, 0 포함을 민감도 분석**으로 진행하도록 결정했다. 이는 0=미평가 확정이 아니며 의미는 여전히 미확정이다. 추가 정책 승인 게이트를 다시 요구하지 않는다.
- 사용자 승인에 따라 bias 및 MF 설정, 콘텐츠 프로필·Hybrid alpha를 기존 validation에서만 비교했다. 공통 사용자168명, labels/candidates479개는 유지했고 낮은 활동 사용자는 train-only다.
- 실제48개 MF fit와 profile/alpha 비교 후 선택: **threshold3, bias 없는 MF factors4 / epochs160 / learning_rate .01 / regularization .01 / seed12, rating-weighted content, alpha .25**. bias 실험은 개선되지 않아 채택하지 않았다. 기존 모델은 비교 증거로 보존했다.
- validation Hybrid NDCG@10 .04318527, 이전 파이프라인 .04040234. 작은 관측 증가이며 유의성 주장이 아니다. 모델·단어장·데이터·코드 해시는 outputs/final/freeze.json으로 고정했다.
- 내부 test1회, Basenotes 외부1회를 실행했다. Hybrid NDCG@10 내부 .03853318, 외부 .02636523. 외부 구조적 적격35명, support122개, held-out140개, positive 사용자26명이다. 결과를 보고 설정을 바꾸지 않았다.
- 외부 candidates는 사전 동결된 개발479개. 신규 사용자 IDs는 독립 가명화, hash 기반 support/answer 분리, 기존 factor는 read-only. rate/9는 ordinal mapping 가정이며 외부 MAE/RMSE는 의미 검증 부족으로 N/A다. inference는 매칭된 기존 Fragrantica 벡터를 썼으므로 미매칭/새 아이템 일반화 결과가 아니다.
- reports/MODEL_IMPROVEMENT.md, outputs/improvement/frozen_results.csv와 figures가 Word/PPT 최종 반영 근거다. 초기 Word/PPT 초안은 역사적 중간 결과로 보존했다.
- 팀 역할/기여율/개인 소감/GitHub URL, 수업 외 기법 여부, 발표 슬롯은 계속 미확정. 최종 제출 준수는 BLOCKED다.
