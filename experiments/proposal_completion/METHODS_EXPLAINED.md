# 보조 실험 방법·API·파라미터 설명

최종 정리 2026-10-25. 이 문서는 이번 단계의 새 코드만 설명한다. 원래 모델 설명은 루트 METHODS_EXPLAINED.md이며 수정하지 않았다. 아래 함수 목록은 AST로 현재 소스에서 추출했다. 테스트는 가상 데이터 전용이고 실제 user ID를 문서에 저장하지 않는다.

## 데이터 흐름과 수식

Parfumo: unique(normalize(brand), normalize(name)) key 연결 → 농도/버전/알려진연도 충돌제외 → notes/accords phrase set → J=|A∩B|/|A∪B|. 양쪽 nonempty일 때만 평균. empty/empty는 None. 별도 synonym 사전 없음. 7456연결은 상품 동일성의 수동 확정이 아니다.

kNN: train 딕셔너리의 co-observed 항목만 cosine을 계산한다. overlap n<min_common2면0, 그렇지 않으면 cosine×n/(n+shrinkage5). mode=user면 다른 사용자의 후보평점, mode=item이면 사용자의 알려진향수 평점을 유사도로 가중평균한다. k=5/10/20은 이웃수이며 ranking K=10과 다르다. 이웃0이면 train log-popularity. neighbors가 부족하면 있는 수만 사용하고 없는 좌표를 평가0점으로 넣지 않는다. new-user support 선택인자는 train 사용자 이력과 직접 비교하는 방식이며 MF fold-in이 아니다. validation은 fit/similarity의 인자가 아니고 score 후 evaluate에만 쓴다. Test 정답 파일은 읽지 않는다.

K-means: 원래 상위5 accord를 84차원 unscaled binary vector로 만들고 Euclidean distance로 군집화한다. kmeans++ D² sampling 후 Lloyd assignment/centroid mean. k=3/4/5/6/8, seed12, n_init3은 seed12/13/14 세 초기화 중 inertia최소, max_iter100, center L2 shift tolerance1e-5. all-zero feature행 제외(실제0건). empty cluster는 현재최장거리점을 재seed. sample silhouette s=(b−a)/max(a,b): a는 같은군집내평균거리, b는다른군집별평균거리의최소. singleton0, 군집하나/모두singleton이면정의불가None. seed12 표본800은 모든k에동일하다. PCA는 centered covariance XᵀX의 eigenvectors 상위2개; 분산설명비는 eigenvalue합 대비. score labels는 쓰지 않는다.

Fuzzy: normalized same-brand 상품만 비교, SequenceMatcher phrase ratio와token-sort ratio의max. autojunk=False. minimum.72, high.94, second-best margin.08. EDT/EDP/Parfum/Elixir등 version/flanker 충돌·year차이·tie를별도분류한다. 높은similarity도실제identity의확률이아니다. year미상은동일연도를증명하지못하고, 수동검증0/최종데이터반영0을명시한다. UNKNOWN농도/오탈자/새로운flanker어휘는남는한계다.

Supplementary: 저장mean/MF errors 및 CSR만읽는다. Mean은관측평점예측, Popularity는ranking이다. MAE=mean(abs(y−prediction)), RMSE=sqrt(mean((y−prediction)²)); y/prediction둘다[0,1]이지만MF의가용관측151개와Mean168개는같은분모가아니다. CSR=satisfied/returned; returned0이면None. 과거규칙테스트를현재frozen모델의새품질평가로표현하지않는다. season/price는개발필드미가용이므로0/479 reliable값이며기능비활성유지.

## 라이브러리·중요 메서드와 파라미터

| 라이브러리/API | 파라미터와 용도 |
|---|---|
| pathlib.Path / resolve / parents / relative_to / rglob | path문자열, parents[2]루트, rglob패턴; 고정ROOT기준 파일접근 |
| Path.open/read_text/write_text | mode/encoding/newline; 입력읽기 및 별도outputs로만쓰기 |
| csv.DictReader/DictWriter | stream,delimiter,fieldnames; CSV를열이름사전으로읽고동일key출력 |
| json.loads/dumps | text/value,ensure_ascii=False,indent=2; 구조를읽기/집계저장 |
| hashlib.sha256 / update / hexdigest | bytes를블록별로hash, 원본내용은출력안함 |
| collections.Counter/defaultdict | iterable 또는 default_factory; 빈도/관측딕셔너리/브랜드그룹 |
| difflib.SequenceMatcher | isjunk=None,a,b,autojunk=False; 결정적문자열ratio |
| difflib.get_close_matches | word, possibilities,n=1,cutoff=.85; 유사브랜드경고만, cross-brand자동연결안함 |
| NumPy array/asarray/zeros/full | shape,dtype; feature/거리벡터. 결측을실제관측0으로학습하는행렬이아님 |
| np.sum/mean/min/max/norm | array,axis; 거리·중심·가중평균·L2크기 |
| np.maximum / clip | array,lower,upper; roundoff음거리방지·범위제한 |
| np.random.default_rng / integers / choice | seed,high,size,replace,p; 초기화/가중D²/고정표본 |
| np.argsort / argmin / bincount / flatnonzero / unique | array,axis,kind='stable',minlength; assignment/안정정렬/군집수/비어있는군집검사 |
| np.linalg.eigh | 대칭covariance행렬; PCA고유값/고유벡터 |
| np.linalg.norm | vector/matrix,axis선택; cosine/center이동크기 |
| np.fill_diagonal | array,val=0; silhouette자기거리0 |
| numpy.testing.assert_* / allclose | actual,expected,atol; 가상테스트 수치/결정성확인 |
| unittest.TestCase / assert* / mock.patch | 테스트이름/실제값/기대값/교체대상; 가상이웃·버전·emptycluster·해시중단분기검증 |
| ast.parse/walk/get_docstring/unparse | Python소스/tree; 함수인자목록·금지Test입력정적검사. 코드실행안함 |
| inspect.signature/getsource | object; fit인터페이스·허용입력검사 |
| html.escape / ElementTree.fromstring | public제목문자열 / SVGtext; XML안전출력·구조검사 |
| time.perf_counter / sys.version | monotonic초차이 / Python버전; 실행증거 |
| sorted/max/min/set/intersection | key/reverse/default; 동점명시순서, 공통관측/버전집합. URL은향수publicID이고사용자ID출력안함 |
| perfume.data.normalize/identity/fragrantica/laure_catalog | 문자열brand/name 또는CSV/metadata경로; 기존함수읽기재사용, 원본코드불변 |
| perfume.evaluation.evaluate | predictions,answers,k=10,relevance=.7; **새kNN만**기존정의로검증, aggregate만보존 |

SVG는패키지설치없이표준XML문자열로작성했다. 과학표현은정적독립SVG파일이며실측aggregate를사용한다. PCA그림은표본scatter로서전체공간분리를보장하지않는다. 신규함수/클래스목록의self는객체자신,main/run/test함수의인자없음은고정설정entry point를뜻한다. *args/**kwargs는테스트mock의전달인자다.

## 새 모듈·클래스·함수·메서드 API

### build_reports.py — report

인자: `name, text`

Write only this stage's uniquely named report; existing original files protected by baseline.

### build_reports.py — mdtable

인자: `rows, keys=None`

Render aggregate rows as Markdown, sanitizing newlines and pipe delimiters.

### build_reports.py — main

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### common.py — load

인자: `path`

Read JSON path relative to ROOT; callers restrict which data they request.

### common.py — save

인자: `name, value`

Save aggregate or public product metadata only under supplementary OUT.

### common.py — table

인자: `name, rows`

Write common-key rows; no individual user histories are allowed as outputs.

### common.py — read_csv

인자: `path, encoding='utf-8-sig', delimiter=','`

Read CSV using explicit encoding and delimiter.

### common.py — fields

인자: `value`

Comma-separated phrases, normalized separately; no semantic synonym merging.

### common.py — jaccard

인자: `a, b`

Intersection/union; both empty is undefined (None), never perfect agreement.

### common.py — versions

인자: `name, concentration=''`

Extract explicit versions; absent tag is unknown, not proof of equivalence.

### common.py — conflict

인자: `a, b`

Known mutually different concentrations or asymmetric flankers reject a link.

### common.py — sha

인자: `path`

Stream SHA256 without exposing input contents.

### common.py — guard

인자: `(없음)`

Raise before work if original frozen19 or known manifest differs.

### common.py — bar

인자: `name, title, labels, values, subtitle=''`

Dependency-free static SVG chart; values are measured aggregates, not user rows.

### common.py — main_run

인자: `fn, name`

Guard, time one independent supplementary command, then guard again.

### finalize_evidence.py — main

인자: `(없음)`

Audit SVG syntax, index final source hashes and describe every new API parameter.

### finalize_evidence.py — main.walk

인자: `nodes, prefix, filename`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### fuzzy_match_audit.py — ratio

인자: `a, b`

Max of phrase/token-sorted character ratios; high score is not identity proof.

### fuzzy_match_audit.py — classify

인자: `brand, name, year, targets`

Return best same-brand candidate, mark version/year conflicts and score ties.

### fuzzy_match_audit.py — main

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### integrity.py — paths

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### integrity.py — main

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### kmeans_analysis.py — distance2

인자: `x, c`

Squared Euclidean point-to-center matrix (nonnegative after roundoff).

### kmeans_analysis.py — kmeans

인자: `x, k, seed=12, n_init=3, max_iter=100, tol=1e-05`

kmeans++ weighted seeding, Lloyd means; empty centers reseed farthest point.

### kmeans_analysis.py — silhouette

인자: `x, labels`

Exact Euclidean silhouette for a fixed sample; singleton score0, undefined→None.

### kmeans_analysis.py — main

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### knn_baselines.py — KNN

인자: `class`

Overlap-only cosine with n/(n+shrinkage); no missing-as-zero interpretation.

### knn_baselines.py — KNN.__init__

인자: `self, mode, k=10, min_common=2, shrinkage=5`

mode user/item; k maximum contributing neighbors per candidate; min_common overlap; shrinkage confidence damping.

### knn_baselines.py — KNN.fit

인자: `self, train`

Store observed edges only; similarities have no validation input.

### knn_baselines.py — KNN.similarity

인자: `self, a, b`

Cosine on co-observed coordinates only; undefined/insufficient overlap→0.

### knn_baselines.py — KNN.predict

인자: `self, user, pool, support=None`

Existing-user inference; optional new support compares to train only. Fallback is train log-popularity.

### knn_baselines.py — main

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### parfumo_crosscheck.py — compare

인자: `a, b`

Comparable iff both have at least one phrase; empty never equals true quality.

### parfumo_crosscheck.py — main

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### supplementary_metrics.py — main

인자: `(없음)`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### tests/test_supplementary.py — MetadataTests

인자: `class`

관련 상태·메서드를 묶는 클래스; 생성자는 아래 __init__ 항목 참조.

### tests/test_supplementary.py — MetadataTests.test_exact_normalization

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — MetadataTests.test_edt_edp

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — MetadataTests.test_elixir_parfum

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — MetadataTests.test_specific_notes_not_synonyms

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — MetadataTests.test_missing

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — MetadataTests.test_jaccard

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — MetadataTests.test_missing_comparison

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests

인자: `class`

관련 상태·메서드를 묶는 클래스; 생성자는 아래 __init__ 항목 참조.

### tests/test_supplementary.py — NeighborTests.setUp

인자: `self`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### tests/test_supplementary.py — NeighborTests.test_no_common

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_missing_not_zero

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_two_common_similarity

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_no_self

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_fallback

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_deterministic

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_only_train_fit_interface

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_no_test_inputs

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_validation_cannot_affect_similarity

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — NeighborTests.test_new_support_is_not_foldin

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests

인자: `class`

관련 상태·메서드를 묶는 클래스; 생성자는 아래 __init__ 항목 참조.

### tests/test_supplementary.py — ClusterTests.setUp

인자: `self`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### tests/test_supplementary.py — ClusterTests.test_reproducibility

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests.test_size_sum

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests.test_distances

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests.test_degenerate_features

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests.test_silhouette_singletons

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests.test_silhouette_separated

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests.test_empty_reseed_branch

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — ClusterTests.test_empty_reseed_branch.forced

인자: `x, c`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### tests/test_supplementary.py — ClusterTests.test_saved_visual_sample

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests

인자: `class`

관련 상태·메서드를 묶는 클래스; 생성자는 아래 __init__ 항목 참조.

### tests/test_supplementary.py — FuzzyTests.targets

인자: `self, *names`

별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.

### tests/test_supplementary.py — FuzzyTests.test_brand_gate

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_cross_brand_candidates

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_version

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_elixir

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_year

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_tie

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_unverified

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_reordered

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — FuzzyTests.test_short_ambiguous

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — IntegrityTests

인자: `class`

관련 상태·메서드를 묶는 클래스; 생성자는 아래 __init__ 항목 참조.

### tests/test_supplementary.py — IntegrityTests.test_current_protected19_and_manifest

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

### tests/test_supplementary.py — IntegrityTests.test_mismatch_stops

인자: `self`

합성 입력의 해당 경계조건/불변성을 검증한다.

