# V3 구현 설명과 API·파라미터

이 문서는 수업 이수 여부를 추정하지 않고 새 V3 구성요소를 설명한다. 교수님의 추가 필수요건이라는 의미가 아니다. 원본 V1/V2 코드는 수정하지 않았으며 아래에 재사용 범위를 명시한다. 새 V3 코드의 수식·분할·예산 계수는 직접 구현했다. 외부 프로젝트의 구현 코드를 복사하지 않았다.

## 수학과 척도

내부 평점 r은 0–1이다. 사용자 입력 0–10은 명시적 adapter에서 10으로 나눈다. 원본 Atrafshan 0을 학습에서 제외하는 분석 가정과, 사용자가 명시적으로 준 0점 입력을 처리하는 것은 서로 다른 정책이다.

MF 예측은 μ+bᵤ+bᵢ+pᵤᵀqᵢ다. μ는 해당 fit의 평점 평균으로 고정한다. 관측 edge의 목적함수는 ½[(예측−r)²+λₗ(||p||²+||q||²)+λᵦ(bᵤ²+bᵢ²)]다. 전체 loss는 edge 평균이므로 규제도 관측 빈도에 따라 누적된다. 관측되지 않은 평점을 0으로 채워 최적화하지 않는다. SGD는 같은 이전 p,q와 오차 e로 네 gradient를 구한 뒤 learning_rate만큼 빼며 Normal(0,.05), bias0으로 초기화한다. seed는 난수 생성과 epoch 내 순서를 고정한다. factors는 잠재 차원, epochs는 전체 edge 순회 횟수, latent_l2/bias_l2는 별도 규제 강도다. inference는 [0,1]로 clip한다.

Fold-in은 관측 support 중 MF factor가 있는 항목만 사용한다. n개 support에서 A=[qᵢᵀ,1], y=r−μ−bᵢ, D=diag(λlatent,…,λuserbias)로 (AᵀA+nD)z=Aᵀy를 푼다. z의 마지막 값은 신규 사용자 bias다. V1은 bias 열과 평균을 쓰지 않는다. Q·item bias·평균을 학습하지 않는다. 정규화가 양수이므로 zero vector에서도 안정적인 선형계를 구성한다. float64 y는 정수 배열에 실수를 in-place 차감하는 오류를 방지한다.

Content는 기존 ContentV2를 재사용한다. neutral 방식은 .5 notes/.5 accords TF-IDF 코사인 프로필이며 fit 문서 집합은 해당 train 고유 향수다. V1은 원래 rating 방식이다. Hybrid linear는 αContent+(1−α)MF, minmax는 현재 사용자 seen 제외 후보 점수를 성분별 [0,1]로 변환한 뒤 결합한다. α는 Content 비중이다. 동일값·결측 처리, component fallback, 인기도 fallback, RRF는 기존 `hybrid_v2.combine` 구현을 재사용한다. 이는 새 Test 정답 기반 보정이 아니다.

## 평가·선택·통계

긍정 집합 Rᵤ={held-out 향수:r≥.7}, 추천 Lᵤ의 최대 길이는10이다. Precision@10=|Lᵤ∩Rᵤ|/10, Recall=|Lᵤ∩Rᵤ|/|Rᵤ|. DCG=Σⱼ₌₁¹⁰ 1[Lᵤⱼ∈Rᵤ]/log₂(j+1), IDCG는 min(10,|Rᵤ|)개 정답이 앞에 온 경우다. NDCG=DCG/IDCG. Rᵤ가 비면 정확도 평균에서 제외하며 별도 인원수를 기록한다. fold 내 사용자 산술평균, fold 사이 동일 가중 평균이다. unknown-factor held-out을 삭제하지 않는다. unknown MF는 NaN, hybrid는 content로 fallback한다. 공개 479 후보 범위 밖 기록은 이번 CV relevance 범위 밖이다.

Coverage는 전체 평가 추천의 고유 향수 수, catalog coverage는 이를479로 나눈 값이다. Top10 집중도는 전체 추천 슬롯 중 가장 많이 등장한 10향수의 슬롯 비율이다. Gini는479개 노출수의 불평등, entropy는 노출확률의 −Σp log₂p다. 사용자 간 Top10 Jaccard는 |교집합|/|합집합|의 사용자쌍 평균이다. bias/latent SD는 한 사용자의 알려진 후보별 항 변동성으로 정확도 자체가 아니다. Spearman은 tie 평균순위를 사용한다.

Inner selection은 사전에 정한 coverage/집중도 guardrail, NDCG, .002 근접 동점 규칙만 사용한다. 모든 Inner 및 최종 F 선택을 Outer보다 먼저 고정한다. paired bootstrap은 같은 사용자의 모델별 NDCG 차이를 묶어 3,000회 재표집하고 fold macro 평균 차이의2.5/97.5백분위를 낸다. seed별 진단은 정책을 재선택하지 않는다. Train 재사용과 작은 집단 때문에 독립 Test 유의성·비열등성을 증명하지 못한다.

## 라이브러리·재사용·출처

- NumPy: `asarray(...,dtype=float64)` 명시형 배열; `linalg.solve(A,b)` 선형계; `default_rng(seed)` 결정적 난수; `normal(loc,scale,size)` 초기화; `permutation(n)` SGD 순서; `clip(a,0,1)` 범위; `argsort(kind='stable')` 동점 안정성; `corrcoef` 순위 상관; `quantile` CI; `load(allow_pickle=False)` 안전한 numeric weights 로딩; `savez` 저장. API 근거: https://numpy.org/doc/stable/reference/ (링크 안내이며 이번에 네트워크 조회하지 않음).
- Python 표준: `hashlib.sha256` 내용 식별; `json` 설정·로그; `pathlib` 경로 경계; `sys.setprofile` 실제 fit 진입 감시; `sys.addaudithook` 금지 입력 open 차단; `subprocess.check_output` 읽기 전용 Git 상태; `time.perf_counter` 시간; `collections` 집계; `argparse` CLI; `unittest` 합성 검증; `ast` API 목록 생성. 문서: https://docs.python.org/3/library/ (이번에 조회하지 않음).
- 팀 내부 재사용: `src/perfume/{models,evaluation,data}.py`의 V1 MF/인기도/지표/카탈로그 읽기, `experiments/development_v2/{mf_v2,content_v2,foldin_v2,hybrid_v2,data}.py`의 baseline·content·입력 검증·fusion·중첩 stopping. import를 통해 재사용하며 기존 파일·모델 상태는 수정하지 않는다. 출처·설계는 STEP7 원본 보고서와 blueprint이며 해시를 실행 설정에 보존했다.
- 위 모듈의 상세 기존 설명·외부 인용은 프로젝트 `METHODS_EXPLAINED.md`, `REFERENCES.md` 및 V2 설명을 함께 참조한다. 새 외부 코드를 차용하지 않았으므로 기존 REFERENCES를 수정하지 않았다.

## API 인벤토리

아래 서명은 현재 새 V3 소스에서 AST로 추출했다. 입력 `rows/fit/train/source`는 (사용자,향수,정규화 평점) 행, `pool`은 고정 후보 향수 목록, `support/supports`는 사용자 입력만, `answers`는 지표 계산 전용 held-out이다. `model`은 해당 fold에서만 fit된 인스턴스, `policy/config/settings`는 사전 실행 JSON, `seed`는 정수 난수/해시 seed다. `path/name`은 로컬 경로이며 공개용 사용자 기록이 아니다. `self`는 인스턴스다. 반환과 부작용은 모듈별 설명을 따른다.


### check_runtime.py

stable(result)는 시간 필드를 제외한 결과 비교용이다. no_mf_fit(frame,event,arg)는 통합 검증 중 MF.fit 시 즉시 오류다. main()은 합성 정상48개/비정상8개·순서·재로딩·latency·RSS를 측정한다. 모델 정확도 평가가 아니다.

- `stable(result)`
- `no_mf_fit(frame, event, arg)`
- `main()`

### evaluate_v3.py

avg_rank(v)/corr(a,b)는 tie-aware Spearman이다. ScoringContext(fit,pool,catalog,raw,supports)는 현재 fit 전용 content/인기도 캐시, content(kind)는 v1/neutral fit, predict(model,policy,kind,known)는 content/mf/hybrid 추천과 fallback·변동성·시간을 반환한다. known=True만 기존 사용자 보조다. assess(pred,answers,pool,fb,diagnostics,times)는 정확도·노출 지표와 사용자별 NDCG를 반환하며 모델을 호출하지 않는다. select_policy(rows,policies,settings)는 Inner 집계만 받고 mean(name,key)는 내부 정책별 평균이다. paired_bootstrap(rows,reference,target,seed,draws)는 모델명별 paired 사용자 NDCG의 기술적 CI다.

- `avg_rank(v)`
- `corr(a, b)`
- 클래스 `ScoringContext`
- `ScoringContext.__init__(self, fit, pool, catalog, raw, supports)`
- `ScoringContext.content(self, kind)`
- `ScoringContext.predict(self, model, policy, kind='hybrid', known=False)`
- `assess(pred, answers, pool, fb=None, diagnostics=(), times=())`
- `select_policy(rows, policies, settings)`
- `paired_bootstrap(rows, reference='V1H', target='Nested', seed=20261109, draws=3000)`

### fit_budget.py

FitBudget(caps)는 phase별·총상한과 이번 실행 메모리 캐시다. check(phase)는 초과 전 중단, profile(frame,event,arg)는 Python frame의 실제 MF.fit 진입 집계, persist()는 ledger 저장, invoke(model,rows,phase,tag,stop=())는 캐시 키 검증 후 계측된 fit 또는 정확한 재사용이다. tag는 진단 라벨, stop은 V2 내부 early-stop 데이터이며 key에 포함된다.

- 클래스 `FitBudget`
- `FitBudget.__init__(self, caps)`
- `FitBudget.check(self, phase)`
- `FitBudget.profile(self, frame, event, arg)`
- `FitBudget.persist(self)`
- `FitBudget.invoke(self, model, rows, phase, tag, stop=())`

### foldin_v3.py

normalize_support(support,rating_scale=10)는 scale1/10 명시 변환과 finite·범위 검사다. fold(model,support,policy)는 고정Q ridge 사용자 벡터 또는 support없으면 None, score(model,z,pool)는 신규 사용자 점수다. z=None 또는 unknown item은 NaN이다. fold_latent/fold_bias는 별도 정규화다.

- `normalize_support(support, rating_scale=10)`
- `fold(model, support, policy)`
- `score(model, z, pool)`

### mf_v3.py

edge(p,q,bu,bi,r,mean,latent_l2,bias_l2)는 관측1개 loss와 네 gradient를 반환한다. p/q는 잠재 벡터, bu/bi/mean은 scalar다. MFV3(config,seed).fit(rows)는 SGD 실제학습이며 .score(user,pool)는 알려진 사용자 예측, 미학습 사용자는 NaN이다.

- `edge(p, q, bu, bi, r, mean, latent_l2, bias_l2)`
- 클래스 `MFV3`
- `MFV3.__init__(self, config, seed=12)`
- `MFV3.fit(self, rows)`
- `MFV3.score(self, user, pool)`

### post_checks.py

main()은 저장58개 fit 모델의 mapping·digest·사용자 분리·finite weight 및21개 cache key를 읽기 전용으로 검증한다. 재학습·ranking 재평가는 없다.

- `main()`

### recommend_v3.py

ServiceV3()는 최종 저장 weights를 read-only 배열로 읽고 source hash를 검증한다. recommend(support,condition,rating_scale,k)는 조건·Top5/10을 검증하고 fold-in/fusion/규칙필터만 실행한다. synthetic_support(service,scenario)는 high/low/mixed/equal/zeros/tens 데모다. main()의 argparse 인자는 README와 동일하며 legacy 정답 파일을 support로 넣을 수 없다.

- 클래스 `ServiceV3`
- `ServiceV3.__init__(self)`
- `ServiceV3.recommend(self, support, condition='none', rating_scale=10, k=5)`
- `synthetic_support(service, scenario='mixed')`
- `main()`

### run_experiments.py

table(name,rows)는 V3 CSV 저장, training_config(p)는 MF 파라미터만 추출, train_model(fit,policy,seed,budget,phase,tag)는 baseline/후보 학습과 V2 probe 포함, persist_model(model,path,policy,seed)는 private weights/mapping 저장이다. evaluate(context,model,policy,answers,stage,outer,inner,seed,kinds)는 공통 점수/지표 orchestration, kinds=True는 구성모델도 기록한다. main()은 테스트 receipt·보호→Inner선택lock→Outer→seed진단→최종fit→완료 receipt 순서이며 기존 run이 있으면 중단한다.

- `table(name, rows)`
- `training_config(p)`
- `train_model(fit, policy, seed, budget, phase, tag)`
- `persist_model(model, path, policy, seed)`
- `evaluate(context, model, policy, answers, stage, outer, inner=-1, seed=12, kinds=False)`
- `main()`

### split.py

hkey(seed,*parts)는 고정 해시 순서다. outer_specs(train,seed)는 history≥4 사용자 3그룹, inner_specs(outer_train,outer_index,seed)는 현재 outer train 사용자 2그룹이다. user_evaluation(source,fit,held,pool,seed)는 held 사용자에서 알려진 factor 항목3개를 ID 해시로 support에 배정하고 나머지를 answers로 분리한다. known_split(rows,outer_index,seed)는 기존 사용자 보조 진단용 사용자당1개 holdout이다.

- `hkey(seed, *parts)`
- `outer_specs(train, seed=20261109)`
- `inner_specs(outer_train, outer_index, seed=20261109)`
- `user_evaluation(source, fit, held, pool, seed=20261109)`
- `known_split(rows, outer_index, seed=20261109)`

### v3_config.py

POLICIES/V1/V2/SETTINGS는 승인된 유한 후보·상한이다. verify_source()는 원본 두 파일 해시 및 A–F 표를 비교하고 불일치 시 중단한다.

- `verify_source()`

### v3_data.py

sha(p)는 파일 해시, digest(rows)는 순서 포함 행 해시, save(name,value)는 V3 출력 경계 안 JSON 저장, guard()는 브랜치·protected19·manifest 검사다. deny(event,args)는 audit event 이름/인자로 금지 파일 읽기를 차단한다. load_train()은 허용 Train/479/metadata만 읽고, histories(rows)는 사용자별 묶음, snapshot()은 기존 파일 SHA·크기·mtime 증거를 만든다.

- `sha(p)`
- `save(name, value)`
- `guard()`
- `deny(event, args)`
- `load_train()`
- `histories(rows)`
- `digest(rows)`
- `snapshot()`

### write_reports.py

load(path)/rows(path)는 새 V3 JSON/CSV만 읽는다. avg(data,key)는 결측 제외 평균, md(data,keys)는 Markdown표, report(name,text)는 새 보고서 생성(기존 파일 거절)이다. main()은 기존 새 결과에서 요약과 보고서3개를 만들며 모델을 학습·평가하지 않는다.

- `load(path)`
- `rows(path)`
- `avg(data, key)`
- `md(data, keys)`
- `report(name, text)`
- `main()`

### tests/test_v3.py

합성 테스트의 self는 unittest 인스턴스다. 인자가 있는 로컬 helper는 synthetic 입력과 예상값만 받는다. 모든 수학·누수·분할·선택 경계는 원본 개인 평점 없이 검사한다. 개별 테스트 이름과 서명:

- `fixture(self)`
- `model(self)`
- `test_policies_match_original_report(self)`
- `test_six_policies_three_training_recipes(self)`
- `test_budget_arithmetic(self)`
- `test_budget_cap(self)`
- `test_cache_data_boundary(self)`
- `test_cache_seed_identity(self)`
- `test_outer_users_removed(self)`
- `test_inner_users_removed(self)`
- `test_support_answer_disjoint(self)`
- `test_split_order_invariant(self)`
- `test_metric_formula_and_denominator(self)`
- `test_gradient_and_distinct_penalties(self)`
- `test_fold_ridge_normal_equation(self)`
- `test_fold_order_repeat(self)`
- `test_invalid_values(self)`
- `test_missing_factor_nan(self)`
- `test_zero_inputs_finite(self)`
- `test_idf_fit_boundary(self)`
- `test_scorer_no_answers_parameter(self)`
- `test_deny_legacy(self)`
- `test_guardrail_retention(self)`
- `test_integer_raw_zero_ten_boundary(self)`
- `test_float_raw_inputs(self)`
- `test_normalized_int_zero_one(self)`
- `test_raw_out_of_range_nan_inf(self)`
- `test_hand_sgd_numeric_values(self)`
- `objective(z)`
