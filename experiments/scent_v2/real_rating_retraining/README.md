# V2-16 — 실제 사용자 평점 통합 준비

결과: **BLOCKED_NO_EXACT_479_MATCHES**. 수집CSV12명/85평점/58제품을 검증했으나 기존479에 확정 연결되는 평점0개다. 실제학습·추론·A/B평가·튜닝0회. 모델 변경도 없다. 이 runner는 현재의 무매칭 감사 결과를 재현하며, 범용 재학습 완료 도구가 아니다.

## 재현 (프로젝트 루트, 기존 Python3.12/NumPy 환경, 설치 없음)

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/real_rating_retraining/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.real_rating_retraining.run --csv "$V216_ORIGINAL_CSV" --consent-confirmed --snapshot "$V216_BEFORE_SNAPSHOT"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.real_rating_retraining.reporting
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.real_rating_retraining.verify --csv "$V216_ORIGINAL_CSV" --snapshot "$V216_BEFORE_SNAPSHOT"
```

`V216_ORIGINAL_CSV`는 원본 로컬경로, `V216_BEFORE_SNAPSHOT`은 작업 전에 만든 `{프로젝트상대경로: SHA256}` JSON이다. snapshot과 같은 디렉터리의 `scent-v216-<발표문서명>` 사본으로 append-only를 검증한다. 사후 snapshot은 과거 보존 증거가 아니다. 원본/카탈로그/기존 strictTrain/분할 manifest/runtime content가 없는 소스만의 clone에서는 실제감사를 재현할 수 없으며 fixture 검사만 가능하다.

이미 생성된 V2-16 결과를 덮어쓰거나 자동 재학습하지 않는다. 명령 전체를 반복하면 기존 결과 충돌로 중단한다. 처음 실행할 때도 개인정보 저장/학습/평가/집계 발표 동의가 확인되지 않으면 `--consent-confirmed`를 넣지 않는다. 이번 실행에서는 사용자에게 해당 범위를 실제로 확인했다. 이 flag가 원본 데이터 재배포를 승인하지 않는다.

## 처리와 보존

- `audit.py`: canonicalCSV 검증, 원점수 유지, 정확한 브랜드+농도/판본 포함 제품명 또는동일URL 매칭. opaque 제품ID hash를 역추정하지 않는다. fuzzy/자동번역 없음.
- `run.py`: 기존75명 전체이력을 decode 전에 건너뛰는 경계 파서만 재사용. 기존 held-out 답을 읽지 않는다. V2-14Store·SQLite·독립평가 저장소도 파싱하지 않는다. 실제MF.fit 진입을 guard로 차단하고0회를 기록한다.
- `private/unmatched_ratings.csv`: 이번85행을 source별 가명/원점수로 보관. 원본participant ID 미포함. HMAC키는 별도 `private/identity.key`. 파일0600/폴더0700, Git에는 이미 제외된 outputs 아래에만 저장. 가명화는 익명화가 아니다.
- `reporting.py`: 기존 aggregateCSV/보고서만 인용, V1@10/V2@5와Inner/Outer를 구분해 서술. 기존5개발표문서는말미에만추가. 새MD/CSV만생성하며Word/PPT/차트이미지는만들지않았다.
- `verify.py`: 원본CSV/Frozen19/manifest/서비스/이전결과/발표prefix/Git의실제사후검사8개. 합성사전24개와구분한다.

현재 source_type=catalog의73개평점은우리479카탈로그에서선택된것이아니다. 고정후보에exactbrand가없고ID도호환되지않는다. custom12개는원본score와제품표기를보존해수동검토대상으로남겼다.574는479활성메타데이터token수이고604는보존된runtimeIDF사전크기다. 두수치를맞추려고모델을변경하지않았다.

추후 검증된 대응표/479경험평점이 생기면 먼저 label-blind 사용자단위 학습/평가분리와 사람중복 검토를 확정해야 한다. 그 전에는 본runner가비어있지않은매칭을뜻밖에발견해도재학습하지않고중단한다. 이번에 사용하지 않은 새재학습경로를구현완료라고주장하지않는다. 후보확장/새Notes취득/복수취향Content는이번범위밖이다.
