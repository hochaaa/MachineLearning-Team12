# SCENT MATCH — Team 12 로컬 실행 가이드

최종 서비스는 **Frozen V1 Hybrid**다. V2/V3는 비교 실험이며 웹에 연결하지 않는다. 향수를 검색해 선택하고0–10점으로 평가하면 Top5를 추천한다. 실제 API는1–50개 입력을 허용하며 화면은3개 이상을 권장한다.

> **현재 공유 상태:** GitHub source는 Clone할 수 있지만 비공개 런타임8개 파일은 포함되지 않는다. 사용자가 확인한 권한은 로컬 사용뿐이며 **팀원에게 별도 전달하는 권한은 보류**다. 아래 자산 배치·실행은 담당자가 공유 권한을 확인한 뒤 진행한다. 현재 Clone만으로 웹 추천이 실행된다고 설명하지 않는다. 이 가이드·V2/V3 source의 향후 반영도 아직 commit/push하지 않았다.

## 1. 준비와 검증 범위

- Git, Python3.12(64bit 권장), Node20.20.0와 npm을 준비한다. Vite가 요구하는 Node 범위는 `^20.19.0 || >=22.12.0`이다.
- macOS Apple Silicon: 기존 개발용 venv와 분리한 **Python3.12.0 새 venv**, lockfile 설치/pip check, npm ci/build, 실제 GitHub Clone+로컬 임시 자산의 검색/추천/프록시를 검증했다. 기존 개발 환경3.12.14를 그대로 복사하지 않았다.
- Windows x64: **가이드 작성 완료, 실행 검증 미실시**. Intel Mac, Windows ARM, 다른 Python/Node 버전도 미검증이다.
- 새 환경 설치에는 네트워크가 필요하다. 설치 후 inference는 외부 향수 API·이미지·온라인폰트에 의존하지 않는다. 실제 오프라인 차단 시험은 하지 않았다.
- API key는 필요 없다. 원본 CSV/JSON·개인평점·모델을 공개 저장소나 공개 링크로 공유하지 않는다.

## 2. Clone: macOS와 Windows 공통

확인한 URL은 `https://github.com/hochaaa/MachineLearning-Team12.git`, 브랜치는 `development-v2`다. STEP10 실제 원격 Clone의 HEAD는 `aebd9abd85b175e6076d8b2d9c2445201d8b2602`, tracked107개였다. 현재 원격에는 V2/V3 미추적 source와 이 신규 가이드가 아직 없다. 반영 후 다시 확인해야 한다.

```sh
git -c core.autocrlf=false clone --single-branch --branch development-v2 https://github.com/hochaaa/MachineLearning-Team12.git
cd MachineLearning-Team12
git branch --show-current
```

Windows의 자동 CRLF 변환을 막기 위해 Clone 때 `core.autocrlf=false`를 명시했다. 동결 로더는 소스와 자산의 바이트 해시를 확인한다. 기존 Clone에서 변경된 해시를 맞추려고 파일을 편집하거나 manifest를 고치지 않는다. 권한이 필요한 저장소라면 팀원이 본인의 GitHub 계정으로 접근 승인을 받아야 한다. 토큰/비밀번호를 URL이나 채팅·설정 예제에 넣지 않는다.

## 3. 모델·메타데이터 준비 — 전달 승인 전 보류

`RUNTIME_MANIFEST.json`은 파일 정보만 있는 목록이며 모델 묶음이 아니다. 실제 원본을 이 문서에 넣거나 압축하지 않았다. 로컬 검증에 사용한 임시 복사본도 외부로 전달하지 않았다.

승인 후 담당자가 정확한 원본 바이트로 아래 경로를 준비해야 한다. 프로젝트 루트 아래 경로를 그대로 유지하고 JSON을 다시 저장하거나 CSV 인코딩을 바꾸지 않는다.

```text
MachineLearning-Team12/
├── Term-project-datasets/fra_cleaned.csv
└── outputs/
    ├── validation/train_exclude_3.json
    ├── improvement/candidates.json
    ├── improvement/selection.json
    └── final/
        ├── freeze.json
        ├── model.npz
        ├── model.json
        └── content.json
```

특히 `train_exclude_3.json`은 가명화된 개인 평점, `model.json`은 사용자 mapping을 포함한다. 웹에서 새 학습에 쓰지는 않지만 기존 freeze 로더의 해시 계약 때문에 필요하다. 이 문제를 해결하려고 보호 코드를 변경하지 않는다. Fragrantica CSV도 재배포 권한을 별도로 확인해야 한다.

추가로 Git source의 `configs/improvement.json`, `src/perfume/*.py`, `scripts/freeze.py`, `scripts/final_evaluate.py` 등 protected code가 정확한 버전이어야 한다. Atrafshan/Laure/Parfumo 원본 전체, 옛 Validation/Test 정답, V2/V3 모델·실험 출력은 웹 실행에 필요 없다. 크기·SHA256·Git 상태·용도·배치 경로는 manifest34항목에 있다.

가이드·검사기가 승인 후 저장소에 반영되면 아래 읽기 전용 검사를 사용한다.

```sh
# macOS
python3.12 -B tools/team_setup/check_runtime.py
```

```powershell
# Windows PowerShell
py -3.12 -B tools/team_setup/check_runtime.py
```

PASS가 아니면 missing/hash mismatch 경로를 담당자에게 알린다. 해시를 재생성해 오류를 숨기거나 모델을 재학습하지 않는다.

## 4. Backend: macOS

프로젝트 루트에서 수행한다. 기존 개발자의 `.venv`, `runtime.local.json`, 홈 디렉터리 경로를 복사하지 않는다.

```sh
python3.12 --version
python3.12 -m venv .venv
.venv/bin/python -m pip install -r web/backend/requirements-lock.txt
.venv/bin/python -m pip check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m uvicorn web.backend.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

활성화는 선택 사항이다(`source .venv/bin/activate`). 위 명령은 직접 venv Python을 호출하므로 활성화하지 않아도 된다. 새 venv는 `include-system-site-packages=false`여야 한다.

다른 터미널에서 `http://127.0.0.1:8000/api/health`를 확인한다. `recommendation_ready:true`, `candidate_count:479`여야 한다. 서버가 떠 있다는 사실만으로 모델이 준비된 것은 아니다.

## 5. Backend: Windows PowerShell — 실행 검증 미실시

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r web/backend/requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -B -m uvicorn web.backend.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

활성화가 필요하면 `.\.venv\Scripts\Activate.ps1`을 사용할 수 있다. 실행정책에 막히면 정책을 약화하지 말고 위 Python 전체 상대경로를 그대로 사용한다. `py`가 없으면 Python3.12 설치 상태와 PATH를 확인한다. 관리자 권한 실행은 기본 요건이 아니다.

## 6. Frontend: 두 OS 공통

백엔드와 별도 터미널에서 프로젝트 루트 기준으로 실행한다.

```sh
node --version
npm --version
npm --prefix web/frontend ci --ignore-scripts --no-audit --no-fund
npm --prefix web/frontend run dev
```

PowerShell에서 npm.ps1 실행이 차단되면 다음을 사용한다.

```powershell
npm.cmd --prefix web/frontend ci --ignore-scripts --no-audit --no-fund
npm.cmd --prefix web/frontend run dev
```

`ci`는 기존 package-lock을 사용한다. STEP10에서 같은 설치 옵션과 `npm run build`가 임시 Clone에서 통과했다. 원본 프로젝트의 node_modules/dist는 건드리지 않았다. `npm install`로 임의 버전을 갱신하지 않는다.

로컬 주소는 **http://127.0.0.1:5173/**다. 기존 `vite.config.ts`가 /api를8000으로 proxy한다. `web/frontend/.env.example`에는 production placeholder가 있으므로 로컬 실행을 위해 그대로 `.env.local`로 복사하지 않는다. **로컬 기본값은 VITE_API_BASE_URL 미설정**이다. 이미 `.env.local`이 있으면 올바른 로컬 설정인지 사용자 본인이 확인하고, 외부 API 도메인이나 비밀값을 넣지 않는다.

Backend `WEB_CORS_ORIGINS` 기본값은 localhost/127.0.0.1:5173이다. 기본 로컬 실행에는 별도 환경변수가 필요 없다. `web/deployment/.env.example`은 별도 배포 앱용이고 이 로컬 가이드에 복사하지 않는다. VITE_ 변수는 브라우저에 공개되므로 키를 넣지 않는다.

## 7. 동작 확인과 종료

1. 웹 페이지와 health의 모델 준비 상태를 확인한다.
2. `Dior Sauvage Elixir`, `Bleu de Chanel Parfum`, `Tom Ford Black Orchid`를 각각 검색해 선택한다.
3. 임의의9/8/2점 또는0/.5/10점 등으로 입력하고 추천 버튼을 누른다.
4. Top5, 입력 향수 제외, 이름/노트/점수/공통 특성 표시를 확인한다. 점수는 확률이 아니다.
5. Woody/Floral/Rose를 바꾸고 다시 추천한다. 조건에 맞는 향수가 부족하면0–5개일 수 있다.
6. Frontend/Backend 각각 자신이 시작한 터미널에서 Ctrl+C로 종료한다. 다른 팀원·기존 개발 서버를 임의 종료하지 않는다.

API 입력은유한 숫자0–10, 중복금지,479후보 내, top_k=정수5 고정이다. UI 슬라이더는0.5간격이다. 1~2개 추천도 허용되나 품질 제한이 있다. 평점은 요청 메모리에서만 쓰며 현재 서비스에 DB/계정 저장 기능은 없다.

## 8. 오류 해결

| 증상 | 확인·조치 |
|---|---|
|python/py 없음|Python3.12 설치·PATH·OS/아키텍처 확인. 다른 Python의 site-packages를 복사하지 않음|
|venv 활성화 실패|활성화 생략하고 `.venv/bin/python` 또는 `.venv\Scripts\python.exe` 직접 사용|
|pip 설치 실패|명령이새venv인지·네트워크·정확한lockfile확인. 라이브러리버전을임의변경하지말고로그제공|
|npm/node 없음|Node20.19이상 지원버전·npm PATH확인; PowerShell은npm.cmd사용가능|
|모델/데이터누락|manifest검사결과와8개파일배치확인. 현재전달권한보류상태면담당자승인대기|
|hash mismatch|잘못된버전·CRLF·CSV/JSON편집여부확인. freeze재작성·재학습금지|
|포트충돌|기존프로세스소유자확인. 임의kill금지. 기본5173 strictPort는다른포트로자동우회하지않음|
|CORS/API실패|두서버실행·health·VITE_API_BASE_URL미설정·5173→8000proxy확인. CORS를*로풀지않음|
|빈검색결과|479후보제한·철자·name/notes모드확인. 톰포/vanill등지원범위만검색됨|
|추천생성실패|후보ID·중복·평점범위·health·오류로그확인. 사용자평점/키를공개로그에올리지않음|

예전 검색 unittest는 기존 `web/evidence/`를 다시 저장하는 코드가 있으므로 원본에서 그대로 실행하지 않는다. 새 checker 합성 테스트만 실행하려면 다음을 사용한다.

```sh
# macOS (Windows는 Python 경로만 .venv\Scripts\python.exe로 바꿈)
.venv/bin/python -B -m unittest discover -s tools/team_setup -p test_manifest.py -v
```

학습/튜닝/최종평가 진입점(`improve`, `freeze`, `final_evaluate`, V2/V3 run_experiments)을 설치 확인용으로 실행하지 않는다.

## 9. 이번 검증의 정확한 의미

실제 GitHub Clone(107 source)→독립pip/npm설치→자산누락503 확인→**동일기기 임시 자산만**배치→검색·Top5·4필터→새 frontend/backend의HTTPproxy를 확인했다. 테스트 포트는 충돌방지를 위해15173/18100, 임시proxy config만 사용했고 기존8000/5173은 변경하지 않았다. 새 Clone의 npm build도 통과했다. 이번 단계에서는 새 Clone을 실제 Chrome에서 별도 UI 시연하지 않았으며 HTTP/빌드와 API 통합을 확인했다. Windows는 미검증이다.

원격반영 예정 V2/V3 source를 더한 임시배포본 검증은 별도 감사에 구분해 기록한다. 현재 원격 GitHub에 새 파일이 이미 올라갔다는 의미가 아니다. 팀원 런타임 전달 승인도 아니다.
