# V2-14 — SCENT MATCH 실제 평점 수집 도구

**독립적인 로컬 수집 시스템입니다. 기존 추천 모델·API·웹사이트는 변경하지 않습니다.** 실제 사용·시향한 기존 479개 향수만 0~10점, 0.5점 단위로 평가합니다. 3개만 알고 있다면 3개만 입력하세요. 신규 실제 응답 0개로 초기화했으며, 자동 검증과 브라우저 테스트는 임시 테스트 저장소에서만 진행했습니다.

## 1. 실행·종료

Mac, 프로젝트 루트에서:

```sh
sh experiments/scent_v2/real_user_dataset/run-macos.sh start
```

브라우저: **http://127.0.0.1:8014**

운영자 화면: **http://127.0.0.1:8014/admin**

실행 터미널에서 **Ctrl+C**로 이 수집 서버만 종료합니다. 다시 같은 명령으로 실행하면 같은 저장소를 사용합니다. 포트 충돌 시 `sh experiments/scent_v2/real_user_dataset/run-macos.sh start --port 8016`으로 별도 포트를 쓰세요. 쿠키는 포트별로 분리되므로 다른 포트에서는 새 참여 세션으로 보입니다. 기존 서비스 포트는 건드리지 않습니다.

Windows PowerShell, 프로젝트 루트에서(직접 실행 **미검증**):

```powershell
powershell -File experiments/scent_v2/real_user_dataset/run-windows.ps1 -Command start -Port 8014
```

두 스크립트 모두 프로젝트 상대경로를 사용합니다. 기존 Python 환경이 없으면 설치된 Python3.10+ 표준 라이브러리만으로 실행할 수 있습니다. 패키지 설치는 하지 않습니다. 필요하면 `SCENT_COLLECTION_PYTHON`에 사용할 Python 실행 파일을 지정하세요. 운영체제 보안 정책을 우회하도록 안내하지 않습니다.

필수 로컬 자산: `outputs/improvement/candidates.json`과 `Term-project-datasets/fra_cleaned.csv`. 모델·개인평점 파일은 수집 화면 실행에 필요하지 않습니다. 기존 Train과의 결합에는 추가로 `outputs/validation/train_exclude_3.json`이 필요합니다. 이 자료의 공유 권한이 보류 상태이므로 **Git Clone만으로 원본 자산까지 확보된다고 주장하지 않습니다.**

## 2. 참여·검색·입력·제출

1. 참여 목적·로컬 보관·공유·철회 안내를 읽고 동의합니다. 동의 전 시작할 수 없습니다.
2. 원래 향수 이름이나 브랜드(예: `Black Orchid`, `Tom Ford`)로 검색하고 ‘추가’를 누릅니다. 원본 이름·브랜드·URL ID를 그대로 사용하며 후보 밖 제품을 만들지 않습니다.
3. 각 향수에서 ‘직접 사용’ 또는 ‘직접 시향’을 선택하고 실제 평점을 입력합니다. ‘경험 없음’에서는 평점 입력이 비활성화되며 제출에서 제외됩니다.
4. 0점은 경험자가 실제로 부여한 최저 점수이며, 미경험·미입력을 0으로 바꾸지 않습니다. 신뢰도·개인정보 없는 이유는 선택사항입니다.
5. ‘입력 내용 검토하기’ → ‘확인하고 제출’을 누릅니다. 같은 향수의 기존 기록은 새 행으로 복제하지 않고 수정합니다. 저장 완료/CSV 지연 메시지를 확인하세요.
6. 같은 브라우저·포트에 재방문하면 내 기록을 다시 보고 수정할 수 있습니다. 브라우저 쿠키 삭제·기기 변경은 동일인 확인이 불가능합니다. 동일인의 중복 가입을 완벽히 막지 못하며 사람 단위 독립성에도 이 한계가 남습니다.

동의 문구는 **로컬 운영용 초안**입니다. 외부 참여자를 모집하기 전에 운영자가 목적·보관 종료 예정일(기본2026-11-30)·삭제 방법·접근·공유 범위를 검토해야 합니다. 자동 보관기간 삭제는 구현하지 않았으므로 운영자가 일정에 맞춰 삭제해야 합니다. 인터넷 공개 배포는 이번 범위가 아닙니다.

## 3. 저장 파일과 복구

`outputs/scent_v2/real_user_dataset/data/`:

```text
participants.sqlite3                 # 동의/고정 역할/해시화된 세션 인증 원장
participants.csv                     # 동의 버전·시각·역할, 인증 토큰 없음
collection_metadata.json             # 원장 revision, CSV checksum/출처
real_user_ratings.csv                # 개발용 응답만, 초기에는 헤더뿐
.admin_token                         # 관리자 비밀 코드, 업로드 금지
.store.lock                          # 프로세스 간 원장/내보내기 직렬화
development/ratings.sqlite3          # 개발용 평점 원장
development/real_user_ratings.csv    # 개발용 CSV 뷰
independent/ratings.sqlite3          # 독립 평가용 평점 원장
independent/real_user_ratings.csv    # 평가용 CSV, 개발 코드 사용 금지
merged_real_ratings.csv              # 기존 Train + 신규 개발용만
training_ready_ratings.csv           # 후보479에 속한 통합 개발용만
merge_report.json                   # 원본 hash/출처/별도 제외 건수/revision
```

CSV UTF-8 고정 스키마: `user_id, perfume_id, rating, experience_type, confidence, preference_reason, created_at, updated_at, source`. 시각은 서버 UTC. `source=real_user_collection`. 동의는 participants 원장에 별도 버전·시각으로 저장합니다. 개발/평가 역할은 임의 사용자ID와 seed12의 해시로 **등록 시, 평점 입력 전에** 정해집니다. 60/40은 해시 비율이며 적은 인원에서 정확한 수 비율을 보장하지 않습니다. 기존 인원의 역할은 재배정하지 않습니다.

기준 원장은 SQLite이며, multi-database transaction으로 동의·평점·중복 요청 기록을 반영합니다. CSV는 같은 파일시스템 임시 파일→fsync→원자적 replace 방식의 스냅샷입니다. 여러 CSV의 완성 여부는 마지막 metadata checksum/revision으로 확인합니다. 디스크 오류로 CSV 내보내기가 실패해도 이미 확정된 원장 평점은 보존하며 `csv_sync_pending`을 표시합니다. CSV를 기준 원장으로 오인하지 마세요.

복구(공간·권한 문제를 먼저 해결):

```sh
sh experiments/scent_v2/real_user_dataset/run-macos.sh recover
```

같은 제출 ID 재시도는 중복 행을 만들지 않으며 다른 내용으로 같은 ID를 재사용하면 거부합니다. 동시에 여러 요청/CLI가 접근해도 파일 잠금과 DB 트랜잭션으로 직렬화합니다. 새 데이터 입력 후 과거 training export는 revision 검사에서 거부되므로 다시 결합해야 합니다.

파일은 기본 디렉터리0700/파일0600(Mac/POSIX), 출력 전체는 기존 `.gitignore`의 `outputs/`로 제외됩니다. 신규 소스 디렉터리에도 응답·DB·비밀 파일 제외 규칙을 추가했습니다. 기존 `.gitignore`는 수정하지 않았습니다. Windows ACL은 실제 운영 환경에서 별도 확인이 필요합니다. 로컬 파일은 암호화된 저장소가 아니며 같은 OS 계정 소유자는 원시 파일에 접근할 수 있습니다.

## 4. 관리자·품질 검사

관리자 코드 확인(로컬 터미널에서만, 채팅·Git에 붙여넣지 마세요):

```sh
sh experiments/scent_v2/real_user_dataset/run-macos.sh admin-code
```

`/admin`에 코드를 입력합니다. 화면에는 누적 참여·평점·coverage·개발용 평점 분포, 독립 평가용 건수/적격 인원만 표시합니다. 개별 평점/독립 정답·평균·분포는 표시하지 않습니다. 일반 참여자 화면과 관리자 API가 분리되며 로그인 없이 관리자 집계를 읽을 수 없습니다.

품질 JSON 생성:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m experiments.scent_v2.real_user_dataset.quality_report
```

또는 기존 venv Python을 사용하세요. 결과 `outputs/scent_v2/real_user_dataset/dataset_quality.json`. 평점0개면 평균/비율은 null, 건수0·미관측479로 정상 출력합니다. 개인별 통계는 개발용 집계/히스토그램으로만 공개하며 평가용 label 분포는 보류합니다. 현재 수집 현황은 모델 정확도를 뜻하지 않습니다.

## 5. 기존 자료와 결합·재사용

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m experiments.scent_v2.real_user_dataset.dataset_builder
```

기존 1,805개 정규화 Train은 읽기 전용입니다. 신규 **개발용** CSV만 읽고 동의 원장의 역할·checksum·revision·ID 충돌·출처·경험·척도·중복·결측을 검증합니다. 독립 평가 평점 파일·과거 합성 파일은 읽거나 결합하지 않습니다.

기존 1,805개에는 서비스479개 밖의 **72평점/59향수**가 있습니다. `merged_real_ratings.csv`에는 이 기존 행도 `in_service_candidates=False`로 보존합니다. 명시적 `training_ready_ratings.csv`에서만 후보 정렬 후 **1,733개**가 남고 제외 수를 보고합니다. 신규 개발 평점0개인 현재 수치이며, 원본 행을 삭제하거나 1,805개 모두479개에 속한다고 주장하지 않습니다.

기존 source의 0점 제외는 분석 가정, 신규 source의 경험한 명시적0점은 유효값입니다. raw0..10과 normalized0..1을 둘 다 저장하고 출처별 `zero_policy`를 구분합니다. 기존 MF 모델 함수는 정규화0을 처리할 수 있지만, 신규 CSV를 기존 Atrafshan raw ETL의 zero-exclude 경로에 넣으면 안 됩니다. 기존 ETL·모델을 수정하지 않았습니다.

향후 실험은 `dataset_builder.load_training_rows()`로 검증된 최신 개발용 view를 읽을 수 있습니다. 독립 평가 평점은 기본 학습 경로로 제공하지 않습니다. 역할 분리·집계는 `collection_metadata.json`, 관리자 건수, 신규 `split_summary.json`으로 확인합니다. 미래 평가는 `split_manager.support_split()`의 seed12/ID-only 정렬로5 Support와 나머지를 분리하며 n<5/정확히5는 별도 부적격입니다. 실제 평가·모델 학습은 이번에 실행하지 않습니다. 독립 정답의 공개·열람/평가 실행은 모델·프로토콜 선택 완료 후 별도 평가 절차에서 진행해야 합니다.

## 6. 철회·삭제

참여자는 같은 브라우저에서 ‘참여 철회 및 내 데이터 삭제’를 누릅니다. 원장의 해당 평점·동의·세션·재시도 기록을 삭제하고 현재 CSV를 다시 만들며, Collector 소유의 통합/학습/평가 파생 export는 폐기합니다. 원본 기존 데이터는 건드리지 않습니다. CSV 오류가 나면 화면의 지연 경고에 따라 운영자가 recover를 실행해야 합니다.

수동 복사본·OS 백업·디스크 잔존 데이터까지 포렌식 삭제를 보장하지 않습니다. 브라우저 쿠키를 잃으면 익명ID로 운영자에게 삭제를 요청할 수 있으나, 임의 ID만으로 자동 로그인/복구 기능을 제공하지 않습니다. 운영자는 동의 문구에 표시한 일정과 별도 보관본까지 관리해야 합니다.

## 7. 테스트·공개 배포 제한

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -W error -m unittest discover -s experiments/scent_v2/real_user_dataset/tests -v
```

단위·HTTP 테스트는 `TemporaryDirectory`만 사용합니다. 브라우저 테스트는 `--test-mode --data-root /private/tmp/... --port 8015`로 분리하며 ID/source가 `testuser_`/`test_fixture`라 실제 결합에서 거부됩니다. 실제 `data/`에 테스트 평점을 넣지 않습니다. Mac 실행·HTTP·브라우저 동작은 검증했고 Windows는 미검증입니다.

공개 배포 전 별도 검토: 적법한 동의·보관/삭제 운영, TLS·사용자 인증·rate limiting·접근 계정 분리, DB 백업/암호화/권한, CSRF/CORS/공개 프록시, 악성 입력·감사·운영 모니터링, 익명 응답의 재식별/공유 위험, 기존 metadata 재배포 권한. 현재 loopback 전용 구현을 그대로 인터넷에 노출하지 마세요.
