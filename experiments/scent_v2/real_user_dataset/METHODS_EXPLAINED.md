# V2-14 구현 설명과 파라미터

새 추천 모델·학습·성능 평가는 없습니다. 수집 시스템의 목표는 검증된 실제 응답을 별도로 저장하는 것입니다. 동의 문구·보관일·보안은 로컬 운영 초안이며 외부 모집 전 운영자 검토가 필요합니다. 교수 슬라이드의 ‘직접 데이터 구성 가능’과 사용자 요청의 보안/품질 구현 선택을 구분합니다.

## config.py / catalog.py

ROOT는 `__file__`의 프로젝트 상대 위치로 결정합니다. OUT/DATA는 새 실험 출력뿐, 후보/메타데이터/기존Train은 읽기 전용 경로입니다. 기본 포트8014, bind127.0.0.1, seed12, 개발비율.60, 평점0..10/.5, batch<=479, 이유<=300자를 고정합니다. CONSENT_VERSION은 표시 문구 버전입니다. 정책 문구를 바꿔 실제 운영할 경우 버전과 재동의 절차를 검토해야 합니다.

`load_catalog(candidate_path,metadata_path)`는 기존 후보 JSON479개 고유 URL과 cp1252/semicolon Fragrantica CSV를 연결하고 원래 이름·브랜드를 그대로 반환합니다. 기존 사용자·Q·model loader는 읽지 않습니다. `normalize(value)`는 NFKD/casefold/결합문자 제거와 공백 정리, `search(catalog,query)`는 원문 이름/브랜드 토큰·공백 제거 매칭으로 결정적 최대10개를 반환합니다. 이 패턴은 Team12의 web/backend/search.py를 참고한 표시용 검색이며 원본 데이터나 추천순위를 바꾸지 않습니다. 새 한국어 번역·브랜드·제품은 만들지 않습니다.

## validation.py

`validate_batch(payload,catalog)`는 허용 필드만 받습니다. request_id는8~80자 영숫자/underscore/hyphen,1~479개 후보 고유 ID, 경험 used/sampled, bool/문자열/NaN/Inf가 아닌 숫자0..10/.5격자, 선택 confidence(empty/low/medium/high), NFC 이유<=300자·제어문자 없음 등을 검사합니다. 부동소수점 오차1e-9 이내의 half-step은 정확한 .5격자로 canonicalize합니다. 미경험은 유효한0점이 아니며 제출에서 거부합니다. 이유의 이메일·전화번호 패턴은 우발적 입력을 줄이지만 모든 개인정보 탐지가 가능한 것은 아닙니다. `csv_safe(value)`는 텍스트의 선행공백 뒤=,+,-,@,탭·개행 등 수식 시작을 apostrophe로 무력화합니다. DB 원문/개인화면은 값 그대로, CSV 텍스트는 안전표시형입니다. 학습에는 이유를 쓰지 않습니다.

## split_manager.py

`assign_role(user_id)`는 SHA256(`12:realuser-split:ID`)의 처음64bit/2^64가.60 미만이면development, 나머지independent입니다. 무작위ID 등록 시 역할을 저장하고 평점·향후 사용자 수로 재배정하지 않습니다. 작은 표본의 정확한60/40명수는 보장하지 않습니다.

`support_split(user_id,rows)`는 향수ID 해시(`12:realuser-support:ID:item`) 순서로5 Support/나머지Heldout을 고릅니다. 평점값으로 고르지 않으며 n<5와 n=5는 각각 Support부족/Target없음입니다. 실제 평가 입력/정답 분리는 모델 선택 완료 후 별도 절차에서 고정해야 하며, 이 함수 호출만으로 모델 평가나 영구 evaluation release를 실행한 것은 아닙니다.

## storage.py

`now()`는 UTC ISO seconds, `digest(text)`는 SHA256입니다. `atomic_write(path,bytes)`는 같은 디렉터리0600 임시파일, flush/fsync, os.replace로 대상파일을 갱신합니다. replace 이전 오류에는 옛 파일이 보존됩니다. `csv_bytes(fields,rows)`는 고정 헤더 UTF-8/CSV quoting과 수식 방지를 적용합니다.

`FileRLock(path)`는 threading.RLock+POSIX fcntl.flock 또는 Windows msvcrt byte locking을 결합합니다. 중첩 export는 depth로 같은 락을 재사용하며 다른 스레드/프로세스의 mutation→CSV publish를 직렬화합니다. Windows 구현은 실행 미검증입니다. `close/__del__`은 lock descriptor를 닫습니다.

`Store(root,catalog,legacy_ids=(),dataset_kind=...)`는 participants.sqlite3와 역할별development/independent/ratings.sqlite3를 초기화합니다. real_user_collection과test_fixture는 메타데이터·ID prefix·source가 다르며 같은 저장소에 섞일 수 없습니다. 폴더0700/파일0600(POSIX)과 별도 admin code를 사용합니다. 기존 legacy user IDs가64hex인 것을 별도로 검증했고 새 realuser_UUID namespace는 disjoint입니다. UUID4,난수session/CSRF,unique DB constraints 및 collision retry가 기술적 충돌을 막습니다. 사람의 실제 경험·동일인 재가입·기기변경을 입증하지 않습니다.

`connection()`은 disk master DB에 두 역할 DB를 ATTACH하고 DELETE journal/synchronous FULL/secure_delete를 설정합니다. SQLite의 disk main multi-database transaction으로 등록/평점/요청기록·revision을 반영합니다. 권한/락이 파일 소유자의 직접 접근까지 막는 sandbox는 아닙니다. `bump(conn)`은 revision 증가입니다.

`register(consent,version)`은 현재 버전 true 동의 후 ID·역할·해시화된 session token·CSRF·동의 UTC를 저장합니다. `participant(conn,token)`은 token hash로 인증하며, `session(token)`은 본인 식별/CSRF만 제공합니다. `own_ratings(token)`는 인증된 본인의 역할 DB 기록만 조회합니다. 외부인이 ID만으로 조회할 수 없습니다.

`submit(token,csrf,payload)`는 전 항목 validation과 CSRF 후 BEGIN IMMEDIATE, 같은 사용자·향수 upsert, created_at 보존/updated_at 변경, request_id+body hash receipt를 수행합니다. 같은 요청 재시도는 중복 삽입하지 않고 다른내용의 key 재사용은 거부합니다. DB 실패는 rollback, CSV 실패는 확정DB 보존+csv_sync_pending입니다. `withdraw(token,csrf)`는 본인의 동의·평점·session·receipt를 삭제하고 collector 소유 파생 merge/training exports를 무효화/삭제한 뒤 CSV를 재생성합니다. 오류 시 pending을 알려 recover가 필요하며 외부 복사본/OS backup/포렌식 삭제는 보장하지 않습니다.

`export()`는 DB의 일관된 snapshot에서 CSV들을 교체하고 마지막 collection_metadata의 revision/sha256으로 그 세대를 인증합니다. root real_user_ratings.csv는 **개발용만**이며 독립 자료는 independent 하위에만 저장합니다. 여러 CSV 전체가 한 파일처럼 동시에 atomic인 것은 아니므로 실패 중에는 metadata checksum/revision 검사를 통과하지 못하고 builder가 거부합니다. 재시작/recover는 원장으로부터 복구합니다.

`aggregate()`는 개발용 rating값과 독립용 user/item ID만 조회합니다. 독립 평점값을 select하거나 histogram/평균으로 개발 화면에 노출하지 않습니다. 저장·본인 조회·독립CSV export 자체는 수집 I/O로 해당 자료를 처리하지만 모델 개발 경로에는 제공하지 않습니다.

## dataset_builder.py

`merge_rows(legacy,new,candidates,development_ids)`는 기존 normalized triple와 실제 신규개발 CSV를 검증합니다. 기존source는0제외 분석가정/새source는경험한0유효라는 차이를 source/zero_policy에 남기고 raw·normalized를 모두 제공합니다. 합성/test/비개발ID, 충돌/중복/범위/격자/미경험·후보밖신규를 거부합니다. 기존후보밖행은 플래그로 통합파일에 남기고 training-ready479뷰에서만 제외합니다.

`build(root,legacy_path,candidates)`는 개발CSV·동의원장의개발ID·현재revision·snapshotchecksum만검증하고 **독립평점파일은열지않습니다**. merged_real_ratings.csv/명시적training_ready_ratings.csv 및 보고서를 새로 생성합니다. 기존1805평점 중72행/59아이템이 후보밖이라 merged1805/training-ready1733(신규0)로 구분합니다. 기존원본은수정하지않습니다. `load_training_rows(root)`는 권위revision·출처종류·viewhash가맞는 최신개발용만 (u,i,float(normalized))로 반환합니다. 새데이터 입력후 stale export는 거부하므로 rebuild가필요합니다. 기존MF함수는0을허용하지만 신규CSV를과거Atrafshan zero-exclude ETL에재입력하면안됩니다. 실제모델학습은하지않았습니다.

## quality_report.py / app.py / UI

`distribution(values)`는 빈목록에None,그외mean/median/populationSD/min/max입니다. `summarize(participants,roles,candidates,kind)`는 참여/동의/제출·고유아이템/활동량/평점다양성/경험0점·positive7/low5·격자오류·신규tail건수·Support5/Target가능수를 제공합니다. 실제/테스트건수를분리합니다. 독립은건수/eligibility만,분포는개발용만입니다. 기존V2-13strictTrain item 빈도파일이있으면비식별집계만읽어기존미관측/≤2향수의새개발관측도집계하며actualfoldTrain빈도와구분합니다. `main()`은새출력범위의quality JSON을만듭니다.

`CollectorServer(port,store)`는127.0.0.1만bind하는ThreadingHTTPServer입니다. `Handler`는static파일whitelist,JSONAPI,Host/Origin/customheader,CSRF·HttpOnly/SameSiteStrict포트별cookie,관리자난수코드와1시간메모리session,512KBbody·중복JSONkey·nonfinite차단,CSP/no-store/nosniff/no-referrer를사용합니다. request logging을꺼IP/검색/평점을보관하지않습니다. 관리자값은log/URL에쓰지않습니다. 본인기록/관리자집계외원시파일다운로드엔드포인트가없습니다. `strict_json`은중복key·NaN/Inf를거부합니다. 예외응답은SQL/평점/개발자파일경로를반사하지않습니다.

`app.main()`은start/init/recover/admin-code를제공하고실제저장소위치는신규DATA에고정합니다. test-mode는명시적임시root만허용합니다. main.js는textContent/element API로검색·카트·경험에따른입력비활성화·검토·동일요청재시도·내기록수정·철회를구현합니다. 기본평점을임의5점으로채우지않습니다. admin.js는인증후집계만표시합니다. CSS만신규수집페이지에적용하고원래React디자인은건드리지않습니다.

## 검증·표준 라이브러리·한계

unittest/mock/TemporaryDirectory는가짜응답을임시root에서만검증합니다. HTTP도임시포트/임시test_fixture원장만사용하고실제응답0을유지합니다. `verify_runtime.main()`은실제페이지/479후보/관리자접근/원시파일차단을검증하되참여등록·평점제출은하지않고운영자기존code를로컬요청메모리에서만사용합니다. 브라우저테스트는8015의/tmp저장소에서0점→7.5점수정·재방문을검증했고닫았습니다. 실제화면8014는동의하지않은빈상태로열어두었습니다.

표준라이브러리만사용: pathlib/os/tempfile/fsync/replace는휴대가능경로·원자적파일쓰기,sqlite3는트랜잭션,threading/fcntl/msvcrt는동시성,uuid/secrets/hashlib는ID·인증·일관성해시,datetime는UTC,decimal격자검사는math/round,statistics/collections는집계,json/csv는직렬화,unicodedata/re는입력·검색정규화,http.server/http.cookies/urllib는로컬HTTP·쿠키·테스트,argparse는CLI,unittest/mock는검증입니다. 각함수파라미터·기본값은위와docstring/config에기록했습니다. 새외부코드차용·패키지설치·네트워크업로드는없습니다.

실제경험은자기신고이며독립검증하지못합니다. 쿠키삭제/다른기기/과거사이트참여자를동일인으로연결하지않고개인식별정보도수집하지않으므로**사람단위독립성은등록ID단위분리이상의보장이아닙니다**. Windows/공개배포/자동보관기간삭제는미검증/미구현범위입니다. 기존자료재배포HOLD,동의초안운영자검토,공유범위·보관종료운영을유지합니다. 정확도개선은측정하지않았습니다.
