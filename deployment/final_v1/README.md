# SCENT MATCH — 동일 Frozen V1 실행 구성

**소스 설치·연결 구성 완료 / 실제 모델의 추가 추론·공유·교수 시연 HOLD.** 합성 Demo가 아닌 기존 Frozen V1을 실행하는 명시적 진입점이다. 권한 증빙이 없으면 기존 로더를 import하기 전에 종료한다. 기록을 임의로 VERIFIED로 바꾸어 실행하지 않는다.

## 바꾸지 않는 것

`deployment.standalone_v1.app:create_app`을 그대로 호출한다. 기존 React 소스9개를 byte-for-byte로 신규 `.local/frontend/`에 복사하고 해당 복사본에서 npm 설치/빌드한다. 기존 웹·로더·모델·데이터·후보479·content/MF/fold-in/Hybrid alpha .25·Knowledge 규칙을 수정하지 않는다. 자산이 없을 때 Demo나원자료로자동대체하지 않는다.

- 원본 manifest SHA256: `3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130`
- 최소자산 manifest pin: `ff9a748e28cfc723aa972af705c07663827e82b1881291cecd2e5f1985ed3caa`
- 프로젝트기본자산위치: `outputs/step12_runtime/assets/`
- 자산5개 총604,291bytes. 현재모두HOLD이며설치기가다운로드·복사·압축하지않는다.

## 현재 GitHub와의 관계

Repository `hochaaa/MachineLearning-Team12`, branch `development-v2`, 현재HEAD `195fe635b273813c10b67c60671de5b650ea1cce`다. 이 신규 실행 구성은 **아직 로컬 미추적 파일**이므로 현재 원격Clone만으로 아래 스크립트가 제공되지는 않는다. source검토/사용자의Git반영승인 이후 팀원에게 안내한다. STEP16 demo/는 보존하지만 이 실행 경로에 연결하지 않는다.

## 1. 소스 설치 — 권한 HOLD에서도 가능

Python3.12(실측3.12.0),Node20.20 또는지원Node22.12+,Git/npm이필요하다. 기존가상환경을복사하지않는다. 신규 `.local/venv`만 생성하며라이브러리설치에는네트워크가필요하다. source만설치하며실제모델은읽지않는다.

macOS, 프로젝트 루트:

```sh
sh deployment/final_v1/run-macos.sh install
sh deployment/final_v1/run-macos.sh check
```

Windows PowerShell — **NOT TESTED**:

```powershell
& .\deployment\final_v1\run-windows.ps1 install
& .\deployment\final_v1\run-windows.ps1 check
```

로컬정책상ps1이막히면실행정책을우회하지말고같은Python진입점을직접사용한다:

```powershell
py -3.12 -B deployment/final_v1/manage.py install
py -3.12 -B deployment/final_v1/manage.py check
```

bootstrapPython은3.12여야한다. venv활성화/관리자권한이필요없다. Windows의공식Node설치배치에서는node.exe와npm-cli.js를직접실행해cmd.exe문자열해석을피한다. 다른npm배치나심볼릭링크구성은안내오류로중단할수있으며실제Windows에서검증해야한다. UTF-8 및줄바꿈을유지한다. 새Clone시 `git -c core.autocrlf=false clone --single-branch --branch development-v2 https://github.com/hochaaa/MachineLearning-Team12.git`를사용할수있다(source반영후).

`install`은source설치성공만뜻한다. `check`는도구·의존성·원UI복사본·자산SHA·권한을분리해출력한다. 현재기술검사는PASS지만권한HOLD라전체BLOCKED/exit2가정상이다. 자산/코드hash가다르면pin이나원파일을고쳐우회하지않는다. 로컬UI복사본이달라도자동덮어쓰지않고중단한다.

## 2. 권한 확인 이후의 실행 — 지금 실행 금지

권리자증빙을받은후자산/채널/수신자/기간별실제검토기록을비공개로보관한다. `authorization.example.json`은HOLD상태의형식예시일뿐허가서가아니다. 예시파일을복사하고상태만바꾸는것은허용근거가아니다. 현재추가증빙은없다.

확인된권리근거가생긴뒤담당검토자가모든4payload를포함하는명세·manifestpin·증빙reference·검토자·유효기간·허용행위를기록한다. 추가추론에는local_inference,교수시연에는local_inference와classroom_demo가필요하다. 이기록은워크플로검사이지법률판정/전자서명/OS보안경계가아니다. 팀원전달·GitHub·파일제출·서버호스팅권한은별도이며이레코드로자동생성되지않는다.

다음명령은해당권한확보후에만사용한다. 검토기록의실제경로는각사용자가비공개로정한다. 아래는경로형식예시이며그파일을생성하지않았다.

```sh
sh deployment/final_v1/run-macos.sh check --authorization deployment/final_v1/authorization.local.json
sh deployment/final_v1/run-macos.sh start --authorization deployment/final_v1/authorization.local.json --purpose local_inference
# 교수 비공개 시연 권한까지 확인된 뒤에만:
sh deployment/final_v1/run-macos.sh start --authorization deployment/final_v1/authorization.local.json --purpose classroom_demo
```

Windows는같은인자를PowerShellwrapper또는 `py -3.12 -B deployment/final_v1/manage.py`에전달한다. 자산위치는 `--assets` 또는 `SCENT_MATCH_STANDALONE_ASSETS`,검토기록은 `--authorization` 또는 `SCENT_MATCH_FINAL_AUTHORIZATION`로지정한다. 상대경로는프로젝트루트를기준으로해석한다. `.env`파일은자동로드하지않으며비밀값을프론트에넣지않는다. 자산전달방법은권한확인전제공하지않고자동다운로드도없다.

성공시새API8004,기존UI동일복사본5177이다. `VITE_API_BASE_URL=http://127.0.0.1:8004`, `WEB_CORS_ORIGINS=http://127.0.0.1:5177`를프로세스환경으로설정한다. 원vite.config.ts의8000 proxy가남아있지만프론트fetch는명시한8004절대주소를사용하므로기존서버와연결하지않는다. 기존8000/5173/STEP16포트를교체하지않는다.

권한·hash·의존성·포트검사후API→health ready479→React순으로시작한다. 준비실패/포트충돌은중단하며타프로세스를kill하지않는다. Ctrl+C는자신이만든자식프로세스만종료한다. macOS는분리한자식processgroup,Windows는자신이시작한PIDtree만정리한다. 실제모델서버동작및이종OS수치동일성은현재미검증이다.

## 3. 테스트

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m unittest discover -s deployment/final_v1/tests -v
sh -n deployment/final_v1/run-macos.sh
```

Windows는 `py -3.12 -B -m unittest discover -s deployment/final_v1/tests -v`다. 테스트의가짜Q/JSONbyte와허가record는일시적합성픽스처이며실제자산/권한으로사용할수없다. 신규27테스트는설정·hash·실행차단·연결·자식정리만검사한다. **기존144개동일성은STEP12과거증거**이며이번재실행결과가아니다. 과거허용오차atol1e-12/rtol1e-10,관측점수차이0. 신규권한확인후의동등성검사는기존코드가과거증거파일을다시쓰지않도록새receipt경로를별도설계해야한다. 지금기존verify_equivalence나평가를실행하지않는다.

## 4. 발표와정리

`PRESENTATION_AND_CLEANUP.md`에4분시나리오·권한전제·학기말삭제가이드를적었다. 현재교수실제모델시연은HOLD다. 대체발표는설계와저장된기존집계결과/한계설명이며Demo를V1로대체하지않는다. 실행해놓은기존서비스의존재가권리허가를입증하지않는다.

실제추가추론·자산공유·외부배포·원래평가재실행·Git반영은이번에하지않았다. source와합성테스트는공유검토후보,5자산은HOLD,개인평점·mapping·전체모델·secrets·환경·빌드는제외한다. 새`.local/`·evidence/·실제권한기록은새디렉터리ignore다. 원rootignore와STEP16을바꾸지않았다.
