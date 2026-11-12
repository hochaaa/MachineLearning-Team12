[https://scent-match-team12.vercel.app](https://scent-match-team12.vercel.app)

# SCENT MATCH · Team 12

향수 선택과 0–10점 취향 입력으로 실제 Frozen V1의 Top 5를 추천하는 머신러닝 프로젝트다. FastAPI와 React/TypeScript/Vite를 사용하며, 콘텐츠 TF-IDF/cosine과 SGD Matrix Factorization의 점수를 **0.25 / 0.75**로 결합한다. 신규 사용자는 고정 item factor에 Ridge fold-in을 적용한다. 479개 후보에서 입력 향수를 제외하고 Woody / Floral / Rose 조건을 적용한다. 점수는 확률이 아니다.

## Clone → Install → Start

Git, **Python 3.12**, Node 20.20 또는 지원 Node 22.12+, npm이 필요하다. Python 의존성은 `web/backend/requirements-lock.txt`, npm은 `web/frontend/package-lock.json`으로 고정한다. 기존 가상환경·node_modules를 복사하지 않는다. 첫 설치에는 패키지 registry 접근이 필요하다.

```sh
git -c core.autocrlf=false clone --single-branch --branch development-v2 https://github.com/hochaaa/MachineLearning-Team12.git
cd MachineLearning-Team12
```

macOS:

```sh
sh deployment/final_v1/run-macos.sh install
sh deployment/final_v1/run-macos.sh check
sh deployment/final_v1/run-macos.sh start
```

Windows PowerShell (**실제 Windows 실행 미검증**):

```powershell
& .\deployment\final_v1\run-windows.ps1 install
& .\deployment\final_v1\run-windows.ps1 check
& .\deployment\final_v1\run-windows.ps1 start
```

PowerShell 정책으로 제한되면 정책을 바꾸지 않고 `py -3.12 -B deployment/final_v1/manage.py install` / `check` / `start`를 사용한다.

- 웹: http://127.0.0.1:5177 — start가 React와 API를 함께 실행한다.
- API: http://127.0.0.1:8004 — 두 포트가 비어 있어야 한다.
- 종료: start 터미널에서 Ctrl+C. 재시작: 같은 start 명령.
- 시연: Tom Ford 검색 → Bitter Peach / Black Orchid / Ebene Fume 선택 → 9 / 7 / 2 입력 → Discover my matches. 추천 카드 5개를 확인한다.

실행은 Git에 이미 포함된 `outputs/step12_runtime/assets/`의 최소 자산 5개를 사용한다. 원본 CSV, 학습 사용자 평점, 사용자 mapping, 기존 개발자의 `.local`은 필요하지 않다. 파일 해시가 다르면 오류로 중단하며 합성 결과로 대체하지 않는다. authorization JSON은 실행 조건이 아니다. 이 실행 가능성이 실제 자료의 사용·재배포 권한 확인을 뜻하지는 않는다.

## 어디를 수정하나요?

```text
configs/                 모델·실험 설정 (동결 설정 보호)
data/                    데이터 계약 안내
src/perfume/             전처리·콘텐츠·MF·Hybrid·평가 원 구현
scripts/                 연구 실행·진단·보고서 도구
experiments/             V2/V3 등 비교 실험과 synthetic_demo 학습 예제
deployment/final_v1/     현재 설치·실행 진입점
          /standalone_v1/개인 평점 없이 실제 동결 모델을 읽는 로더
web/frontend/            실제 React UI
web/backend/             API 스키마·검색·기존 연구 로더
web/demo/, web/deployment/ 과거 실행/배포 진단 도구 (현재 시작점 아님)
tests/                   핵심 ML 합성 테스트
demos/stage2/            여러 회귀 테스트가 사용하는 합성 취향 입력
outputs/                 로컬 실험·평가 증거; Git에는 최소 자산 5개만 포함
docs/                    문서 안내 및 과거 실행 가이드
reports/                 로컬 분석 보고서 (Git 제외)
tools/team_setup/        이전 환경 감사 도구 (현재 설치기는 아님)
```

일반 웹 개발은 `web/frontend/src/`, 검색은 `web/backend/advanced_search.py`와 관련 테스트, 실행 관리는 `deployment/final_v1/`에서 시작한다. 학습 연구는 `experiments/`에서 진행하고 서비스 모델과 분리한다. `experiments/synthetic_demo/`는 실제 모델과 다른 선택적 예제다. 과거 코드/문서의 `demo/`는 이 경로로 이동했다.

## 테스트와 모델 보존

```sh
python3.12 -B -m unittest discover -s deployment/final_v1/tests -v
# start 후, macOS의 새 런타임 Python으로 실제 서버 확인:
deployment/final_v1/.local/venv/bin/python -B -m deployment.final_v1.tests.live_smoke
```

Windows smoke의 Python은 `deployment/final_v1/.local/venv/Scripts/python.exe`다. 테스트는 합성 취향을 사용하며 모델 재학습이나 기존 Validation/Test 평가를 실행하지 않는다. 자세한 실행·오류 안내는 [런타임 README](deployment/final_v1/README.md)를 따른다.

Frozen V1 소스는 기준 커밋 `2c33038`과 해시로 보존한다. manifest·모델·벡터·후보군·고정 소스의 바이트를 임의로 변경하거나 재동결하지 않는다. 소스나 자산 해시 오류는 원인을 먼저 확인한다. V2/V3의 실험 결과를 보고 서비스 모델을 자동 교체하지 않는다.

## 팀 협업

1. `development-v2`에서 최신 소스를 받고 작업별 브랜치를 만든다. main은 직접 수정하지 않는다.
2. 변경은 작은 단위로 검토하고 관련 테스트를 실행한다. 의존성 설치는 pip lock / npm ci를 사용한다.
3. `.local`, `.venv`, node_modules, dist, 원본·가공 평점, 사용자 매핑, 비밀정보, 새 모델/실험 출력은 추가하지 않는다. 기존 최소 자산을 재생성·교체하지 않는다.
4. API 요청/응답, React 디자인, frozen 알고리즘을 바꾸는 작업은 팀과 먼저 범위를 합의한다. 커밋 전 diff를 확인한다.

ML 설계·교수 요구·결과 근거는 [문서 안내](docs/README.md), [AGENTS.md](AGENTS.md), [방법 설명](METHODS_EXPLAINED.md), [요구사항 추적](REQUIREMENTS_TRACEABILITY.md)을 확인한다. 원본 데이터 없는 Clone은 서비스 추론과 합성 테스트를 재현하며, 비공개 데이터가 필요한 연구 재학습까지 재현한다는 의미는 아니다.
