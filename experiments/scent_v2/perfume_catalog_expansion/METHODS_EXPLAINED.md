# V2-17 구현 설명

수업 외 여부를 팀이 확인하기 전까지 아래 항목을 설명 대상으로 둔다. 새로운 ML 알고리즘을 구현한 것이 아니라 원래 특징식의 읽기 전용 투영과 출처 표를 작성했다.

## 특징 변환 및 파라미터

`feature_tokens(notes,accords)`: notes/accords는공식원문라벨목록이며각각note:/accord:채널을단다.기존normalize를호출해NFKD/악센트제거/casefold/구두점정리를한다.동의어추론·단복수교정·accord접미사제거·분자대체는없다.
`transform(tokens,idf)`: tokens는중복없는관측token집합,idf는수정하지않는frozen사전이다. binaryTF*기존IDF후L2정규화식은src/perfume/models.py::Content.fit의transform부분과같다. fit이나IDF계산은하지않는다. OOV는생략하고관측token이전부OOV면빈sparsedict를반환한다. metadata미확인은호출자가None/NOT_ASSESSED로구별한다.
`coverage(tokens,vocabulary)`: prefix별고유관측label분모와교집합분자를계산한다. 분모0이면known_fraction=None이다.604는frozenIDF범위,574는기존479카탈로그활성token범위다. source단어가다른것만으로실제향기가다르다고해석하지않는다.

## 원본/근거 경계

`product_inventory(path)`는CSVreader의각행에서4제품열만선택해유일sourceID목록을반환한다. user/score/time값을산출물로반환하지않는다. `canonical_brand(brand)`는원본언어와공식참고브랜드의수기대응이고제품농도를확정하는함수가아니다.각evidence의identity_verified/notes_url/review_reason이별도로있다.
`source_product_id`는향수원본ID이지사용자ID가아니다. raw58개를prospective중복이라고곧바로합치지않는다. 가능한Blackberry&Bay/ANOTHER13중복은참고URL그룹으로만표시한다. 원본품목과같은농도·edition확인전rating을병합하지않는다.
`research_evidence.json`은조회한공식페이지의짧은사실라벨/검토이유를수기로구조화한입력이다.사이트원문/리뷰/이미지를저장한파일이아니며자동진위인증서도아니다.보고일2026-10-30,source_registry.csv의페이지와표의source_url로추적한다.동일SKU/지역/원본배치의동일성을보장하지않는다.

## 표준 라이브러리

Path는프로젝트기준상대경로조합과read/open입출력이며open("x")는기존결과를덮어쓰지않는다. csv.reader는원본제품열추출,DictWriter(fieldnames)는고정열표,DictReader는자신의집계표읽기다. json(ensure_ascii=False,indent=2,allow_nan=False)은한글/들여쓰기유지및비유한값거절이다.
Counter/defaultdict(list,set)는상태수와출처그룹을집계한다. math.sqrt/isfinite는L2길이와기존IDF유효성검사다. hashlib.sha256(bytes).hexdigest는바이트동일성확인이지이용권한증거가아니다. unittest.assert*/assertRaises는수식·격리·오류·참조검사이며fixture는제조사제품정보의진위근거가아니다. argparse는로컬CSV와private snapshot경로인자를받는다. subprocess의Git호출은branch/rev-parse/status읽기만수행한다. ast는이함수목록작성용이며별도패키지설치는없다.

## 함수/메서드 목록

|위치·이름|파라미터|설명|
|---|---|---|
|build.py::write_json|`name, data`|Exclusive new-output JSON; no pre-existing result is overwritten.|
|build.py::write_csv|`name, rows`|Source/status columns ensure missing evidence never looks like a verified fact.|
|build.py::product_inventory|`path`|Read only source product fields; never retain/return user/score/time fields.|
|build.py::canonical_brand|`brand`|Manually researched bilingual brand labels; never merge product variants.|
|build.py::main|``|--csv local input contains products; curated source facts are reviewed offline.|
|compatibility.py::feature_tokens|`notes, accords`|notes/accords: literal verified labels, with distinct channel prefixes.|
|compatibility.py::transform|`tokens, idf`|Same binary-TF/IDF/L2 equation as src/perfume/models.py::Content.fit transform.|
|compatibility.py::coverage|`tokens, vocabulary`|Unique labels by channel; None for an empty denominator, never fake0%.|
|report.py::main|``|Read this experiment's evidence; exclusively create report, append five original docs.|
|tests/test_research.py::test_01_separate_channels|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_02_original_normalization|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_03_no_synonym_guess|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_04_no_accord_inference|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_05_literal_accord_name|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_06_binary_tf|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_07_l2_equation|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_08_missing_and_oov|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_09_invalid_idf|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::setUpClass|`cls`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_10_full_inventory|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_11_source_date_required|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_12_no_inferred_pyramid|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_13_no_ingredient_or_description_dump|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_14_status_accounting|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_15_ambiguous_not_transformed|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_16_never_merge_concentrations|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_17_vector_scope|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_18_normalized_vectors|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_19_no_production_or_models|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::test_20_product_only_fields|`self`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|tests/test_research.py::pick|`name`|합성수식/저장출처/제품경계 assertion, self는TestCase객체|
|verify.py::main|``|--snapshot private pre-task SHA256 map; --csv unchanged product inventory source.|
