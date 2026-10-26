# SCENT MATCH — Team 12 shared source execution guide (STEP18)

이 문서는 STEP18에서 공유하는 소스의 실행 상태를 설명한다. 단계별 README의 ‘아직 로컬/미반영’ 문장은 해당 단계 작성 당시 기록이다. 기존 단계 문서와 연구 파일은 보존했다. GitHub에 포함된 소스와 실행에 필요한 별도 자산을 구분한다.

## 두 경로

|경로|Clone 후 가능한 작업|추가 조건|
|---|---|---|
|`demo/`|완전 합성80개 기반 콘텐츠 추천·React·테스트 실행|Python3.12, Node20.20 또는 지원 버전, 의존성 설치. 실제 Frozen V1/MF/Hybrid가 아님|
|`deployment/final_v1/`|소스 설치·기존 React 동일 복사본 빌드·정적 검사|실제 Frozen V1 추론에는 별도 권리 증빙과 승인된5개 자산 필요. 현재 HOLD|

**실제 런타임5개, 원자료, 개인별 평점·mapping·P/Q 모델 파일은 이 업로드에 포함하지 않는다.** 자산/권한이 없을 때 최종 V1 실행기가 합성 Demo로 바뀌지 않는다. 예시 권한 JSON은 허가서가 아니다.

## Clone

저장소 접근 권한이 있는 팀원이 새 폴더에서:

```sh
git -c core.autocrlf=false clone --single-branch --branch development-v2 https://github.com/hochaaa/MachineLearning-Team12.git
cd MachineLearning-Team12
```

기존 작업 폴더를 덮어쓰거나 원자료를 지우지 않는다. 이 안내는 소스가 반영된 브랜치에 대한 것이며 실제 런타임 재배포 권한을 부여하지 않는다.

## 합성 Demo — macOS

```sh
python3.12 -m venv demo/.venv
demo/.venv/bin/python -m pip install -r demo/requirements-lock.txt
npm --prefix demo/frontend ci --ignore-scripts --no-audit --no-fund
PYTHONDONTWRITEBYTECODE=1 demo/.venv/bin/python -B -m uvicorn demo.backend.app:create_app --factory --host 127.0.0.1 --port 8002 --no-access-log
```

별도 터미널, 같은 프로젝트 루트:

```sh
npm --prefix demo/frontend run dev
```

브라우저 `http://127.0.0.1:5175/`. DEMO MODE — Synthetic Data 표시를 확인하고 가상 향수3개와0~10평점을 입력한다. 동일 입력은 결정적이며 낮은 평점은 비선호로 반영한다. Woody/Floral/Rose AND 필터를 제공한다.

## 합성 Demo — Windows PowerShell (NOT TESTED)

```powershell
py -3.12 -m venv demo/.venv
.\demo\.venv\Scripts\python.exe -m pip install -r demo/requirements-lock.txt
npm.cmd --prefix demo/frontend ci --ignore-scripts --no-audit --no-fund
$env:PYTHONDONTWRITEBYTECODE = "1"
.\demo\.venv\Scripts\python.exe -B -m uvicorn demo.backend.app:create_app --factory --host 127.0.0.1 --port 8002 --no-access-log
```

별도 터미널에서 `npm.cmd --prefix demo/frontend run dev`. 실행 정책 우회나 관리자 권한은 요구하지 않는다. 실제 Windows 검증은 남아 있다. 다른 포트를 쓰면 Demo README의 API/CORS 설정도 함께 맞춘다.

## 실제 V1 소스 설치 — 추론과 구분

```sh
sh deployment/final_v1/run-macos.sh install
sh deployment/final_v1/run-macos.sh check
```

Windows는 `py -3.12 -B deployment/final_v1/manage.py install` 및 `check`. 현재 자산 또는 권한이 없으면 check 전체 BLOCKED/exit2가 정상이다. 이를 고치려고 자산을 임의 다운로드하거나 허가 예시를 VERIFIED로 바꾸지 않는다. 실제 V1 시연·파일전달·GitHub 저장은 별도 권리 확인 후 결정한다. 새 start는 권한을 확인하기 전 모델을 import하지 않는다.

## 검증·한계

STEP18에서 원자료를 쓰지 않는 최종 setup27개와 Demo29개 테스트를 실행했다. 합성 Demo는 이전 macOS Clean Clone 검증 근거도 있다. Windows는 미검증이며 합성 추천을 실제 향수 선호 정확도로 설명하지 않는다. 기존 STEP12의144응답 동일성은 과거 실측이고 STEP18 재실행 결과가 아니다.

자세한 명령·수식·제약은 `demo/README.md`, `deployment/final_v1/README.md`와 각 METHODS_EXPLAINED.md를 따른다. 자신의 서버만 Ctrl+C로 종료한다. `.venv`, node_modules, dist, 로그, 실제 자산, 비밀정보를 Git에 추가하지 않는다. 프로젝트 코드/합성 자료의 정식 공개 라이선스 선택은 팀 확인 사항이며, 이 소스 업로드가 제3자 데이터 권한을 해결하지 않는다.
