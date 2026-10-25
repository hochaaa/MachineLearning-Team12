# SCENT MATCH 로컬 발표 실행

이 Mac의 기존 환경만 사용한다. 설치·외부 업로드·모델 변경은 하지 않는다.

1. Finder에서 **start_demo.command** 더블클릭 → 준비 확인 후 기본 브라우저에 localhost5173을 연다. 정상 기존8000/5173은 재사용한다.
2. 발표 전 프로젝트 root에서 `web/backend/.venv/bin/python -B web/demo/check_demo.py` →14 PASS 확인.
3. 입력은 Sauvage Elixir9 / Bleu de Chanel Parfum8 / Black Orchid2. 필터를 바꿀 때마다 추천 버튼 클릭.
4. 실패 시 `web/evidence/final-demo/backup.html` 또는 JPEG9개 사용. 사전 실행 화면이라고 말한다.
5. 끝에 **stop_demo.command**: 실행기가 직접 시작한 프로세스만 정상 종료. 기존 서버는 유지한다.

다른 작업 폴더에서도 .command를 절대경로로 실행할 수 있다. 상태/로그/runtime.local.json은 현재 기기 전용이며 공개 제외다. runtime hint가 없는 새 Mac/옮겨진 venv는 별도 준비와 검증이 필요하다. freeze와 발표 준비 때의 manifest snapshot도 있어야 한다. 자동 설치나 강제 종료를 하지 않는다. local node_modules를 사용하며 실제 Node binary를 실행해 Volta shim의 자식 PID 혼동을 방지한다.

실행 로그는 logs/demo.log의64KiB rotation(backup3개). raw 서버 traceback·평점·이력·키를 수집하지 않는다. 상태 파일은 .state/owned.json이며 uid/start/command/cwd를 현재 프로세스와 다시 비교한다. 빈 lock/cache는 남을 수 있다. raw PID만 보고 kill하지 않는다. lsof에서 PID가 안 보여도 TCP가 응답하면 포트가 비었다고 가정하지 않고 중단한다.

안전 QA: `web/backend/.venv/bin/python -B -m unittest web.demo.test_demo -v`.
기존 회귀: `web/backend/.venv/bin/python -B -m web.demo.check_regressions > web/evidence/final-demo/regression-tests-new.log 2>&1`(새 파일명 사용).
무결성: `web/backend/.venv/bin/python -B web/demo/check_integrity.py`.

실제 인터넷 차단 시험은 NOT VERIFIED. Wi-Fi/방화벽/절전/브라우저 설정을 바꾸지 않는다. Finder의 iCloud 자동 동기화 표시가 관찰되어 보관 범위를 팀이 별도 확인해야 한다. 직접 외부 업로드하지 않은 것과 OS 자동동기화가 없는 것은 다르다.

대본/오류 대응/한계: reports/WEB_DEMO_SCRIPT.md, WEB_DEMO_TROUBLESHOOTING.md, WEB_LOCAL_DEMO_READINESS.md.
