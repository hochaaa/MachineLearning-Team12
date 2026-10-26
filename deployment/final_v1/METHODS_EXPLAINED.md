# Frozen V1 실행 구성 설명 — 로컬 정책 변경

2026-10-26. 원 추천 수식·모델·UI는 수정하지 않았다. authorization()/authorization_path()/--authorization/--purpose와 권한 JSON 의존성을 제거했다. 허가를 확인했다고 출력하지 않고 검토 문서를 실행 gate로 사용하지 않는다.

- config.ROOT/HERE/LOCAL: __file__로 계산하는 프로젝트/구성/새 설치 위치. UI_FILES9개는 복사 allowlist다.
- sha256(path): 1MiB 단위 바이트 hash. inspect_assets(directory,root,expected_pin)는 manifest provenance, 정확한4payload 이름·크기/hash, 원sourcehash를 검사한다. root/pin 주입은 합성 unit fixture용이며 운영 CLI는 pin 변경 옵션을 제공하지 않는다. 이 검사만으로 모델을 로드하지 않는다.
- assets_path(value=None,root=ROOT): 명시 인자→SCENT_MATCH_STANDALONE_ASSETS→기본5자산 경로, 상대경로는 root 기준이다.
- tools(): Python3.12/지원Node/npm version 검사. npm_argv(npm,node,windows)는 Windows에서 Node+npm CLI를 직접 실행해 cmd 문자열 문제를 피한다. python_path(local,windows)는 OS별 venv 실행파일을 선택한다. 주입 인자는 단위테스트용이다.
- check_ui(root,local): 원9개 source와 로컬 복사본 hash가 같은지 검사한다. 변경된 로컬 source를 자동 덮어쓰지 않는다.
- install(): 별도venv를 만들고 기존 requirements-lock의== 버전으로 설치/pip check, byte-identical UI 복사본에 npm ci/build. 자산 다운로드·fit·추천·권한 승인 없음.
- dependencies(): 별도venv 라이브러리 import·pip check·Vite 존재 검사. 실제 버전 고정은 install의 lock 파일이 담당한다.
- plan(asset_dir): 별도8004/5177 command arrays와 env를 만든다. 기존 검토 env는 전달하지 않으며 VITE_API_BASE_URL/CORS/고정manifest pin만 연결한다. shell=True나 .env 저장 없음.
- free_ports(): loopback bind 검사. start(asset_dir)는 자산hash/도구/의존성/UI/포트 검사 후 API→health479→React 순으로 시작한다. ready=false는 즉시 오류로 처리한다. KeyboardInterrupt/오류는 자신이 만든 POSIX group 또는Windows PID tree만 정리한다.
- main(argv=None): install/check/start와--assets만 공개CLI다. 기술오류는ERROR/exit2, 통과는PASS/exit0. 사용권 확인 메시지를 만들지 않는다.
- app.create_app(): 정적무결성·프로젝트cwd 검사 후 기존 standalone_v1.app.create_app(directory,pin)의 반환값을 그대로 사용한다. 새 route·알고리즘·fallback 없음.
- run-macos.sh/run-windows.ps1: 프로젝트root를 계산하고 Python3.12 진입점에 인자배열을 전달한다. 권한JSON·활성화·policy bypass 필요 없음.
- tests/test_setup.py: 가짜파일의 hash/누락/변조/경로·이식성·기존factory위임·새실행정책·기술실패·own child정리를 검사한다. 가짜 승인 기록은 더 이상 생성하지 않는다.
- tests/live_smoke.py::verify(base,frontend,reference=None): loopback actual API health/479/alpha.25/Top5/finite/seen제외·선택적 기존추론ID/순서/점수를검사한다. reference는외부테스트하네스의기대값일뿐서버의필수자료가아니다. HTTP 요청은새로운합성취향입력이며기존평가정답을읽지않는다. score비교는abs1e-12/rel1e-10이다.

원primitive의계산은 src/perfume/models.py와improvements.py, standalone_v1/METHODS_EXPLAINED.md를참조한다. 고정 Q로ridge fold-in,content와MF를.25/.75로결합하고기존규칙으로랭킹한다. 라이브러리API는 Python3.12 stdlib(hashlib/venv/subprocess/unittest/urllib), 기존 FastAPI/Pydantic/NumPy를사용한다. 외부구현코드복사없음; 프로젝트내부코드재사용범위만변경했다.
