# 데이터 계약

원본 위치는 `Term-project-datasets/`, 원본은 읽기 전용으로 취급한다. 해시는 `outputs/audit/input_sha256.json`. 사용자가 2026-10-22 수업 프로젝트 로컬 사용권을 확인했다. 이 확인을 원본 사이트 약관의 독립 검증이나 재배포 허가로 표현하지 않는다.

| 데이터 | 실제 파일/형식 | 역할과 계약 |
|---|---|---|
| Fragrantica | fra_cleaned.csv, semicolon, cp1252로 strict decoding | URL 고유 ID; Perfume/Brand, Top/Middle/Base comma-separated phrases, mainaccord1..5. 숫자 Rating Value는 콘텐츠에 사용하지 않음. |
| Atrafshan | atrafshan_data.json UTF-8 JSON list | user_id/perfume_id, user_vote_on_perfume.votes.رایحه만 개인 향 평점; users_vote는 상품 집계이므로 사용 안 함. |
| Laure | perfumes/reviews/brand/notes/category/season/users.json, Django fixture list pk/model/fields | 정수 FK 복원. reviews의 user/perfume ID만 가능성 감사에서 사용. rate 값은 현 실험에서 열람·학습·튜닝 안 함. users 프로필은 로드 안 함. |
| Parfumo | parfumo_data_clean.csv UTF-8 comma CSV | 보조 consistency 전용, 현재 보조 실험은 미실행. |

Atrafshan rating은 숫자 0..10 범위 검사 후 /10으로 변환한다. 0 포함·제외는 서로 다른 가정일 뿐 확정 의미가 아니다. 결측과 파싱 실패는 invalid로 집계한다. 같은 user/item의 동일 점수 중복은 축약하고 상충 점수는 제외한다. 매칭 후 하나의 target에 중복 연결되어 값이 충돌해도 격리한다. 사용자 ID는 `SHA256('atrafshan:'+id)`로 가명화하고 이름/댓글은 출력하지 않는다.

매칭은 Unicode NFKD, 악센트/구두점/공백 정리, 대소문자 정규화, eau de parfum→edp 등 동의 농도 표기 통일 후 brand+name 정확 일치만 허용한다. EDT/EDP/Elixir/연도/버전 단어를 삭제하지 않는다. 다중 target은 ambiguous. accepted도 수작업 의미 검증이 필요하다. 낮은 매칭 커버리지와 false negative를 감수하는 보수적 초기 정책이다.

Laure 39,699행 중 PK 26130001이 서로 다른 내용으로 두 번 나온다. 두 행을 모두 카탈로그에서 격리해 39,697개 usable ID를 얻는다. 외부 평점의 PK 누락/충돌 항목은 추천 후보로 받아들이지 않는다. FK 감사와 배제 수를 보고한다. 외부 시즌/가격은 개발 필터의 근거로 사용하지 않는다.

개발 train의 아이템 문서로만 vocabulary/IDF를 fit하고 나머지 카탈로그는 transform만 한다. 외부 support/정답 분리, 평점 scale mapping, final freeze는 아직 미완료다. 이 단계 전에 외부 평점 기반 모델 실행을 하지 않는다.

## 동결 평가 완료 후 추가 계약

2026-10-22 사용자 결정: 0 제외는 주 분석 가정이며 0의 의미는 미확정. 0 포함은 민감도 분석이다. 외부 평가에서는 고정 개발 candidate479개로만 범위를 제한해 독립 Basenotes 신규 사용자 선호를 측정했다. source rated perfume70개에 trained factor가 있고 후보479개와 겹치는 source perfume은64개다. source ID별 상품과 canonical 상품 수를 구분한다. 구조적 적격35명, support122개, answer140개, positive 사용자26명. support는 ID hash순 n//2로만 정하고 rating을 보고 선택하지 않았다.

외부 범위0..9는 사전 ordinal scale 가정으로 고정했다. 실제 검증에서도 이 범위를 벗어나는 값은 없었다. /9 support mapping과 normalized>=.7 positive 정의를 외부 결과로 바꾸지 않았다. 척도의 선호 의미가 Atrafshan과 같다는 주장은 하지 않고 외부 MAE/RMSE는 N/A다. 외부 정답은 별도 private 파일과 harness에만 두며 추천기는 support만 받았다.

Laure 복원 note phrase의 train vocabulary coverage는93.14%이고, 추론은 기존 matched Fragrantica 표현을 썼다. 외부 정답이나 external metadata로 vocabulary/IDF를 다시 fit하지 않았다. test 소비 뒤 모델/alpha/threshold/프로필/매칭 변경은 하지 않는다. 동결 모델과 원본 해시 검증은 outputs/final/integrity_check.json, 마지막 결과는 reports/MODEL_IMPROVEMENT.md에 있다.
