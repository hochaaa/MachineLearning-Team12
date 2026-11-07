# V2-15 — 외부 실제 평점 확보·통합 준비

이번 조사 결과는 **BLOCKED_NO_ELIGIBLE_NEW_SOURCE**다. 실제 외부 평점 확보/479 매칭/안전한 추가 학습 평점은 **0/0/0**이다. 빈 데이터셋을 만들지 않았다. 인터넷 검색과 공식 페이지·스키마 검토는 수행했으며, raw 파일 다운로드는 하지 않았다. `dataset_discovery.py`는 조사 기록이지 다운로드 허용 목록이 아니다.

## 실행 (프로젝트 루트, Python 3.10+ 표준 라이브러리)

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s experiments/scent_v2/external_real_data/tests -v
```

기존 자산이 없는 클론에서는 Frozen19 검사에 원본 자산이 필요하다. 파일 불변 검사는 별도 작업 전 SHA256 스냅샷을 `SCENT_V215_BEFORE_SNAPSHOT`으로 지정해야 한다. 미지정 시 해당 검사 3개는 SKIP이며 PASS로 세지 않는다. 이번 실제 실행에서는 스냅샷을 지정했고 30개 모두 통과했다. 설치·학습·추천·평가 명령은 포함하지 않는다.

보고서 집계 재생성(공개 웹 재조사나 데이터 확보가 아님):

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m experiments.scent_v2.external_real_data.run --snapshot "$SCENT_V215_BEFORE_SNAPSHOT"
```

스냅샷 JSON은 `{프로젝트 상대경로: SHA256}` 형식의 로컬 비공개 파일이다. 프레젠테이션 append 확인에는 같은 스냅샷 디렉터리의 `scent-v215-<문서명>` 원본 사본도 사용한다. `run`은 자신의 산출물 디렉터리에만 쓰며 최초 보고서의 외부 페이지 증거를 재검증하지 않는다. 다른 시점 스냅샷으로 과거 불변성을 재구성할 수는 없다.

## 나중에 허가된 자료가 제공되면

1. 제공자/버전/원본 서비스, 다운로드·학술 이용·파생·개인정보·상위 약관의 근거를 사람이 검토한다. 재배포 허가는 별도다. 지금 승인된 신규 출처는 없다.
2. `license_audit.verified_file(path, evidence)`로 로컬 파일을 열기 전에 권한과 SHA256을 확인한다. `schema_inspection.read_original`은 CSV/JSON/JSONL만 읽는다. 원본 열에서 canonical 열로의 매핑은 출처별 검토가 필요하다. Parquet/대용량 스트리밍은 구현하지 않았다.
3. 검토 완료된 파일만 비공개 `outputs/scent_v2/external_real_data/data/raw/<source>/`에 보존한다. 현재 이 폴더와 평점 CSV는 만들지 않았다. 원본 행·리뷰·사용자명을 보고서에 넣지 않는다.
4. `dataset_builder.prepare(rows, evidence, scale, catalog, secret)`에 명시적 실제 평점, 출처별 scale/0의미 근거, 원본 479 ID를 갖는 카탈로그, 외부에 저장하지 않는 개인용 HMAC 키를 제공한다. 결과는 최소 컬럼의 가명 평점·매칭 집계·충돌 격리 기록이다. 같은 시각/평점만으로 동일 리뷰라고 확정하지 않는다.
5. 동일 제품의 농도·판본·연도·성별 메타데이터가 불완전하면 수동 검토한다. 교차 서비스 숫자 ID는 동일 ID가 아니다. fuzzy는 제안만 하며 자동 확정하지 않는다. 원본 브랜드/제품명은 바꾸지 않는다.
6. 기존 75명 평가 사용자의 **전체 이력**을 값 디코딩 전에 제거한 strict train만 `assemble`에 전달한다. 교차 출처의 사람 중복이 불명확하면 외부 행은 격리한다. 네임스페이스가 다르다고 독립 사용자가 되는 것은 아니다. V2-14 저장소는 이 코드에서 읽지 않는다.
7. 신규 합법 자료 확보 후에만 보관용 전체 결합본과 strict 학습본을 별개로 승인·생성한다. 현재 코드/fixture 검증은 실제 출처 어댑터나 실데이터 통합 완료를 의미하지 않는다. 전체1805 보관본을 읽어 내보내는 기능은 이번에 실행/구현하지 않았다.

모든 행 fixture는 테스트 내부/임시 폴더에만 있다. `APPROVED_LOCAL` 예시는 테스트용 검증 분기를 검사하며 실제 허가 기록이 아니다. 함수는 근거의 진위나 법률상 유효성을 자동 판단하지 못한다. 현재 실데이터의 다운로드·통합·원본 scale 의미·cross-source 중복·연결성 개선은 미검증이다.
