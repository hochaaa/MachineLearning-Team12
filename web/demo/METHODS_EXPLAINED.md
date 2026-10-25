# STEP3-4 도구·파라미터 설명

2026-10-23. 신규 실행/점검 도구는 자체 작성했다. check_regressions.py는 기존 팀 runner에서 출력 폴더만 바꿔 재사용한다. ML·검색 원본 구현은 변경하지 않았다. 외부 코드 복사/새 패키지 설치는 없다.

## 모듈/설정

manager.py: pathlib/os로 root·기존 runtime 경로를 찾고 subprocess(argv, shell=False)로 같은 Mac 프로세스를 시작/관찰한다. fcntl.flock은 실행/종료 동시 조작을 차단한다. ps/lsof는 uid/start/command/cwd/listener를 읽는다. socket.create_connection은 PID가 보이지 않을 때127.0.0.1 포트가 실제 응답하는지 확인하며, 응답하는데 신원 불명이면 중단한다. signal.SIGTERM은 다시 신원을 확인한 소유 process에만 사용한다. time.monotonic은 준비 timeout, sleep은 최대30초 준비 확인/최대5초 정상 종료 확인 중 짧게 대기한다. logging RotatingFileHandler는64KiB×현재+backup3, umask077은 새 파일을 비공개 권한으로 생성한다. 사용자 입력/환경변수 전체/원본 파일 내용을 로그로 출력하지 않는다. urllib ProxyHandler({})와 NoRedirect는 loopback 검사에서 시스템 proxy와 redirect 외부 연결을 방지한다. hashlib/json은 original19+manifest 검증 및 synthetic-only 응답 비교에 사용한다. unicodedata NFC는 macOS 경로 한글 조합 차이를 맞춘다. 정적 감사/문서 생성의 ast/re/html은 소스 import/함수 signature·HTML safe output 용이다. unittest/mock/tempfile은 실행기 PID 재사용/잘못된 소유권을 실제 다른 앱 종료 없이 검증한다.

start_demo.command/stop_demo.command: dirname을 기준으로 root를 찾고 기존 .venv Python만 실행한다. 설치하지 않는다. Finder의 PATH가 짧으면 runtime.local.json의 현재 기기 hint·표준 설치 위치를 사용한다. Node shim은 실제 binary로 해석한다. npm --version은 준비 검사이며 실제 Vite는 기존 node_modules의 CLI로 직접 실행한다. 새 server는 detached session, stdout/stderr DEVNULL, PYTHONDONTWRITEBYTECODE=1. VITE_API_BASE_URL 빈값과 loopback proxy를 강제한다.

CLI manager.py action=start|stop, --backend-port(기본8000), --frontend-port(기본5173), --state-dir(기본web/demo/.state), --no-browser(자동 QA에서만 browser 생략). 비특권 서로 다른 포트만 허용한다. 별도8002/5174는 원래 서버 보존을 위한 QA였다. check_demo.py --output은 synthetic-only JSON 경로, 생략 시 결과 파일을 쓰지 않는다. check_integrity.py는 새 evidence만 쓰며 원래 모델·manifest를 쓰지 않는다. vite.demo.config.mjs는 원래 config를 import하고 host/strictPort/proxy/cacheDir만 지정한다. backup.html은 정적 JPEG9개와 inline CSS의 별도 자료이며 원래 website가 아니다.

## 함수/메서드

| 파일 / 함수 | 파라미터 | 역할 |
|---|---|---|
| `check_regressions.py::main` | `` | No fits, no evaluation datasets; compare old golden responses and synthetic inference. |
| `check_demo.py::run` | `backend_port=8000, frontend_port=5173` | Return per-check statuses and synthetic response objects; no output file by default. |
| `check_demo.py::main` | `` | Optional --output saves synthetic-only evidence; ports support isolated lifecycle QA. |
| `check_demo.py::__init__` | `self, port` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `check_demo.py::request` | `self, path, body=None` | path: relative local path; optional body: synthetic JSON. Return parsed JSON. |
| `check_demo.py::search` | `self, q, mode='name'` | q: synthetic search text; mode:name/notes. Never logs a user request body. |
| `check_demo.py::check` | `name, fn` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `check_demo.py::search_check` | `` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `check_demo.py::recommendation` | `scent=scent, token=token` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `check_demo.py::redirect_request` | `self, req, fp, code, msg, headers, newurl` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `check_integrity.py::main` | `` | Write new final-demo integrity.json; never changes source/data/model hashes. |
| `test_demo.py::info` | `self` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `test_demo.py::test_identity_parser` | `self` | 합성 안전 검증: test_identity_parser |
| `test_demo.py::test_project_uid_path_module_port_checks` | `self` | 합성 안전 검증: test_project_uid_path_module_port_checks |
| `test_demo.py::test_existing_frontend_command` | `self` | 합성 안전 검증: test_existing_frontend_command |
| `test_demo.py::state` | `self, path` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `test_demo.py::test_no_state_never_signals` | `self` | 합성 안전 검증: test_no_state_never_signals |
| `test_demo.py::test_mismatched_pid_never_signals` | `self` | 합성 안전 검증: test_mismatched_pid_never_signals |
| `test_demo.py::test_dead_pid_cleans_only_ownership_state` | `self` | 합성 안전 검증: test_dead_pid_cleans_only_ownership_state |
| `test_demo.py::test_owned_matching_identity_only_sigterm` | `self` | 합성 안전 검증: test_owned_matching_identity_only_sigterm |
| `test_demo.py::test_multiple_listeners_stop_without_adoption` | `self` | 합성 안전 검증: test_multiple_listeners_stop_without_adoption |
| `test_demo.py::test_reachable_port_without_visible_pid_is_not_free` | `self` | 합성 안전 검증: test_reachable_port_without_visible_pid_is_not_free |
| `test_demo.py::test_unknown_port_owner_aborts_without_spawn_or_signal` | `self` | 합성 안전 검증: test_unknown_port_owner_aborts_without_spawn_or_signal |
| `test_demo.py::test_browser_target_is_only_fixed_loopback` | `self` | 합성 안전 검증: test_browser_target_is_only_fixed_loopback |
| `manager.py::norm` | `value` | value: path/command text. Normalize macOS composed/decomposed Korean. |
| `manager.py::capture` | `command` | command: trusted argv; short read-only process/runtime query, no shell. |
| `manager.py::identity` | `pid` | pid: integer. Return uid/start/command/cwd; None if dead or unverifiable. |
| `manager.py::project_process` | `info, role, port` | Require same uid, exact project cwd and expected executable/module/port. |
| `manager.py::listener` | `port` | port: loopback service port. Multiple/unknown listeners are unsafe to adopt. |
| `manager.py::get_local` | `url` | url: fixed loopback address. Ignore system HTTP proxies and reject redirects. |
| `manager.py::ready` | `role, port` | Validate health479 or SCENT MATCH page; false on any transport/schema error. |
| `manager.py::verify_frozen` | `` | Check original protected19 plus manifest against preserved pre-demo snapshot. |
| `manager.py::runtimes` | `` | Find installed Node/npm via PATH, local hints or standard macOS locations. |
| `manager.py::save_state` | `path, records` | path: private state JSON; records: owned processes only. Atomic local replace. |
| `manager.py::stop_owned` | `path, log` | Recheck uid/start/command/cwd before SIGTERM; never kill mismatched/stale PID. |
| `manager.py::start` | `args, state_path, log` | args: ports/no-browser; reuse verified project services, spawn only free ports. |
| `manager.py::main` | `` | start/stop; optional isolated test ports/state-dir; default is 8000/5173. |
| `manager.py::find` | `name` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |
| `manager.py::redirect_request` | `self, req, fp, code, msg, headers, newurl` | 인접 docstring의 내부 helper; 명시된 인자/반환 계약으로 실행 |

## 공식 API 참고(이 단계에서 외부 접속 안 함)

Python 표준 API: pathlib, subprocess.Popen/run, urllib.request, fcntl.flock, logging.handlers.RotatingFileHandler, hashlib, unittest.mock. 기존 web/deployment/METHODS_EXPLAINED.md 및 REFERENCES.md를 함께 참고한다. 이 문서에서는 새 외부 문서를 다운로드하거나 코드 예제를 차용하지 않았다.
