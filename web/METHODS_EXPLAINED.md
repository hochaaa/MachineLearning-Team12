# 웹 전용 구성요소 설명

기존 `METHODS_EXPLAINED.md`와 동결 코드는 변경하지 않았다. 이 문서는 추가 웹 모듈의 역할·입출력·주요 파라미터를 설명한다. 수업에서 배웠는지 여부는 미확정이다.

## Python

- `adapter.FrozenService()`는 프로젝트 루트를 현재 디렉터리로 요구한다. 기존 `load_frozen('outputs/final')`의 상대경로 해시 검증을 그대로 실행한다. `candidates`는 원본 순서 tuple, `allowed`는 같은 URL의 frozenset이다. 479개 및 item factors 포함 여부, alpha .25를 검증한다. API 시작 시 한 번 생성한다.
- `record(item)`은 URL 문자열 하나를 받아 기존 catalog의 이름·브랜드·accord·note만 반환한다. ID 정규화/재매칭/가상 이름 생성은 하지 않는다.
- `search(query)`는 공백 제거·casefold 후 이름/브랜드 부분 일치를 찾는다. 하이픈을 공백으로 바꾼 표시명도 검사한다. 브랜드·이름·URL로 결정적으로 정렬하고 최대10개를 반환한다. 공백 질의는 빈 목록이다.
- `recommend(ratings,scent)`는 검증된 Rating 목록과 `none/woody/floral/rose`를 받는다. 평점/10 및 support 제외 후보를 기존 `mf.fold_in`, `mf.score_vector`, `content.score`, `baseline.score`, `hybrid`, `knowledge`로 전달한다. 기존 CLI의 조합 순서를 따라가며 수식·정렬·규칙은 기존 함수에 위임한다. `knowledge` 결과 앞5개 및 입력 metadata token 교집합을 JSON 형태로 포장한다. user/item factors를 업데이트하지 않는다.
- `SCENTS`는 none→None, woody→accord:woody, floral→accord:floral, rose→note:rose의 고정 매핑이다. soft preference/금지 조건/계절/가격 인자는 노출하지 않는다.
- `Rating`: perfume_id는 길이1..500 URL 식별자, rating은 유한 숫자0..10. `numeric(value)` pre-validator가 bool/문자열을 거부한다. `Recommendation`: ratings 1..50개, required_scent 고정 enum, top_k 정수5만 허용. `unique()`가 중복을 거부한다. `ConfigDict(extra='forbid')`는 정의하지 않은 필드를 거부한다.
- FastAPI는 요청 검증 및 OpenAPI를 제공한다. `lifespan(app)` async context manager는 시작/종료 시 서비스 참조를 설정/해제한다. 로딩 실패 시 상태를 None으로 유지하여 health는 원인을 구분하고 나머지는503을 반환한다. 내부 실패 내용은 API 응답으로 노출하지 않는다.
- `service(request)`는 준비된 싱글턴을 반환하거나503. `health(request)`는 서버·모델·추천 준비 여부. `perfumes(request,q)`는 최대100자 검색어. `recommend(body,request)`는 support ID 허용집합을 확인하고 adapter를 호출한다.
- `no_store(request,call_next)` middleware는 응답 Cache-Control:no-store를 설정한다. `validation_error(request,exc)`는422 고정 안내만 반환하여 원본 입력이나 비유한 숫자를 오류 JSON에 반영하지 않는다.
- `CORSMiddleware(allow_origins,allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type'])`: 지정한 origin만 브라우저에서 허용한다. CORS는 인증 수단이 아니다. `WEB_CORS_ORIGINS`는 쉼표 구분 origin.
- Uvicorn `module:app`, `--host 127.0.0.1`, `--port 8000`, `--no-access-log`: 로컬 바인딩 및 URL 접근 로그 비활성화. 요청 본문을 저장하지 않는다. 서버 종료 시 메모리 선택정보도 없어지며 DB가 없다.
- 테스트 `ApiTests`는 unittest/TestClient를 사용한다. `setUpClass`는 .fit을 실패하도록 패치하고 합성 예시만 사용하며 MF 배열 사본을 보관한다. `tearDownClass`는 context/patch 복구. `test_*`는 건강 상태·검색·잘못된 입력·정상 추론·정확한 CLI 동등성·CORS·메타데이터 교집합·읽기전용 배열을 검사한다. subTest는 한 테스트 메서드 안의 여러 조건이다. CLI 동등성은 subprocess로 **추론 명령만** 실행한다. 평가 함수를 호출하지 않는다.

## Frontend

- React `App()`는 단일 페이지를 그린다. `useState`는 선택/질의/검색결과/조건/응답/대기/오류 상태를 메모리에만 유지한다. `useEffect`는 health 조회와220ms 검색 debounce를 실행하고 cleanup에서 타이머/이전 요청을 취소한다. `useRef`는 결과 섹션 scroll 대상이다. `StrictMode`는 개발 모드 부작용 점검용이며 학습을 실행하지 않는다.
- `request<T>(path,init?)`는 API 기준 URL+path로 fetch하며 JSON을 반환한다. 일반 요청은20초 timeout, 검색은 query 변경 시 AbortController로 취소한다. HTTP 오류는 한국어 안내로 변환한다. `T`는 TypeScript 응답형이다.
- `display(value)`는 표시할 때 하이픈을 공백으로 바꾼다. URL ID나 원본 catalog는 변경하지 않는다. `changed()`는 기존 결과를 이전 입력의 결과로 표시한다. `recommend()`는 ratings·required_scent·top_k=5를 POST하고 결과·오류·busy를 갱신한다. `setTimeout`50ms는 결과 DOM 반영 후 scroll 용도다.
- `Perfume`, `Selection`, `Result`, `Scent`는 정적 타입이다. 평점 range는 min0/max10/step.5이며 임의 문자열 입력을 허용하지 않는다. API는 별도로 범위/숫자 검증한다. 빈 선택 시 추천 버튼 비활성화. API 한도와 같은50개를 넘는 추가를 막는다.
- Vite dev 서버는5173 고정, /api를8000으로 proxy. build는 TypeScript 검사와 정적 JS/CSS 번들 생성이다. `VITE_API_BASE_URL`은 빌드시 공개 번들에 들어가므로 비밀을 넣지 않는다.
- Tailwind4 Vite plugin과 CSS import가 스타일을 빌드한다. 추가 CSS는 grid, media query(640/1000px), focus, reduced-motion을 사용한다. 향수병 그림은 CSS 도형이며 외부 이미지/폰트는 요청하지 않는다.
- `qa-mobile.html`은390×844 iframe으로 모바일 CSS를 검사하는 개발 전용 페이지다. Vite 기본 production entry에 포함하지 않는다. 실제 iOS/Android 브라우저 검증을 대신하지 않는다.

이 추가 코드는 자체 작성했다. 기존 추천 orchestration 참고 경로와 라이브러리 문서는 `web/REFERENCES.md`에 기록했다.

`web/verify_integrity.py`는 `before.json`의 경로별 SHA256과 현재 바이트를 비교하고, 기존 freeze의 protected_sha256도 비교한다. 파일을 복구/변경하지 않으며 새 evidence/integrity.json만 기록한다. 성공은 exit0, 변경·누락·freeze 불일치는 exit1이다. hashlib.sha256은 내용 해시, pathlib.Path는 경로 접근, json은 감사 기록 직렬화에 사용한다.
