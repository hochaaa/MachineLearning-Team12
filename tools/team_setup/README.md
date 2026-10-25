# Team setup 검증 도구 — STEP10

모델·평가 코드를 바꾸지 않고 환경 설치와 합성 입력의 동결 V1 추론만 확인한다. 팀원 실행 문서는 루트 TEAM_SETUP_GUIDE.md, 자산 목록은 RUNTIME_MANIFEST.json이다. 원본/가공 평점·mapping·모델의 별도 팀원 전달 권한은 보류이며 manifest는 실제 자산을 담지 않는다.

## 도구와 파라미터

- check_runtime.py: verify(root,manifest)는 required 파일의 상대 경로 경계·size·SHA256을 읽기 전용으로 검증한다. main의 --root는프로젝트루트, --manifest는별도목록경로(생략시root/RUNTIME_MANIFEST.json). 모델을 import하거나 결과를 저장하지 않는다. Windows/macOS에 공통인 Path·표준라이브러리만 사용한다.
- test_manifest.py: RuntimeManifestTests의 setUp/tearDown은 새 TemporaryDirectory만 생성/정리한다. 유효파일/누락/바이트변경/경로탈출의4테스트이고 원본 자산·기존웹증거를 읽거나 쓰지 않는다.
- protect.py: sha(path)는 bytehash, freeze()는원래manifest19개비교, snapshot()은기존파일의hash/size/mtime다. save(name,obj)는새STEP10증거를배타적으로생성한다. main before/after가변경목록을비교한다. STEP9 metadata9개는이번시작상태로기록하되원래동결기준은변경하지않고수정시각도복원하지않는다.
- build_manifest.py: main()은원래protected19경로+웹 source/의존성파일의byte정보와Git상태를목록화한다. 데이터내용파싱·패키징·전송은하지않고새rootmanifest를한번만생성한다.
- clean_validate.py: --root는임시clone, --phase missing/ready는자산부재/준비상태, --output은새집계JSON이다. 독립venv로실행하며 source는targetclone에서import한다. fit함수를mock차단하고공개제품에만든평점으로search3/Top5/4조건을확인한다. 이전정답·원본이력을평가하지않는다.
- live_clean.py: --root는전용/private/tmp/scent-step10-* 복사본만허용, --output은새JSON이다. get(path,body,port)는loopbackHTTP다. main은기존포트8000/5173을쓰지않고18100/15173이비었을때만자체서버를시작하며자기프로세스만종료한다. 프론트proxy config는임시복사본안에만쓴다. macOS감사도구이며Windows팀원의필수실행명령이아니다.
- sharing_audit.py: sha(path)는hash, main()은정확한source후보를목록화·패턴검사하고tracked source+승인예정source의임시배포본을구성한다. git add/commit/push하지않고공유용zip도만들지않는다. source리뷰로그와해시만보존한다.

실제실행은 outputs/step10_sharing/의로그·receipt에있다. 기존API/search unittest중일부는원래web/evidence를다시쓰므로이번에실행하지않았다. 의존성설치와빌드는임시경로에서만했다. 패키지설치권한과데이터재배포권한은별개다.

Python 표준 hashlib/pathlib/json/argparse/tempfile/unittest/mock/subprocess/socket/urllib은 https://docs.python.org/3/library/ , NumPy finite/array는 https://numpy.org/doc/stable/reference/ 참고다. 문서링크만안내하며이번네트워크문서조회를하지않았다. 새도구는직접작성했고외부구현코드를복사하지않았다. 기존팀web.backend와FrozenService를import재사용한다. 새root가이드는개발자의개인절대경로없이표준python/node/상대venv명령을사용한다.
