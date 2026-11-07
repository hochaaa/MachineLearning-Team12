"""Summarize saved aggregate evidence; never score users or refit historical experiments."""
import csv,json,os
from pathlib import Path
from .run import ROOT,OUT,json_file,csv_file

EXPERIMENTS=[
 ('V2-1','lambda_tuning','Fold-in λ .01/.1/1','inner_accuracy_pooled.csv'),
 ('V2-3A','fallback_policy','MF 없는 후보의 Content fallback 배율','inner_accuracy_pooled.csv'),
 ('V2-3B','mf_calibration','clip/sigmoid/centered sigmoid','inner_accuracy_pooled.csv'),
 ('V2-4','signed_content','절대/사용자 평균 중심화 Content','inner_accuracy_pooled.csv'),
 ('V2-5','hybrid_weight','α .25/.5/.75','inner_accuracy_pooled.csv'),
 ('V2-7','pairwise_mf','관측 높은 평점–낮은 평점 pairwise MF','inner_results.csv'),
 ('V2-8','rating_aware_content','학습 평점 기반 Content 특징 가중치','inner_results.csv'),
 ('V2-9','personalization','사용자 선호 Ridge/SVD 표현','inner_results.csv'),
 ('V2-11','synthetic_augmentation','실제/합성/저가중 합성 보강 MF','model_comparison.csv'),
 ('V2-12','few_shot_preference','합성 Support5→held-out 선호 W 학습','model_comparison.csv')]

def history():
    """Read only saved aggregate tables, mark Inner and Outer as distinct protocols."""
    records=[]
    for version,directory,change,file in EXPERIMENTS:
        source=Path('outputs/scent_v2')/directory/file
        for r in csv.DictReader((ROOT/source).open()):
            if r.get('track')!='A' or r.get('phase','inner')!='inner':continue
            if not ('hybrid' in r['method'] or directory=='personalization'):continue
            label=r.get('policy') or 'lambda='+r.get('lambda','UNKNOWN')
            records.append(dict(version=version,phase='HISTORICAL_INNER_CV',change=change,policy=label,
                method=r['method'],ndcg_at5=r['ndcg'],users=r['users'],contexts=r.get('contexts','UNKNOWN'),
                source=str(source),adoption='Existing baseline retained per saved selection/report',
                not_independent_validation=True))
    csv_file('experiment_history.csv',records)
    return records

def main():
    """Create narrative/report and append five original presentation documents once."""
    v=json.loads((OUT/'data_validation.json').read_text());s=json.loads((OUT/'dataset_integration_summary.json').read_text())
    u=json.loads((OUT/'user_rating_distribution.json').read_text());high=u['profiles'][0]
    t=json.loads((OUT/'training_data_summary.json').read_text());baseline=t['strict_existing_baseline']
    records=history()
    tables={version:[] for version,_,_,_ in EXPERIMENTS}
    for r in records:tables[r['version']].append(f"{r['policy']} / {r['method']}: {float(r['ndcg_at5']):.6f}")
    nested_table='\n'.join(f"|{version}|{change}|{' ; '.join(tables[version])}|기존 모델 유지|`outputs/scent_v2/{directory}/{file}`|" for version,directory,change,file in EXPERIMENTS)
    narrative=f'''# V1–V2-16 모델 개선 이야기 (2026-10-30)

## 1. 문제 정의와 초기 구조

향수를 경험한 사용자의 평점5개로479 후보 중Top5를 찾는다. 원래 실제 Train pool은330명/1805평점, 후보 안은1733평점이었다. Content는 notes/accord의 binary TF·smoothed IDF·정규화 및 평점 가중 프로필 cosine, MF는4차원/160epoch/lr.01/L2.01/seed12의 명시 평점 SGD다. 신규 사용자는 고정 item factor와 Support만으로 Ridge λ=.01 fold-in을 한다. 둘 다 점수가 있으면 H=.25C+.75M이며 한 성분만 있으면 기존 fallback 규칙을 따른다. MF는[0,1] clipping 및 ID 동점 정렬이다. 무관측은 싫음이라는 정답이 아니다.

## 2. V1의 평가와 한계

Frozen V1은 내부 validation에서 설정을 고르고 내부/외부 Test를 동결 후 평가했다. 저장된 Hybrid NDCG@10은 validation .043185, internal .038533, external .026365다. 원문 `outputs/improvement/frozen_results.csv`, `reports/MODEL_IMPROVEMENT.md`. 이 셋은 사용자·데이터 출처가 다르며 서로 점수를 빼서 개선 폭이라 하면 안 된다. 특히 이@10을 다음의 신규 사용자@5와 직접 비교하면 안 된다.

## 3. V2-0: 서비스와 비슷한 신규 사용자 평가 환경

사용자 전체를 해당 fold의 Train에서 제외하고 Support5/나머지 답으로 평가했다. Outer3-fold,75명 중 긍정 정답69명, 후보479다. Content/MF/Hybrid NDCG@5=.027594/.015966/.042667. 이는 Frozen 가중치를 그대로 평가한 점수가 아니라 고정 V1 설정으로 fold별 재학습한 baseline이다. 자료: `outputs/scent_v2/baseline/accuracy.csv`, `REPORT.md`.

MF의 신규 사용자 점수가 제한적이어서 정규화·결합·표현을 통제 실험했다. 모델 선택은 Inner에서만 하고 Outer는 반복 활용된 탐색적 증거로 구별했다. 이후 실험들을 통과할 때마다 독립된 새 검증이 생긴 것은 아니다.

## 4. V2-1~V2-9: 구조 가설을 검증했지만 성공을 과장하지 않기

아래는 각 실험의 **저장된 Inner Track A** 집계다. 변경 모델마다 수치가 높아질 수 있지만, 사용자별 paired 불확실성·coverage·강건성 등 사전 채택 조건을 함께 봤다. 동일 baseline값의 반복은 추가 개선 증거가 아니다. 원자료 및 표의 전체 행은 `experiment_history.csv`에 있다. V2-9 ranker는 정책별 서로 다른 모델이므로 method와 policy를 같이 읽는다. raw/sigmoid diagnostic은 자동 채택 후보가 아니다.

|실험|바꾼 변수|Inner NDCG@5(정책/모델별)|채택|저장 근거|
|---|---|---|---|---|
{nested_table}

- **V2-1:** 큰 λ에서 안정성은 개선됐지만 정확도 개선의 CI가0을 포함했다. 세 Outer 모두 .01을 유지했다. 안정성과 정확도는 별개다.
- **V2-2:** 점수 분포와 fallback을 진단했다. C와MF가 모두0–1이라고 척도가 같지는 않았다. H–MF Pearson .9802, λ1에서 fallback Top5 점유율1.47%→41.33% 관측. 이는 인과 확정이나 새 정책 채택이 아니다. `score_diagnostics/REPORT.md`.
- **V2-3A/3B:** fallback 배율/score calibration을 통제했다. 순위·동점·안정성 변화와 추천 정답 개선은 달랐으며 기존 정책을 유지했다.
- **V2-4/5:** signed 프로필과 Content 가중치 확대를 시험했지만 사전 조건을 충족하지 못했다. 높은 점추정만 보고 채택하지 않았다.
- **V2-6:** 긍정 정답422개 중314개(74.41%)가 Content/MF 모두Top20 밖에 있었다. 이것만으로 MF 손실이 원인이라고 단정하지 않고 pairwise 가설로 이어갔다. `failure_diagnosis/REPORT.md`.
- **V2-7:** 관측 높은/낮은 평점 간 pairwise MF를 시험했으나12회 실제 fit 이후에도 baseline 유지. 관측하지 않은 향수를 싫음으로 만들어내지 않았다.
- **V2-8:** rating-aware 특징 학습6회, 추가MF fit0. 새 표현을 학습했지만 정확도·다양성·강건성 채택 조건은 충족하지 않았다.
- **V2-9:** 개인화 신호를 진단하고 regularized 사용자 선호 Ridge/SVD 모델을6회 학습했다. 개선 채택 조건 미충족, 서비스 Hybrid 유지. 원문 `personalization/REPORT.md`, `selection_locked.json`.

## 5. V2-10~V2-12: 합성 데이터는 실제 취향을 대신 검증하지 못했다

V2-10은 전체 평가75명을 제외한 Train에서 분포를 추정해 가상1000명/15362평점을 생성했다. 형식·재현성 검증은 실제 사용자 정확도 향상의 증거가 아니다. `synthetic_data/REPORT.md`.

V2-11은 실제/합성/낮은 가중치 합성보강 MF를 통제 비교했다. Inner Hybrid는 각각 .040170/.014929/.040901이며 보강 점추정의 소폭 증가만으로 채택하지 않았다. 실제MF fit18회, 기존 모델 유지. V2-12는 합성 few-shot W 학습6회, 신규MF fit0. 결합 모델 Inner .040170으로 baseline과 같았고 채택하지 않았다. 합성 생성기의 가정과 실제 사람의 향 경험·노출·평가 방식은 다르며 충분한 실제 held-out 일반화가 입증되지 않았다. 수치 출처는 위 표와 각 `summary.json`이다.

## 6. V2-13: 알고리즘 반복 변경보다 데이터/평가의 병목을 확인

strict 공통 Train은254명/823평점이며479 중172개 미관측,374개는2개 이하 관측이었다. 이것은 원래 각Outer의1531/1481/1493 학습행과 다르다. 추천375슬롯 중362개는 기존 평가에서 미관측이었고 긍정 사용자69명 중59명 NDCG0. 모르는 정답이 많으므로 평가0을 모두 잘못된 추천이라고 해석하지 않는다. 이 사실 역시 모델이 좋다는 증거는 아니다. `data_evaluation_diagnostics/REPORT.md`.

## 7. V2-14~15: 실제 자료를 얻기 위한 경로

V2-14는 경험한 향수 평점을 받는 로컬 수집·저장·개발/독립평가 분리 시스템을 구축했다. 그 단계 완료 당시 새 참여자/평점은0/0이었다. 이번 CSV가 V2-14의479 카탈로그를 사용했다는 근거는 없으며 외부 catalog ID를 그대로 동일시하지 않는다.

V2-15는 외부 자료 후보/제외대상10개를 검토했으나 사용 조건과 개별 명시 평점 요건을 만족하는 신규 자료를 확보하지 못했다. 신규 실제 평점0, 학습 추가0. 무단 수집이나 평균 평점→가짜 사용자 변환을 피하고 권한·매칭·중복·scale 검증 코드를 준비했다. `external_real_data/REPORT.md`.

## 8. V2-16: 실제 경험 평점은 생겼지만 서비스 후보와 연결되지 않았다

참여자의 로컬 저장/학습/평가/비식별 집계 발표 동의를 사용자에게 확인한 CSV를 직접 검증했다. **{v['users']}명/{v['rows']}평점/{v['unique_product_ids']}제품**, catalog73/custom12, 결측0·user/product ID 중복0. 평균{v['score']['mean']:.6f}, 중앙7, 범위4–10이다. 실제 사용 경험이라는 사용자 확인과 데이터 형식의 기술적 검증은 구별한다.

catalog73개 평점의 ID는 원래479 URL이 아니며 브랜드도 고정 후보의 정확 브랜드 색인에 없다. Byredo/Diptyque/Le Labo/Jo Malone London/Aesop/Tamburins를 유사한 다른 브랜드 제품으로 붙이지 않았다. custom12개는 한국어명/판본 등 수동 검토가 필요하며 확정하지 않았다. **정확 매칭0, 안전한 학습 추가0, Support5+답을 구성할 수 있는 매칭 사용자0.**

원본 이력 수만 보면6개 이상 사용자는3명이고5개 이상은5명이다. 그러나479 정합성을 적용하면 모두 평가 부적격이다. 가장 활발한42개 평가자도 매칭0이다. 기록은 원본점수 그대로 격리 보존했다. 이 사람의평점을 지우거나 평균보정하지 않았으며 새로운 Notes/Accords도 만들지 않았다.

따라서 A/B 재학습·NDCG·bootstrap을 **실행하지 않았다**. “평점85개를 추가해서 성능이 유지/개선/악화됐다”는 결론은 모두 근거가 없다. 실제MF fit0, 가중치 파일없음. 기존823개와 데이터 입력이 같다는 이유로 미실행 모델의 점수를 복사하지 않았다. 모델 비교 행은 NOT_EVALUATED다. 새 사용자 자료는 기존 평가자와 다른 namespace라는 이유만으로 독립성을 보장하지도 않는다.

특징 수는 혼동을 구분했다: 기존479 메타데이터의 활성 token union은574이고, 보존된 runtime IDF 사전은604이다. 범위가 다른 수치로 기존 모델을604차원으로 바꾼 것이 아니다. 외부 제품의 메타데이터를 추정해서 호환을 만들지 않았다.

## 9. 현재 모델과 V2-17 계획

서비스는 검증된 기존 Frozen Hybrid를 유지한다. 지금까지의 실험에서 사전 채택 기준을 만족하는 새 정확도 개선을 입증하지 못한 상태다. baseline 유지 자체를 성능 상승으로 말하지 않는다.

우선순위는479에 실제로 연결되는 경험 평점을 별도로 확보하는 것이다. 예컨대 기존 웹의479 탐색 목록에서 **실제로 경험한 제품만** 선택하게 하며 경험 없는 제품에 평점을 강요하지 않는다. 추가 제품 후보 확장은 이번 작업에서 금지되었으므로 향후 별도 설계/승인이 필요하다. catalog export 또는 공식 제품·판본 대응표를 받으면 custom12개만 독립적으로 재검토할 수 있다.

V2-17의 Max Similarity/Top-k Similarity/Multi-Prototype Content는 **예정**, 구현/성능은 NOT_EVALUATED다. 이번 무매칭 결과만으로 단일 취향 프로필이 정확도 병목이라고 단정하거나 복수 취향 모델이 해결한다고 예측하지 않는다. 호환 데이터와 신규 사용자 단위 Support/held-out 프로토콜을 먼저 확보해야 가설을 시험할 수 있다.

## 10. 발표용 흐름도와 말할 수 있는 결론

```mermaid
flowchart TD
  A[479후보 · Content+MF Hybrid] --> B[V2-0 신규사용자 Support5 평가]
  B --> C[V2-1~9 정규화·결합·표현 통제 실험]
  C --> D[사전 채택 기준 미충족 · 기존모델 유지]
  D --> E[V2-10~12 합성 학습 검증]
  E --> F[V2-13 희소 관측·불완전 평가 확인]
  F --> G[V2-14 수집 도구 · V2-15 외부 권한 조사]
  G --> H[V2-16 실제85평점 확보]
  H --> I[479 정확매칭0 · 학습 및 평가 미실행]
  I --> J[호환 경험평점 확보가 선행 · V2-17은 예정]
```

발표 문장: “정규화와 표현 변경을 반복 검증했지만 안정적인 개선을 입증하지 못했습니다. 실제 사람의85개 평점을 얻는 데는 성공했으나, 기존479개 서비스 후보와 연결되는 제품이 없어 이번에는 학습하지 않았습니다. 데이터 수집량뿐 아니라 제품 정합성과 평가 가능성이 모델 개선의 전제임을 확인했습니다.”

개별 팀원 소감·담당·기여율은 팀 확인 전 미확정이다. 이 글은 통합 기술적 해석이며 실제 개인의 학습 소감을 대신하지 않는다. 새 그래프 이미지/PPT 파일은 만들지 않았으며 비교표·CSV와 Mermaid 흐름도를 제공한다.
'''
    (OUT/'MODEL_IMPROVEMENT_NARRATIVE.md').write_text(narrative)
    summary=f'''# V2-16 — 실제 평점 통합 및 동일 Hybrid 재학습 검토 (2026-10-30)

## A. Executive Summary
**감사/보존 PASS; 데이터 통합·재학습 BLOCKED_NO_EXACT_479_MATCHES.** 실제85개를 확보했지만479 정확 연결0, 안전한 학습 추가0, A/B NDCG 개선 여부 NOT_EVALUATED. 재학습/추론/튜닝0회, 새 모델 가중치 없음.

## B. 신규 CSV 검증 결과
`data_validation.json`:12명/85행/58고유product ID. catalog73/custom12. 점수4–10, 평균7.752941, 중앙7, 모집단표준편차1.728011. 0.5단위 준수(현재 실제값은정수). 결측0, user/product ID 중복0, 정규화된 user/brand/name 중복0. 언어가 다른 동일 제품의 중복 가능성은 custom 검토 전 UNKNOWN. CSV SHA256 `{v['original_sha256']}`. 원본은 Downloads의 `scent-ratings.csv`를 읽기만 했다. 사용자에게 로컬 저장·학습·평가·비식별 집계 발표 동의 범위를 확인했으며 재배포 허가를 생성하지 않았다.

## C. 사용자별 평점 분포
활동수 분포:1개4명,2개1명,3개2명,5개2명,9개1명,12개1명,42개1명. 신원이 없는 활동 순위별 서술 통계는 `user_rating_distribution.json`에 비공개 저장했다.42개 평가자는 전체의49.41%지만 실제학습비중은0이다. 평균{high['ratings']['mean']:.6f},표준편차{high['ratings']['population_std']:.6f},10점비율{100*high['ratings']['maximum_score10_fraction']:.2f}%,5미만{100*high['ratings']['low_below5_fraction']:.2f}%,브랜드5개. 기존574특징에 연결되는향수가0이므로 Notes/Accords 취향다양성은미측정이다. 브랜드5개를 향취다양성5개로 바꾸지 않는다. 높은점수를 이유로 삭제/보정하지 않았다.

## D. 기존479 향수 매칭
ID 직접 일치0. catalog73행/46제품의 브랜드가 고정479 정확브랜드색인에 없다. custom12행/12제품은수동검토. 정확매칭0/고유향수0/매칭사용자0. `perfume_matching_report.csv`는58제품별 출처/표기/건수/판정을 제공하며 사용자ID는 없다. 농도·연도·flanker를 제거하지 않았고 새로운 브랜드/제품 번역이나 fuzzy자동확정을 하지 않았다. 신규 데이터가 catalog에서선택되었다는 사실은우리479소속증거가아니다. custom12를존재하지않는제품이라고단정하지않는다.

## E. 실제 학습 추가 평점
0개. 전체85개 원점수는 `private/unmatched_ratings.csv`에 출처별 HMAC가명/원점수/제품표기/격리이유와함께 보존했다. 원본participant ID를 쓰지않았다. 독립 HMAC key와 출력폴더0700/파일0600은로컬비공개다. 아직가명개인자료이므로 공개/외부전송금지다. 합성평점 없음. 새 MF용 합본/모델가중치 파일 없음.

## F. 학습·평가 분리
원본평가75명의910이력은상품·평점값decode전skip. strict기존train은후보제한전255명/895행,후보내254명/823행/307관측제품. 실제원래Outer학습1531/1481/1493행과혼동하지않는다. 신규 raw이력≥6명수3,≥5명수5지만 매칭후Support5+heldout가능사용자0. 단5개로는답이없다. 억지평가분할/평가사용자재학습없음. 기존사람과신규사람중복은UNKNOWN이므로 미래자료통합에서별도검토해야한다.

## G. 기존 Hybrid 재학습
실제MF.fit호출0. 빈추가분gate가차단했으며B모델을학습했다고표현하지않는다. 고정계획은factors4/epochs160/lr.01/L2.01/seed12/foldinλ.01/α.25,후보479,동일Content·입력제외·동점규칙이다. 후보의활성특징574와runtimeIDF604는서로범위가다른수치다. 모델/특징변경없음. 미래비어있지않은매칭자료가생기면label-blind사용자분할을먼저확정해야하며본runner는예상과달리매칭이생기면학습하지않고중단한다.

## H. 기존모델 대비 성능
NOT_EVALUATED. `model_comparison.csv`에서역사적V2-0 Outer3의Content/MF/Hybrid@5 .027594/.015966/.042667은별도protocol행이다.이번A/B점수는NOT_EVALUATED이며0이나기존점수로대체하지않았다.원래V1@10이나반복분석된Outer결과를새독립검증으로쓰지않았다.

## I. 사용자별 성능 변화
NOT_EVALUATED. 관측가능한새평가사용자0이므로paired변화/적중수/bootstrap미실행. 작은표본의유의미한차이를발견했다고주장하지않는다.

## J. 추천 다양성·안정성
새추천을실행하지않아Coverage@5/Top1·Top5집중도/강건성은NOT_EVALUATED. 기존미관측172개는그대로이며신규관측향수0/연결성변화없음. 85개를수집한사실만으로정확도·다양성개선이라하지않는다.

## K. 데이터누수 검사
기존Validation/Internal/External답parse0. Nestedmanifest는users배열만읽고support/answers는skip. V2-14Store/SQLite/독립평가행접근0. V2-15실험결과및기존원본변경없음. synthetic자료투입0. heldout을학습·특징·매칭에사용하지않았다. csv검증용전체85점수서술통계와아직시작하지않은blind모델평가를구별한다.

## L. 테스트
사전합성24개PASS:CSV/schema/users/count/범위/0.5/중복/결측/정확ID/custom/479/기존및신규평가사용자제외/Support5답분리/고정설정/후보제외/0추가차단/비실제자료차단/수식/namespace/ID충돌. 사후실데이터·원본보존검사는 `post_checks.json`, 최종로그 `tests.log`참조. fixture는실제85행에포함하지않았다. 실행명령은 `execution.log`와소스README에있다.

## M. Frozen V1 무결성
`integrity.json`:Frozen19 및freeze manifest,원본CSV,기존평가manifest·MFQ·서비스API·V2-14/V2-15보존검증. branch `development-v2`,HEAD `b2eb5455b0ae2bbb9ba0c6dd073ddb783bd6116b` 유지; d92c59a는요청서의역사적baseline으로구분. Git변경명령/설치없음. Gitstatus는기존과같은두untracked폴더표시를유지한다.

## N. 모델 개선 스토리
`MODEL_IMPROVEMENT_NARRATIVE.md`와`experiment_history.csv`:V1@10과V2@5,Inner와Outer,정확도와안정성,진단과채택을구분했다.V2-0~9제어실험→10~12합성검증→13희소평가→14수집→15이용권검토→16실제데이터의후보불일치로이어지는과정을정리했다.모든사람의개별소감/담당/기여는미확정그대로다.

## O. 발표 문서 업데이트
기존5개문서말미에만V2-16요약을추가했다.기존prefix바이트보존검증.기존보고서/PPT덮어쓰기없음.실제별도차트이미지/PPT생성없고비교CSV와Mermaid흐름도를제공했다.

## P. V2-17 필요성
복수취향Content는예정/NOT_EVALUATED.이번결과로단일프로필의문제를입증하지못했다.먼저기존479에서실제로경험한제품평점확보또는검증가능한제품·판본대응표가필요하다.후보확장/새노트취득/다른제품강제매칭은이번에진행하지않았다.모델개선효과를평가하지못한이유는높은평점이나특정참여자가아니라이번정확연결평점0이라는확인된경계다.

### 요구사항 판정
CSV감사/원점수보존/비공개격리/누수방지/고정모델보호/이력서술PASS. 실제데이터추가MF학습및성능검증BLOCKED,새NDCG/신규최종모델선택NOT_EVALUATED.전체과제완료를선언하지않으며기존 `REQUIREMENTS_TRACEABILITY.md`는읽기전용으로보존했다.
'''
    (OUT/'REPORT.md').write_text(summary)
    for name in ('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md'):
        p=ROOT/'docs/presentation'/name;old=Path('/tmp/scent-v216-'+name).read_bytes()
        if p.read_bytes()!=old:raise ValueError('Presentation changed concurrently; do not overwrite')
        section='\n\n## V2-16 — 실제 경험 평점 확보와 후보 정합성 검증 (2026-10-30)\n\n'
        section+='12명/85평점/58제품을 실제CSV로 검증했다. catalog73/custom12,결측·ID중복0. 기존479 정확연결0,안전한학습추가0,매칭후Support5+답사용자0. catalog의제품ID는우리후보URL과다르며정확브랜드색인에도없었다. custom12는수동검토로격리했다. 원점수삭제·평균보정·후보확장·새Notes생성없음.\n\n'
        section+='CSV참여자의로컬저장·학습·평가·비식별집계발표동의를사용자에게확인했다. 하지만0매칭gate로MF학습/추천/평가0회, A/B NDCG는 NOT_EVALUATED다. 기존 .042667은역사적V2-0 Outer@5이며이번실험결과가아니다. 기존823strictTrain과원래각Outer학습행수를혼동하지않는다.\n\n'
        if name=='MODEL_IMPROVEMENT_STORY.md':section+='이야기: 통제된모델실험에서안정적개선미입증 → 실제데이터필요성확인 → 경험평점수집 → 수집량만큼중요한제품정합성확인. 기존Hybrid유지,V2-17복수취향Content는예정이며호환경험평점확보가선행한다.\n\n'
        if name=='PRESENTATION_SLIDES_OUTLINE.md':section+='슬라이드후보: “85개 실제평점, 그러나 학습가능한평점은0”. 수집85→후보정확매칭0→학습추가0 표와원인(외부catalog≠479)을설명한다. raw6개이상사용자는3명이지만479매칭후평가가능0명임을강조한다.\n\n'
        if name=='EXPERIMENT_TIMELINE.md':section+='|V2-16|실제평점추가효과검토|고정Hybrid구조·MF설정|실제12명/85개|479매칭0으로학습/평가미실행|BLOCKED|호환데이터확보선행|\n\n'
        if name=='PERFORMANCE_COMPARISON.md':section+='|조건|NDCG@5|판정|\n|---|---|---|\n|역사적V2-0 Outer Hybrid|0.042667|기존측정값,재실행아님|\n|이번V2-16 Model A/B|NOT_EVALUATED|정확매칭0;전후개선비교불가|\n\n'
        section+='근거: `outputs/scent_v2/real_rating_retraining/REPORT.md`, `MODEL_IMPROVEMENT_NARRATIVE.md`, `data_validation.json`, `dataset_integration_summary.json`, `experiment_history.csv`, `integrity.json`. 사용자원본ID/개별평점은발표에포함하지않는다.\n'
        with p.open('a') as f:f.write(section)
    for p in OUT.rglob('*'):
        if p.is_file():p.chmod(0o600)
    print('Narrative, A–P report, historical aggregate table, five append-only presentation sections created')

if __name__=='__main__':main()
