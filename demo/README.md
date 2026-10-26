# SCENT MATCH — Synthetic Demo

**DEMO MODE — Synthetic Data.** 가상의 향수80개로 TF-IDF·중심화 평점 프로필·cosine 추천을 실제 계산한다. Frozen V1 Hybrid/MF를 실행하지 않으며 기존 성능을 재현하지 않는다. 실제 사용자 평점·개인정보·원본 향수자료·기존 모델·최소 런타임5개를 요구하지 않는다.

현재 STEP16 파일은 **로컬 신규 파일**이다. 아직 commit/push하지 않았으므로 현재 GitHub Clone에는 이 Demo가 없다. 코드 검토 및 별도 Git 반영 승인 이후 팀원 Clone 실행이 가능하다. 저장소는 `https://github.com/hochaaa/MachineLearning-Team12.git`, 브랜치 `development-v2`; 현재 기준 HEAD는 `195fe635b273813c10b67c60671de5b650ea1cce`다.

## 구조

- `backend/generate_data.py`: 파일 입력 없이 seed1612로 80개 가상 레코드 생성.
- `backend/data/synthetic_perfumes.json`: 시연용 고정 합성 카탈로그(10계열×8).
- `backend/recommender.py`: 표준 Python으로 구현한 binary TF-IDF·signed cosine·규칙 필터.
- `backend/schemas.py`, `backend/app.py`: 입력 검증·독립 FastAPI.
- `frontend/`: 독립 React/TypeScript/Vite UI. 기존 source는 변경하지 않는다.
- `tests/`: 수식 oracle·오류·결정성·HTTP·Clean Clone 격리 검사.
- `evidence/`: 로컬 검증 로그/화면, 새 demo/.gitignore로 Git 제외.
- `METHODS_EXPLAINED.md`, `REFERENCES.md`, `DATA_PROVENANCE.md`: 수식·API·자료 출처·한계.

## 설치와 실행 — macOS

Python3.12, Node20.19 이상(실측20.20.0), npm, Git이 필요하다. 새 Clone/공유 승인된 소스의 **프로젝트 루트**에서 실행한다. 기존 root .venv를 덮어쓰지 않도록 Demo 전용 가상환경을 사용한다.

```sh
python3.12 -m venv demo/.venv
demo/.venv/bin/python -m pip install -r demo/requirements-lock.txt
demo/.venv/bin/python -m pip check
npm --prefix demo/frontend ci --ignore-scripts --no-audit --no-fund
```

터미널 A:

```sh
PYTHONDONTWRITEBYTECODE=1 demo/.venv/bin/python -B -m uvicorn demo.backend.app:create_app --factory --host 127.0.0.1 --port 8002 --no-access-log
```

터미널 B:

```sh
npm --prefix demo/frontend run dev
```

브라우저 `http://127.0.0.1:5175/`, API health `http://127.0.0.1:8002/api/health`. health는 mode=demo/data_origin=synthetic/recommendation_ready=true/candidate_count=80이다. model_loaded=false는 정상이며 MF 학습 모델이 없다는 의미다.

## Windows PowerShell — NOT TESTED

Windows 실제 실행은 하지 않았다. 새 프로젝트 루트에서 다음 명령을 사용하도록 설계했다. Python 실행파일을 직접 호출하므로 Activate.ps1·관리자 권한·실행 정책 우회가 필요하지 않다.

```powershell
py -3.12 -m venv demo/.venv
.\demo\.venv\Scripts\python.exe -m pip install -r demo/requirements-lock.txt
.\demo\.venv\Scripts\python.exe -m pip check
npm.cmd --prefix demo/frontend ci --ignore-scripts --no-audit --no-fund
```

터미널 A:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\demo\.venv\Scripts\python.exe -B -m uvicorn demo.backend.app:create_app --factory --host 127.0.0.1 --port 8002 --no-access-log
```

터미널 B:

```powershell
npm.cmd --prefix demo/frontend run dev
```

UTF-8 소스를 유지한다. 줄바꿈 자동 변경을 피하려면 새 Clone 시 `git -c core.autocrlf=false clone --single-branch --branch development-v2 https://github.com/hochaaa/MachineLearning-Team12.git`를 사용한다(단, Demo 반영 이후). 비ASCII 경로·의존성·브라우저는 실제 Windows PC에서 확인해야 한다.

## 조작 및 실제 계산 확인

1. 상단 Demo 배너·80개 ready 표시 확인.
2. ID/이름/브랜드로 검색하거나 note mode에서 `rose`, `woody`, `vanilla` 등 일반 영어 단어 검색.
3. 가상 향수3개 선택, 평점0~10(0.5간격) 입력, Discover 버튼 클릭.
4. Top-5 카드·점수·상세·공통 특성 확인. 입력 상품은 제외된다.
5. Woody/Floral/Rose를 체크하면 AND 조건이다. 후보가5개 미만이면 가능한 개수와 이유를 표시한다.
6. 같은3개 `DEMO-001`, `DEMO-014`, `DEMO-038`에 [9,7,2]와 [2,7,9]를 입력해 추천이 달라지는지 확인할 수 있다. 이 ID는 검사 사례이며 추천 코드에 특별 취급되지 않는다.

UI는 시연 흐름을 위해 정확히3개를 받지만 API는 기존 기본 형식과 호환되도록1~50개를 허용한다. 기존 UI의 단일 필터와 달리 Demo는 추가 AND 조합도 제공한다. 계절·가격·강도·지속력 필터는 구현하지 않았다.

## 수식과 중립 처리

N=80, typed token은 note/accord 구분, binary TF. `idf(t)=log((N+1)/(df(t)+1))+1`, 각 상품 벡터를 L2 정규화한다. 사용자 프로필 `p=Σ((rating−5)/5)·v_i`; 점수 `p·v_j/||p||`다(상품 norm=1). 입력 ID 제외 → 모든 필수 필터 적용 → 점수 내림차순/ID 오름차순 → 최대5개. float 오차를 [-1,1]로 clip한다.

5점은 가중치0, 낮은 평점은 음수다. 프로필 norm≤1e-12이면 모두0점과 명시적인 ‘선호 방향 없음’ 안내를 내며 ID 순서로 결정한다. 개인화 근거가 없는 이 경우를 성공적인 취향 추론으로 주장하지 않는다. shared_tokens는 메타데이터 교집합이지 각 토큰이 점수에 긍정적으로 기여했다는 보장은 아니다.

## 테스트

서버 없이:

```sh
PYTHONDONTWRITEBYTECODE=1 demo/.venv/bin/python -B -m unittest discover -s demo/tests -v
npm --prefix demo/frontend run build
```

서버 실행 후 HTTP 통합:

```sh
demo/.venv/bin/python -B -m demo.tests.http_smoke
```

Windows는 Python 명령을 `.\demo\.venv\Scripts\python.exe -B`로 치환하고 환경변수는 위 PowerShell 방식으로 설정한다. 새 source-only Clone에서만 `python -B -m demo.tests.clean_smoke`를 실행한다. 이 검사는 outputs/원자료 폴더가 있으면 거절한다. **통과하려고 기존 폴더를 삭제하지 말고 새 임시 Clone을 사용한다.**

실제 결과: macOS ARM64/Python3.12.0 새 venv의29테스트 PASS, Vite build PASS, 원본 자료 없는 GitHub Clone+Demo 로컬 복사에서29테스트/격리/HTTP/브라우저 PASS. Windows NOT TESTED. 자세한 현재 증거는 `reports/STEP16_DEMO_VALIDATION.md`다.

## 오류·종료·포트

422: 평점·중복·unknown ID·빈 입력·JSON·필터·Top5 형식,404: 상세 ID 없음,503: 합성 카탈로그 준비 실패,500: 계산 실패. UI 네트워크 오류는 한국어로 안내한다. 서버가 처음부터 꺼져 있었다면 서버 시작 후 페이지를 새로고침한다. 자신이 시작한 두 터미널만 Ctrl+C로 종료한다. 기존 서버를 kill하지 않는다.

다른 포트는 백엔드 `--port`, 프론트 `--port`와 `VITE_DEMO_API_URL`, 백엔드 `DEMO_CORS_ORIGINS`를 함께 맞춰야 한다. 기본5175는 --strictPort로 충돌 시 중단한다. CORS는 접근인증이 아니며 이 데모는 localhost 전용이다. 외부 호스팅을 이번에 하지 않았다.

## 한계·공유 상태

알고리즘 동작 시연이며 실제 향수 선호 정확도·학습된 MF/Hybrid·Frozen V1 결과를 뜻하지 않는다. 데이터는 코드 상수로 생성했고 실제 자료와의 대조/웹 수집은 하지 않았다. 실제 상품과 우연한 이름/조합 중복이 전혀 없다는 전세계 보증은 아니다. 일반 어휘 외 레코드·브랜드·설명은 이 데모용으로 구성했다. 코드·자료의 정식 공개 라이선스 선택은 팀 확인 사항이다. 검토된 새 파일만 명시적으로 선정해야 하며 Git add .를 사용하지 않는다. 원자산의 HOLD는 유지된다.
