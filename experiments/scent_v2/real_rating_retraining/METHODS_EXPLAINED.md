# V2-16 구현 및 파라미터 설명

수업 외 구성요소로 간주해 설명한다. 이 작업은 신규모델 실험을 수행하지 않았으며0매칭 감사·보존만 완료했다. 외부코드 차용 없음.

## 자료 경계

`rows`는 실제CSV의 canonical records이며 사용자 원본ID는 메모리 검증 후 가명화된 비공개파일에만 대응한다. `catalog`는 원본 브랜드/이름/tokens, `candidates`는 고정479 URL 목록이다. `source_type`의catalog값은 기존서비스479소속을보장하지않는다. `secret`은32바이트이상의HMAC키로원본ID가공개출력에남지않게한다. 키는로컬개인파일이며재배포승인이아니다.

## 설정

MF_POLICY의factors4/epochs160/learning_rate.01/regularization.01/seed12와POLICY의alpha.25/foldin_ridge.01/support5/k5/relevance.7은요청한고정설정이다. 실제MF생성/fit/추론은0회이다. content의후보활성token574와frozenIDF604는범위가다르며604개차원으로모델을새로바꾼것이아니다.

## 표준 라이브러리

csv.DictReader는헤더별문자열행을읽으며DictWriter(fieldnames=...)는정해진비공개/집계열만쓴다. jsondump(ensure_ascii=False,indent=2,allow_nan=False)는한글과들여쓰기를유지하고NaN을거절한다. Path.open(mode="x")는기존산출물덮어쓰기를막는다. chmod(0600/0700)는POSIX로컬보호이며WindowsACL까지검증한것은아니다.

Counter는빈도/defaultdict(list)는사용자·제품그룹이다. mean/median/pstdev는모집단서술통계이며신뢰구간아니다. math.isfinite는NaN/Inf거절,re/unicodedata NFC/casefold는표기정리만하며제품판본은제거하지않는다. sha256(data).hexdigest는동일바이트검사,HMAC(key,message,sha256)는출처별가명,secrets.token_bytes(32)는비공개난수키다. 가명화는동일사람의cross-source중복이나법적권한을보장하지않는다.

unittest.TestCase/assert*는합성·실데이터보존검사,TemporaryDirectory는fixture임시파일수명관리다. patch.object(MatrixFactorization,"fit",side_effect=AssertionError)는이번무매칭실행의오학습을차단하며call_count를기록한다. 실제허용모델학습을시험한것이아니다. argparse는csv/snapshot/consent flag를받으며Git subprocess는branch/rev-parse/status/diff읽기만수행한다.

## 재사용 코드

`synthetic_data.boundary.evaluation_users(text)`는Nestedmanifest에서users만읽고답은skip한다. `safe_train(text,excluded)`는제외사용자의item/rating을decode전에skip한다. 이두함수를가져온것은합성평점사용이아니다. `external_real_data.quality_report.summarize(rows,candidates)`는기존strictTrain관측/연결성집계만재사용했다. `scent_v2.evaluate.metrics(top,answers)`는합성수식검사에서만사용했고실제평가답을로드하지않았다.

## 함수 목록

|모듈/함수|파라미터|역할|
|---|---|---|
|audit.py::norm|`value`|NFC/casefold, preserve accents and all words/numbers/variant tokens.|
|audit.py::pseudonym|`user, secret`|Source-specific local HMAC; original IDs are never written to output.|
|audit.py::stats|`values`|Descriptive population statistics, not a confidence interval.|
|audit.py::read_csv|`path`|Return validated actual rows and aggregate audit. Fail on bad rows, never impute.|
|audit.py::match_one|`row, catalog, candidates`|Only trusted same URL identity or unique exact normalized brand+full-version name.|
|audit.py::split_eligibility|`rows, matches`|Only matched unique histories >=6 can supply five support + held-out.|
|audit.py::require_training_additions|`matched_rows`|No MF fit, A/B evaluation or model weights can be produced with zero additions.|
|audit.py::support_answers|`history, seed=12`|Five support by item hash only; disjoint remainder, never sort by ratings.|
|audit.py::validate_training|`train, evaluation_users, candidates`|Reject evaluation users and non-candidates, without fitting any model.|
|reporting.py::history|``|Read only saved aggregate tables, mark Inner and Outer as distinct protocols.|
|reporting.py::main|``|Create narrative/report and append five original presentation documents once.|
|run.py::json_file|`name, data`|Exclusively create local aggregate/private JSON, chmod0600; never overwrite.|
|run.py::csv_file|`name, rows`|Write nonempty reviewed records; private outputs never enter Git.|
|run.py::main|``|--csv original readonly; --consent-confirmed actual user attestation; --snapshot pre-task hashes.|
|tests/test_audit.py::row|`**kw`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::parse|`self, rows`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_01_csv_schema|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_02_users|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_03_counts|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_04_range|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_05_step|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_06_duplicates|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_07_missing|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_08_exact_catalog|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_09_custom_review|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_10_fixed479|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_11_old_eval_excluded_before_values|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_12_new_eval_training_excluded|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_13_support_heldout|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_14_content_structure|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_15_mf_policy|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_16_alpha|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_17_candidate_exclusion|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_18_no_fuzzy_or_version_loss|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_19_zero_additions_prevents_training|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_20_five_not_evaluable|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_21_synthetic_and_independent_training_rejected|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_22_metrics|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_23_pseudonym_namespace|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|tests/test_audit.py::test_24_product_id_metadata_collision|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::verify|`snapshot, csv_path`|snapshot: actual pre-task SHA256 map; csv_path: unchanged original local CSV.|
|verify.py::test_01_real_schema_and_original|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::test_02_frozen19_and_manifest|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::test_03_data_and_manifests_unchanged|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::test_04_services_unchanged|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::test_05_v214_v215_preserved|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::test_06_append_only_presentation|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::test_07_git_unchanged|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|
|verify.py::test_08_all_original_and_no_training|`self`|테스트 fixture/계수/오류/불변성 assertion, self는테스트객체|

## 미실행/한계

학습/재탐색/새정답평가/통계bootstrap/모델weights는생성하지않았다.매칭제품0에대해성능이나신뢰구간을0으로채우지않는다.관측된맞지않는제품을기존후보에번역·fuzzy로강제연결하지않는다.신규모델trainer를완성했다고주장하지않는다.원본제품·판본대응표나호환경험평점확보가다음조건이다.
