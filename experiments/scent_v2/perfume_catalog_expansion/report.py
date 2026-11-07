"""Report observed evidence and append presentation sections; no live system changes."""
import csv,json
from pathlib import Path
from .build import ROOT,OUT,DATE

def main():
    """Read this experiment's evidence; exclusively create report, append five original docs."""
    s=json.loads((OUT/'feature_compatibility.json').read_text())
    notes=s['aggregate_unique_token_coverage_frozen']['note'];accord=s['aggregate_unique_token_coverage_frozen']['accord']
    identity=list(csv.DictReader((OUT/'perfume_identity_mapping.csv').open()))
    sources=list(csv.DictReader((OUT/'source_registry.csv').open()))
    report=f'''# SCENT MATCH V2-17 — 향수 메타데이터 및 확장 준비

2026-10-30. **PASS WITH LIMITATIONS — 조사·호환성 분석 완료, 실제 카탈로그/모델/서비스 변경 없음.**

## 1. 핵심 실측 결과

| 항목 | 결과 | 의미 |
|---|---:|---|
| 조사 대상 |58|원본 source product ID58개. 물리적으로 다른58개 제품이라는 확정은 아님|
| 정확한 제품·제공 형식 식별 |46|농도/브랜드 제품형식을 공식 자료와 연결; 원본 병의 제조연도/배치 보증 아님|
| 제품 범위가 확인된 공식 Notes 확보 |46|나머지 참고제품 노트11개는 별도 격리|
| 참고 제품의 Notes까지 발견 |57|정확한 원본 제품 확정/학습 허용 수가 아님|
| 명시된 구성 Accord 확보 |6|공식적으로 이름 붙인 composition accord; 일반 주요향조/강도 데이터와 다름|
| VERIFIED |6|아래의 엄격한 조사 필드 기준|
| PARTIALLY_VERIFIED |40|정체·노트 근거는 있으나 Accord 누락/출처 충돌 등|
| NEEDS_REVIEW |11|원본 농도·형식·정확 명칭 또는 EDP SKU 확인 필요|
| UNRESOLVED |1|평가한 제품 형식을 공식 향수 자료로 확인하지 못함|
| 확인이 더 필요한 원본 ID |12|NEEDS_REVIEW11+UNRESOLVED1|
| 기존479와 확정된 정확키 중복 |0|미확정 제품까지 비중복이라 증명한 결과는 아님|
| 신규 원본 ID 사이 가능한 중복 그룹 |2|Blackberry & Bay / ANOTHER13; custom농도 확인 전 병합 금지|
| 기존 IDF로 비영벡터 표현 가능 |45|확인된 제품·노트 중 수학적 투영 가능, 추천 정확도 증거 아님|
| 확인한 노트가 모두 OOV인 0벡터 |1|AMBRETTE9의공식 Ambrette seed 표기가어휘에없음|
| 벡터 평가 보류 |12|미확인 제품·판본을0벡터로 세지 않음|

6+40+11+1=58, 45+1+12=58이다. 동일 source ID를 보존해 후속 원본 연결이 가능하다. 원본85평점의 점수/사용자 이력을 이번 연구에 이용하거나 집계하지 않았다. CSV 파서는 행을 읽되 product_id/brand/product_name/source_type4개 열만 추출했다.

## 2. 조사 방법과 출처

제조사의 공식 제품·컬렉션·브랜드 설명 페이지를 우선하여 대상 이름을 좁혀 웹검색/페이지 읽기를 수행했다. 개별 웹사이트를 도는 HTML/리뷰 수집기, API 우회, 원본 페이지 덤프, 이미지 수집은 하지 않았다. 상품명·농도·노트·명시적 구성 Accord 등 짧은 사실 필드만 출처와 함께 기록했다. 원문 마케팅 문단/리뷰를 데이터셋으로 복사하지 않았다. 실시간 재고가 확인된 것으로 과장하지 않고 Product Status는 대체로 공식 페이지 존재/판매가능 여부 미검증으로 기록했다. 검색 결과에만 표시된 항목도 출처를 표시하며, 제조사 현재 페이지가 원래 평가한 병의 배치와 같다고 보증하지 않는다.

출처 registry는{len(sources)}개 URL이며 제품/노트/이용조건 역할과 확인일을 기록했다. [Byredo Blanche](https://www.byredo.com/eu_en/p/blanche-eau-de-parfum?sku=0065204849)는공식피라미드, [Diptyque Tam Dao EDP](https://us.diptyqueparis.com/en-us/products/eau-de-parfum-tam-dao-tamdaop75cv1)는구분되지않은주요노트목록, [Le Labo의공식설명](https://www.lelabofragrances.com/our-creations.html)은정확히이름을명시한노트만사용했다. 원재료성분표의알레르겐/용제는향료노트목록으로전환하지않았다.

## 3. 제품 식별 및 농도·중복

`perfume_identity_mapping.csv`는 원본58 ID를 모두 유지하며 원본/공식/참고 이름, 농도, variant, status, URL, 확정 여부를 구별한다. EDT/EDP/Absolu를별도행으로보존했다. Tamburins의PERFUME은제조사의상품형식이고향료농도백분율이나EDP로추측하지않았다. 공식페이지가제품에이름을붙였다는것과과거다른이름·제조배치와동일하다는주장은구분했다.

- Aesop의Silently, Hwyl / Rōzu Arises / Tacit Truths는현재공식페이지에서그이름을확인했다. 예전명칭으로임의되돌리지않았다.
- custom의르라보어나더13과조말론블랙베리앤베이는기존catalog원본ID와같은참고상품URL을가리키지만평가한농도·형식이확인되지않아possible_duplicate만기록했다. 평점이나원본ID를합치지않았다.
- Clean ‘클린솝’은Pure Soap이라고확정하지않았다. Pure Soap은참고후보이며그노트는확정제품투영에서제외했다.
- Lush Guardians oftheForest는공식샤워젤/목욕제품정보만확인했다. 제품형식이향수인지bodyspray인지확인되지않아그성분을향수노트로복사하지않았다. ‘단종됨’은원본입력주장으로남기고사실로확정하지않았다.
- Byredo Rose ofNoMan’sLand는공식컬렉션이EDP와Absolu를함께다뤄서그설명을특정EDPSKU의피라미드로확정하지않았다. 가족수준의참고노트는격리했다.

기존479 중복은원본고정목록과공식브랜드/제품전체키를보수적으로비교했다. 확정일치0이지만suffix·별칭으로인한누락가능성이있으므로semantic중복검사완료를뜻하지않는다. 특히미확인custom은실제품별칭/판본을확인할때다시검토한다. 신규58 ID를그대로더해537후보가된다고계산하면안된다.

## 4. Notes와Accords의 구분

`perfume_notes.csv`: source_product_id / layer / original_note_label / normalized_token / source_url / checked_date. 공식자료가top/heart/base를명시한경우에만각층을사용한다. heart→middle은필드명대응이고순서추정이아니다. Diptyque의주요노트는전부unspecified로남겼다. 향수이름이나묘사속비유만으로노트를생성하지않았다.

`perfume_accords.csv`는‘Marine accord’,‘Matchatea accord’,‘Rice steam accord’처럼공식자료가명시한이름의구성Accord만저장한다. 제조사의Aroma/GoodtoKnow/향계열설명은별도descriptor필드이며임의로Accord로변환하지않았다. Fragrantica/다른향수DB의주요향조/강도프로필은취득하지않았다. 구성Accord가있다는것은Woody/Floral등의일반주요Accord목록을모두확보했다는뜻이아니다.

VERIFIED의정의는**제품정체/제공형식+공식노트+최소1개의명시된구성Accord를근거로확인했고기록된충돌이없는것**이다. 완전한원료공식·전체주요향조강도·과거배치·학습/재배포권한까지검증한표현은아니다. PARTIALLY_VERIFIED는확인된노트가거짓이라는뜻이아니라부족/충돌필드가있다는뜻이다.

## 5. 실제 출처 충돌과 미해결 상태

- Mojave Ghost EDP의일부공식SKU에는base의Magnolia가기재되어있고다른페이지에는없다. 채택한CA페이지목록과해당차이를함께기록했다.
- Mojave Ghost Absolu의공식SKU0065212558과0065217987은노트표기가다르다. 하나로평균/합집합해실제공식이라고만들지않고특정URL/SKU목록을남겼다. 원본병대응은미확인이다.
- Silently,Hwyl의US표기는Frakincense,말레이시아공식컬렉션은Frankincense다. 후자를출처로쓰고오탈자차이를주석으로기록했다. 기존vocabulary를고친것이아니다.
- L’Ombredansl’EauEDP페이지에는EDT문구가혼재한다. 제목/SKU에연결된목록을보존하고충돌을표시했다.
- Eau des Sens EDT의관측페이지는한정판병설명이다. 같은이름의일반병과원래평가병배치가같다고확정하지않았다.

상세미확인/부분확인목록은 `unresolved_perfumes.csv`에있다. 여기에는PARTIALLY_VERIFIED도포함하므로행수는엄격한identity미해결12와다르다.

## 6. 기존 특징 생성과 호환성

`src/perfume/data.py::tokens/normalize`: Top/Middle/Base를comma분리해note:채널로합치고mainaccord1–5를accord:채널로분리한다. NFKD/악센트제거/casefold/구두점·공백정리, eau deparfum→edp 등기존처리를그대로사용했다. 결측 '',unknown,nan,na는token을만들지않는다. 성분표allergen이나공식향취descriptor는노트로만들지않는다.

`src/perfume/models.py::Content.fit`: train문서에등장한token만으로binaryTF, IDF(t)=log((1+N)/(1+df(t)))+1을계산하고그idf로벡터를L2정규화한다. 프로필은knownsupport의양의평점가중합과cosine이다. 이번에는fit을호출하지않고보존된idf값으로transform식만적용했다.

- 고정479메타데이터활성token수 **574**, frozenIDF사전 **604**. 서로다른범위로기존모델을새로만든것이아니다.
- 확인된46제품의고유정규화Notes121개중frozenIDF에68개(**{100*notes['known_fraction']:.2f}%**)존재한다. 활성479token과비교하면67/121=55.37%다. 이는출현건수평균이아닌고유token교집합비율이다.
- 확인된구성Accord의고유문자열8개중기존accord어휘와정확일치는0개(**0%**)다. ‘marine accord’를‘marine’으로축약하거나구성Accord를일반향조로바꾸지않은보수적결과다. 실제향조가없다는뜻이아니다.
- 45개는nonzero,1개AMBRETTE9는allobservedOOV다. Ambrette seed를musk/ambrette(muskmallow)로추측매핑하거나공식적으로명시하지않은pear를보태지않았다.
- 12개는정체/판본미확인으로NOT_ASSESSED이며zero로세지않는다. 참고제품의조건부노트를확정점수에섞지않았다.

단복수/학명/상품명/수식어차이예:musks↔musk,ambretteseed등이비율을낮출수있다. 그동의어매핑은향료학적근거와별도검증후후속단계에서정의할일이다. 사전에맞추려고새노트를고르거나기존idf를바꾸지않았다. `research_vectors.json`은읽기전용호환성의파생벡터이며추천후보·학습가중치로등록하지않았다. 수학적으로nonzero라는것만으로향취/선호의충분한표현이라고주장하지않는다.

## 7. 이용 조건과 데이터 준비의 범위

[Byredo이용조건](https://www.byredo.com/ca_en/terms-of-use),[Diptyque법적고지](https://us.diptyqueparis.com/en-us/policies/legal-notice),[LeLabo조건](https://www.lelabofragrances.com/terms-and-conditions.html),[JoMalone조건](https://www.jomalone.com/terms-conditions),[Aesop말레이시아조건](https://malaysia.aesop.com/pages/terms-conditions)을조사범위에맞게기록했다. 각사이트의접근/저작권조건과사실확인은ML학습·공개데이터재배포허가의증거가아니다. 모든신규자료의rollout_ready는False다. 명시적이용근거가없는상태에서웹사이트원문대량복제나외부향수DB크롤링을실행하지않았다.

이번목적은출처가있는소량사실필드의로컬연구·검토이고,신규metadata의배포/서비스반영권한을확보했다고표시하지않는다. 미래모델/카탈로그확장전에해당용도·범위의이용근거를별도확인해야한다. 사이트약관에대한보편적법률판단을내린것은아니다.

## 8. 후속 확장에 필요한 일

1. 미확인12개의정확제품·농도·형식·원래병정보를확인한다. 기존479와canonical브랜드/제품/농도/년판/edition을대조하고가능한중복2그룹도확정한다.
2. sourceID→검증된신규canonicalID대응표를리뷰한다. 원본평점은그뒤에만연결한다. 확장본은새버전으로관리하고Frozen479를덮어쓰지않는다.
3. 노트동의어/한글·영어/수식어·분자명과공식구성Accord/일반Accord의매핑정책을명시한다. 근거가없으면OOV로남긴다. 추가로필요한자료의이용범위를확인한다.
4. 기존MF에는신규아이템factor가없다. Content벡터가생겼다고CF도가능해진것이아니다. 후속승인범위에서평가사용자를분리해실제평점을연결하고학습/콜드스타트정책을검증해야한다.
5. 확장데이터에서도train-only변환적합,동일사용자Support/held-out분리,비교후보정의,서비스선택입력의제품정합성을재검증한다. 이번에는어느것도학습/정확도평가로실행하지않았다.

## 9. 발표 스토리 및 수행 범위

**V2-16:실제사용자평점확보→기존카탈로그불일치확인→V2-17:실제사용자중심메타데이터/확장준비.** 이전문서의‘V2-17복수취향Content예정’은과거계획으로보존하고이번명칭의현재범위를새섹션에명시했다. 복수취향모델을구현/검증했다고쓰지않았다.

발표문서5개에는새섹션만append했다. 성능비교에는NOT_EVALUATED로기록하고모델정확도상승을주장하지않는다. 그래프/Word/PPT를새로만든것도아니다. 신규코드·수학/출처검사와Frozen검증은tests.log/integrity.json에실제증거를남긴다. 기존 `REQUIREMENTS_TRACEABILITY.md`는수정하지않았다. 신규메타데이터출처·분리검사PASS,부분/미확인제품및공개사용허가미확인은후속조건,모델개선NOT_EVALUATED로구분한다.

## 10. 파일 및 실행

요청된9개파일모두생성. 추가로수기검토사실 `research_evidence.json`,투영 `research_vectors.json`,검사 `tests.log`,실행기록 `execution.log`를저장했다. 각CSV는source_product_id또는source_id로추적할수있다. source_registry는URL기준으로노트/제품행과결합한다.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.perfume_catalog_expansion.build --csv "$V217_ORIGINAL_CSV"
SCENT_V217_ORIGINAL_CSV="$V217_ORIGINAL_CSV" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/perfume_catalog_expansion/tests -v
```

기존출력이있으면build는덮어쓰지않고중단한다. 새출처근거변경은다음버전으로리뷰한다. Gitbranch/HEAD/status,원본,모델,서비스,이전실험은변경하지않는다. 실제최종무결성판정은 `integrity.json`参照。
'''
    with (OUT/'REPORT.md').open('x') as f:f.write(report)
    for name in ('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md'):
        p=ROOT/'docs/presentation'/name;before=Path('/tmp/scent-v217-'+name).read_bytes()
        if p.read_bytes()!=before:raise ValueError('Presentation changed concurrently')
        section='\n\n## V2-17 — 향수 메타데이터 조사·카탈로그 확장 준비 (2026-10-30)\n\n'
        section+='현재V2-17은이전의복수취향Content예정과달리,이번사용자요청에따라메타데이터조사로범위를정했다. 이전계획문구는과거기록으로보존한다.\n\n'
        section+='V2-16실제평점확보→479와불일치→실제사용자중심제품메타데이터준비. 원본제품ID58개를유지해공식제품/노트46개를연결했고,6개는명시된구성Accord도확인했다. 품질VERIFIED6/PARTIALLY_VERIFIED40/NEEDS_REVIEW11/UNRESOLVED1. 구성Accord는일반주요향조강도목록과구별하며누락을추정하지않았다.\n\n'
        section+='기존574활성특징/604frozenIDF를바꾸지않은투영에서45개nonzero,1개관측노트OOV,12개제품·판본미확인으로평가보류다. 고유Notes정확어휘포함68/121=56.20%,구성Accord문자열0/8. 동의어차이를자동보정하지않은보수적호환성수치이며추천정확도가아니다.\n\n'
        if name=='PRESENTATION_SLIDES_OUTLINE.md':section+='슬라이드핵심: “확장준비는학습완료가아니다”. 58→공식제품노트46→기존IDF비영투영45 흐름과원본제품ID/농도분리/불확실성표를사용한다. MF신규factor는없고외부자료공개사용허가도자동확보된것이아님을설명한다.\n\n'
        if name=='PERFORMANCE_COMPARISON.md':section+='모델학습·추천·정확도평가0. NDCG/Recall/HitRate변화는NOT_EVALUATED. 45개표현가능이라는수치를정확도개선이나추천후보추가완료로바꾸지않는다.\n\n'
        section+='기존479·Frozen모델·서비스·원본평점·기존평가자료는보존했다. 새카탈로그등록/MF재학습/서비스연결은다음단계다. 근거: `outputs/scent_v2/perfume_catalog_expansion/REPORT.md`, `perfume_identity_mapping.csv`, `perfume_notes.csv`, `perfume_accords.csv`, `feature_compatibility.json`, `source_registry.csv`, `integrity.json`.\n'
        with p.open('a') as f:f.write(section)
    print('REPORT and five append-only presentation sections created')

if __name__=='__main__':main()
