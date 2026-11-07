"""A–O report from executed local artifacts; append presentation evidence only."""
import csv,json
from pathlib import Path
from .catalog import ROOT,OUT


def main():
    """Create actual measured report and five append-only sections; never invent accuracy."""
    feature=json.loads((OUT/'expanded_feature_summary.json').read_text());mapping=json.loads((OUT/'rating_mapping_summary.json').read_text())
    elig=json.loads((OUT/'evaluation_eligibility.json').read_text());diag=json.loads((OUT/'recommendation_diagnostics.json').read_text())
    a,b=diag['track_A'],diag['track_B'];case=diag['real_support_technical_cases'][0] if diag['real_support_technical_cases'] else None
    source=feature['source'];case_text='실제 Support 입력 사례 없음.'
    if case:
        t=case['top5'];case_text=f"실제 사용자1명의 Support5만 입력한 기술 사례에서 Top5를 생성했다. 신규 {t['new_slots']}개/기존 {t['old_slots']}개, 브랜드 {t['top5_brands']}개, Top5 pairwise cosine 평균 {t['top5_pairwise_cosine']:.6f}. 같은 입력의 전체 점수·순서는 정확히 같았다. 이 사람의 정확도/적중 여부는 계산하지 않았다."
    report=f'''# SCENT MATCH V2-18 — Expanded Catalog Content Experiment

2026-10-30. **실험 구현·Track A 회귀·허가된 대체 출처의 추천 동작 PASS WITH LIMITATIONS. 신규 사용자 정확도 NOT_EVALUATED.**

## A. Executive Summary

원래 V2-17 제조사 수집 메타데이터의 추천 이용 근거는 여전히 미확인이다. 사용자 지시에 따라 그 Notes/Accords/벡터로 추천하지 않았다. 추가 조사에서 Scento의 공개 **CC BY 4.0** 라이선스와 자체 검토/저술 정책을 확인했고, 해당 별도 버전의 메타데이터만 사용했다.

| 항목 | 실제 결과 |
|---|---:|
| 기존 후보 |479, 그대로 보존|
| 원본58 제품 ID 중 허가된 출처로 추가 |{feature['new']}|
| 독립 실험 후보 |{feature['total']}|
| 연결된 실제 사용자/평점 |{mapping['mapped_users']}명/{mapping['mapped_ratings']}개|
| Support5+held-out 조건을 만족한 사용자 |{elig['matched6plus_users']}명|
| 기존 Track A Content NDCG@5 |{a['ndcg']:.9f}, A/B 동일|
| 신규 사용자 NDCG@5 |NOT_EVALUATED, 1명만 가능|
| MF/Content-IDF fit |0/0|
| 서비스/원래 후보 변경 |없음|

## B. 확장 후보 수와 출처

출처: [Scento 공개 저장소](https://github.com/Scento-com/perfume-dataset), [라이선스](https://github.com/Scento-com/perfume-dataset/blob/{source['commit']}/LICENSE).
고정 commit `{source['commit']}`, 2026-10-30 수신. 원본 metadata JSONL의 실제 행수 **{source['measured_rows']}**. README의 주장과 별도로 파일 행수를 셌다. LICENSE/README/datapackage/JSONL 각각의 URL·bytes·SHA256은 `licensed_source/provenance.json`에 있다. 개인 평점·ID는 다운로드 요청이나 외부 서비스로 전송하지 않았다.

명시적으로 보존한 출처 표기: **Scento — https://www.scento.com/perfume-database**, CC BY 4.0, https://creativecommons.org/licenses/by/4.0/legalcode. 변경 내용: 일부 제품을 선택하고, literal notes만 정규화해 기존 IDF에 투영했다. 원문 설명·popularity rank·family·season은 점수에 쓰지 않았다. 제공자의 보증/추천을 받았다는 의미도 아니다.

58 ID의 실측 처리: 기존 V2-17 identity 미확인12개 제외, 허가된 데이터의 정확 제품/농도가 없거나 유일하지 않은27개 보류, 한국어 custom의 정확한 bilingual 대응이 없는1개 보류,18개 추가. PARTIALLY_VERIFIED라는 이유나 일반 Accord 부재만으로 제외하지 않았다. `candidate_review.csv`가 제품별 사유를 기록한다. V2-17의45개 벡터를 복사하거나524개를 미리 정하지 않았다.

## C. 신규 메타데이터 품질 및 이용 조건

V2-17의 제조사 직접 수집 경로는 **BLOCKED_USAGE_SCOPE_UNVERIFIED**로 유지한다. 그 결과를 수정하거나 허가 기록을 만들지 않았다. 본 실험은 독립적으로 이용 근거가 있는 **Scento snapshot** 경로다.

Scento는 제조사/공인 판매처의 사실을 점검하고 설명은 직접 작성하며 제3자 원문은 포함하지 않는다고 공개한다. LICENSE의 데이터 재사용 근거를 확인한 범위에서 로컬 비상업 실험을 수행했다. CC BY는 출처·라이선스·수정 표시가 필요하며, 상표/사생활 권리나 데이터 정확성까지 보증하지 않는다. 미래 배포에는 해당 범위와 표기를 다시 확인해야 한다. 이는 V2-17 원본이나 제조사 사이트의 별도 사용 허가를 얻었다는 주장이 아니다.

대체 자료에도 한계가 있다. 농도가 비어 있는 Jo Malone 상품은 이름이 같아도 Cologne으로 채우지 않았다. Tam Dao의 EDP를 자료에 있는 EDT로 바꾸지 않았다. Absolu는 출처명 자체에 그 변형명이 명시되고 parfum으로 분류된 경우에만 명시적 교차 필드 규칙으로 수용했다. 정확한 병의 제조 배치/리뉴얼 연도는 여전히 보증하지 않는다. 기타 대안과 보류 사유는 `USAGE_REVIEW.md`에 정리했다.

## D. 기존 IDF 호환성과 특징 밀도

Main A/B의 기존479 **idf604 및 item vector 값은 그대로**다. Binary TF, 기존 smoothed IDF, L2, cosine을 사용한다. 새 IDF/동의어/향조 분류기를 학습하지 않았다. 신규 상품은 **Scento의 literal flat Notes만** 사용하고, Notes/Accords 채널을 구분했다. 제조사의 named accord나 외부 family를 일반 accord token으로 바꾸지 않았다.

| Main representation | 제품 | 평균 활성 token | 평균 Notes | 평균 Accords |
|---|---:|---:|---:|---:|
|기존 Notes+Accords|479|{feature['existing_vector_density']['mean_tokens']:.6f}|{feature['existing_vector_density']['mean_note_tokens']:.6f}|{feature['existing_vector_density']['mean_accord_tokens']:.6f}|
|새 licensed Notes-only|18|{feature['new_vector_density']['mean_tokens']:.6f}|{feature['new_vector_density']['mean_note_tokens']:.6f}|0|

따라서 B는 **전체가 Notes-only인 모델이 아니라 기존 Notes+Accords와 새 Notes-only가 섞인 표현**이다. 같은 L2 정규화로도 특징 밀도/노출 편중 문제가 사라지는 것은 아니다. 새 OOV 목록과 known token 수는 `expanded_feature_summary.json`에 있다.

## E. 실제 평점 연결

원본12명/85개 중 **8명/37개**가 엄격한 licensed 제품 대응에 연결됐고48개는 연결하지 않았다. 원점수는 수정하지 않고 Support에서만0–10을0–1로 변환했다. 매칭 후 사용자 활동수는1개2명,2개2명,3개1명,5개2명,18개1명이다. 같은 canonical 사용자–상품 충돌이 있으면 임의 삭제하지 않고 중단하도록 했다.

신규 namespace가 다르다고 기존 사용자와 실제 사람이 다름을 보장하지 않는다. 기존/신규 사람 중복 UNKNOWN이다. V2-14 독립 평가 데이터는 읽지 않았다. 원본CSV와 V2-16/17은 읽기 전용으로 유지했다.

## F. 실험용 Content 구현

`models.py::ContentExperiment.score(support,candidates)`는 정확히5개의 고유 Support만 받으며, `sum(max(0,rating/10)*item_vector)` 프로필과 cosine을 원래 Content와 같은 식으로 계산한다. 점수 내림차순/원래 ID 오름차순, 알려진 입력5개 제외, all-zero/미등록 입력은 NO_USABLE_PROFILE이다. 임의 추천이나 Popularity fallback을 추가하지 않았다. held-out 인자는 API에 없다.

Main A는 원래479 vector만 보유하므로 새 ID5개는 엄격히 미등록이며 프로필을 못 만든다. B는 새 licensed vector도 보유한다. 별도 **A_shared_support_adapter**는 B와 같은 Support projection에 기존479 후보만 주는 노출/후보 커버리지 통제다. 이것은 변경 없는 엄격한 A가 아니며 A의 성공으로 이름 붙이지 않았다.

추가로 synthetic input 데모는 실제 licensed 상품벡터5개와 명시적으로 합성 입력임을 표시한 평점으로 Top5/재현성을 검증했다. 이것을 실제 사용자나 정확도 결과로 집계하지 않았다. `synthetic_input_demo.json`.

## G. Track A — 기존479 고정 평가

역사적 Outer3-fold/사용자75명/긍정 정답69명/Support5/held-out/후보479/입력 제외를 그대로 사용했다. 이 트랙은 **각 fold의 저장된 train IDF**를 재사용한다. 현재 global Frozen IDF604를 과거 fold IDF 대신 쓰면 기존 평가와 조건이 달라지므로 섞지 않았다. 원래 fold vector 파일이나 global Frozen vector를 변경한 것은 아니다.

원래 Content와 실험 함수의75명 Top5·점수·지표가 **완전히 같았고 최대 점수 차이0**이었다. 저장 baseline NDCG도 재현했다.

| 모델 | NDCG@5 | Recall@5 | Hit Rate@5 | Coverage/479 |
|---|---:|---:|---:|---:|
|원래 fold Content|{a['ndcg']:.9f}|{a['recall']:.9f}|{a['hit_rate']:.9f}|157/479|
|실험 함수, 같은 fold 표현/479|{a['ndcg']:.9f}|{a['recall']:.9f}|{a['hit_rate']:.9f}|157/479|

사용자별 변화는 모두0, 긍정69명 NDCG 서술표준편차 {a['ndcg_user_std']:.6f}. 기존 Outer는 반복 분석된 탐색/회귀 자료이며 새로운 독립 개선 검증이 아니다. 실제 적중6건이며, 미관측을 싫음으로 라벨링한 것은 아니다. 독립적인 모델 차이가 없는 복제 회귀의 유의성/개선 CI를 만들지 않았다.

## H. Track B — 확장 후보

계획을 실제 성능을 보기 전에 `policy.json`에 고정했다. 매칭된 고유 평점6개 이상, hash로5 Support/나머지 분리, 최소3명일 때만 탐색적 point accuracy를 계산한다. 최소3명은 표본1–2명에 대한 과장 방지를 위한 프로젝트의 보고 규칙이지 교수 요구나 통계적으로 충분한 표본이라는 뜻은 아니다.

적격 사용자는 **1명**, 연결 평점18개에서 Support5/held-out13이다. 따라서 **NDCG/Precision/Recall/Hit Rate/적중수/긍정 사용자 수/bootstrap은 NOT_EVALUATED**다. held-out 값으로 추천·사용자 선택·모델 설정을 조정하지 않았다. held-out label을 실제 정확도 harness에 전달하지 않았다. 점수와 노출 진단은 실제 Support5만으로 실행할 수 있어서 별도로 보고했다.

엄격한 A는 새 입력 ID를 모르므로 NO_USABLE_PROFILE이고 NDCG0으로 대체하지 않았다. A_shared_support_adapter는 기존479만 추천하므로 새 향수 정답에 대한 후보 커버리지 자체가 다르다. 이 조건으로 B의 정확도가 개선됐다고 주장하지 않는다.

## I. 추천 다양성

{case_text}

실제 단1명/5슬롯에서 Coverage5/497=1.006%는 단일 사례의 노출 수일 뿐 집단 다양성 검증이 아니다. 같은 이유로 신규/기존 어느 쪽의 과도한 편중 여부도 확정하지 않는다. 벡터의 feature density 차이와 새/기존 score 분포를 기록했으나 편중의 인과 원인으로 단정하지 않았다.

## J. 신규 향수 추천 비율 및 score 분포

실제 Support 기술 사례의 Top5 중 새 상품1개(20%), 기존4개(80%). 새 입력5개를 제외해492개 후보(기존479+신규13)를 점수화했다. 신규 후보 mean score .166673, 기존 후보 mean score .093559였다. 이 표본의 차이를 일반적인 새 향수 선호나 향후 만족도라고 해석하지 않는다.

Top1 concentration은 **모든 Top5 슬롯 중 가장 자주 등장한1개 상품의 점유율**, Top5 concentration은 가장 자주 등장한5개 상품의 합계다. rank1의 동일 상품 비율과 다르다. Track A는각 .045333/.170667. Track B 한 사람은구조적으로 .2/1.0이므로 안정적인 집중도 추정치가아니다. 같은입력 결과동일성만확인했고 ±평점 교란 실험은실행하지않았다.

## K. 사용자별 사례와 개인정보

`recommendation_examples.csv`는 익명 사례번호/추천 제품/점수/새기존 구분만 담는다. 원본 user ID나 사용자의 실제 평점 행을 공개 결과로 넣지 않았다. `private/`의 기술/회귀 기록도 로컬 비공개로 관리한다. 사용자별 Track A delta0은 저장했고 Track B 성능 변화는 NOT_EVALUATED다. 같은입력 adapter 통제의추천은별도명칭으로구분했다.

## L. 테스트 및 실행

사전 합성23개 PASS. 출처/실데이터 후속12개를 더해 **35개 PASS**, SKIP0. 원래 수식 일치, 불변 vector, EDT/EDP/Absolu, provider 중복, 빈 농도, OOV/0vector,Notes/Accords분리,5Support,seen제외,Top5,점수범위,determinism,신규노출,답poison,source-isolation을검사했다. source-isolation test는V2-17 notes/accords/vector 파일을열면실패하도록막고도18개후보를재구성했다. 합성fixture는실제평점에섞지않았다.

실제MF/Content.fit은guard로감시·차단했고각0회다. Hyperparameter search0,서비스변경0,패키지설치0. 커맨드는execution.log와소스README에기록한다. 생성표/숫자는실제출력JSON/CSV에근거한다.

## M. Frozen V1 및 기존 파일 무결성

`integrity.json`에실제검사결과를남긴다. Frozen19/manifest/IDF/원래479 vectors/기존서비스/원본CSV/기존V2-16/17보존. 기존Final Validation/Internal/External 정답은파싱하지않았다. TrackA의요청된과거Outer답만평가harness에서점수계산뒤읽었다. Gitbranch/HEAD/status유지,Git변경명령없음.

## N. 발표 문서 업데이트

기존5개문서의끝에만새섹션을추가했다. 흐름: V2-16 실제평점과카탈로그불일치→V2-17공식자료조사→V2-18미승인경로보류및별도CCBY소스로추천가능성검증. 실제로한일과보류한일을구분했다. 기존문장/보고서/PPT를덮어쓰지않았고성능향상을입증했다고쓰지않았다.

## O. V2-19 권고

1. 원래제조사수집자료의추천경로는이용근거전까지계속BLOCKED. Scento버전/출처표기는유지한다. 필요하면원권리자에게목적·규모·배포범위를명시한허가요청을팀이진행한다. 이번에외부메시지를보내거나승인을만들지않았다.
2. 새18개제품에서실제로경험한여러사용자의평점을더모집해사용자단위개발/독립평가를분리한다. 1명의많은평점이여러독립평가자를대체하지않는다.
3. 허가된자료의농도/판본/원본한국어상품대응을검증해37개연결평점을늘리되유사도매칭으로숫자를만들지않는다.
4. 표현밀도차이와후보커버리지를통제한별도ablation을설계한다. Frozen표현은유지하고새실험버전에서만sharedNotes표현을비교할수있다. 본실험은이분석을이미수행했다고주장하지않는다.
5. 신규제품에는기존MFfactor가없다. Hybrid확장은학습/콜드스타트/fallback/동일후보평가정책을따로확정한뒤진행해야한다. 이번에새factor·가중치·서비스연결은하지않았다.

### 진행/보류 판정

- **PASS:** 기존479 TrackA 회귀, 출처버전/라이선스기록,독립18후보추가,37실제평점연결,신규5입력추천동작/재현성,합성·출처테스트,원본보존.
- **BLOCKED:** 이용근거없는V2-17제조사Notes/Accords/벡터의추천사용.
- **NOT_EVALUATED:** 신규사용자정확도/적중/통계적개선,집단편중검증,신규Hybrid학습및실제서비스.

새로운독립자료를추가했다는것은교수제출요건전체완료나모델성능상승의증거가아니다. 기존REQUIREMENTS_TRACEABILITY.md는읽기전용으로보존했다.
'''
    with (OUT/'REPORT.md').open('x') as f:f.write(report)
    for name in ('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md'):
        p=ROOT/'docs/presentation'/name;old=Path('/tmp/scent-v218-'+name).read_bytes()
        if p.read_bytes()!=old:raise ValueError('Presentation changed concurrently')
        extra='\n\n## V2-18 — 확장 Content 독립 실험과 사용권 분리 (2026-10-30)\n\n'
        extra+='V2-16실제평점확보/479불일치→V2-17제품메타데이터연구→V2-18별도허가된출처의추천가능성검증. 제조사직접수집한V2-17 notes/accords/researchvectors는용도미확인으로추천사용BLOCKED를유지했다. 추가조사에서CCBY4.0Scento를확인해commit58da85556a4bb42a7d56279d66fbec4dbf42cc4a의1479행을보존/검증하고그Notes만사용했다.\n\n'
        extra+='정확제품/농도/비중복/비영vector조건을통과한신규18개로독립497후보를구성했다. 기존479벡터/IDF604는변경없음. 기존은Notes+Accords,신규는licensedNotes-only다. 실제8명/37평점연결,평가적격≥6개사용자1명(Support5/나머지13). 사전최소3명보고규칙으로신규NDCG/Recall/HitRate/적중/CI는NOT_EVALUATED.\n\n'
        extra+='TrackA는과거75명/긍정69명/각5Support/479후보와각fold의저장IDF를재사용해원래ContentNDCG@5=.027594399를정확재현했다. 실험함수와모든Top5·점수동일,최대점수차0이며정확도개선실험결과가아니다. 과거Outer는반복사용된회귀/탐색근거다.\n\n'
        extra+='실제Support기술사례에서는Top5신규1/기존4,동일입력재현성을확인했다. 한사례의20%신규노출은정확도향상·집단다양성검증이아니다. 엄격한기존모델은새ID입력을몰라미평가이며0점으로대체하지않았다. MF/IDF재학습0,Hybrid/서비스/Git변경없음.\n\n'
        extra+='근거: `outputs/scent_v2/expanded_content/REPORT.md`, `model_comparison.csv`, `expanded_feature_summary.json`, `rating_mapping_summary.json`, `evaluation_eligibility.json`, `recommendation_diagnostics.json`, `licensed_source/provenance.json`, `integrity.json`. 후속은호환제품경험평가자확보및개발/독립평가분리,농도보강,신규MF콜드스타트정책이다.\n'
        with p.open('a') as f:f.write(extra)
    print('A–O report and five append-only presentation updates created')

if __name__=='__main__':main()
