# STEP12 API·모듈·수식 설명

수업에서사용했는지추정하지않고신규구성요소를설명한다. 기존팀코드만import/상속재사용했고외부구현코드는복사하지않았다. 라이브러리API는 https://docs.python.org/3/library/ , https://numpy.org/doc/stable/reference/ , 기존web/REFERENCES.md의FastAPI·Starlette설명을참고한다. 이링크는출처안내이며이번에네트워크문서조회하지않았다.

## 모델 계산을 바꾸지 않는 범위

새코드는학습하지않는다. MatrixFactorization 생성자는파라미터검사·속성초기화뿐이며fit호출이없다. 원Q의479개행을복사하고그행을itemID로찾도록새item-index를만든다. score_vector는원래pᵀq clipping, fold_in은원래 `(Q_s.T Q_s+nλI)p=Q_s.T y` solve다. 원상수factors4/reg.01/seed12와profile rating/alphaContent.25를보존한다. 전체train용P/users는이두메서드에서읽지않는다.

ProfileContent의기존vectors·IDF값을동일float로보존한다. support와candidate는479내이므로나머지catalog벡터는실행에불필요하다. CatalogSearch·AdvancedCatalogSearch·FrozenService.record/search/search_response/recommend는원함수그대로다. baseline.counts는479만보존하지만로그정규화maximum은원538상품기준의원값을유지한다. mean은웹score에서쓰지않는다. 어떤카탈로그명·향특성도새로번역/추정하지않는다.

## 모듈·함수·파라미터

- runtime_config.py: ROOT는코드위치기반프로젝트루트; ASSET_NAMES는4payload의고정이름; SOURCE_FREEZE_SHA256은원manifest 식별자다. asset_directory(value=None)는명시Path, SCENT_MATCH_STANDALONE_ASSETS, 프로젝트기본출력의순서로경로를정한다. 개인홈절대경로를하드코딩하지않는다.
- runtime_loader.py: RuntimeAssetError는입력자산오류다. sha256(path)는스트리밍bytehash다. inspect_assets(directory,expected_manifest_sha256=None)는정확한파일명/size/hash, provenance, 재사용source hash를검사하고manifest를반환한다. optionalpin은별도신뢰경로의SHA;없으면자체일관성검사일뿐이다. StandaloneService(directory=None,expected_manifest_sha256=None)는초기화만교체한다. np.load allow_pickle=False/float64/(479,4)/finite검사, Q writeable=False, item/catalog/vector집합일치검사,허용metadata필드검사를한다. mf에는users나P속성을주지않는다. 기존학습사용자score API는지원대상이아니고원웹요청도사용자ID를받지않는다.
- export_local.py: export(directory)는프로젝트outputs의**존재하지않는**새경로만허용한다. 원freeze19byte를검사하고Q만읽어candidate순으로복사한다. runtimeJSON은필요설정·items·count/max만,content는고정IDF/479벡터,카탈로그는brand/name/tokens만보존한다. np.save(...,allow_pickle=False)는비압축npy다. 개인mapping을로컬파싱하지만출력하지않고P는archive에서읽지않는다. main의--output은새로컬출력경로며기존파일덮어쓰기를거절한다.
- app.py: create_app(directory=None,expected_manifest_sha256=None)는독립FastAPI 인스턴스다. lifespan은새로더만초기화하고실패시stateNone/healthfalse/서비스503으로남긴다. 기존Rating/Recommendation/route/검증exception/no-store/CORS미들웨어설정을재사용한다. 기존app객체·원래lifespan을patch하거나기존서버에연결하지않는다. 새manifest pin env는SCENT_MATCH_STANDALONE_MANIFEST_SHA256이다.
- preflight.py: main의--assets와--expected-manifest-sha256는위경로/pin이다. 모델fit없이실제복원과환경/479/Qshape/개인별속성부재를확인하고PASS또는BLOCKED만출력한다. 원자료값은로그에없다.
- verify_equivalence.py: audit(event,args)는standalone scope동안원래outputs/원자료open을차단하고읽은신규자산이름만기록한다. standalone_only()는그scope를관리한다. main은별도프로세스의old/new TestClient와fit금지mock으로144개합성응답·17검색·15오류·2CORS를비교한다. parity(body)는같은합성요청의ID/순서/metadata와score오차를검사하는내부함수다. 기존정답·peruser평가결과를읽지않는다.
- clean_smoke.py: main의--assets는임시Clone내새자산, --output은새receipt다. 원본8경로부재를확인하고legacy open을차단한다. TestClient의검색·4조건·오류·missing자산을검사하고직접시작한loopback18112 ASGI도검사한다. http(route,data=None)는그소유포트만호출한다. 기존서버를kill하지않는다. assert가원래프로젝트실행을거절하면원본파일을삭제하지말고임시Clone루트에서다시실행한다.
- tests/test_runtime_loader.py: setUp/tearDown은새TemporaryDirectory의자산복사본만바꾼다. rewrite_manifest(edit)는그임시manifest만수정한다. 정상복원/fit금지/Q불변/사용자속성부재/유효pin·잘못된pin/파일누락·변조/경로탈출/sourcehash/정렬mapping/원메서드동일성/개인ID미복사등14검사를한다. user-ID검사는원metadata keys를메모리비교만하므로CleanClone용suite와구분한다.

## 주요 라이브러리 동작과 한계

json의기본순서를보존하여content토큰가산순서를유지한다. np.save/load는float64값을그대로직렬화하고재fit/양자화하지않는다. np.testing.assert_allclose는atol1e-12/rtol1e-10으로점수를검사하지만ID·순서는정확히같아야한다. unittest.mock.patch는검증프로세스의fit만차단하고파일·실행중서버에는영향이없다. sys.addaudithook는해당테스트프로세스에서금지된읽기를검출하며보안제품/모든프로세스의OS격리를의미하지않는다. subprocess는새venv의새ASGI만시작·종료한다.

SHA는전자서명이아니며원본hash확인도모든과거학습이력의증명은아니다. itemQ/집계카운트/메타데이터는파생데이터로민감할수있다. 사용자ID/P/평점행을제거한것은차등개인정보보호나재배포권한확보가아니다. 외부공유·개인정보역추정공격실험은하지않았다.
