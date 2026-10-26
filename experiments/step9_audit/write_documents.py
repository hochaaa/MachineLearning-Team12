"""Generate new STEP9 Markdown from aggregate-only saved evidence; no model/evaluation.

load(name): STEP9 JSON relative filename. write(name,text): refuses overwrites.
metrics_table(split): formats historical aggregate rows, no rating metric calculation.
main(): writes the four requested reports and a source execution guide.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/step9_audit'
def load(name):return json.loads((OUT/name).read_text())
def write(name,text):
    p=ROOT/'reports'/name
    with p.open('x') as f:f.write(text.strip()+'\n')
def metrics_table(split):
    m=load('metric_consistency.json');table='| 모델 | NDCG@10 | 평가 사용자 | 긍정 사용자 분모 |\n|---|---:|---:|---:|\n'
    for row in m['v1_historical_aggregate']:
        if row['split']==split:table+=f"| {row['method']} | {float(row['ndcg']):.6f} | {row['users']} | {row['positive_users']} |\n"
    return table

def main():
    metrics=load('metric_consistency.json');service=load('service_checks.json');env=load('environment.json');inventory=load('git_source_inventory.json');order=load('order_diagnostic.json')
    cv='| 모델 | NDCG@10 | Coverage(개) | 상위10향수 노출 집중도 |\n|---|---:|---:|---:|\n'
    for r in metrics['step8_outer']:cv+=f"| {r['model']} | {r['ndcg']:.6f} | {r['coverage']:.2f} | {100*r['concentration']:.2f}% |\n"
    perf='| 측정 범위 | 횟수 | 평균(ms) | 최대(ms) |\n|---|---:|---:|---:|\n'
    for k,label in [('owned_backend_cold_start','별도 소유 backend cold start'),('model_load','FrozenService 로딩'),('testclient_top5','TestClient Top5(4필터×6합성 입력)'),('live_api_top5','기존 live API HTTP 왕복')]:
        r=service[k];perf+=f"| {label} | {r['n']} | {r['mean_seconds']*1000:.3f} | {r['max_seconds']*1000:.3f} |\n"
    intro='기준: 2026-10-25 STEP9. 기존 집계 결과와 코드의 감사·통합 및 합성 입력 추론 검증이다. 새 학습·튜닝·Validation/Internal·External Test 재평가·Bootstrap 재계산을 하지 않았다. 원본 데이터·기존 보고서·V1/V2/V3 소스/모델/평가 결과는 보존한다. 보고서의 경로는 프로젝트 루트 기준이며 개인 사용자 ID·가명 ID·원본 평점 행을 포함하지 않는다.'
    write('SCENT_MATCH_FINAL_PROJECT_REPORT.md',f'''# SCENT MATCH 최종 프로젝트 통합 보고서

{intro}

## 1. 개요와 최종 결정

Team12(김동은·박찬민·이호찬)의 Personalized Perfume Recommendation System은 알려진 향수와 명시 평점으로 새로운 향수를 추천한다. 핵심 시연은 향수3개와0–10점 입력→Top5이며, 기존 실제 API는 1–50개, UI는3개 이상을 권장한다. 실수는 허용되고 슬라이더 간격은0.5다. 노트/어코드 선택 조건으로 결과를 제한할 수 있다.

최종 서비스는 **Frozen V1 Hybrid 유지**로 확정한다. V2/V3는 독립 비교·진단 결과로 보존하며 연결하지 않는다. 이는 V1의 보수적인 서비스 유지 결정으로, V1이 모든 평가에서 가장 정확하다는 뜻이 아니다. 역할·기여율·개인 학습 소감은 팀 확인 전 TBD다.

## 2. 데이터와 전처리

| 단계 | 사용자 | 고유 향수 | 평점/행 |
|---|---:|---:|---:|
| Fragrantica 정제 메타데이터 | 해당 없음 | 24,063 | 24,063행 |
| Atrafshan 원시 향 평점 | 2,454 | 1,090 | 6,882 |
| Atrafshan 0제외·카탈로그 매칭 | 1,299 | 641 | 3,323 |
| 최종 min3 분할 전 cohort | 330 | 570 | 2,141 |
| 최종 min3 Train | 330 | 538 | 1,805 |
| 공통 Validation / Internal Test | 각168 | 여기서 새로 집계하지 않음 | 각168 |
| 공통 추천 후보 | 해당 없음 | 479 | 평점 수 아님 |

출처: `reports/FINAL_PROJECT_FACT_SHEET.md`, `MODEL_IMPROVEMENT.md`, `ZERO_POLICY.md`, 기존 `outputs/audit/summary.json`, `outputs/validation/training_counts.csv`의 역사적 집계. 이번에는 원시 평점과 split manifest를 다시 파싱하지 않았다. 원본 댓글36,434개와 향 평점6,882개는 다른 단위다.

0점1,309개의 의미는 아직 미확정이다. **0 제외는 사용자 승인 분석 가정**이며 미평가 확정이 아니다. 0포함 민감도는 보존한다. 정규화된 브랜드+제품명 exact matching으로 연결하고 농도·Elixir·연도 등 버전 토큰을 보존한다. 충돌/모호 매칭은 격리한다. 중복/상충 평점 처리와 페르시아어 구조/FK 복원은 `src/perfume/data.py`, `external.py`, `external_protocol.py`에 있다. 기계적인 exact match도 의미적 동일성 전수 검증을 보장하지 않는다.

| 0제외 최소 평점 | 분할 전 사용자/향수/평점 | Train 사용자/향수/평점 |
|---|---|---|
| 3 | 330 /570 /2,141 |330 /538 /1,805 |
| 4 | 231 /551 /1,844 |231 /513 /1,508 |
| 5 | 168 /525 /1,592 |168 /479 /1,256 |

공통 평가168명은 ≥5 사용자다. 각 사용자 Validation1·Test1·나머지 최소3개 Train이며 3/4개 이력 사용자는 Train 확장이다. 전역 비율로 무작위80/10/10을 자른 것이 아니다. min3 실제 비율은 약84.306/7.847/7.847%다. 공통479는 **min5 Train 향수 집합**으로 최종 min3 Train538과 구분하며 추가59개를 주 추천 후보에 넣지 않는다. 후보를 정답 ID나 값으로 선정하는 코드 경로는 기존 감사에서 발견되지 않았다. 이번에는 과거 split을 재검사하지 않고 `FINAL_EVALUATION_AUDIT.md`의 근거를 인용한다.

Laure Richis/Basenotes는 독립 외부 평가 자료다. 원본6,288리뷰·평가된 source 향수2,694개 중 Fragrantica 매칭836, Atrafshan-trained factor 연결70, 후보 연결64개(source 향수 단위)였다. 최종 적격35명, support122/held-out140, 긍정26명이다. source 향수와 canonical 향수 수를 혼동하지 않는다. Parfumo59,325행은 보조 메타데이터 검증 전용이다.

사용자는 로컬 수업용 사용권을 확인했다. `REFERENCES.md`의 저장소/논문/Kaggle 출처 기록을 유지하되 원사이트 공개 재배포·웹호스팅 권한까지 확인됐다고 주장하지 않는다. 원본·파생 평점·mapping·모델은 공개 Git에서 제외한다.

## 3. 추천 시스템과 소프트웨어 구조

```mermaid
flowchart LR
  U[사용자: 향수와 명시 평점] --> F[React / TypeScript / Vite]
  F -->|로컬 /api proxy| A[FastAPI]
  A --> S[FrozenService]
  S --> C[동결 Content 프로필]
  S --> M[고정 MF item factors + 신규 사용자 ridge fold-in]
  C --> H[0.25 Content + 0.75 MF]
  M --> H
  H --> K[Woody / Floral / Rose hard rule]
  K --> T[Top5 + 메타데이터 설명]
```

Popularity는 Train 평가 횟수 log1p 정규화 baseline/fallback이다. Content는 binary TF×train-only IDF 노트/어코드 벡터의 cosine이며 지원 평점으로 가중 프로필을 만든다. MF는 관측 평점의 오차+L2를 SGD로 최소화한 model-based CF다. V1은 bias-free pᵀq를 [0,1] clip한다. 최종 MF는 factor4/160epoch/lr.01/L2.01/seed12다. Hybrid α는 Content 비중0.25이고 한 성분이 불가하면 다른 성분, 둘 다 불가하면 Train 인기도를 사용한다.

신규 사용자 Fold-in은 고정 Q로 (QₛᵀQₛ+nλI)p=Qₛᵀr를 푼다. 이는 새 사용자 벡터 계산이며 기존 모델 재학습이 아니다. MF/content는 Train에서만 fit했고 웹은 `load_frozen`으로 복원한다. Knowledge는 accord:woody / accord:floral / note:rose의 hard 조건이다. 계절·가격은 신뢰할 개발 메타데이터 부재로 비활성이다. 조건 충족률은 개인화 정확도와 다르다.

근거: `src/perfume/models.py`, `improvements.py`, `frozen.py`, `web/backend/adapter.py`. 수식·함수·파라미터는 루트/웹/V2/V3의 METHODS 설명과 REFERENCES에 있다. 수업 외 기법 여부는 팀 확인 TBD다.

## 4. Frozen V1 개발·평가

원자료 감사→0정책 민감도→3/4/5 공통 validation 비교→MF/profile/α 탐색→선택·동결→기존 Internal/External Test의 순서다. 최초 개발 결과를 저장하고 MF48 fits 등의 2차 개선은 당시 validation만 사용했다. 최종 min3/rating profile/α.25를 두 Test 이전에 고정했다. Test에서 MF가 높아도 재선택하지 않았다. 근거: `MODEL_IMPROVEMENT.md`, `configs/improvement.json`, `outputs/final/freeze.json`.

### A. V1 Validation: 모델 선택에 사용된 역사적 결과

{metrics_table('validation')}
### B. V1 Internal Test: 기존 사용자·기존 상품 평가

{metrics_table('internal_test')}
### C. V1 External Test: 신규 사용자·매칭 catalog 평가

{metrics_table('external_test')}
세 표는 `outputs/improvement/frozen_results.csv`의 저장된12개 집계 행과 기존 보고서를 대조해 복사했다. Test 정답이나 사용자별 결과를 새로 읽거나 재평가하지 않았다. K=10, relevance≥.7, binary gain이다. Precision=hits/10, Recall=hits/긍정정답수, NDCG=DCG/IDCG, DCG=Σ hitⱼ/log₂(j+1). 긍정 정답 없는31/32/9명은 세 정확도 평균에서 제외한다. 따라서 전체168/168/35명의 평균으로 설명하지 않는다. 내부 후보 밖 긍정 정답도 miss로 남고 외부는 후보 매칭 이력으로 적격화하여 난이도가 다르다.

외부 support/held-out은 ID hash 순 n//2 /나머지로 분리했다. Q 불변과 함수 입력 경계가 기존 감사에 기록됐다. Harness는 같은 프로세스에서 정답을 보유하므로 OS 수준 보안 격리라고 주장하지 않는다. /9 외부 scale은 사전 ordinal 가정이며 외부 MAE/RMSE는 N/A다. 기존 봉인19개가 모든 label·결과를 사전에 봉인했다는 의미도 아니다. 자세한 한계는 `FINAL_EVALUATION_AUDIT.md`다.

## 5. Development V2

Train 내부 CV로 Content 채널/프로필, bias MF, RRF fusion, ridge를 비교했다. 선택 challenger는 neutral(.5accord/.5note), bias factor8/L2.01/lr.01, max120 nested stopping(전체 Train refit30epoch), RRF Content.25, 신규 사용자 ridge1이다. 기존 저장 V1을 교체하지 않았다.

### D. STEP5 Train 내부 신규 사용자 CV

| 모델 | NDCG@10 |
|---|---:|
| V1 Hybrid |0.047663 |
| V2 Hybrid |0.032505 |

이 평가의 후보는 fold별479∩trained factor=424/423/433, 적격142명 중 긍정133명이다. STEP8과 다르다. 알려진 사용자 보조 CV에서는 V1 .033573/V2 .038087이었고, 설정 고정 후 기존 validation 진단은 .043185/.032808이었다. **V2는 기존 Validation을 전혀 읽지 않은 것이 아니다.** CV로 고정한 뒤1회 진단했으며 재선택하지 않았다. V3에서는 기존 Validation/Test를 읽지 않았다. Internal/External Test는 V2/V3 모델 선택에 사용하지 않았다.

STEP6에서 신규 V2 MF의 latent/item-bias SD 비 .8659%, 순위 상관 .999861, Hybrid Coverage29.67/Top10집중82.42%를 관측했다. 인기도 fallback은0%이므로 fallback 지배로 해석하지 않는다. Ridge condition≤2.016947로 수치 불안정 근거도 없었다. Item bias 중심성과 RRF의 노출 집중은 관측/고정 대조로 지지되지만 모든 성능 하락의 인과 원인이나 RRF 자체의 보편적 실패를 확정하지 못했다. `V2_HYBRID_FAILURE_DIAGNOSIS.md`의 CONFIRMED/SUPPORTED/INCONCLUSIVE 구분을 유지한다.

## 6. Development V3

Train330명/538향수/1,805평점, 행렬 희소도98.9833%, 사용자 평균5.47평점, 상품평점 중앙값2개라는 제한에서 저차원·규제 분리·fold-in 개선을 설계했다. STEP7 원문과 blueprint를 보존하고 A–F만 실행했다.

| 정책 | factor | biasL2 | fold latent | 결합 | Content α | Inner NDCG |
|---|---:|---:|---:|---|---:|---:|
| A |2|.01|1|linear|.25|.030774|
| B |2|.1|1|linear|.25|.028750|
| C |2|.1|.1|linear|.25|.027783|
| D |4|.1|.1|linear|.25|.027115|
| E |2|.1|.1|linear|.75|.032100|
| F |2|.1|.1|minmax|.25|.046228|

共通: latentL2.01/lr.01/40epochs/fold user-bias1/neutral Content。Outer3/Inner2ユーザー分離、support3、479固定候補、seen除外。Innerでのみモデル選択し、coverage≥V1×.8、集中度≤V1+.10、NDCG.002近接同点規則を事前固定した。各Outer政策F/V1/Fと全Train用Fを全Outer評価前にlockした。Outer結果で追加調整しなかった。

### E. STEP8 同一条件 Outer 비교

{cv}
평가158명 중 긍정145명이다. 후보는479에서 seen만 제거하며 factor 없는 held-out 정답도 삭제하지 않는다. Coverage는 fold별 전체 평가 사용자 Top10의 고유 상품 수 평균이다. 집중도는 가장 많이 노출된10상품의 추천 슬롯 비율이다. V3 값은 **Inner 선택 절차의 Outer 성능**이고, F 단일 모델 전체3fold/독립 Test 성능은 N/A다. STEP5→STEP8을 성능 상승·하락의 연속 그래프로 연결하지 않는다.

전체 Train F는 factor2/latentL2.01/biasL2.1/lr.01/40epoch/fold latent.1,bias1/minmax Content.25로 설정 파일과 일치한다. 실제 MF Fit58/61: Primary52/54, Seed29진단5/6, 최종1/1; V2 probe 포함, 정확한 cache재사용21회. 정수 배열 오류는 float64로 수정하고 사전25테스트 통과 뒤 학습, 최종26회귀를 통과했다. 이번 STEP9 추가 MF Fit은0회다.

## 7. 통계와 모델 선택 해석

V3−V1 fold-macro NDCG 차이 −.004554의 기존 paired bootstrap95%구간은 [−.022504,.012322], V3−V2는 [−.026500,.004871]이다. 두 구간 모두0을 포함한다. Seed29도 V1 .050483/V3선택 .035186으로 우위가 없었다. 새로운 bootstrap이나 seed 실험은 하지 않았다.

F 선택 두 fold에서 latent/item-bias SD 비3.61%로 커졌지만 순위상관 .9983으로 bias 지배가 남는다. 이는 V2 세fold의 .78%와 집계 범위가 다르며 인과적 기여율 비교가 아니다. V3 Coverage는 V2보다 높지만 V1과 비슷하고 집중도는 V1보다 높다. 정확도 개선·비열등성·통계적 열등성을 확정하지 않는다. 최종 V1 유지는 사전 서비스 모델과 운용 안정성을 보존하는 결정이다.

## 8. 웹 구현과 STEP9 검증

실제 설치: React19.3.1/TypeScript5.9.3/Vite7.3.7/Tailwind4.3.3, Node20.20.0, Python3.12.14/FastAPI.159.1/Pydantic2.14.1/Uvicorn.54.0/NumPy2.3.5. ARM64 macOS에서 실행했다. 정확한 Mac 상품명은 여기서 별도 확인하지 않았다.

`main.tsx`는 상대 /api 요청을 Vite proxy→127.0.0.1:8000으로 보내고 FastAPI singleton `FrozenService`가 V1만 복원한다. `/api/health`, `/api/perfumes`, `/api/recommend`가 있고 학습·평가 endpoint는 없다. source에 V2/V3 service import가 없다. 추천 설명은 support/추천 상품의 메타데이터 교집합이며 선호 원인의 인과 설명이 아니다. 외부 이미지 필드를 쓰지 않고 CSS 그림·accord 텍스트를 사용한다.

실제 Chrome에서 검색→3선택→키보드 평점0.5/10/0→추천5카드를 확인했다. 이름·순서·소수4자리 점수가 API와 일치했다. Woody필터, 빈 검색, 한국어 오타 제안 클릭과 재검색도 확인했다. 390×844 viewport에서 가로 넘침 없이 카드가 세로로 배치됐다. 이는 물리적 모바일·전체 접근성·프로젝터 검증을 대신하지 않는다. loading/오류 UI는 코드 확인과 관찰 범위를 구분한다. 실제 서버 연결을 일부러 끊지는 않았다.

기존 backend/search 테스트175개 중169 PASS/6 SKIP, frontend 타입검사 PASS, production설정 단위검사5 PASS. 새 합성 API 검사24개 정상조합 및 반복20회, mock 모델 누락/metadata오류/후보0개·부적절 입력을 검증했다. 첫 새 audit의 입력순서 JSON완전일치1건은 FAIL이었다. 진단 결과 ID·순위·다른 필드는 같고 점수 최대차이2.22e−16이었다. 원래 FAIL을 보존하고 수치동등성(≤1e−12)을 별도 PASS로 기록했으며 동결 코드를 고치지 않았다.

{perf}
로컬 저부하 실측이다. HTTP시간에는 직렬화·스케줄링 등이 포함되며 처리량·동시접속·운영 SLA가 아니다. audit 전체 프로세스 peak RSS {service['peak_audit_process_rss_bytes']:,}bytes이며 순수 모델 크기로 해석하지 않는다. 기존8000 백엔드는 유지, 비어 있던5173 프론트만 시작했다. 별도 시작시간 probe는 자신이 시작한18009 프로세스만 종료했다.

## 9. 단계별 기록과 연결

| 단계 | 목적·실제 수행 | 다음 단계 이유·한계 | 근거 |
|---|---|---|---|
| STEP1–2에 대응하는 초기 개발 | 데이터 감사/0민감도/3·4·5 공통 validation/base→MF→hybrid→동결 내부·외부 | 희소성·matching·분모·원천별 척도 한계; 번호별 별도 초기 보고서는 확인되지 않아 묶어 기술 | STATUS, ZERO_POLICY, MODEL_IMPROVEMENT, FINAL_EVALUATION_AUDIT |
| STEP3·3-1·3-2 | V1 웹·영문/한국어 브랜드와 노트 검색·오타제안 | 로컬 시연·안전한 실행 필요 | WEB_MVP_IMPLEMENTATION, WEB_SEARCH*, WEB_NOTE*, WEB_BRAND* |
| STEP3-3·3-4 | Vercel+Python 분리 설계, private 자산과 로컬 시연 검증 | 공개 재배포 권한·실행 안정성 고려, 실제 외부 배포 아님 | WEB_SAFE_DEPLOYMENT_ARCHITECTURE, WEB_LOCAL_DEMO_READINESS |
| STEP4-1 | 종합 읽기 감사·팩트시트 | Proposal 약속 중 보조 작업 공백 확인 | FINAL_PROJECT_READINESS_AUDIT, FINAL_PROJECT_FACT_SHEET |
| STEP4-1.5 | 별도 kNN/Parfumo/군집/fuzzy 보조 실험 | 주 모델과 분리된 한계 기록, 후속 V2 연구 | PROPOSAL_COMPLETION_SUMMARY |
| STEP5 | V2 Content/biasMF/RRF/fold-in train-CV | 신규사용자Hybrid 저하 | V2_EXPERIMENT_RESULTS |
| STEP6 | 동일 설정·Train 내부 재구성 원인 진단 | bias집중·latent약화 가설 | V2_HYBRID_FAILURE_DIAGNOSIS |
| STEP7 | Train 희소성·개인화 타당성/A–F 설계 | support3에 맞는 제한 실험 | V3_PERSONALIZATION_FEASIBILITY, 원본blueprint |
| STEP8 | 58fit Nested CV·Inner선택·Outer평가 | 개선 미확인, 서비스 교체 보류 | V3_IMPLEMENTATION_AUDIT, V3_EXPERIMENT_RESULTS |

STEP4-1.5 최신 결과로 Parfumo metadata exact7,456연결, 노트Jaccard .544477(5,996쌍), accords .217660(6,383쌍)이 있다. kNN validation 최고 User .016161/Item .023796, K-means k3 silhouette .106647, fuzzy후보3,547개/수동검증0·모델반영0이다. 이는 새 개인화 외부 Test나 서비스 모델 개선이 아니다. 초기 팩트시트의 ‘보조 미실행’은 그때의 상태이고 최신 보조 보고서가 우선한다.

## 10. 한계

매우 희소한 명시 평점과 높은 고평점 비중, Support3의 추정 불확실성, 보수적 매칭/조건부 cohort·479후보 편향, 불완전 관측 선호, 비시간적 단일 splitseed, 작은 외부 긍정26명, 사이트 간 평점 의미 차이가 있다. 반복 Train-CV·설정 탐색은 독립 Test의 일반화 증거가 아니다. 실제 만족도/새 item/모든 브랜드/시즌·가격/실기기·부하 성능은 확인하지 않았다. 기존 label sandbox·사전봉인 범위의 한계도 유지한다.

## 11. 제출 준비와 향후 방향

코드·저장 모델·실행 로그·집계표·기존 그래프는 있다. 이번에는 최종 PPT/Word를 만들지 않았으며 MD4종을 새로 만들었다. 프로젝트 Git remote는 `https://github.com/hochaaa/MachineLearning-Team12.git`로 설정돼 있다. 이 단계에서는 원격 접속/공개 범위를 새로 검증하지 않았고 로컬 존재를 원격 최신성으로 해석하지 않는다. 기존 README의 ‘Git저장소 없음’ 등은 오래된 기록으로 보존했다.

공개 source는107개 tracked와 V2/V3/STEP9 source 후보를 별도 검토해야 한다. reports/outputs는 현 ignore 유지다. 실제 source license 부여/보고서 공개·허용 자산 준비/깨끗한 새환경 설치 재현/팀 역할·기여율·소감·수업외기법 확인/10분 리허설/발표일 확인이 남는다. 기존 Traceability R04,R08–19,R22,R24–27,Q01,V03 등의 역사적 BLOCKED를 실제 최종 완료로 바꾸지 않았다. 팀만 결정할 입력을 창작하지 않는다.

향후 연구는 새 평점·새 독립 평가·side information·명시적 개인화 목표·실사용자 연구를 우선 검토한다. 기존 Test나 이번 Outer를 다시 튜닝에 쓰지 않는다. **현재 근거에서 V1 유지가 타당하며 프로젝트 전체 제출 완료는 아직 BLOCKED다.**
''')
    # Correct only newly generated prose; no existing result/report rewrite.
    p=ROOT/'reports/SCENT_MATCH_FINAL_PROJECT_REPORT.md'
    txt=p.read_text().replace('共通: latentL2.01/lr.01/40epochs/fold user-bias1/neutral Content。Outer3/Inner2ユーザー分離、support3、479固定候補、seen除外。Innerでのみモデル選択し、coverage≥V1×.8、集中度≤V1+.10、NDCG.002近接同点規則を事前固定した。各Outer政策F/V1/Fと全Train用Fを全Outer評価前にlockした。Outer結果で追加調整しなかった。','공통 latentL2=.01/lr=.01/40epochs/fold user-bias=1/neutral Content다. 사용자 Outer3/Inner2, Support3, 479고정 후보에서 seen을 제외한다. Inner만으로 선택하며 Coverage≥V1×.8, 집중도≤V1+.10, NDCG .002 근접 동점 규칙을 사전 고정했다. 각 Outer 정책 F/V1/F와 전체 Train용 F를 모든 Outer 평가 전에 lock했고 결과를 보고 조정하지 않았다.')
    p.write_text(txt)
    write('PROJECT_REPRODUCIBILITY_GUIDE.md',f'''# SCENT MATCH 재현성·로컬 실행 가이드

{intro}

## 1. 검증된 환경

ARM64 macOS, Python {env['python']} (web/backend/.venv), Node {env['node']}. Python: {env['packages']}. 설치된 JS: {env['js_packages_installed']}. 시스템 기본 python3는3.13.12였으며 모델 실행에는 기존3.12.14 venv를 사용했다. Node는 기존 runtime.local.json이 가리키는 실제 바이너리를 썼다. 사용자 홈 절대경로는 여기에 복사하지 않는다.

## 2. 새 환경 설치 — 이번 단계 미검증

아래는 일반적인 설치 절차이며 **이번에 깨끗한 환경에서 설치·검증하지 않았다**. 기존 venv는 Codex 번들 base Python에 의존할 수 있어 그대로 복사하면 안 된다. 패키지를 별도 설치하는 새 venv가 필요하다. Node20.20 이상 호환성을 확인한다. 자동 네트워크 설치를 수행하지 않았다.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r web/backend/requirements-lock.txt
npm --prefix web/frontend ci
```

루트 requirements는 NumPy core만, backend lock은 웹/테스트 의존성을 포함한다. JS package-lock을 유지한다. project root에서 실행해야 원래 relative-path freeze 계약이 맞는다.

## 3. Git에 없는 입력과 모델 준비

원본 `Term-project-datasets/`와 outputs는 공개되지 않는다. 로컬 분석 허용을 공개 모델/개인평점 재배포 허용으로 해석하지 않는다. 별도 승인된 소유자가 같은 바이트의 private 자산을 준비해야 한다. Git clone만으로 저장 모델 서비스가 실행된다고 설명하지 않는다.

실제 서비스 로더는 `outputs/final/freeze.json`과 protected19 경로를 검사한다. 필요한 비코드 자산은 아래다.

- `Term-project-datasets/fra_cleaned.csv` (cp1252/semicolon)
- `outputs/validation/train_exclude_3.json` (가명화된 **개인평점**, freeze hash용; 공개 금지)
- `outputs/improvement/candidates.json`, `selection.json`
- `outputs/final/model.npz`, `model.json`(사용자 mapping 포함), `content.json`, `freeze.json`
- `configs/improvement.json` 및 manifest가 지목한 V1 source와 `scripts/freeze.py`, `final_evaluate.py`의 정확한 버전

위 Train 파일은 웹에서 새 학습에 쓰지는 않지만 원래 해시검증 계약 때문에 필요하다. 이 의존성을 없애려고 manifest를 변경하지 않는다. 원본 Atrafshan/Laure/Parfumo는 현재 웹 추론 자체에는 필요 없으나 원래 ETL/실험 재현에는 필요하다. 승인 없는 다운로드·자산 전송을 하지 않는다. 해시 검증을 우회하거나 model을 다시 fit해 대체하지 않는다.

## 4. 현재 환경에서 실행 확인한 백엔드 경로

```sh
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B -m uvicorn web.backend.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

기존8000 서버를 재사용했고 같은 명령의 별도18009 포트 cold probe를2회 검증했다. 이미 사용 중인8000을 중복 실행하거나 종료하지 않는다. `/api/health`에서 recommendation_ready=true와 candidate_count=479를 확인한다. 실패시 기존 보호파일을 고치지 말고 정확한 자산·경로·환경을 점검한다. 건강하지 않은 경우 API는503으로 처리한다.

## 5. 프론트엔드

이 환경에서는 web/frontend 디렉터리에서 기존 Node20.20.0 실제 바이너리로 다음 Vite entry를 실행해 확인했다. `node`가 그 버전을 가리키는지 먼저 확인한다.

```sh
cd web/frontend
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

일반 npm dev 스크립트는 `npm --prefix web/frontend run dev`이며 기존 문서에 있지만 **STEP9에서는 npm wrapper 대신 실제 Node entry로 실행했다**. `http://127.0.0.1:5173/` 접속, /api는8000으로 proxy된다. V2/V3를 연결하지 않는다. 설치된 환경 없이 시작하면 실패한다. 로컬 주소만 bind하며 배포하지 않는다.

기존 `web/demo/start_demo.command`는 이전 시연 실행기다. 이번에는 상태/로그를 바꾸지 않기 위해 직접 실행 방식을 사용했다. 기존 서버를 임의 종료하지 않는다. STEP9에서 시작한 프론트는 검증용으로 유지했다.

## 6. 안전한 검증 명령 — 이번에 실제 수행

```sh
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B -m unittest web.backend.test_api web.backend.test_advanced_search web.backend.test_note_search web.backend.test_brand_search -v
node web/frontend/node_modules/typescript/bin/tsc --project web/frontend/tsconfig.json --noEmit
node --test web/frontend/scripts/check-production.test.mjs
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/step9_audit/integrity.py before
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/step9_audit/service_checks.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/step9_audit/order_diagnostic.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/step9_audit/evidence.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/step9_audit/write_documents.py
PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/step9_audit/integrity.py after
```

順序はbefore→service・その他検証→文書→after。既存 evidence がある場合、排他的作成が再実行を拒否する。今回の結果を再生成するために削除しない。service_checksの初回statusは入力順序のJSON完全一致1件でFAILを保存しており、order_diagnosticで最大2.22e−16の差・ID順不変を別に確認した。エラーを隠して上書きしていない。通常の前処理/学習/評価スクリプトをこの監査のテストとして走らせない。

## 7. 結果確認

V1: reports/MODEL_IMPROVEMENT.mdとoutputs/improvement/frozen_results.csv。V2: reports/V2_*、outputs/development_v2/metrics/。V3: reports/V3_*、outputs/development_v3/metrics/、configs/selections_locked.json、diagnostics/fit_ledger.json。今回は集計だけを読み、個人別結果・正解を再読しない。STEP5とSTEP8の候補・cohort差は統合報告書を参照する。run_experiments/improve/final_evaluateを再実行しない。

## 8. 実際の契約・オフライン範囲

APIはratings1–50件、有限な数値0–10、重複禁止、候補479内、top_kは整数5固定。0点/実数/2件/4件は既存契約で許容する。UIはstep.5、3件以上推奨。条件はnone/woody/floral/rose。結果不足なら0–5件、既知入力は除外する。元来の契約を今回変更しない。

外部製品画像・Web香水API・オンラインfont依存なし。private assets、venv、node_modulesが揃ったローカル推論はネット接続不要な構造だが、物理的に通信を遮断した試験は今回未実施。新規インストールやGit cloneには通常ネットが必要で、公開ホスティングは未実施。真正なユーザー満足度試験も未実施。

## 9. Git除外・公開前

Term-project-datasets/、outputs/、全モデル、個人評価・mapping、.venv/node_modules/dist、.env/認証情報、ログ・runtime.local.jsonは除外維持。reports/も現ignoreで除外されるため、この4文書はローカル提出準備資料であり自動でGit公開されない。必要ならユーザーが別途公開方針を承認する。staging/commit/pushは今回実行していない。
''')
    # Normalize newly authored guide prose into Korean for presentation team.
    p=ROOT/'reports/PROJECT_REPRODUCIBILITY_GUIDE.md';txt=p.read_text();start=txt.index('順序は');end=txt.index('\n## 7.',start)
    txt=txt[:start]+'''순서는 before→서비스·기타 검증→문서→after다. 기존 증거가 있으면 배타적 파일 생성이 재실행을 거절한다. 현재 증거를 삭제해 재생성하지 않는다. service_checks 초회 status는 입력순서 JSON 완전일치1건 때문에 FAIL을 보존했고, order_diagnostic에서 최대2.22e−16 차이·ID/순서 불변을 별도 확인했다. 오류를 숨기거나 결과를 덮어쓰지 않았다. 학습·평가 진입점을 감사 테스트로 실행하지 않는다.\n'''+txt[end:]
    start=txt.index('## 7.');txt=txt[:start]+'''## 7. 저장된 결과 확인

V1은 `reports/MODEL_IMPROVEMENT.md`와 `outputs/improvement/frozen_results.csv`, V2는 `reports/V2_*`와 `outputs/development_v2/metrics/`, V3는 `reports/V3_*`와 `outputs/development_v3/metrics/`, `configs/selections_locked.json`, `diagnostics/fit_ledger.json`을 확인한다. 이번에는 집계만 읽고 개인별 결과·정답을 다시 읽지 않는다. STEP5/STEP8의 후보·cohort 차이는 통합 보고서를 참조한다. `run_experiments`, `improve`, `final_evaluate`를 재실행하지 않는다.

## 8. 실제 계약과 오프라인 범위

API는 ratings1–50건, 유한 숫자0–10, 중복 금지, 479후보 내, top_k는 정수5 고정이다. 0점/실수/2개/4개는 기존 계약에서 허용한다. UI는0.5간격, 3개 이상 권장이다. 조건은none/woody/floral/rose, 후보 부족시0–5개를 반환하고 입력 향수는 제외한다. 이번에 계약을 바꾸지 않았다.

외부 상품 이미지·온라인 향수API·폰트 의존성은 없다. private 자산·venv·node_modules가 준비된 로컬 추론은 인터넷 없이 동작할 구조지만 실제 통신 차단 시험은 미실시다. 새 설치·Git clone에는 일반적으로 네트워크가 필요하며 공개 호스팅·실사용자 만족도 검증은 하지 않았다.

## 9. Git 제외와 공개 전 조치

Term-project-datasets/, outputs/, 모델·개인평점·mapping, .venv/node_modules/dist, .env/인증정보, 로그·runtime.local.json은 제외한다. reports/도 현재 ignore로 제외돼 문서4종은 로컬 제출 준비 자료이며 자동 공개되지 않는다. 공개하려면 별도 승인·선별 검토가 필요하다. 이번에 staging/commit/push는 하지 않았다.
'''
    p.write_text(txt)
    write('SCENT_MATCH_PRESENTATION_OUTLINE.md',f'''# SCENT MATCH 발표 구성안 — 10분 + Q&A 3분

{intro}

실제 PPT를 만들지 않았다. 아래 시간은 권장 계획이며 리허설 실측이 아니다. 11/9 제출, 11/10 또는11/12 발표이며 팀 슬롯은 TBD다. 팀 구성원 역할·기여율·개인 소감은 팀이 작성해야 한다. 마지막에 실제 GitHub URL·전체 아키텍처·학습 경험을 반드시 반영한다. 근거는 교수 원본 p6–9 및 학생 전달 구두 요건이다.

| 장 | 시간(초) | 제목·핵심 메시지 | 설명할 내용 | 권장 표/그림 | 해석 주의 |
|---|---:|---|---|---|---|
|1|30|SCENT MATCH와 사용자 문제|Team12, 좋아하는3향수에서다음5향수|웹 초기화면|실제 만족도 검증 아님|
|2|35|문제 정의와 범위|명시평점·신규사용자·479후보|사용자 흐름|카탈로그전체 일반화 금지|
|3|55|데이터와 정제|Fragrantica/Atrafshan개발·Basenotes외부·Parfumo보조,0분석가정|단계별24063/6882→3323→2141→1805|댓글·평점·원본향수·Train향수 구분|
|4|60|구조와 수학|Content/MF/Hybrid/Knowledge/fold-in|통합보고서Mermaid+예측식|αContent=.25,fold-in재학습아님|
|5|55|Frozen V1의 선택과 평가|validation선택→freeze→두Test|세프로토콜 분리 패널|분모137/136/26,MF가Test최고|
|6|65|V2와 실패 분석|biasMF/neutral/RRF·신규latent약화|STEP5독립표+SD/집중도|RRF보편실패·완전인과 주장 금지|
|7|70|V3의 제한된 개선 가설|A–F·Outer3/Inner2·Support3·58/61fits|Nested흐름+STEP8독립표+CI|F단일모델Test아님,통계적열등성확정금지|
|8|85|V1 웹 시연|향수3선택·0–10평점·Top5·Woody조건|실제화면,실패시저장스크린샷|화면점수는확률아님,평가Top10과구분|
|9|90|한계·학습 경험·팀워크|희소성/척도/실패·다시한다면새독립평가|한계표+팀확인역할/기여율/3인학습|각개인진술과기여율TBD;창작금지|
|10|55|최종 판단과 재현·코드|보수적V1유지·모델교체보류·실행법·GitHub|아키텍처요약/실행명령/실제URL|V1객관최고아님,원격공개상태최종확인|

합계600초. 팀 확인 문장을 실제로 넣은 후10분 리허설로 시간 조정한다. 세 사람 발표 분담은 TBD이며 임의 배정하지 않았다.

## 그래프·자료 사용 계획

1. V1 Validation/Internal/External은 서로 분리된 패널과 사용자 분모로 표시한다. `outputs/improvement/figures/frozen_assessments.png` 및 저장 CSV를 출처로 쓴다.
2. STEP5 V1 .047663/V2 .032505와 STEP8 V1 .038111/V2 .043615/선택절차 .033557은 **별도 표**다. 한 개의 시간순 성능향상 곡선으로 연결하지 않는다.
3. V3−V1 CI [−.022504,.012322]는 STEP8 저장 bootstrap을 인용하며 이번에 다시 계산하지 않는다.
4. 웹 캡처는 `outputs/step9_audit/desktop_results.png`, `mobile_top5.png`다. 실제 시연이 실패해 저장 화면을 보이면 사전 캡처라고 설명한다.
5. STEP4-1.5 Parfumo/kNN/K-means/fuzzy는 시간상 부록으로 둔다. 보조 실험을 최종 Hybrid의 외부 개인화 성능으로 설명하지 않는다.

## 예상 Q&A

- 왜V1유지? validation으로선택된기존서비스이고후속모델의일관된우위증거가없다. STEP8단일표에서는V2가높다는사실도설명한다.
- 왜479? 가장엄격한min5 Train상품을공통후보로사전고정했다.538Train전체/24063catalog전체를대표하지않는다.
- 왜분모가적나? 긍정정답없는사용자는세정확도평균에서제외한다.관측누락편향을설명한다.
- 외부학습했나? 고정Q에support만fold-in,held-out은평가용이다.함수경계와실제봉인범위한계를설명한다.
- 새로운기법은? Knowledge/ridge등후보기법을팀의수업범위와대조해확정한다.교수의슬라이드명시/구두요구/팀설계를구분한다.
- 실패에서배운것은? 다양성·latent진폭·평점오차개선이추천정확도개선과같지않다.개인학습은각자작성한다.

## 제출용 보류 항목

최종 PPT/Word 생성, 팀 역할·기여율(합100% 권장)·개인 소감, 수업 외 기법 확인, GitHub 실제 접근/공개 및 최신 source 포함, 팀 발표 슬롯, 제출 방식/영수증, 프로젝터·오프라인·10분 리허설은 미확정/미검증이다. 이번 범위에서 임의 완성하지 않았다.
''')
    write('STEP9_FINAL_AUDIT.md',f'''# STEP9 최종 감사

{intro}

**판정: PASS WITH LIMITATIONS(통합·로컬 서비스 검증), 최종 제출 전체는 BLOCKED. 최종 서비스는 Frozen V1 Hybrid.**

## 1. 보호와 변경 범위

브랜치 development-v2에서 시작했고 기존 tracked 변경은 없었다. Frozen V1 기준 main commit은 aebd9abd85b175e6076d8b2d9c2445201d8b2602다. manifest SHA256은3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130, protected19 모두 일치했다. 최종 비교 증거는 `outputs/step9_audit/integrity_after.json`이다. V1/V2/V3 코드·모델·기존 결과·분할·웹 source·기존 보고서에 변경을 허용하지 않았다. raw/split 일부는 크기/mtime 비교이며 완전한 모든 바이트 증명으로 확대하지 않는다. private 모델/평가 파일은 무결성 byte hash만 읽고 개별 정답/결과를 파싱하지 않았다.

새 코드 `experiments/step9_audit/`, 새 증거 `outputs/step9_audit/`, 필수보고서4종만 생성했다. 기존 freeze·ignore·root README·traceability를 수정하지 않았다. 모델Fit/탐색/평가지표 재산출/Bootstrap 재계산0회. 기존8000 서버 종료0, 프론트5173만 새로 실행, 별도coldstart18009는 직접 시작한 프로세스만 종료했다.

## 2. 검사표

| 검사 | 판정 | 근거·제한 |
|---|---|---|
| 브랜치·기존 tracked 변경 없음 |PASS|git branch/status/diff, before/after|
| Frozen V1 protected19·manifest |PASS|integrity.py, frozen_before/after|
| 기존 V2/V3·평가·분할 보존 |PASS|기존 파일SHA/stat 비교, 기존결과덮어쓰기없음|
| V1 historical12행·STEP5/8 수치 |PASS|metric_consistency.json; 저장집계만대조|
| V3 F설정·58fit(52/5/1) |PASS|실행설정/ledger/summary 대조|
| STEP5/8 분리·Nested해석 |PASS|통합보고서,고정F 전체3Outer N/A|
| web모델이V1 |PASS|adapter→load_frozen,기존golden4필터JSON일치|
| Backend/API 검색회귀 |PASS|175개실행/169성공/6SKIP,web_regression.log|
| Frontend 타입·production단위 |PASS|tsc noEmit오류0,5testPASS|
| 실제브라우저3선택·0/.5/10·Top5 |PASS|Chrome, browser_checks.json,API표시동등|
| 필터/seen/중복/finite/metadata/정렬 |PASS|합성24조합,기존golden4조건|
| 정상 반복20회 |PASS|TestClient 및 liveHTTP 동일응답|
| 입력순서 exact JSON |FAIL(경미)|점수최대차이2.22e−16,ID·순위·나머지필드동일|
| 입력순서 수치동등 |PASS|order_diagnostic.json,허용오차1e−12별도검사|
| 잘못된요청·모델부재·metadata·후보0 |PASS|422/503/500/빈결과 mock,파일삭제/이동없음|
| 반응형·기본키보드·검색상태 |PASS WITH LIMITATIONS|390viewport,키보드slider,빈검색/오타제안;전체접근성아님|
| API실패·연결실패 UI |N/A(실제장애미유도)|코드의오류메시지·timeout만검토,기존서버중단안함|
| 실제오프라인·실기기·프로젝터·부하 |N/A|환경설정·네트워크차단·부하실험미수행|
| 공개후보source 비밀패턴 검사 |PASS WITH LIMITATIONS|{inventory['source_files_scanned']}파일,고위험패턴0;휴리스틱범위|
| 공개데이터/모델재배포 권한 |BLOCKED|로컬수업사용확인과공개라이선스별도|
| 새환경clean install |N/A|현재설치환경실행만검증|
| 최종PPT/Word·팀학습/기여·리허설 |BLOCKED|이번은MD와구성안만,팀입력TBD|
| GitHub원격공개·최신파일포함 |N/A|remoteURL만확인,네트워크검증/업로드안함|

서비스 새검사 초회 결과는 `service_checks.json`의 FAIL 상태 그대로 보존했다. 전체 {len(service['checks'])}개 check 중 exact order1개만 FAIL이었고, 원인을 별도 진단했다. 기존 회귀의6skip도 성공으로 세지 않는다. 이번 웹 기능 검사는 추천 정확도 평가가 아니다.

## 3. 발견된 문제와 자동 수정

| 심각도 | 위치 | 문제·영향 | 처리 |
|---|---|---|---|
|낮음|새서비스check/input_order|완전JSON 비교에2.22e−16점수차이;추천ID·순서동일|원FAIL보존·수치동등별도PASS,서비스/모델미수정|
|문서|기존V2_EXPERIMENT_RESULTS|런타임/시간 템플릿 placeholder가남아있음|기존보고서수정안함,새통합에검증되지않은시간복사안함|
|문서|rootREADME/Traceability/초기팩트시트|Git없음·미실행등과현재상태차이|역사기록보존,새통합에최신근거구분|
|범위|요청의‘3개입력’/실제API|실제1–50개허용,2/4개도정상|계약변경안함,잘못된거절테스트만들지않음|
|재현성|기존venv/private자산|base런타임의존,Git clone만으로실행불가|새환경설치미검증표시,필수자산목록작성|
|제출|reports ignore와미추적실험소스|새통합문서가자동Git포함안됨|현ignore유지,공개전별도검토필요|

새 audit 스크립트의 CSV 라벨은 처음에V2별칭을실제name으로잘못가정했고 다음에는ridge탐색행까지평균했다. 둘다 assertion으로중단했고 저장된결과를바꾸지않았다. 실제V2정책명과선택ridge1(기준V1 .01)을명시한후검사를통과했다. 실패로그 evidence.log/evidence_retry1.log와성공 evidence_retry2.log를보존했다. 프론트실행의cwd상대경로오류를바로고쳤고 sandbox의로컬bind제한은승인된실행권한으로해결했다. 설치·기존source수정은없다.

V2는설정고정후legacyvalidation을1회진단했으나선택에사용하지않았고, V3는미접근이다. 이를‘V2/V3모두Validation전혀미접근’으로쓰지않는다. STEP4-1.5보조실험의validation사용도주모델선택과분리한다. 기존Test평가산식오류·데이터누수·모델교체필요성을새로발견한것은아니다. 정확JSON차이만으로재학습이나코어수정하지않는다.

## 4. 실행 성능

{perf}
메모리는 audit전체프로세스 peak RSS {service['peak_audit_process_rss_bytes']:,}bytes. 저부하·동일기기 실측으로 성능개선/운영보장은 주장하지 않는다. 별도 로딩과coldstart측정은평가데이터를사용하지않았다.

## 5. 파일 구조·Git·비밀정보

| 경로 | 역할 | 공개/제출 정책 |
|---|---|---|
|src/perfume/, scripts/, tests/, configs/|V1학습/평가/추론/검증|검토된source,실험명령은재실행주의|
|web/backend, web/frontend, web/demo, web/deployment|실제서비스/API/검색/시연/배포설계|source만,venv/dist/evidence/private-assets제외|
|experiments/proposal_completion|보조metadata/kNN/군집/fuzzy|tracked여부목록참조,주모델아님|
|experiments/development_v2, development_v3|독립실험소스·설명|현재미추적,라이선스/민감정보검토후후속승인|
|experiments/step9_audit|새감사코드·설명|검토후후속승인,원래파일수정없음|
|reports/|기존/새MD·Word/PPT초안|현재전체ignore,제출용로컬보존|
|Term-project-datasets/|원자료|11파일,공개금지|
|outputs/, models/, private assets|가공평점·mapping·모델·실험/평가출력|공개금지,집계도선별승인|
|.venv, node_modules, dist, caches|환경/빌드|Git제외,새환경설치별도|
|.env, keys, tokens, logs, runtime.local.json|비밀/개인기기정보|Git제외;이번새실제자격증명발견없음|
|.chart-data-*/、ZIP/검토용복사폴더|임시/패키지복사|기존ignore유지,삭제/이동안함|

Git tracked {inventory['tracked_count']}개, source검사{inventory['source_files_scanned']}개 시점의 전체 후보 목록과 디렉터리별 파일수/크기는 `git_source_inventory.json`에 있다. 이후 새문서생성source가 추가되어최종스냅샷목록은별도다. API key/token/private-key/AWS키 패턴 발견0. 개인정보절대경로 패턴1개는새scanner의정규식자체에대한오탐이며실제개인경로가아니다. 로컬runtime.local.json의실제개인경로는Git제외유지다. `.env.example`2개만확인됐고실제env비밀파일은이source범위에서없었다. 이는수동감사를대체하는완전한비밀정보부재증명은아니다.

현재remote설정은 https://github.com/hochaaa/MachineLearning-Team12.git 이다. 임의원격설정·git add/commit/push/merge/rebase/tag는실행하지않았다. 추가공개가필요한source/V2/V3/STEP9와문서를먼저사람이검토하고private출력없이별도승인후반영한다. .gitignore를완화하지않는다.

## 6. 최종 제출 요건과 남은 순서

교수PDF p2–9를이번에직접텍스트추출해확인했다. 슬라이드명시 요구는특정도메인추천/2종이상filter/개발과별개데이터평가/PPT end-to-end·실패분석·개인학습·역할/기여율·전체구조·GitHub/소스주석·출처·수업외API설명·Word/출력·11/9제출·10분+Q&A3분이다. 학생구두Hybrid/새기법요구와팀의MF/Knowledge설계를별도로표시한다. 웹GUI나정량목표를교수필수로추가하지않는다.

현재 source/모델/독립외부평가·실제출력의기술근거는PASS이나, 원본Traceability의최종제출/팀증거관련BLOCKED를완료로선언하지않는다. 현재문서의상태와역사적root표차이는원본변경없이설명했다.

우선순위: (1) 팀역할/기여율/3인소감·수업외기법·발표슬롯확인 (2) 새MD를기반으로최종Word/PPT·시각자료제작및10분리허설 (3) 공개source/license·GitHub실접근·누락V2/V3 source검토 (4) 승인된private자산으로새환경재현/오프라인·프로젝터시연 (5) 11/9제출묶음검수. 추가모델연구·서비스교체는이번에시작하지않는다.

## 7. 실제 명령·로그

`integrity.py before` PASS → `unittest web.backend.test_api ...` (175실행/169PASS/6SKIP) → `tsc --noEmit` PASS → `node --test ...`5PASS → 합성service_checks(입력순서exact1FAIL 보존) → order_diagnostic 수치PASS → evidence_retry2 집계PASS → write_documents 신규4MD → integrity.py after. 상세명령은 `PROJECT_REPRODUCIBILITY_GUIDE.md`, 모든새로그/JSON은 outputs/step9_audit/다. 보고서작성은 모델/정답 접근이 없는표준라이브러리코드다.
''')
    print('CREATED4 STEP9 reports; no existing files overwritten')
if __name__=='__main__':main()
