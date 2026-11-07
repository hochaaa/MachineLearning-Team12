# V2-15 구현 설명

수업 외 여부를 팀이 확인하기 전까지 아래 구성 요소를 설명 대상으로 둔다. 함수의 입력/출력 및 실패 조건은 각 docstring과 테스트를 함께 참조한다. 외부 코드 차용 없음.

## 처리 순서

권한 근거 검토 → gate-before-open/SHA256 → 출처별 열 매핑 → 명시 평점·scale 확인 → 원본479 제품과 보수적 매칭 → HMAC 가명화 → 중복/충돌 분리 → 평가 이력 없는 Train과만 결합. 실제 신규 자료가 없어 이번에는 합성 fixture만 이 경로를 실행했다.

## 모듈과 파라미터

- `evidence`: source/version/evidence_urls/review_reference 및 download/academic_use/derivatives/privacy_review/upstream_terms의 수동 검토 결과. status=APPROVED_LOCAL은 이번 조사에서 실제로 부여하지 않았다. redistribution은 독립 항목이다.
- `scale`: minimum/maximum/zero(valid, missing, unknown)/evidence. raw_rating은 보존하고 normalized_rating만 affine 0–10으로 만든다. 선호 의미의 등가성은 가정하지 않는다.
- `catalog`/`candidates`: 기존479 ID→brand/name/선택 variant 메타데이터 사전 또는 고정 ID 집합. 새 향수 추가 금지.
- `secret`: 로컬 비공개 HMAC 키 bytes(32바이트 이상). 같은 출처 이력 연결에는 같은 키를 사용하며 키를 잃으면 ID도 일치하지 않는다. 키·원본 사용자명은 산출물에 쓰지 않는다.
- `excluded_users`: 기존 평가 사용자 ID 집합. boundary 파서가 평가 상품·값에 접근하기 전에 제외한다. `legacy_safe`는 이 필터를 통과한 (사용자,상품,0–1 평점)이고 external 정규화는0–10이다.
- `overlap_verified`: 외부와 기존 사용자 중복에 대한 별도의 검토 assertion, 기본 False. 이 bool 자체가 독립성의 증거는 아니다. 이번에는 True로 실자료를 통합하지 않았다.
- `rows`: canonical 실제 명시적 평점 목록. `is_synthetic=False`는 provenance 검토자가 확인한 assertion이며 알고리즘이 실사용자를 판정하는 것은 아니다. fixture 안의 값은 실제 기록이 아니다.
- `previous_counts`: 기존 아이템별 관측 수, 누락 시 신규 관측 수는 UNKNOWN. 7+ 및<5의 서술 기준은 정확도 평가 정의 변경이 아니다.
- `--snapshot`/`SCENT_V215_BEFORE_SNAPSHOT`: 작업 전에 별도로 저장한 SHA256 맵. 자동 생성된 임의 사후 스냅샷으로 과거 불변성을 증명하지 못한다. 개인 경로는 소스에 하드코딩하지 않는다.

## 표준 라이브러리/클래스

`Path`는 파일 경로를 조합하고 read/write는 해당 경로만 연다. `csv.DictReader/DictWriter`는 헤더 기반 행 입출력(fieldnames 지정), json.load/loads/dump는 JSON 직렬화(ensure_ascii=False, indent=2로 한국어와 들여쓰기). hashlib.sha256(data).hexdigest는 바이트 동일성, hmac.new(key,message,sha256)는 키가 있는 가명 해시다. 파일 해시는 적법성 증거가 아니다.
`unicodedata.normalize("NFC",text)`와 casefold, re.findall은 표기만 정리한다. `SequenceMatcher(None,a,b).ratio()`는 문자 유사도0–1이며0.8 이상 최대3개 제안만 남긴다. `Counter`, `defaultdict(list/set)`는 빈도/그룹/그래프를 구성한다. BFS는 set으로 방문 중복을 방지한다. mean/median/pstdev는 모집단 서술 통계이며 유의성 검정이 아니다.
`unittest.TestCase`의 self는 테스트 객체이고 assert*/assertRaises는 값·오류 경로 검사다. TemporaryDirectory는 fixture 파일을 저장했다가 정리한다. argparse.ArgumentParser는 유일한 snapshot 인자를 받는다. subprocess.check_output의 Git 호출은 branch/rev-parse/status 읽기만 한다. datetime.fromisoformat은 입력 timestamp 형식을 검사하며 시점 선택 규칙을 만들지 않는다. ast는 이 API 목록 작성에만 사용했고 런타임 의존성이 아니다.

## 함수/메서드 목록

|파일·이름|파라미터|설명|
|---|---|---|
|dataset_builder.py::prepare|`rows, evidence, scale, catalog, secret`|Rights gate precedes iteration; return minimal matched rows, aggregate audit.|
|dataset_builder.py::assemble|`legacy_safe, external, candidates, excluded_users, *, overlap_verified=False`|Use ONLY previously filtered legacy train, never the full 1805-row archive.|
|deduplication.py::deduplicate|`rows`|Exact canonical duplicates collapse; conflicting user/item histories quarantine.|
|license_audit.py::require_permission|`evidence`|Require version-bound documented approval of each necessary local use.|
|license_audit.py::verified_file|`path, evidence`|Gate before opening a local original; compare the approved SHA256/version.|
|perfume_matching.py::normalized|`text`|NFC/casefold and punctuation/space normalization; retain all version tokens.|
|perfume_matching.py::match|`row, catalog`|Unique exact normalized brand/name only, with supplied variant attributes checked.|
|quality_report.py::summarize|`rows, candidates, previous_counts=None`|Canonical rows use 0..10 normalized_rating; 7+ positive, <5 low descriptive assumptions.|
|rating_normalization.py::normalize_rating|`value, scale`|scale: minimum, maximum, zero meaning(valid/missing/unknown), evidence URL.|
|run.py::write_json|`name, value`|Write only this experiment's aggregate artifacts, never original rows.|
|run.py::write_csv|`name, rows`|Write administrative evidence tables; these are not acquired rating files.|
|run.py::main|``|--snapshot: private pre-task SHA256 map, required to verify original-file preservation.|
|schema_inspection.py::read_original|`path, evidence`|Read approved CSV/JSON/JSONL without remote loaders or executable scripts.|
|schema_inspection.py::validate|`row`|Canonical row needs real user/item IDs, product brand/name and explicit rating.|
|tests/test_pipeline.py::evidence|``|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::row|`**kwargs`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_01_provenance_required|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_02_license_hold|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_03_gate_before_file_open|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_04_hash_and_csv|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_05_schema|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_06_no_user|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_07_aggregate_not_explicit|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_08_id_consistency|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_09_brand_name|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_10_concentration_collision|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_11_fuzzy_never_accepts|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_12_scale|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_13_missing|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_14_zero_meaning|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_15_namespace_privacy|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_16_dedup_conflicts|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_17_candidates_not_expanded|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_18_evaluation_skipped_before_decode|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_19_independent_and_protected_sources|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_20_synthetic|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_21_frozen19|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_22_original_data_unchanged|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_23_service_unchanged|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_24_previous_results_unchanged|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::snapshot|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::check_prefix|`self, prefix`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_25_variant_metadata|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_26_cross_source_unknown_quarantined|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_27_pipeline_minimizes_identity|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_28_quality_and_no_rows|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_29_duplicate_timelines_quarantined|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::test_30_unicode_version|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|tests/test_pipeline.py::__iter__|`self`|테스트용 합성 fixture/불변성 assertion; tests.log의 실행 여부 참조|
|user_id_mapping.py::pseudonym|`source, user_id, secret`|Namespace source and HMAC raw ID with private >=32-byte secret; do not persist it here.|

## 한계

출처별 실파일 열 매핑, 대규모 Parquet 처리, 전체1805 archive export, 다운로드 실행기, 실제 교차 출처 사람/리뷰 중복 해소는 구현·실증하지 않았다. 원본 license 승인 근거와 실제 자료가 있어야 다음 단계로 진행할 수 있다. 테스트 통과와 데이터 확보 완료는 구별한다.
