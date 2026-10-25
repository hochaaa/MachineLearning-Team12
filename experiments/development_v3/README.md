# SCENT MATCH Development V3 — STEP 8

실행 완료. MF Fit 58/61회(Primary 52/54, Seed 29 진단 5/6, 최종 학습 1/1). 기존 V1/V2·웹과 연결하지 않는 독립 연구 코드다. Outer NDCG@10은 V1 0.038111, V2 0.043615, V3 선택 절차 0.033557이며 개선되지 않았다. 서비스는 V1 유지 권고다.

## 실행 환경과 실제 명령

프로젝트 루트에서 Python 3.12.14 / NumPy 2.3.5 환경을 사용했다. 기존 `web/backend/.venv/bin/python`을 사용했으며 환경을 재설치하거나 웹 서버를 변경하지 않았다. 아래 명령의 기록은 `outputs/development_v3/logs/`에 있다.

```sh
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B -m unittest discover -s experiments/development_v3/tests -v
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v3/run_experiments.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v3/check_runtime.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v3/post_checks.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v3/recommend_v3.py --demo mixed --condition woody --k 5
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/development_v3/write_reports.py
```

학습 실행기는 기존 `configs/run_started.json`이 있으면 재실행을 거절한다. 이 기록을 삭제해 추가 실험하지 않는다. 위 학습 명령은 실행 증거·재현 절차 설명용이다. 현재 산출물에 대한 재학습 또는 평가 재실행 지시가 아니다. 보고서 생성기도 기존 보고서 덮어쓰기를 거절한다.

최초 21개 테스트 중 정수 0점 dtype 오류 1건을 보존했다(`pretraining_tests.log`). `foldin_v3.py`의 평점 배열을 float64로 수정하고, 정수/실수/0·10 추가 4개를 포함한 **25개 사전 테스트 통과 후** 학습했다(`pretraining_tests_retry1.log`). 이후 SGD 손계산 테스트를 더해 최종 **26개** 통과했다(`final_regression_tests.log`). 통합 정상 48개, 비정상 8개 거절, 재로딩·입력순서·불변성 검증도 통과했다. 합성 수학 테스트에는 실제 MF.fit 호출이 없다.

## 입력·선택 경계

사용 가능한 학습 평점은 `outputs/validation/train_exclude_3.json` 하나다(330명, 538향수, 1,805평점). 후보는 기존 `outputs/improvement/candidates.json`의 479개, 공개 콘텐츠는 `Term-project-datasets/fra_cleaned.csv`다. 기존 Validation/Internal·External Test 정답은 읽지 않는다. 입력 파일은 별도 사용권이 필요하고 Git에서 제외한다. 이 저장소 코드만으로 실제 데이터 결과를 재생성할 수 있다는 주장은 하지 않는다. 합성 테스트는 데이터셋 없이 실행할 수 있지만 기존 V1/V2 소스와 Python 의존성이 필요하다.

사용자 Outer 3-fold / Inner 2-fold, Support 3개, relevance≥0.7, Top10을 사용한다. split seed=20261109, 기본 MF seed=12, 진단 seed=29다. 평가 사용자는 학습에서 전부 제외한다. 각 fit의 IDF·인기도·bias·평균은 fit 평점만 사용한다. 점수 함수는 support만 받으며 held-out은 평가 함수에만 전달한다. 모든 모델은 같은 사용자·support·정답·479 후보를 쓰고 seen을 제거한다. 해당 fold에 MF factor가 없는 정답도 제거하지 않는다.

6개 Inner fold를 먼저 완료하고 `configs/selections_locked.json`을 저장한 뒤 Outer 평가를 시작했다. Outer별 정책 F/V1/F, 전체 Train용 정책 F를 Inner에서 고정했다. Outer 평균은 **정책 선택 절차** 성능이다. 고정 F를 모든 Outer에서 평가하지 않았으므로 F 단일 정책의 3-fold 성능은 N/A다. 추가 튜닝은 하지 않았다.

## 승인된 후보

공통 lr=.01, latent L2=.01, 40 epochs, user-bias fold-in L2=1, neutral content, α는 Content 비중이다.

|정책|factor|학습 bias L2|fold-in latent L2|결합|α|
|---|---:|---:|---:|---|---:|
|A|2|.01|1|linear|.25|
|B|2|.1|1|linear|.25|
|C|2|.1|.1|linear|.25|
|D|4|.1|.1|linear|.25|
|E|2|.1|.1|linear|.75|
|F|2|.1|.1|candidate minmax|.25|

`v3_config.verify_source`가 STEP7 원문 A–F 표 및 원본 해시와 비교한다. 원본 blueprint/보고서를 수정하지 않았다. Inner guardrail은 V1 대비 평균 coverage≥80%, Top10 집중도 증가≤.10이다. 최대 NDCG에서 .002 이내면 저차원, 강한 bias/fold 정규화, ID 순으로 선택하며 V1 유지도 허용한다. Outer 결과로 이 규칙을 바꾸지 않는다.

## 재사용·예산·저장 모델

`FitBudget`은 실제 MF.fit 진입을 세며 V2 정지용 probe도 포함한다. 캐시는 이번 실행 내 class, training/stop 행 순서 digest, seed, training config가 모두 같을 때만 재사용한다. 21회 재사용 중 18회는 B/C/E/F의 동일 MF, 3회는 선택 V1의 baseline 공유다. 초기 planned 61회보다 실제 3회 절약했다. V2 ledger epoch는 best/selected epoch이며 전체 optimizer 순회 수라는 의미는 아니다.

- 최종 전체 Train 모델: `outputs/development_v3/models/final/{weights.npz,metadata.json,input_recipe.json}`
- Outer 비교 모델: `models/outer{0,1,2}/{V1,V2,Nested}/`
- 실제 fit 캐시: `models/cache/` (58개)
- 설정/선택: `configs/{execution.json,selections_locked.json,run_complete.json}`
- 지표: `metrics/{inner.csv,outer.csv,known_secondary.csv,seed29.csv,final_summary.json}`
- 검증: `diagnostics/{fit_ledger.json,post_checks.json,runtime.json,paired_bootstrap.json,final_verification.json}`

최종 F: factor2, biasL2=.1, latentL2=.01, lr=.01, 40epoch, fold latent=.1/bias=1, minmax αContent=.25. 이는 Inner로 정한 연구용 최종 모델이며 배포 승인이나 독립 Test 성능 증거가 아니다.

## 독립 CLI

`--demo`는 합성 평점이다. 실제 사용자 ID·평점 기록은 예제에 넣지 않았다. `--support`는 사용자 본인이 제공하는 `[["후보 향수 ID",9], ...]` JSON(서로 다른 3개 이상)이다. 기본 입력 범위는 0–10, 정규화된 입력은 명시적으로 `--rating-scale 1`을 사용한다. 자동 scale 추론은 하지 않는다. `--condition none|woody|floral|rose`, `--k 5|10`을 지원한다. fold-in은 고정 Q·item bias·평균을 사용하며 MF.fit은 실행하지 않는다. IDF/인기도는 모델 recipe와 동일한 Train으로 로딩 시 재구성한다.

## 결과 해석·공개 범위

정확도 분모는 긍정 정답이 있는 사용자다. Outer 전체 158명 중 145명이 해당하며 보고 점수는 fold별 사용자 평균을 다시 동일 가중 평균한 값이다. Coverage/노출 집중도는 긍정 정답 유무와 무관한 전체 평가 사용자 추천으로 계산한다. 기존 실험과 후보·평가집단이 다르므로 예전 숫자와 직접 증감 비교하지 않는다. Bootstrap은 재사용 Train 기반 CV의 기술적 불확실성이고 독립 Test 검증이 아니다.

새 V3 소스·테스트·설명만 공개 검토 대상이다. `outputs/`의 평점, 사용자 mapping, 캐시 모델, 로그, 비공개 데이터는 강제 스테이징하지 않는다. 기존 `.gitignore`를 유지했다. 전체 보고서는 `reports/V3_IMPLEMENTATION_AUDIT.md`, `V3_EXPERIMENT_RESULTS.md`, `V3_FINAL_COMPARISON.md`에 있다. Git 작업과 웹사이트 변경은 하지 않았다.
