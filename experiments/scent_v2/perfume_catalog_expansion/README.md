# V2-17 — 제조사 근거를 이용한 향수 메타데이터 연구

**조사/호환성 분석 PASS WITH LIMITATIONS.** 입력 source product ID58개를 유지했다. 제품·제공형식 및 Notes46개, 명시적 구성Accord6개. 확정된범위의벡터45개nonzero/1개allOOV,12개미확인으로분석보류. 서비스후보·모델·원본평점은변경하지않았다.

## 재현

기존 로컬 Python3.12/NumPy 환경을 사용하며 설치하지 않는다. 원본 데이터와 재사용 소스가 없는 클론에서 실행 가능하다고 주장하지 않는다.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.perfume_catalog_expansion.build --csv "$V217_ORIGINAL_CSV"
SCENT_V217_ORIGINAL_CSV="$V217_ORIGINAL_CSV" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/perfume_catalog_expansion/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.perfume_catalog_expansion.report
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.perfume_catalog_expansion.verify --snapshot "$V217_BEFORE_SNAPSHOT" --csv "$V217_ORIGINAL_CSV"
```

`V217_ORIGINAL_CSV`는 원본 CSV, `V217_BEFORE_SNAPSHOT`은 실제 작업 전 상대경로→SHA256 JSON이다. 같은 snapshot 디렉터리의 `scent-v217-<발표문서명>` 사본으로 append-only를 확인한다. 현재 산출물을 덮어쓰지 않으며 재실행은 이미 결과가 있으면 중단한다. `report.py`는 이번 작업의 before사본을 요구한다. 사후 snapshot으로 과거 불변성을 소급 증명하지 않는다.

웹 조사는 제조사 페이지/검색을 사람이 좁혀 확인하고 그 사실을 `outputs/scent_v2/perfume_catalog_expansion/research_evidence.json`에 기록했다. build는 이 검토 파일을 표와 벡터로 변환하는 도구이며, 웹 페이지를 다시 조회하거나 사실의 진위를 자동 인증하는 다운로더가 아니다. 날짜/지역/SKU의 페이지 내용은 바뀔 수 있다. 다음 변경은 새 버전 근거로 리뷰해야 한다. source_registry.csv가 각제품/노트/이용조건의 URL과확인일을제공한다.

## 데이터 계약

- 입력4열만사용: product_id/brand/product_name/source_type. 사용자ID/평점/시간 열은 반환/저장/분석하지 않는다. CSV parser가 원본행을 읽는 것과 개인평점분석을 구분한다.
- identity mapping58행은원본ID를유지한다. official_product_name/official_product_url은확인된제품만,reference_product_name/reference_url은검토후보도포함한다. custom의정보부족을자동영문변환·농도선택으로채우지않는다.
- notes의layer는top/middle/base/unspecified. 출처가층을명시하지않으면unspecified다. accord는명시적으로이름붙은구성accord만,official scent descriptor는별도이고vector에넣지않는다.
- feature compatibility는확인된제품만기존normalize와frozenIDF로투영한다. OOV는버리고새vocabulary/IDF를만들지않는다. 미확인제품은NOT_ASSESSED로남기며없는특징값을가짜0으로세지않는다.
- research_vectors.json은호환성계산의파생산출물이다. 새itemfactor/개인화프로필/추천카탈로그/모델가중치가아니다.

## 품질과 후속 사용

VERIFIED6은정체/농도 또는제조사제공형식/노트/최소1구성Accord에공식근거가있고기록된충돌이없는것이다. 전체formula/향조강도/제조배치/배포권한검증이라는뜻이아니다. PARTIAL40은근거가있으나누락/충돌이있고,REVIEW11은제품정체확정이더필요하며,UNRESOLVED1은향수형식의공식자료를확인하지못했다.

기존어휘일치56.20%는확인된제품의고유note token68/121이며전체58제품의완성도나정확도점수가아니다. Accord0/8은원문구성Accord이름을기존의일반향조단어로억지매핑하지않은결과다. 동의어가있을수있다는사실과확정매핑은다르다. NOTE 단복수/수식어/분자명매핑은후속리뷰대상이다.

사이트의공식출처와향취사실검증은학습/공개재배포허가가아니다. 현재모든rollout_ready=False. 향후권한·정체·중복·신규MFfactor/콜드스타트·학습평가분리를확인하고확장본을별도로관리한다. 원래Frozen479를덮어쓰지않는다. Git조작이나서비스연결은이번코드에없다.
