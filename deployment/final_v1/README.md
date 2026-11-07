# SCENT MATCH — Frozen V1 local runtime

기존 Frozen V1을 그대로 로드하는 FastAPI + React 실행 경로다. Content + MF/Ridge fold-in, Hybrid 0.25/0.75, 후보479개, 기존 필터와 UI를 유지한다. 합성 Demo로 대체하지 않는다.

**authorization JSON·검토 상태·`--authorization` 옵션은 실행 조건에서 제거했다. 이 변경이 데이터/모델의 사용·재배포 권한 확보를 뜻하지 않으며 허가 기록을 생성하지 않는다.** 이전 권한 조사는 별도 역사 자료로 남는다.

## 새 컴퓨터에서 Clone → Install → Start

Python3.12, Node20.20 또는 지원 Node22.12+, npm, Git이 필요하다. macOS ARM64를 실제 검증 대상으로 삼았으며 Windows는 **NOT TESTED**다.

```sh
git -c core.autocrlf=false clone --single-branch --branch final-submission-20261107 https://github.com/hochaaa/MachineLearning-Team12.git
cd MachineLearning-Team12
sh deployment/final_v1/run-macos.sh install
sh deployment/final_v1/run-macos.sh check
sh deployment/final_v1/run-macos.sh start
```

start 한 번으로 다음 두 프로세스를 함께 시작한다.

- FastAPI: http://127.0.0.1:8004
- React: http://127.0.0.1:5177

첫 실행 전 install이 필요하다. install은 새 `.local/venv` 생성, pip lock 설치·check, 기존 React9파일의 동일 복사본 생성, npm ci, TypeScript/Vite build를 수행한다. 다른 PC의 .local/.venv/node_modules를 복사하지 않는다. start는 무결성/의존성/포트 검사 → API ready479 → React 순서로 시작한다. 종료는 start 터미널에서 Ctrl+C, 재시작은 같은 start 명령이다. 타 서버를 종료하지 않는다.

현재 브랜치에는 사용자가 추가한 커밋 `8dca493`의 최소 런타임5개가 기본경로에 있다. 설치기가 새로 원자료를 수집하거나 별도 자산을 다운로드하지 않는다. 파일이 누락·변조되면 명확한 기술 오류로 종료하며 다른 모델로 대체하지 않는다. 원본 CSV·학습 사용자 평점·user mapping·P는 팀원 런타임에 필요 없다. 실제 자산의 이용권리 판단은 소스 실행 여부와 별개다.

## Windows PowerShell — 실제 OS 미검증

```powershell
git -c core.autocrlf=false clone --single-branch --branch final-submission-20261107 https://github.com/hochaaa/MachineLearning-Team12.git
cd MachineLearning-Team12
& .\deployment\final_v1\run-windows.ps1 install
& .\deployment\final_v1\run-windows.ps1 check
& .\deployment\final_v1\run-windows.ps1 start
```

PowerShell 정책상 스크립트 실행이 제한되면 정책을 우회하지 않고 동일 Python 진입점을 직접 사용한다.

```powershell
py -3.12 -B deployment/final_v1/manage.py install
py -3.12 -B deployment/final_v1/manage.py check
py -3.12 -B deployment/final_v1/manage.py start
```

활성화·관리자 권한은 필요 없다. Windows npm은 공식 Node 배치의 node.exe와 npm-cli.js를 직접 호출한다. 비표준 npm 설치 배치는 안내 오류로 중단할 수 있다. UTF-8과 LF 소스를 유지하고 경로는 프로젝트 위치에서 자동 계산한다. 개인 홈 절대경로를 소스에 넣지 않는다.

## 고정 의존성과 무결성

- Python: `web/backend/requirements-lock.txt`의 모든 `==` 버전으로 설치한다.
- npm: 기존 `web/frontend/package-lock.json`의 전이 의존성까지 `npm ci`로 설치한다. package.json의 범위 표기를 다시 해석하는 `npm install`로 버전을 갱신하지 않는다.
- 원 React source 9개를 hash 비교한 동일 복사본에서만 실행한다. 원 UI·원 node_modules/dist를 설치기로 변경하지 않는다.
- 최소 manifest SHA256: `ff9a748e28cfc723aa972af705c07663827e82b1881291cecd2e5f1985ed3caa`.
- 원 freeze SHA256: `3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130`.
- 네 payload의 크기/hash와 재사용 원source11개를 검사한다. 기존 로더는 Q dtype/shape/finite와479개 정렬도 추가 확인한다.

`--assets` 또는 `SCENT_MATCH_STANDALONE_ASSETS`로 자산 위치를 지정할 수 있다. 상대경로는 프로젝트 root 기준이다. .env나 권한 JSON을 읽지 않는다. 옛 SCENT_MATCH_FINAL_AUTHORIZATION/PURPOSE 값도 실행 정책에 영향을 주지 않는다. `check`의 PASS는 **기술 검사 통과**이며 권리 허용 선언이 아니다.

## 기능 확인과 테스트

브라우저에서 Tom Ford를 검색하고 Bitter Peach/Black Orchid/Ébène Fumé를 선택해9/7/2를 입력하는 방식으로 시연할 수 있다. 실제 선택은 현재 검색 결과의 ID를 사용한다. 입력상품은 추천에서 제외되고 조건은 none/woody/floral/rose/citrus/amber/vanilla다. UI/API는1개 이상,3개 권장이고 API는최대50개다. score는 확률이 아니다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m unittest discover -s deployment/final_v1/tests -v
# 실행 중인 실제 서버에 합성 취향 요청; 학습/평가 데이터 사용 없음
# 프로젝트 루트에서:
deployment/final_v1/.local/venv/bin/python -B -m deployment.final_v1.tests.live_smoke
```

Windows의 Python 실행파일은 `deployment/final_v1/.local/venv/Scripts/python.exe`다. live_smoke의 --reference는 별도 로컬의 과거 추론 결과를 비교하는 선택 인자다. 이 reference는 서버의 런타임 의존성이 아니며 개인 평점/정답/모델을 가져오는 파일도 아니다. local output/reference는 Git에 올리지 않는다.

## 보존·한계

기존 모델·벡터·알고리즘·alpha·candidate·standalone_v1·React 소스를 변경하지 않았다. 새로운 MF fit/튜닝/Validation·Test 평가를 실행하지 않는다. 소프트웨어 실행 차단 제거와 법적 허가·제3자 공유는 별개이며 어떠한 VERIFIED 권한 기록도 만들지 않는다. 권한 조사는 별도 보고서를 참조한다.

설치에는 패키지 registry 네트워크가 필요하다. 실행은 loopback 전용이며 외부호스팅 구성은 아니다. 포트8004/5177 충돌 시 종료하므로 타 프로세스 소유자를 확인한다. Windows 실제 실행, 발표장 장비·오프라인·다중 브라우저 검증은 별도다. 함수 설명은 같은 디렉터리의 문서를 따른다.
