# STEP3-3 모듈·메서드 설명

2026-10-23. 신규 코드 자체 작성; 기존 ML 파일/루트 설명서는 보존. 테스트는 합성 추론만 실행.

## 라이브러리와 정책

FastAPI/Starlette: 원래 검증 endpoint를 별도 운영 앱에서 호출. CORSMiddleware는 exact origin 허용, JSONResponse는 고정 오류 응답. dataclass(frozen=True)는 immutable 설정. deque는 IP 없이 timestamp만 저장하는 rolling budget. time.monotonic은 시스템 시각 변경 영향 없는 경과 시간. urllib.parse는 URL 구조 검사, urllib.request는 고정 루프백 HTTP만 사용. unittest/patch는 실패·설정·경계 합성 검증. tempfile는 새 임시 폴더의 패턴 스캔 검증. sys.addaudithook는 Python open 관찰만 수행하며 보안 샌드박스가 아니다. pathlib/hashlib/json은 파일경로·무결성·집계 입출력. subprocess는 읽기 전용 Git 명령만 실행. argparse는 dist/output 로컬 경로를 받는다. ast는 이 문서의 signature 추출용. IngressGuard는 ASGI scope/receive/send 인터페이스를 구현한다. 비동기 구간에서 lock 없이 단일 event-loop의 동기 counter 조작을 수행하며 multi-worker 분산 제한이 아니다.

Settings: origins는 정확한 origin tuple, max_body_bytes=65536, requests_per_minute=120, max_inflight=8. 테스트에서만 높은 요청 예산을 주입해 1551개 golden HTTP 비교가 제한에 걸리지 않게 한다. HTTPX TestClient 테스트는 실제 인터넷 요청이 아니다. 실행 시작은 start_backend.sh; PORT 필수, PYTHON_BIN 선택, WEB_CORS_ORIGINS 필수, worker1, proxy headers 비신뢰, Uvicorn concurrency16(초과503)/application8(초과429), keepalive5초. 이 수치는 운영 보호 기본값이며 ML 선택/튜닝과 무관하다. slow body·분산 DoS는 upstream 제한이 추가로 필요하다.

## 신규 함수·메서드와 파라미터

| 파일 / 함수 | 파라미터 | 역할 |
|---|---|---|
| `web/backend/production.py::create_app` | `settings=None` | settings: Settings or explicit env validation; factory target for Uvicorn. |
| `web/backend/production.py::from_environment` | `cls` | Require explicit origins. HTTP loopback only under explicit local simulation. |
| `web/backend/production.py::__init__` | `self, app, settings, clock=time.monotonic` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/production.py::__call__` | `self, scope, receive, send` | scope/receive/send: standard ASGI request interfaces, never logged. |
| `web/backend/production.py::lifespan` | `app` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/production.py::readiness` | `request: Request` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/production.py::recommend` | `body: local.Recommendation, request: Request` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/production.py::safe_headers` | `request, call_next` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/production.py::bounded_receive` | `` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::setUpClass` | `cls` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::tearDownClass` | `cls` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::test_four_condition_parity` | `self` | 검증: four condition parity |
| `web/backend/test_deployment.py::test_all_name_and_note_goldens` | `self` | 검증: all name and note goldens |
| `web/backend/test_deployment.py::test_new_brand_examples_unchanged` | `self` | 검증: new brand examples unchanged |
| `web/backend/test_deployment.py::test_cors_exact_allowed_and_denied` | `self` | 검증: cors exact allowed and denied |
| `web/backend/test_deployment.py::test_invalid_inputs_safe` | `self` | 검증: invalid inputs safe |
| `web/backend/test_deployment.py::test_files_and_docs_not_served` | `self` | 검증: files and docs not served |
| `web/backend/test_deployment.py::test_safety_headers` | `self` | 검증: safety headers |
| `web/backend/test_deployment.py::test_oversize_body` | `self` | 검증: oversize body |
| `web/backend/test_deployment.py::test_inference_error_has_no_sensitive_logs` | `self` | 검증: inference error has no sensitive logs |
| `web/backend/test_deployment.py::test_unhealthy_readiness_503` | `self` | 검증: unhealthy readiness 503 |
| `web/backend/test_deployment.py::test_restart_loads_same_results` | `self` | 검증: restart loads same results |
| `web/backend/test_deployment.py::test_production_env_rejects_missing_and_invalid_origins` | `self` | 검증: production env rejects missing and invalid origins |
| `web/backend/test_deployment.py::test_exact_https_and_explicit_local_simulation` | `self` | 검증: exact https and explicit local simulation |
| `web/backend/test_deployment.py::test_default_budget_and_streamed_body` | `self` | 검증: default budget and streamed body |
| `web/backend/test_deployment.py::test_inflight_limit_and_window_expiry` | `self` | 검증: inflight limit and window expiry |
| `web/backend/test_deployment.py::test_failed_startup_does_not_log_paths` | `self` | 검증: failed startup does not log paths |
| `web/backend/test_deployment.py::test_public_path_policy` | `self` | 검증: public path policy |
| `web/backend/test_deployment.py::test_static_scan_catches_forbidden_content` | `self` | 검증: static scan catches forbidden content |
| `web/backend/test_deployment.py::run` | `` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::run` | `` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::inner` | `scope, receive, send` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::request` | `chunks=None, headers=None` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::inner` | `scope, receive, send` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::request` | `` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::receive` | `` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::send` | `m` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::receive` | `` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/backend/test_deployment.py::send` | `m` | ASGI/테스트 내부 helper; 인자와 반환은 인접 호출 및 주석 참조 |
| `web/deployment/check_regressions.py::main` | `` | No fits, no evaluation datasets; compare old golden responses and synthetic inference. |
| `web/deployment/check_integrity.py::digest` | `path` | path: local Path; return SHA256 without altering model or manifest. |
| `web/deployment/check_integrity.py::main` | `` | Write only this stage's integrity evidence; fail on unauthorized old-file changes. |
| `web/deployment/trace_runtime.py::observe` | `event, args` | event/args: CPython audit hook data. Keep unique relative read paths only. |
| `web/deployment/trace_runtime.py::main` | `` | Observe unmodified loader and synthetic-only search/inference, write new evidence. |
| `web/deployment/check_live.py::request` | `path, body=None, headers=None, method=None, raw=None` | path: API path; body: JSON object; raw: malformed test bytes; no external URL. |
| `web/deployment/check_live.py::main` | `` | Check fresh local production server, write aggregate observations without ratings. |
| `web/deployment/preflight.py::private_path` | `name` | name: repository-relative path; conservative deny policy for public source. |
| `web/deployment/preflight.py::scan_frontend` | `directory` | directory: built static root. Return only flagged paths, bytes/count and digest. |
| `web/deployment/preflight.py::git_inspection` | `` | Inspect tracked and all-ref historical file paths. Never print blob contents. |
| `web/deployment/preflight.py::main` | `` | --dist: alternate local build; --output: audit JSON destination. No network. |
