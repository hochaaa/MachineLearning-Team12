# V2-21 · 실제 사용자 추천 평가 (local only)

기존 모델·서비스·V2-14 DB·V2-16~20을 수정하지 않는 독립 도구입니다. 실제 Frozen Hybrid479만 사용합니다. 497 Content는 지원하지 않으며, Offline 독립성 미확인을 점수로 덮어쓰지 않습니다. 수집 프로그램 완성과 실제 평가 데이터 확보를 구분합니다.

## 실행

Mac 프로젝트 루트:

```sh
sh experiments/scent_v2/real_user_evaluation/run-macos.sh start --policy outputs/scent_v2/real_user_evaluation/operating_policy.json
```

http://127.0.0.1:8021 — Ctrl+C로 이 서버만 종료. 기존 서비스 포트를 사용하지 않습니다.

Windows PowerShell (**직접 실행 미검증**):

```powershell
powershell -File experiments/scent_v2/real_user_evaluation/run-windows.ps1 -Command start -Policy outputs/scent_v2/real_user_evaluation/operating_policy.json -Port 8021
```

기존 final_v1 Python 환경과 runtime5 자산이 필요합니다. 패키지 설치/다운로드는 자동 수행하지 않습니다. 자산 해시가 다르면 MODEL_UNAVAILABLE이며 합성 모델로 대체하지 않습니다. Clone만으로 비공개 자산까지 확보된다고 주장하지 않습니다.

## 확정된 신규 수집 방침

사용자가 확인한 보관 종료일 **2027-02-28**. 원시 응답은 **데이터관리담당자1명 전용 OS 계정**에서만 다룹니다. 다른 팀원에게는 집계 통계만 공유합니다. 운영 담당자의 실명은 임의 지정하지 않았습니다. 같은 OS계정을 공유하면 파일 접근자를 분리할 수 없으므로 전용 계정/기기 접근 권한은 실제 운영자가 관리해야 합니다. 디렉터리0700/파일0600, 암호화나 외부 계정 인증은 아닙니다.

가입 시 삭제코드를 한번만 표시하고 서버에는 SHA256만 저장합니다. 쿠키가 없어도 코드로 연결 원시응답·식별자·세션·피드백을 삭제합니다. 원본 코드는 복구할 수 없고 분실 시 개별 삭제가 제한될 수 있습니다. 이메일·이름·전화번호는 필수 수집하지 않습니다.

기한 후 startup/request에서 purge합니다. **서버가 꺼져 있으면 담당자가 아래 purge를 실행해야 합니다.** 이번에 OS예약작업은 만들지 않았습니다. 수동 백업/복사한 raw 파일도 기한·삭제 요청에 포함해야 합니다.

```sh
sh experiments/scent_v2/real_user_evaluation/run-macos.sh purge
sh experiments/scent_v2/real_user_evaluation/run-macos.sh audit --policy outputs/scent_v2/real_user_evaluation/operating_policy.json
sh experiments/scent_v2/real_user_evaluation/run-macos.sh export --policy outputs/scent_v2/real_user_evaluation/operating_policy.json
```

export는 `outputs/scent_v2/real_user_evaluation/data/v21_*.csv`에만 쓰는 관리자 로컬 명령입니다. 개인별 ID/평점이 들어 있는 원시자료이므로 외부/Git/다른팀원에게 전달하지 마세요. auth/deletion 원본코드는 export하지 않습니다. CSV는 원장의 복구 가능한 파생물이며 삭제시 기존스냅샷을무효화합니다. HTTP admin/export/download는 제공하지 않습니다.

**이 방침은 V2-21 신규 수집에만 적용합니다. 기존 친구12명85개 평점에는 소급하지 않습니다.** 기존85개는 사용자 확인의 당초 프로젝트 활용 범위로 원본을 보존합니다. 신규 삭제/purge는 그 원본이나 기존 실험 폴더에 접근하지 않습니다.

## 평가 경계

추천 전 경험평점과 추천 후 피드백을 서버 시점으로 구분합니다. 사전고유매칭6개 이상이면 hash-selected5 Support와 나머지 held-out 구성이 가능하지만, Frozen학습 사용자와 실제 동일인 여부가 미확인이라 실제 Offline 점수는 차단합니다. 학습사용자 배제와 독립 정답 증거가 마련되기 전 `BLOCKED_FROZEN_TRAIN_MEMBERSHIP_UNVERIFIED`; 신규응답0이면 `NOT_EVALUATED_NO_NEW_DATA`입니다. MF훈련 함수는 이 수집기에 없습니다.

미경험·기억불명은 null, 경험자의0점은 실제점수입니다. 추천 Top5와 uniform 비교5개를 구분하며 포함확률은 Support/Top5에조건부5/469입니다. 후발 피드백은 exposure-based 분석이며 NDCG의 독립 정답이 아닙니다. 사용자당1개immutable세션이므로 반복 클릭 중복은 막지만 쿠키/기기 변경의 실제인물 중복은 확인할 수 없습니다.

원본카탈로그에 농도가 없으면 CATALOG_UNSPECIFIED로 기록합니다. 제품명이 비슷한 EDT/EDP를 추측 연결하지 않습니다. 사용자가 정확한 원본제품 경험을 확인할 수 없으면 미등록검토제품으로 남겨주세요. 새로운 제품에 대한 자동번역·fuzzy identity매칭은 없습니다.

## 재현 검증 명령

기존파일 hash snapshot `/tmp/scent-v221-before.json`과 발표5문서의 `/tmp/scent-v221-<name>` 원문복사본을 작업전에 만들어야 byte불변검증이 성립합니다. 사후snapshot을 사전증거로 만들지 않습니다.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/real_user_evaluation/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.real_user_evaluation.smoke
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.real_user_evaluation.smoke --serve
```

smoke --serve는8022에 실제 Frozen을 쓰는 **임시 test_fixture 서버**를 열며 종료시임시DB를폐기합니다. 실제참여자URL은8021입니다. 합성입력을실제원장으로옮기지않습니다. smoke/report/verify는 저장파일 exclusive create 정책으로 완료한 산출물을 덮어쓰지 않습니다. 새 독립 검증은 별도 버전/출력경로로 수행하세요. live audit/export만은 현재원장을읽는관리명령입니다.

별도 기존85진단: `legacy_diagnosis --csv "$LOCAL_APPROVED_RATINGS"`는 원본/라이선스 snapshot의 **제품 식별만** 분석하고 새 카탈로그나 점수를 만들지 않습니다. 사용자별원본값은출력하지않습니다. `legacy85_product_review.csv`와 summary에서 미연결사유를 보고, 제품·농도 확인은 별도link review로 축적합니다.
