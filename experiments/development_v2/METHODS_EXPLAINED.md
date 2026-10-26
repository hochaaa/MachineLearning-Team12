# V2 메서드·파라미터 설명

새알고리즘은직접구현했으며외부구현코드를복사하지않았다. V1 normalize/fragrantica, Content/MatrixFactorization/Baseline, ranking_metrics는수정없이호출한다. 수식은reports/V2_IMPLEMENTATION_AUDIT.md에있다. NumPy는array/RNG/linalg.solve/norm으로행렬·ridge를구현하고표준json/csv/pathlib/hashlib는입출력·해시,unittest는합성검증,subprocess는읽기Git명령,sys.addaudithook는금지된파일open차단,resource/time은process메모리/시간에사용한다. 라이브러리참조주소는https://numpy.org/doc/ 와https://docs.python.org/3/library/ 이며이번에네트워크조회하지않았다. 추가패키지/인터넷자료를설치·다운로드하지않았다.

주요공통인자: rows/train=(가명user,canonicalperfume,normalizedrating)관측목록; pool/candidates=정답독립ID목록; catalog/raw=공개향수특성/위치노트; support=알려진향수·평점; answers=평가harness에만허용하는별도정답; config=사전격자/선택receipt; seed=초기화/분할salt; regularization=per-observationL2(새fold-in은n배); k=TopK또는군집과다른이웃수혼동금지; stop_rows=outerfit내별도earlystop정답. self는인스턴스다. 함수signature아래docstring과결과report를함께읽는다.

np.linalg.solve(A,b)는ridge선형시스템해,np.linalg.norm는L2,clip는예측범위,default_rng(seed)는결정초기화,permutation는epoch순서,mean/std/quantile는aggregate및bootstrap,savez/load(allow_pickle=False)는수치모델저장,read_input(kind)는allowlist종류만받는다. apply후V1전역값을monkeypatch하지않는다.

## check_runtime.py::substantive

인자: `result`

Strip nondeterministic timing field for exact regression comparison.

## check_runtime.py::main

인자: ``

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## content_v2.py::ContentV2

인자: `클래스(생성자별도참조)`

Separate accord/note or accord/top/middle/base channels, each unit normalized.

## content_v2.py::__init__

인자: `self, config`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## content_v2.py::fit

인자: `self, catalog, raw, train_items`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## content_v2.py::score

인자: `self, support, candidates`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## data.py::sha

인자: `path`

Hash a permitted/protected file, without interpreting record values.

## data.py::write

인자: `name, value`

Write only under ignored V2 outputs; no absolute destination accepted.

## data.py::read_input

인자: `kind`

Allow train/pool/metadata; legacy validation unlocked only after CV selection receipt.

## data.py::guard

인자: ``

Require development-v2 and original protected19+manifest; never invoke V1 pipelines.

## data.py::bundle

인자: ``

Load unchanged train and content-only metadata, restricting transformed catalog size.

## data.py::histories

인자: `rows`

Group observed train edges only; deterministic item order.

## data.py::hashed

인자: `seed, *parts`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## data.py::known_folds

인자: `train, n=3, seed=12`

Per eligible >=4 train-user hold one different item per fold, retain >=3 support.

## data.py::inner_stop

인자: `train, seed=12`

Nested training-only stop split; no outer CV labels enter early stopping.

## data.py::newuser_folds

인자: `train, pool, n=3, seed=12`

User-group CV: remove entire held users, restrict to learned479-item intersection.

## evaluate_v2.py::evaluate_arrays

인자: `scores_by_user, answers, k=10, relevance=0.7`

Positive-only macro metrics exactly matching V1, plus observed rating-independent coverage.

## evaluate_v2.py::component_scores

인자: `model, content, train, pool, supports=None, regularization=None`

No answer argument. All known users or provided synthetic/new-user support are scored.

## evaluate_v2.py::predictions

인자: `cache, kind='hybrid', config=None`

Return ranked lists and exact fallback counters; ranking IDs are never saved publicly.

## evaluate_v2.py::paired_interval

인자: `left, right, seed=12, draws=2000`

Paired user-bootstrap descriptive delta interval; not independent generalization proof.

## foldin_v2.py::validate_support

인자: `support, catalog=None, required=None`

Reject duplicates, nonfinite/out-of-range values; stable sort assures order invariance.

## foldin_v2.py::fold_in

인자: `model, support, regularization=None`

Joint bias/factor ridge, n*lambda; caller validates catalog identity first.

## foldin_v2.py::score_vector

인자: `model, vector, pool`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## hybrid_v2.py::normalize_scores

인자: `values`

User's current unseen candidate finite scores only; constant→.5, missing→NaN.

## hybrid_v2.py::rank_scores

인자: `values, pool`

Weighted reciprocal rank with offset60; stable canonical ID ties.

## hybrid_v2.py::combine

인자: `c, m, b, pool, config, history_n`

Both components→fusion; one→component; neither→explicit train popularity.

## hybrid_v2.py::ranked

인자: `pool, scores, k=10`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## mf_v2.py::edge_objective_gradient

인자: `p, q, bu, bi, r, mean, reg`

Half squared-error plus half per-observation L2; gradients at old state.

## mf_v2.py::BiasMF

인자: `클래스(생성자별도참조)`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## mf_v2.py::train_mf

인자: `rows, config, seed=12`

Legacy exact baseline; bias candidates stop on a nested train-only split then refit.

## mf_v2.py::__init__

인자: `self, config, seed=12`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## mf_v2.py::fit

인자: `self, rows, stop_rows=()`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## mf_v2.py::raw

인자: `self, u, i`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## mf_v2.py::score

인자: `self, u, pool`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## recommend_v2.py::ServiceV2

인자: `클래스(생성자별도참조)`

Load ignored V2 assets, rebuild fixed train-only content representation, no MF refit.

## recommend_v2.py::demo_support

인자: `service, scenario='mixed'`

Synthetic values on deterministic public catalog IDs; never copied user ratings.

## recommend_v2.py::main

인자: ``

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## recommend_v2.py::__init__

인자: `self`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## recommend_v2.py::recommend

인자: `self, support, condition='none'`

Exactly3 normalized ratings; hard optional metadata filter, deterministic Top5.

## run_experiments.py::access_policy

인자: `event, args`

Block old answer/results files even if accidentally requested by a future code path.

## run_experiments.py::table

인자: `path, rows`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## run_experiments.py::aggregate

인자: `rows`

Mean fold score, explicit sum positive denominators; not pooled independent users.

## run_experiments.py::top_names

인자: `rows, limit=2, exclude=()`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## run_experiments.py::snapshot

인자: ``

Hash tracked V1 code and protected19; stat forbidden data/results without opening them.

## run_experiments.py::record_row

인자: `stage, fold, name, cache, answers, kind='hybrid', fusion=None, **more`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## run_experiments.py::save_model

인자: `model, content, config`

Private V2 model bundle; all output stays ignored and cannot replace V1.

## run_experiments.py::main

인자: ``

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## summarize.py::read

인자: `name`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## summarize.py::rows

인자: `name`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## summarize.py::avg

인자: `data, name, ridge=None`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## summarize.py::mdtable

인자: `data, keys`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## summarize.py::save_report

인자: `name, text`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## summarize.py::main

인자: ``

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## test_v2.py::MathTests

인자: `클래스(생성자별도참조)`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## test_v2.py::setUp

인자: `self`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## test_v2.py::model

인자: `self`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.

## test_v2.py::test_v1_sgd_hand_calculation

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_bias_gradient_finite_difference

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_bias_sgd_update

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_mf_determinism

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_mf_unknown

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_content_idf_train_only

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_content_cosine

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_dislike_changes_direction

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_centered_equal_zero

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_positions_separate

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_foldin_fixed_q_and_stationarity

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_support_permutation

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_input_contract

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_no_known_factor

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_normalization

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_rrf_ties

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_hybrid_weight_fallback

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_tie_order

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_metric_denominator

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_known_cv_disjoint

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_user_cv_disjoint

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_nested_split_no_outer_answer

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_scoring_interface_no_answers

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_input_deny

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::test_access_policy

인자: `self`

가상입력으로이름에표시된조건을검증한다.

## test_v2.py::objective

인자: `z`

V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.
