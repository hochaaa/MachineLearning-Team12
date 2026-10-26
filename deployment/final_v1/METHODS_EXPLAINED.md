# 신규 실행 구성의 함수·파라미터·출처

기존알고리즘을복사·재구현하지않았다. 사용자승인범위에서프로젝트의기존factory·UI·요청계약을재사용한다. 외부예제코드복사없음. 새로운ML모듈이아니며수업사용여부와관계없이실행구성을설명한다.

- config.py의ROOT/HERE/LOCAL은__file__기준프로젝트/새구성/별도설치위치다. UI_FILES는읽어서동일하게복사할기존소스9개의allowlist다. secrets/.env/기존자료를재귀복사하지않는다. MANIFEST_PIN/SOURCE_FREEZE는기존검토fingerprint다.
- SetupError는안내할설정오류다. sha256(path)는1MiB씩바이트를읽어해시만구하고Q/카탈로그를파싱하지않는다. inspect_assets(directory,root=ROOT,expected_pin=MANIFEST_PIN)는manifest목록·provenance·5파일size/hash·원sourcehash를검사한다. root/pin인자는단위픽스처주입용이며운영CLI는pin변경옵션이없다. 원STEP12로더검사를대체한모델검증이아니라권한전의정적검사다.
- assets_path(value=None,root=ROOT),authorization_path(value=None,root=ROOT)는명시인자→해당환경변수→자산기본위치순이다. auth는기본없음. 상대경로는cwd아닌프로젝트root기준,expanduser/resolve로정규화한다.
- authorization(path,purpose='local_inference',today=None)는schema/status/evidence/검토자/대상4payload+manifestpin/유효기간/행위를확인한다. today는결정적test용날짜주입이다. 이함수는실제증빙의진위나법적허가를판정하지않는다. 그검토는사람이수행해야한다. 기록을만들었다고권리가생기지않는다.
- tools()는Python3.12와Node지원버전/npm을실제version명령으로확인한다. npm_argv(npm=None,node=None,windows=None)는Windows에서node.exe+npm-cli.js를선택해cmdshell을거치지않는다. optional값은합성test용이다. 비표준Windows배치는중단한다. python_path(local=LOCAL,windows=None)는운영체제별venv실행파일경로를반환한다.
- check_ui(root=ROOT,local=LOCAL)는원9source와로컬복사본hash비교다. UI의컴포넌트·문구·슬라이더·검색우선순위는수정하지않는다.
- manage.install()은tools검사·새venv·고정allowlist의동일복사·piplock설치/check·npmci·TypeScript/Vitebuild만한다. 기존파일과다른로컬copy는덮어쓰지않는다. venv.EnvBuilder(with_pip=True)는각PC에서새환경을만든다. shutil.copyfile은source바이트만새target에쓴다.
- dependencies()는새venv에서FastAPI/Uvicorn/NumPy/Pydantic import가능성과pipcheck만검사한다. 모델loader는import하지않는다. plan(asset_dir,auth,purpose)는별도포트8004/5177·고정pin·CORS·VITE_API_BASE_URL을포함하는명령배열과환경을반환한다. .env저장안함. subprocess에shell문자열을보내지않는다.
- free_ports()는loopback bind가능성을확인하고즉시닫는다. 포트경합을완전히없애는OS예약은아니다. 다른PID탐색/kill없음.
- start(asset_dir,auth,purpose)는권한→hash→tools/의존성/UI→포트→backendhealth479→frontend순이다. urllib요청은권한확인후자신의8004health만읽고추천요청을생성하지않는다. asyncio사용없고짧은pollinterval로준비를기다린다. Ctrl+C/오류는자신이만든processgroup/PIDtree만정리한다. time.sleep는런타임관리내대기이며학습loop아님.
- main(argv=None)의install/check/start, --assets/--authorization/--purpose가공개CLI다. check는항목별BLOCKED사유를JSON으로분리하고전체BLOCKED는exit2다. start는권한없으면Popen전에종료한다. 원자료다운로드·학습·평가·cleanup명령이없다.
- app.create_app()은같은권한검사를uvicorn직접실행에도적용하고정적hash후기존deployment.standalone_v1.app.create_app(directory,pin)을그대로반환한다. 새route/알고리즘/subclass/fallback을추가하지않는다.
- shell/PowerShellwrapper는프로젝트root로이동해Python3.12로CLI와인자배열을전달한다. PowerShell@args는인자를보존하며ExecutionPolicy를변경하지않는다.
- tests/test_setup.py는TemporaryDirectory의완전가짜bytes/명세/허가레코드를쓴다. unittest.mock은실제factory/process/network를대체해연결과차단·정리를검사한다. 테스트허가파일은실제허가가아니며실제자산에사용하지않는다. symlink/경로탈출/손상/누락/Windows경로선택도검사한다. Windows OS를시뮬레이션했다고주장하지않는다.

참고공식API: Python Software Foundation의 [hashlib](https://docs.python.org/3.12/library/hashlib.html), [venv](https://docs.python.org/3.12/library/venv.html), [subprocess](https://docs.python.org/3.12/library/subprocess.html), [unittest.mock](https://docs.python.org/3.12/library/unittest.mock.html). URL은API출처안내이며이번에외부코드복사없음. 의존성고지는기존web/REFERENCES.md와패키지LICENSE/NOTICE를유지한다. 프로젝트자체공개라이선스선택은팀확인사항이다. 기존METHODS_EXPLAINED/REFERENCES를덮어쓰지않았다.
