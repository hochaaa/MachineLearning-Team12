# Demo 알고리즘·모듈·파라미터 설명

수업 사용 여부를 추측하지 않고 모두 설명한다. 기존 모델·고정 IDF·집계·레코드를 import하지 않는다. 표준 Python math만으로 구현하며 scikit-learn/NumPy가 필요하지 않다. 코드는 Team12용 신규 구현, UI 흐름은 사용자 승인에 따라 내부 웹 소스의 아이디어를 재사용했다.

## 수학

`x_it=1[t∈notes/accords(i)]·(log((N+1)/(df_t+1))+1)`, `v_i=x_i/||x_i||₂`. note/accord 접두어로 서로 다른 피처를 만든다. smoothed IDF는 희소 특성을 더 크게 반영하고 모든 document의 특성에도 양수 가중치를 준다. N은 합성80개뿐이다. 이 시연은 정답 기반 성능 평가나 hyperparameter 탐색을 하지 않는다.

`w_i=(r_i−5)/5∈[-1,1]`, `p=Σw_iv_i`, `s_j=clip(pᵀv_j/||p||₂,−1,1)`이다. 프로필은 분자와 norm으로 정규화하므로 단순 양수 평균이 아니다. dislike 항목은 방향을 빼고5점은 중립이다. norm≤EPS(1e-12)면 점수0·경고로 처리해 division by zero를 피한다. 순서는 `(-score,id)`이며 피처/입력 합산도 정렬해 hash seed 차이를 방지한다. 실제 다른 OS의 bitwise 동일성은 미검증이다.

Woody=accord:woody, Floral=accord:floral, Rose=note:rose. 단일 required_scent와 복수 required_scents의 합집합에 AND를 적용한다. 계절·사용상황·강도는 제공하지 않는다. 필터/seen 제외 후 후보 수와 반환 수를 공개하고 없는 결과를 채우지 않는다.

## Python 구성요소

|구성요소|역할·파라미터|
|---|---|
|generate_data.generate()|입력파일 없음. Random(SEED=1612)로10계열×8개 생성, note/accord 서명 중복 거절. JSON main은 demo 내 고정 파일만 기록. 서버는 generator를 실행하지 않음|
|random.Random, sample, choice|고정 독립 RNG, 비복원 k개 추출, 한 원소 선택. 전역 RNG/사용자자료 없음|
|json.loads/dumps, Path.read_text/write_text|UTF-8 합성 레코드 직렬화. 서버의 단일 DATA 경로는 __file__ 상대. 임의 경로/자동탐색 없음|
|tokens(row)|notes와 accords를 typed frozenset으로 바꿈. 빈도 대신 존재만 사용|
|Recommender(path=DATA)|명시 합성JSON 로드·필수필드/고유ID 검사·df/IDF/정규화벡터 구성. 실패시 다른 자료로 fallback 없음|
|search(query,mode='name')|casefold/공백분할 후 AND 부분문자열; name은ID/brand/name, notes는notes/accords. ID 오름차순 최대10. 실브랜드 alias/오타 제안 없음|
|recommend(ratings,required_scent='none',required_scents=())|검증된 Rating 목록, 단일/복수 명시 규칙. signed 프로필/seen 제외/필터/최대5·설명 반환. 평점 저장·fit 호출 없음|
|Counter, sorted, frozenset|문서빈도, 결정적 순회·정렬, 피처 중복 제거|
|math.log/sqrt/isfinite|자연로그IDF, L2 norm, NaN/Inf 차단|
|Rating.numeric(value)|int/float만, bool/string 거절. Field ge0/le10/allow_inf_nanFalse. perfume_id 길이1~80|
|Recommendation.integer_five(value), unique()|top_k가 type int이며5인지, perfume_id 중복 없는지. ratings 길이1~50, required_scents 최대3 지원규칙. ConfigDict extra forbid|
|create_app() / lifespan(app)|독립 FastAPI 생성, 시작시Recommender 하나만 로드/종료시해제. 실패시readyFalse/503. 기존 app import 없음|
|no_store(request,call_next)|응답 Cache-Control no-store, 사용자 입력 캐시 억제|
|invalid(request,exc)|RequestValidationError를422안내로 변환, 원입력/개인경로/stack 미반환|
|engine(request)|app.state의 준비 엔진 확인, 없으면503|
|health/search/detail/recommend routes|README API와 아래 보고서 계약. q최대100,mode name/notes,상세없는ID404,unknown추천ID422. 실패500은상세예외숨김|
|CORSMiddleware|DEMO_CORS_ORIGINS comma-separated 허용origin, 기본 localhost/127.0.0.1:5175. credentialsFalse, GET/POST,Content-Type만. 환경 설정은 demo전용|
|HTTPException/JSONResponse|상태코드·사용자 안내 반환. 잘못된 JSON도 검증오류|
|unittest/TestClient/mock.patch|합성 테스트·lifespan 요청·일부러 내부오류/준비실패 유도. patch는 테스트 객체만 변경|
|clean_smoke audit(event,args)|새 Clone에서 원프로젝트 출력폴더 부재 검사, sys.addaudithook로 demo/venv 외 프로젝트 read 차단. OS 수준 전프로세스 보안 경계는 아님|
|http_smoke.run(base,frontend)|자체 loopback API/프론트에 HTTP smoke, 합성 추천·필터·오류 receipt. argparse --base/--frontend만 허용, 외부URL 거절|
|subprocess/PYTHONHASHSEED test|서로 다른 seed 프로세스의 전체 JSON 응답 비교. 실제 사용자 기록/평가 없음|

## React/브라우저

App은 useState로 검색어/모드/선택/필터/결과/상세/loading/error/ready를 관리한다. useEffect health는 mode=demo/data_origin=synthetic 확인, 검색 effect는180ms debounce와 AbortController cleanup으로 이전 요청을 무효화한다. request(path,init={})는 VITE_DEMO_API_URL(기본8002)에 fetch,15초 timeout, HTTP 오류와 네트워크 오류를 안내한다. recommend는 선택3개·top5·필터를 보내고 응답 mode/origin/engine을 확인한다. changed는 이전 추천을 지워 입력 변경 후 stale 결과를 막는다. showDetail(id)는 별도 GET 상세를 읽고 모달에 표시한다.

input range min0/max10/step0.5, 3개 선택 제한, 추천 버튼의 ready/loading 검사를 쓴다. CSS grid와850/520px media query가 반응형을 만든다. React가 텍스트를 렌더하며 raw HTML 주입을 하지 않는다. Vite dev/preview는127.0.0.1:5175 strictPort, build는 TypeScript noEmit 검사 후 독립 dist 생성이다. 환경변수는 서버 프로세스/빌드 시 설정하며 비밀값을 넣지 않는다. 상세 모달은 닫기 버튼을 제공하나 완전한 키보드 focus-trap/전문 접근성 인증은 미구현이다.

공식 문서와 내부 재사용 범위는 REFERENCES.md를 참조한다. 새 요소의 학습 경험·개인 역할은 팀이 확인해야 한다.
