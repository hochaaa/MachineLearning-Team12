# SCENT MATCH — Team 12 Frozen V1 실행

현재 로컬 실행 구성은 별도 authorization JSON 없이 실제 Frozen V1을 로드한다. 이 실행 정책 변경은 데이터·모델 사용권을 확보했다는 뜻이 아니며 허위 승인 기록을 만들지 않는다. 기존 합성 Demo는 별도로 보존하고 최종 V1으로 대체하지 않는다.

## macOS

Python3.12, Node20.20 또는 지원22.12+, npm/Git 설치 후 새 폴더에서:

```sh
git -c core.autocrlf=false clone --single-branch --branch development-v2 https://github.com/hochaaa/MachineLearning-Team12.git
cd MachineLearning-Team12
sh deployment/final_v1/run-macos.sh install
sh deployment/final_v1/run-macos.sh check
sh deployment/final_v1/run-macos.sh start
```

React http://127.0.0.1:5177 / API http://127.0.0.1:8004. start는 두 서버를 함께 실행하고 Ctrl+C로 자신이 시작한 서버만 종료한다. 다시 start하면 재기동한다. 처음에는install이필요하다.

## Windows PowerShell — NOT TESTED

같은Clone후:

```powershell
py -3.12 -B deployment/final_v1/manage.py install
py -3.12 -B deployment/final_v1/manage.py check
py -3.12 -B deployment/final_v1/manage.py start
```

또는 `& .\deployment\final_v1\run-windows.ps1 install` / `check` / `start`. 실행정책을 우회하거나 .venv를 복사하지 않는다. Windows 실제 실행은 미검증이다.

## 팀원 재현성

개발자의 .local/.venv/node_modules를 복사하지 않는다. 각PC에서 새venv와npm ci로설치한다. Python은기존requirements-lock의==버전, npm은기존package-lock의전이버전까지고정한다. 새로운모델학습/벡터화/후보생성은없다. 개인홈절대경로는소스에넣지않는다.

현재브랜치의8dca493커밋에는outputs/step12_runtime/assets의5개파일이있다. 런타임은이파일과기존sourcehash를검사하며원본향수CSV·개인Train·user mapping·P를요구하지않는다. 자산누락/hash변조는오류로종료하고합성Demo로조용히전환하지않는다. 실제자료의재배포권한이확정됐다는주장은하지않는다.

Tom Ford 등기존검색으로향수3개를선택하고0~10평점을넣으면실제Content+MF/Ridge fold-in Hybrid(.25/.75)의Top5를반환한다. 단일Woody/Floral/Rose필터와seen제외는기존그대로다. 점수는확률이아니다.

테스트: `python3.12 -B -m unittest discover -s deployment/final_v1/tests -v`. 실행중API smoke는새venvPython으로 `-B -m deployment.final_v1.tests.live_smoke`. 세부명령/수식/기술오류는 deployment/final_v1/README.md를따른다. 합성Demo를원하면별도 demo/README.md를사용한다.
