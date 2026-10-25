# 알고리즘과 라이브러리 설명

수업에서 배웠는지 팀 확인 전까지 아래 구성요소를 모두 설명 대상으로 취급한다. Knowledge-Based가 수업 외 기법이라는 사실도 **미확인**이다. 전체 함수/클래스/메서드 실제 signature와 docstring은 `reports/API_REFERENCE.md`에 소스에서 자동 추출한다. 구현 파라미터는 `configs/experiment.json`, 실행값은 `outputs/validation/run_metadata.json`으로 연결된다.

## 모델의 의미와 식

**Content.fit(catalog, train_items)**: catalog는 item→{name,brand,tokens}, train_items는 fit이 허용된 train 향수 ID다. comma로 구분된 노트 phrase를 `note:`, 어코드는 `accord:` namespace로 분리한 binary multi-hot을 사용한다. 어휘를 train 향수에 한정한다. IDF(t)=log((1+n)/(1+df(t)))+1, 이후 문서별 L2 정규화한다. 외부/검증 전용 단어는 OOV로 사라진다. 희소 dict로 저장해 전체 dense item×vocab 행렬을 만들지 않는다.

**Content.score(support,candidates)**: support는 (item,0..1평점) 목록이다. 각 향수의 정규화 벡터를 max(0,rating) 가중합한 뒤 정규화해 후보 문서와 cosine을 계산한다. 낮은 비영점 평점도 작은 양의 가중치를 주는 초기 설계이며 불호를 음수 벡터로 빼는 모델은 구현하지 않았다. support가 없거나 전부 0/OOV이면 NaN으로 명시해 폴백한다. 후보군에 정답을 별도 주입하지 않는다.

**MatrixFactorization**은 희소 user/item/rating 관측 edge list(COO에 해당)를 사용한다. 전체 결측행렬을 채우지 않는다. 사용자 latent P, 상품 latent Q만 학습하며 bias/평균 centering은 넣지 않았다. 목적함수는 관측별 1/2[(r-p·q)^2+λ(||p||²+||q||²)]의 합이다. 이 L2는 관측마다 부과되므로 관측 빈도가 높은 벡터에 더 큰 전체 regularization이 작용한다. proposal의 bias-free 식을 이 해석으로 구현했다.

잔차 e=r-p·q. 이전 p,q를 복사한 뒤 p←p+η(e q-λp), q←q+η(e p_old-λq)로 동시에 갱신한다. 매 epoch 고정 seed RNG로 관측 순서를 섞는다. factors=8/12는 latent 차원, epochs=80/100은 관측 전체 반복 수, learning_rate=.025는 step 크기, regularization=.03/.05는 shrinkage, seed=12는 초기화와 순서 재현값이다. train에서만 fit한다. loss는 regularization 포함 관측 평균으로 저장한다. 추천용 예측은 0..1 clip하며 rating scale 밖 예측을 억제하지만 clipping tie가 생길 수 있다. 동점은 item ID로 결정한다. unknown user/item은 NaN이다.

**fold_in(support)**: 기존 item factor는 고정하고 신규 p만 추정한다. 알려진 train-factor item n개의 행렬 Q_s, 평점 y에 대해 (Q_sᵀQ_s+nλI)p=Q_sᵀy를 푼다. nλ는 위 관측별 L2 목적과 맞춘다. 다른 향수 support는 factor 추정에서 제외하며 알려진 factor가 하나도 없으면 None을 반환한다. 정답 평점과 기존 사용자 ID를 가져오지 않는다.

**Baseline.fit(rows)**: train 관측 수를 item별로 센다. ranking score=log(1+count)/log(1+max_count)이며 인기 비교용이다. rating prediction용으로는 train global mean을 사용한다. 두 baseline을 하나의 의미로 혼동하지 않는다.

**hybrid(content,mf,alpha,fallback)**: αc+(1-α)m. binary positive TF-IDF cosine은 0..1, Atrafshan /10 평점 MF 예측도 clip 후 0..1이다. 이 공통 이론적 범위로 calibration하여 외부 통계를 추정하지 않는다. alpha .25/.5/.75를 개발 validation에서 비교한다. 양쪽 있으면 실제 결합, 한쪽 없으면 나머지, 둘 다 없으면 train popularity다. Pure content/MF 평가에는 이 폴백을 몰래 적용하지 않는다. NaN은 결측이며 0은 유효 점수다.

**knowledge(catalog,candidates,scores,required,forbidden,preferred,soft_weight=.1,season=None,max_price=None)**: required 모든 token 포함(AND), forbidden 어떤 token도 미포함을 hard 조건으로 한다. preferred 중 충족한 비율×soft_weight를 기존 hybrid에 가산한다. family 입력은 `accord:woody`처럼 실제 accord vocabulary로 제한하며 검증하지 않은 향 계열 taxonomy를 만들지 않는다. 반환 설명에 필수조건 충족과 맞은 선호 token을 기록한다. season/max_price는 신뢰 가능한 개발 필드가 없으므로 설정하면 ValueError다. 만족 후보가 없으면 빈 목록을 반환한다.

## 분할과 지표

`partition(rows,seed=12)`는 각 user/item의 hash 정렬로 비영점 >=5 cohort에 validation1/test1/train나머지를 배정한다. rating 값을 보고 긍정만 고르지 않는다. 3~4개 사용자에게 강제로 세 split을 부여하지 않는다. 실제 실험은 비영점 split을 먼저 고정하고 0 포함 시 추가 edge만 train으로 확장해 시나리오 간에도 같은 평가를 유지한다. min threshold는 split 전 유효 고유 평점 수 기준이며 평가 사용자 train은 최소3개다. `assert_disjoint`는 partition 간 user/item 중복이면 ValueError다.

고정 후보 479개는 비영점 >=5 cohort train에 나타난 아이템 집합이다. 모든 시나리오/threshold에 동일하게 사용하며 사용자별 train/support 향수는 제외한다. 후보가 전 카탈로그가 아니므로 결과 범위가 제한된다. 다른 사용자의 학습에 등장하는 동일 상품의 관측은 정상 CF 신호이고, 같은 user/item 정답 누수가 아니다.

`ranking_metrics(ranked,relevant,k=10)`는 binary positives(평점 >=.7)를 기준으로 Precision=hits/k, Recall=hits/긍정 정답수, NDCG=Σ(hit/log2(rank+1))/이상적DCG다. 후보 밖 정답도 recall 분모에 남긴다. 관측되지 않은 향수를 disliked label로 만들거나 rating 손실에 넣지 않는다. 다만 unjudged 후보가 topK에 나오면 observed-positive precision은 낮아지며 실제 선호 전체의 정확도와 다르다. 긍정 정답이 없으면 None으로 두고 대상 수를 보고한다. 지표별 per-user 표준편차와 추천 catalog coverage도 기록한다.

`score_users`는 train/user목록/candidates/model/alpha만 받고 정답 item/value를 받지 않는다. `evaluate`만 정답 label을 읽는다. `rating_errors`는 explicit prediction이 있는 관측에만 MAE=mean|pred-r|, RMSE=sqrt(mean(error²))와 n을 기록한다. content/hybrid를 rating prediction으로 해석하지 않는다. CF와 global mean의 n이 다르므로 직접 우열 비교에 주의한다.

## 데이터와 표준 라이브러리

`data.py`의 path는 입력 파일경로, rows/interactions는 (가명 user,item,0..1 rating) 배열, mapping은 source item→target URL, index는 (normalized brand,name)→target목록이다. zero_policy는 include/exclude만 허용하며 unresolved는 ValueError다. FK directory는 Laure lookup 파일의 디렉터리다. `normalize(text)`는 NFKD accent 분리와 casefold, 정규식으로 공백을 통일하되 농도/버전 단어를 지우지 않는다. cp1252 decode는 대체 문자 없이 strict이며 이 파일의 재현 설정이지 모든 원본에 일반화한 인코딩 추정이 아니다.

- `csv.DictReader(stream,delimiter)`/`DictWriter(stream,fieldnames)`는 헤더 기반 CSV 파싱/출력. delimiter=';'는 Fragrantica의 실제 구분자, 다른 CSV는 기본 comma. newline=''은 CSV 줄바꿈 처리다.
- `json.load(stream)`, dumps(value,ensure_ascii=False,indent=2)는 JSON 입출력과 사람이 읽을 UTF-8 문자열 직렬화다.
- `Path(path)`의 open/read_text/write_text/mkdir(parents=True,exist_ok=True)/iterdir/glob는 경로와 파일 관리. 부모 생성만 하며 원본을 쓰지 않는다.
- `Counter(iterable)`는 빈도, `defaultdict(factory)`는 기본 빈 list/set/float 컨테이너다. union-find는 counts 내부에서 user/item 이분 그래프 연결 성분을 구한다.
- `hashlib.sha256(bytes).hexdigest()`는 입력 해시와 가명 user ID, deterministic split 순서를 만든다. salt가 공개된 고정 prefix이므로 익명성 보장은 하지 않는다.
- `unicodedata.normalize('NFKD',text)`/combining(char)는 accent 분리, `re.findall(pattern,text,flags)`은 Unicode word 추출. `math.log/log1p/sqrt/log2`는 IDF/인기도/L2 norm/discount 계산이다.
- `argparse.ArgumentParser`, add_argument(name,default/choices/type/action/required/help), parse_args는 CLI 입력검증과 도움말. 반복 token은 action='append'.
- `unittest.TestCase` assert*, assertRaises는 합성 fixture의 예상값과 오류 확인. `tempfile.TemporaryDirectory`는 테스트 JSON을 원본과 분리해 자동 정리한다. `ast.parse/unparse/get_docstring`는 소스 구조와 API 설명 추출이다. `platform.python_version()`은 환경 기록이다.
- Python 내장 dict/set/list/tuple은 매핑/고유 집합/순서/관측 레코드다. sorted(key=...)는 재현 가능한 정렬, zip은 후보와 점수 정렬 연결, enumerate는 index 부여, isinstance는 타입검증이다. ValueError/FloatingPointError는 잘못된 계약과 수치 발산을 명시한다.

## NumPy 및 산출물 라이브러리

`np.random.default_rng(seed)`의 uniform(low,high,size)는 latent 초기값, permutation(n)은 epoch shuffle. `np.array(values)`/full(shape,value)/zeros/eye(n)는 관측/결측배열/단위행렬. `@`, `.T`, `.copy()`는 dot/전치/동시 SGD 보존 복사다. `np.linalg.solve(A,b)`는 inverse를 만들지 않고 ridge 선형계를 푼다. isfinite/isnan은 결측 검사, where(condition,a,b)는 폴백, clip(values,0,1)은 이론적 rating 범위 제한. mean/std/abs/square/sqrt는 오차/분산 집계다. std 기본 ddof=0은 평가된 사용자 분포의 기술 통계이며 모집단 유의성 주장이 아니다. savez(path,P,Q)/load(path)는 로컬 잠정 factor 저장/복원. np.testing assert_allclose(rtol,atol)는 수치 잔차 검증이다.

ReportLab Drawing(width,height), Rect(x,y,w,h), String(x,y,text,fontName,fontSize)와 VerticalBarChart.data/categories/valueMin/valueMax/valueStep는 측정 표를 축/단위/출처가 있는 SVG로 만든다. renderSVG.drawToFile(drawing,path)는 벡터 그림 저장이다. Sharp(input).png().toFile(path)는 같은 SVG를 PNG로 변환한다. python-docx는 Word 문단/표/그림을 만들고 bundled LibreOffice 렌더로 확인한다. 이 문서 생성 라이브러리들은 추천 학습이나 평점 생성에 관여하지 않는다.

## 실행 및 문서 작성 스크립트

각 main()은 CLI를 해석해 위 API를 연결하는 인자 없는 진입점이다. audit.py의 --raw는 원본 디렉터리, --output은 집계 경로다. experiment.py의 --config는 seed/K/relevance/MF grid/alpha JSON, --output은 validation 출력 경로다. demo.py의 --scenario는 미확정 include/exclude 민감도 모델, --support는 사용자 입력 JSON, --required/forbidden/preferred는 반복 가능한 exact token, --k는 결과 수, --model-dir은 factor/metadata 경로다. diagnostics.py는 현재 프로젝트 고정 경로로 ID 기반 외부 가능성과 규칙 충족률을 집계한다.

build_report.py의 table(document,headers,rows)는 Word 문서·열 이름·행 기록으로 표를 만든다. Document, add_heading(text,level), add_paragraph(text), add_table(rows,cols), add_picture(path,width), save(path)는 문서 생성 API다. Inches/Pt는 길이/글자 크기 단위, RGBColor는 색, OxmlElement/qn은 문단 테두리·동아시아 글꼴 XML 설정이다. 시각화에만 쓰며 학습값에 영향을 주지 않는다.

build_deck.mjs의 text(slide,value,left,top,width,height,size,bold,color)는 textbox를 배치한다. slide(title,body,notes)는 본문과 발표 시간·출처를 포함한 speaker notes를 만든다. Presentation.create(slideSize)는 픽셀 너비/높이, theme.defaultFont/typeface는 글꼴, charts.add(type,config)는 실측값을 담은 편집 가능한 차트다. position/categories/series/hasLegend/yAxis.numberFormatCode는 위치·범주·계열·범례·소수점 축 서식이다. export({slide,format,scale})는 검토 이미지, PresentationFile.exportPptx/save는 Office 파일 저장이다. finalizePresentation은 파일 구조/배치/글꼴/차트 workbook/import를 검사하고 새 출력에 저장한다. 원본 수치 정확성이나 PowerPoint 실제 실행까지 보장하지 않는다.

## 모델 개선과 동결 평가 추가 설명

ProfileContent(mode='rating',relevance=.7)는 기존 TF-IDF를 유지하면서 프로필 가중치만 바꾼다. rating은 기존 max(0,r), liked는 r>=relevance만, centered는 r-support평균이다. centered cosine [-1,1]은 (score+1)/2로 calibration한다. norm이0이면 NaN이며 pure content에서 몰래 폴백하지 않는다. relevance는 train/validation에서 정한 고정 긍정 기준이다.

BiasedMatrixFactorization은 동일한 factors/epochs/learning_rate/regularization/seed 인자를 쓴다. 예측은 μ+bu+bi+p·q이며 μ는 train 평균이다. 목적은 관측별 1/2[(r-예측)^2+λ(||p||²+||q||²+bu²+bi²)]의 합이다. p,q의 이전 값을 이용해 simultaneous SGD, bu←bu+lr(e-λbu), bi←bi+lr(e-λbi)를 쓴다. μ는 학습 중 고정이다. bias와 factor의 L2를 같은 λ로 묶은 제한된 실험이다. factor 초기화는 평균0/표준편차.05인 Gaussian으로 잔차를 표현한다. bias 없는 기존 모델과 초기화도 다르므로 순수 bias 효과의 인과적 ablation이라고 부르지 않는다. 이번 범위에서 채택되지 않았다.

Biased MF fold_in(support)는 A=[Q_support,1]로 새 user factor와 bias를 함께 푼다. y=r-μ-bi, (AᵀA+nλI)x=Aᵀy. 기존 Q/bi/μ는 고정하고 support에 factor가 없는 아이템은 제외한다. score_vector의 vector는 [latent,user_bias]이며 마지막 원소가 bias다. 기존 bias 없는 MF는 latent만 쓴다. 최종 선택 모델은 bias가 없다.

make_mf(parameters,seed)는 parameters.kind에 따라 legacy/biased 모델을 생성한다. src/perfume/frozen.py의 sha256(path)는 파일 바이트 무결성, load_frozen(directory)는 freeze 해시와 saved model/vocabulary를 확인해 복원하며 fit을 호출하지 않는다. ndarray.flags.writeable=False로 factor/bias 수정도 막는다. score_frozen(support,candidates,mf,content,baseline,alpha,k,user=None)는 user가 있으면 기존 내부 사용자, None이면 신규 사용자 support-only fold-in이다. 반환은 pure component/popularity/hybrid별 ranking이며 정답 레코드를 인자로 받지 않는다.

external_partition(pairs,factor_items,min_history=3,seed=12)는 **값이 없는** (가명user,canonicalitem) 목록으로 split한다. 아이템 hash순서 앞 floor(n/2)를 support, 나머지를 answer ID로 한다. 이력3개 미만 또는 factor support가 없는 사용자는 구조적 제외다. 실제 평가에서는 canonical 중복 pair를 평점값과 무관하게 격리했다. 외부 사용자의 평점은 원래 보고된0..9 ordinal 범위라는 가정에 따라 /9 변환하며, positive는 normalized>=.7이다. 범위에 맞지 않는 값이 있으면 외부평가를 중단하도록 사전 규정했다. 외부 점수로 scale/threshold를 다시 fit하지 않는다. 척도 의미의 동등성이 검증되지 않아 외부 MAE/RMSE는 N/A로 둔다.

scripts/improve.py는16개 MF 설정×threshold3개를 검사하고 순수MF에서 기존보다 높은 설정만 교체 후보로 둔다. Hybrid에는 기존 MF도 유지하고 profile3종×alpha5개를 비교한다. 기존 전체최선보다 높지 않으면 기존 파이프라인을 유지한다. tests/외부 파일을 읽지 않는 튜닝 진입점이다. scripts/freeze.py는 train-only 재현학습과 transformer 저장 후 해시를 동결한다. scripts/final_evaluate.py는 동결검증 후 open('x') 평가 ledger를 만들어 재실행을 거부한다. 내부/외부 성능을 확인한 뒤에도 모델 설정을 고치지 않는다.

aggregate_with_intervals(predictions,answers,k,relevance,seed)는 고정 user별 결과를2000번 복원추출해 mean NDCG의2.5/97.5 percentile을 기술적 구간으로 저장한다. np.random.default_rng(seed).integers(0,n,size=(2000,n))가 bootstrap user index다. 작은 외부 표본·선택 편향·매칭 불확실성을 해결하거나 유의한 모델차를 증명하는 검사는 아니다. reports/MODEL_IMPROVEMENT.md는 이 한계를 명시한다.

scripts/demo_frozen.py의 --support/required/forbidden/preferred/k는 이전 CLI와 같은 입력 의미다. 동결된479개 candidate에서만 추천하며 fit하지 않는다. scripts/report_improvements.py의 records(path)는 저장된 CSV를 읽고 md_table(headers,rows)는 Markdown 표, main()은 실측 CSV만으로 결과표·ReportLab 그래프를 만든다. scripts/render_figures.mjs의 선택 positional directory는 해당 SVG 디렉터리를 PNG로 변환한다. 보고서 생성과 그림 렌더는 모델 재선택을 하지 않는다.
