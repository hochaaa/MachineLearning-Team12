# 독립 V1 런타임 — STEP12

기존 Frozen V1·웹 로더·알고리즘을 수정하지 않는 **별도 실행 경로**다. `StandaloneService`는 기존 `FrozenService`의 초기화만 바꾸고 recommend/record/search/search_response를 그대로 상속한다. 기존 서비스는 계속 `web.backend.app:app`을 사용한다. 새 로더가 원래 서버에 자동 연결되지 않는다.

Train 평점·학습 user mapping·사용자 벡터P 없이 새 사용자 추천을 실행한다. 단, item factorQ·동결콘텐츠·메타데이터·인기도집계는 파생자산이며 **공유권한 UNVERIFIED/HOLD**다. 개인별 필드 제거를 익명성/재배포 허가로 해석하지 않는다. GitHub Clone만으로는 이 코드와 자산이 모두 제공되는 상태가 아니다. 이번단계 Git반영·외부전송·공유용압축을하지않았다.

## 로컬 자산

원본이 있는 개발 환경에서만 다음으로 **새** 로컬 outputs 디렉터리를 만든다. 학습·평가를 실행하지 않으며 기존 파일/출력을 덮어쓰지 않는다. 이미 생성됐으면 재실행하지 않는다.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m deployment.standalone_v1.export_local --output outputs/step12_runtime/assets
```

생성물은 runtime.json, item_factors.npy, content.json, catalog.json, manifest.json의5개다. CSV원본·평점·user mapping·P는복사하지않는다. npy는비압축float64 Q행복사다. 새로운모델학습이나숫자재추정이아니다. 출력영역전체는기존.gitignore로제외된다.

## 실행 전 검사

```sh
.venv/bin/python -B -m deployment.standalone_v1.preflight --assets outputs/step12_runtime/assets --expected-manifest-sha256 ff9a748e28cfc723aa972af705c07663827e82b1881291cecd2e5f1985ed3caa
```

위 SHA는이번로컬export의값이다. 나중에source버전이다른자산을임의로정당화하는값으로재작성하지않는다. manifest 내부data/codehash를검사하고별도pin이있으면manifest자체도비교한다. pin없이도일관성검사는되지만전자서명이나공격자대체방지증명은아니다. 신뢰하는경로로확인한pin을사용한다. manifest/자산불일치는우회하지않는다.

## 별도 로컬 서버(현재 서비스 교체 아님)

기존개발환경venv를복사하지말고새Python3.12 venv에 `web/backend/requirements-lock.txt`를설치한다. macOS ARM64의새Python3.12.0 venv에서검증했다. Windows x64는가이드만이며미검증이다. 아래는프로젝트루트에서기존8000/5173과겹치지않는예다. 스스로시작한서버만Ctrl+C로종료한다.

```sh
# macOS, 승인된 로컬자산이 있는 경우에만
SCENT_MATCH_STANDALONE_ASSETS="$PWD/outputs/step12_runtime/assets" \
SCENT_MATCH_STANDALONE_MANIFEST_SHA256=ff9a748e28cfc723aa972af705c07663827e82b1881291cecd2e5f1985ed3caa \
WEB_CORS_ORIGINS=http://127.0.0.1:5174 \
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m uvicorn deployment.standalone_v1.app:create_app --factory --host 127.0.0.1 --port 8001 --no-access-log
```

```powershell
# Windows: 실행 검증 미실시, 활성화 대신 venv 실행파일 직접 사용
$env:SCENT_MATCH_STANDALONE_ASSETS = "$PWD/outputs/step12_runtime/assets"
$env:SCENT_MATCH_STANDALONE_MANIFEST_SHA256 = "ff9a748e28cfc723aa972af705c07663827e82b1881291cecd2e5f1985ed3caa"
$env:WEB_CORS_ORIGINS = "http://127.0.0.1:5174"
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -B -m uvicorn deployment.standalone_v1.app:create_app --factory --host 127.0.0.1 --port 8001 --no-access-log
```

독립프론트가필요하면기존source를수정하지않고**별도터미널**의프로세스환경에만 API주소를지정할수있다. 이5174/8001 프론트조합은이번에브라우저시연하지않은안내이며, 실제Clean Clone검증은독립ASGI18112와TestClient다.

```sh
VITE_API_BASE_URL=http://127.0.0.1:8001 npm --prefix web/frontend run dev -- --port 5174
```

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8001"
npm.cmd --prefix web/frontend run dev -- --port 5174
```

기존Frontend/Backend의설정파일·.env·서버를변경하지않는다. 실제사용전health의recommendation_ready=true/candidate_count479확인후공개제품3개와합성평점을넣는다. 오류시기존frozen파일을수정하지않고신규preflight를확인한다.

## 검증 기록

이번 실제명령은새임시venv Python으로 다음을수행했다.

```sh
python -B -m deployment.standalone_v1.export_local
python -B -m deployment.standalone_v1.preflight
python -B -m unittest discover -s deployment/standalone_v1/tests -v
python -B -m deployment.standalone_v1.verify_equivalence
# 임시 GitHub Clone루트에서만:
python -B -m deployment.standalone_v1.clean_smoke --assets <clone>/outputs/step12_runtime/assets --output <temporary>/clean-smoke.json
```

14단위테스트, 합성36프로필×4조건=144추천응답, 검색17, 오류15, CORS2를대조했다. ID·순서일치, 점수최대차이0, 원본private경로읽기시도0. tolerance atol1e-12/rtol1e-10이다. 새app의계약·오류응답은원래함수를재사용했다. 이검사는추천정확도·기존Validation/Test평가가아니다.

단위테스트중user-ID복사여부검사는원본metadata의keys를로컬메모리에서만비교한다. 따라서14개전체suite는원본개발환경에서실행하고Clean Clone에서는원본8파일이없어야하는전용clean_smoke를사용한다. 기존 evidence를다시쓰는웹회귀테스트는실행하지않는다.

원본코드/결과/모델/평점은변경하지않았고Git명령은읽기전용확인및임시Clone뿐이다. 새로더source는미추적, assets/log는ignore유지다. 실제팀원전달과기존서비스전환에는별도승인이필요하다.
