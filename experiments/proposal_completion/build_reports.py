"""Generate NEW supplementary reports from measured aggregates; never edit old reports."""
from common import *
import ast,inspect
REPORT=ROOT/'reports'
def report(name,text):
    """Write only this stage's uniquely named report; existing original files protected by baseline."""
    path=REPORT/name
    if str(path.relative_to(ROOT)) in load('outputs/proposal_completion/before_sha256.json'):raise RuntimeError('Refuse overwrite pre-existing report')
    path.write_text(text,encoding='utf-8')
def mdtable(rows,keys=None):
    """Render aggregate rows as Markdown, sanitizing newlines and pipe delimiters."""
    if not rows:return '(N/A)'
    keys=keys or list(rows[0]);s='| '+' | '.join(keys)+' |\n|'+'---|'*len(keys)+'\n'
    for row in rows:
        s+='| '+' | '.join(str(row.get(k,'')).replace('|','/').replace('\n',' ') for k in keys)+' |\n'
    return s

def main():
    p=load('outputs/proposal_completion/parfumo_summary.json'); ks=load('outputs/proposal_completion/knn_selection.json'); sparse=load('outputs/proposal_completion/knn_sparsity.json');km=load('outputs/proposal_completion/kmeans_summary.json');f=load('outputs/proposal_completion/fuzzy_summary.json');su=load('outputs/proposal_completion/supplementary_summary.json')
    knn=read_csv('outputs/proposal_completion/knn_validation.csv');clusters=read_csv('outputs/proposal_completion/kmeans_clusters.csv');grid=read_csv('outputs/proposal_completion/kmeans_grid.csv')
    header='기준일 2026-10-23, STEP4-1.5. 기존 최종 모델·웹·Test 결과를 변경하지 않은 **동결 후 독립 보조 실험**이다. 출처 경로는 프로젝트 루트 기준. 개인정보/사용자ID/개별 평점은 이 보고서에 없다.\n\n'
    baseline=[
      {'항목':'Parfumo','작업 전':'파일만 존재, 분석 미실행','근거':'reports/FINAL_PROJECT_READINESS_AUDIT.md; rg: scripts/src 내 교차검증 구현 없음','이번 처리':'신규 metadata-only 분석'},
      {'항목':'User/Item kNN','작업 전':'독립 memory-CF 구현/결과 없음','근거':'src/perfume/models.py; improvements.py; 기존 지표 method 목록','이번 처리':'별도 min3 train/validation 비교'},
      {'항목':'K-means','작업 전':'Proposal optional, 미실행','근거':'Proposal §4/6; 기존 src/scripts 검색','이번 처리':'별도 accord 군집화'},
      {'항목':'Fuzzy','작업 전':'unique normalized exact만 사용, 후보/수동검증 없음','근거':'src/perfume/data.py::match; outputs/audit/*matching.csv','이번 처리':'unmatched catalog 후보 리뷰만'},
      {'항목':'Global-Mean','작업 전':'구현·결과 있음','근거':'models.py::Baseline.fit; evaluation.py::rating_errors','이번 처리':'재구현/재평가 없음'},
      {'항목':'MAE/RMSE','작업 전':'validation/internal 저장 결과, external N/A','근거':'outputs/improvement/validation_rating_errors.json; outputs/final/internal_rating_errors.json','이번 처리':'저장값 복사, 분모 차이 명시'},
      {'항목':'Constraint satisfaction','작업 전':'3규칙 각1680/1680','근거':'outputs/validation/knowledge_rules.csv; scripts/diagnostics.py','이번 처리':'과거 기능검증임을 표시해 재사용'},
      {'항목':'0점','작업 전':'의미미확정·제외분석가정·포함민감도 존재','근거':'reports/ZERO_POLICY.md; PROJECT_DECISIONS.md §9','이번 처리':'기존 근거 유지, 새 의미 확정 없음'},
      {'항목':'Season/Price','작업 전':'개발 카탈로그 신뢰 필드 없어 disabled','근거':'models.py::knowledge; Fragrantica schema','이번 처리':'479후보 metadata 필드 감사'}]
    report('PROPOSAL_COMPLETION_BASELINE_AUDIT.md','# Proposal 보완: 작업 전 기준 감사\n\n'+header+mdtable(baseline)+'''

원본 `AGENTS.md`, `PROJECT_DECISIONS.md`, `REQUIREMENTS_TRACEABILITY.md`, Proposal Word OOXML, `professor_spec.pdf` p2–9, STEP4-1 세 보고서와 기존 MODEL_IMPROVEMENT/ZERO_POLICY 및 CSV/동결 코드를 확인했다. 교수 PDF의 두 필터링 범주·별도 테스트 출처·최종 자료 요구와 사용자/Proposal의 추가 약속을 구분한다. 웹·kNN·K-means의 특정 성능은 교수 필수 목표가 아니다.

환경: 기존 `web/backend/.venv` Python3.12.14 / NumPy2.3.5. SciPy/sklearn/matplotlib/RapidFuzz 없음. **설치 없이** NumPy·표준 라이브러리로 직접 구현했고 기존 `normalize/identity/fragrantica/evaluate`만 읽기 재사용했다. 외부 네트워크·다운로드·업로드 없음.

최종 동결 설정 min3, MF4/160/.01/.01/seed12, Content .25+MF .75 및 후보479는 보호한다. 입력 baseline은 `outputs/proposal_completion/before_sha256.json`。시작 `integrity.py before`가 manifest와19개 hash를 검사했다. 기존 작업 경로 밖에만 새 코드를 두고 새 보고서명으로 작성했다. 기존 traceability 문서의 ‘미실행’은 당시 기록이므로 덮어쓰지 않고 신규 SUMMARY로 상태를 보완한다.
''')
    agree=[{'field':g,**v} for g,v in p['agreement'].items()]
    strict=[{'field':g,**v} for g,v in p['agreement_explicit_concentration'].items()]
    report('PARFUMO_CROSSCHECK_REPORT.md','# Parfumo 메타데이터 교차 검증\n\n'+header+f'''판정: **PARTIAL** — 실제 매칭·노트/어코드 비교를 완료했지만 다수 상품의 농도·연도 가용성 및 사이트 어휘 차이로 동일 상품/의미를 완전 검증하지 못했다.

## 데이터·매칭

Fragrantica 24,063행 / Parfumo **{p['rows']:,}행**, Brand/Name/Release_Year/Concentration/Main_Accords/Top_Notes/Middle_Notes/Base_Notes가 비교 필드다. 정제본 CSV를 읽기만 했고 모델에 추가하지 않았다. source: `Term-project-datasets/fra_cleaned.csv`, `parfumo_data_clean.csv`; local classroom permission은 사용자 확인, 공개재배포 권한은 별도 미확정 (`REFERENCES.md`, `data/README.md`)。

대소문자·악센트·공백·구두점은 기존 normalize를 쓰며 eau de toilette/parfum은 edt/edp 토큰으로 보존한다. 브랜드 alias·약어 확장·fuzzy·Rose/Bulgarian Rose 의미 병합은 하지 않는다. 양쪽 normalized brand/name가 각각 단일 행인 경우만 연결하고, 명시 concentration/flanker 충돌 및 양쪽 알려진 연도 불일치는 제외한다. 농도 미표시는 unknown이다. ‘accepted’는 기계적 분석 대상이지 수동 동일성 인증이 아니다.

{mdtable([{'stage':k,'Parfumo rows':v} for k,v in p['match_status_rows'].items()])}

연결 **7,456건**, 전체 Parfumo 대비 **{100*p['accepted_fraction_all_parfumo_rows']:.4f}%**. normalized identity key {p['normalized_identity_keys']:,}개, 중복 추가 행{p['duplicate_identity_rows']}개({100*p['duplicate_identity_rows']/p['rows']:.3f}%), 중복그룹 소속 행{p['rows_in_duplicate_identity_groups']}개. 같은 이름의 농도 버전 때문에 중복이 생길 수 있으므로 삭제/대표 선택하지 않고 모호 그룹 전체를 제외했다. 명시 버전 충돌 수는 {p['match_status_rows'].get('version_conflict',0)}이다. 이름 exact라도 연도충돌1,036건이 있어 무조건 동일 상품으로 간주할 수 없다.

## 결측

{mdtable([{'column':k,'missing_fraction':v} for k,v in p['missing_fraction'].items()])}

NA/unknown/nan/empty를 결측으로 계산했다. Release_Year 결측34.25%, Concentration78.96%, Main_Accords45.68%이다. 데이터 수집일·원 사이트 정의/현존 데이터 일치는 이번 오프라인 분석에서 UNKNOWN이다.

## 노트·어코드 일치도

Top/Middle/Base의 쉼표 단위 phrase를 합집합으로 비교한다. 위치별 역할 차이는 평가하지 않는다. Jaccard=교집합수/합집합수. **양쪽 비어 있지 않은 쌍만** 평균/정확 일치율 분모로 사용한다. 양쪽 empty를100%로 계산하지 않는다. exact는 두 토큰 집합이 동일하다는 뜻이다. fra_only/parfumo_only는 상품별 고유 토큰 개수의 평균이다.

{mdtable(agree)}

농도 태그가 양쪽에 명시된 연결은 **{p['concentration_explicit_both']}건**뿐이다. 보수적 보조 subset의 결과:

{mdtable(strict)}

이 subset도 독립 수동 상품 검증이 아니고 작은 선택 집단이다. 전체 연결의 높은/낮은 평균을 Fragrantica 정확도 또는 어느 사이트의 정답률로 해석하지 않는다. Parfumo의 ‘Spicy’와 Fragrantica ‘warm spicy/fresh spicy’처럼 taxonomy 차이, 세부 산지 노트, 결측 및 향수 reformulation 가능성이 차이에 기여할 수 있다. 이는 가설이며 모든 제품에 대한 인과검증은 아니다.

불일치 공개 상품 예시: `outputs/proposal_completion/parfumo_disagreement_examples.csv`。향수명과 두 노트 목록만 있고 사용자 정보는 없다. 동의어 매핑은 **빈 테이블(없음)**이다. 비교 상세 `parfumo_comparisons.csv`, 집계 `parfumo_summary.json`, 그림 `figures/parfumo_agreement.svg`。추천 품질·개인화 정확도·독립 rating Test를 대체하지 않는다. 기존 Content IDF/벡터는 변경하지 않았다.
''')
    comparison=[]
    orig=read_csv('outputs/improvement/frozen_results.csv')
    for r in orig:
        if r['split']=='validation':comparison.append({'method':r['method']+' (stored frozen)','neighbors':'N/A','precision':r['precision'],'recall':r['recall'],'ndcg':r['ndcg']})
    for m,r in ks['selected'].items():comparison.append({'method':m+'_knn (post-freeze exploratory)','neighbors':r['neighbors'],'precision':r['precision'],'recall':r['recall'],'ndcg':r['ndcg']})
    table('knn_and_saved_validation.csv',comparison)
    report('KNN_SUPPLEMENTARY_EXPERIMENT.md','# kNN 보조 validation 비교\n\n'+header+'''판정: **PASS (보조 구현·실행 범위)**. 기존 최종 Hybrid/MF를 대체하거나 Test 성능을 주장하지 않는다.

## 입력·누수 방지

`outputs/validation/train_exclude_3.json` 330명·538향수·1805평점만 fit에 사용한다. `outputs/improvement/validation.json`168명·168평점은 scoring 후 evaluate에만 전달한다. 후보는 기존 `outputs/improvement/candidates.json`479개, train-seen 제외, Top10 deterministic score desc/원본 canonical ID asc. relevance .7, positive-user137/제외31, P hits/10·Recall hits/positive·binary NDCG는 기존 `src/perfume/evaluation.py::evaluate` 재사용이다. 후보밖 validation정답도 기존처럼 miss다. 새 per-user 결과/ID를 파일에 저장하지 않고 aggregate만 기록한다. Internal/External answer 파일을 열지 않는다. 다른 보조 모듈이 읽은 기존 aggregate Test 지표는 kNN에 전달하지 않는다.

## 알고리즘

`knn_baselines.py::KNN.fit/similarity/predict`。사용자 u,v의 공통 관측 I에 대해서만 cosine=Σr_ui r_vi / (sqrtΣr_ui² sqrtΣr_vi²). n<2 또는 norm0이면 유사도0. 그 외 n/(n+5) shrinkage를 곱한다. item-based는 같은 수식을 공통 **사용자** 위에서 계산한다. 미관측을 실제0점으로 학습하지 않으며 observed0도 저장할 수 있다. 자기 자신을 제외한다.

User-based는 후보 상품을 평가한 다른 사용자 중 유사도 상위k명의 weighted rating mean, item-based는 사용자 known향수 중 후보와 유사한 상위k개의 weighted rating mean이다. 양의 유사도만 사용하며 부족하면 있는 이웃만 사용한다. 분모0이면 **train log1p-popularity**로 fallback한다. 이는 순수 kNN만의 성능이 아니라 명시된 fallback을 포함한 운영 정책이다. rating mean과 popularity가 같은 [0,1]이라도 분포 calibration은 같지 않아 fallback이 ranking에 미치는 영향도 크다.

공통 관측 최소2/shrink5는 제한된 탐색 범위를 위해 사전 고정했다. 이웃5/10/20만 validation에서 비교한다. 동점 최선은 작은k 선택. 사후 추가된 탐색이므로 이 validation 수치를 새로운 독립 최종 성능으로 주장하지 않는다.

## 실행 지표

'''+mdtable(knn,['mode','neighbors','precision','recall','ndcg','fallback_candidate_fraction','mean_used_neighbors'])+'\n\n동일 평가 조건에서 읽은 기존 결과와 비교:\n\n'+mdtable(comparison)+f'''

## 희소성

User pair {sparse['user']['pairs']:,} 중 공통 평가 없음 **{100*sparse['user']['pairs_with_no_overlap_fraction']:.2f}%**, valid neighbor 없는 train사용자 {sparse['user']['entities_without_valid_neighbors']}/330명. Item pair {sparse['item']['pairs']:,} 중 공통 사용자 없음 **{100*sparse['item']['pairs_with_no_overlap_fraction']:.2f}%**, valid neighbor 없는 향수 {sparse['item']['entities_without_valid_neighbors']}/538개. 사용자당 평균{ sparse['user']['mean_observations_per_entity']:.4f}평점, 향수당{ sparse['item']['mean_observations_per_entity']:.4f}평점. 분포 전체 `knn_sparsity.json`。

User k5의 모든 후보 fallback 사용자39/168명, Item k5는6/168명이다. 후보 점수79,216개 중 fallback User90.46%/Item93.70%로 직접 이웃 증거가 있는 점수는 소수다. 결과1개도 이웃이 없는 **전체 train entity** 비율과 **평가 사용자의 후보별 fallback** 비율은 다른 분모다.

기존평가사용자는 train에 존재한다. 신규user support만으로 기존 train과 비교하는 선택 인퍼런스 함수는 합성 테스트했지만 별도 실제 신규 사용자 성능은 **N/A**다. MF fold-in을 kNN에 적용하지 않았다. min_common=2 때문에3향수 입력 사용자가 충분한 공통 이력을 갖지 못할 수 있다.

## 해석·산출물

User 최고 NDCG {ks['selected']['user']['ndcg']:.6f}, Item {ks['selected']['item']['ndcg']:.6f}; 모두 기존 Hybrid .043185보다 낮다. Item이 기존 MF validation .023056보다 조금 높지만 동일 Test로 검증된 개선이 아니며 통계적 우위를 주장하지 않는다. 검증용 cohort는 같아 표 병기는 가능하지만 탐색 시점과 선택편향을 설명해야 한다. 새 결과가 더 좋았어도 최종 모델 변경은 금지다.

`knn_validation.csv`, `knn_selection.json`, `knn_sparsity.json`, `knn_and_saved_validation.csv`, `figures/knn_validation.svg`, `knn.log`。코드 내 assertions로6설정의168명·Top10 unique·479소속·seen제외·positive137을 검사했다. 테스트의 입력 파일 allowlist 및 train-only fit signature로 정답 경로를 점검한다.
''')
    reps=read_csv('outputs/proposal_completion/kmeans_representatives.csv')
    report('KMEANS_CLUSTERING_REPORT.md','# Accord 기반 탐색적 K-means\n\n'+header+f'''판정: **PASS (탐색 분석 범위)**. 추천 성능 개선/필터 대체가 아니다.

## 데이터·방법

Fragrantica24,063개, 원본 상위5 accord의 존재를 **84차원 binary multi-hot**으로 만든다. all-zero는 제외 정책이며 실제 제외{km['missing_all_accords_excluded']}개. 기존 TF-IDF는 읽거나 바꾸지 않았다. 큰 토큰 빈도 때문에 Euclidean k-means가 흔한 accord에 지배될 수 있고 multi-hot의 희소/고차원 특성이 한계다.

`kmeans_analysis.py::kmeans`: NumPy kmeans++ D² 가중 초기화, n_init3(초기화 seeds12/13/14), Lloyd assign/mean, max_iter100, center shift tolerance1e-5. 각k의3실행 중 inertia최소 선택. empty center는 현재 가장 먼 점으로 다시 초기화하며 실제 선택 실행의 empty reseed0이다. k=3/4/5/6/8을 비교했다. silhouette은 seed12로 고정 추출한800개 상품에서 Euclidean pair distances로 정확 계산한 **sample score**이며 전체24,063개 silhouette은 아니다. rating·Test/validation label을 사용하지 않는다.

{mdtable(grid)}

가장 높은 표본 silhouette은 **k={km['selected']['clusters']} / {km['selected']['sample_silhouette']:.6f}**. 값이 낮으므로 명확한 자연 향 계열을 발견했다고 과장하지 않는다. 군집 수는 표본 내부 탐색 선택이며 confidence interval/다른seed 안정성 연구는 하지 않았다. 학술적 탐색용이다.

## 군집 특징

{mdtable(clusters)}

Cluster0 aromatic90.37%/woody71.16%/fresh spicy60.29%, Cluster1 sweet99.42%/fruity57.25%, Cluster2 woody51.72%/powdery42.54%/floral42.39%이다. 이는 측정된 중심 빈도로 붙이는 설명이지 전문가 향 계열 정답이 아니다. Cluster2는 혼합적이고 within-radius가 더 커 다양성을 보인다. 각 군집의 distinct accord pattern수도 표에 포함했다.

대표 향수는 중심과 squared Euclidean 거리가 작은5개(동점canonical ID 정렬)이며 사용자 선호가 높은5개가 아니다:

{mdtable(reps,['cluster','brand','name','squared_distance_to_center'])}

## 시각화·한계

`figures/kmeans_sizes.svg`, `kmeans_silhouette.svg`, `kmeans_pca.svg`; grid/cluster/representative CSV와 `kmeans_summary.json`。PCA는 전체 multi-hot covariance의 고유분해로 축을 정하고 동일800표본을 투영했다. PC1 {100*km['pca_explained_fraction'][0]:.2f}% / PC2 {100*km['pca_explained_fraction'][1]:.2f}%, 합 {100*sum(km['pca_explained_fraction']):.2f}% 분산만 설명한다. 2차원에서 겹치거나 떨어진 모양이 원래84차원 분리를 보장하지 않는다. 더 세부 노트, weighted features, 안정성/전문가 검토는 후속 분석이며 이번 final ranking에는 반영하지 않았다.
''')
    fs=[{'source':s,**v['statuses'],'existing_exact':v['existing_exact_accepted'],'analyzed':v['unmatched_or_ambiguous_analyzed'],'generated_ge_072':v['candidate_generated_score_ge_072']} for s,v in f['sources'].items()]
    allkeys=['source','existing_exact','analyzed','generated_ge_072','HIGH_CONFIDENCE_CANDIDATE','REVIEW_REQUIRED','VERSION_CONFLICT','BRAND_CONFLICT','NO_SAFE_CANDIDATE']
    report('FUZZY_MATCHING_AUDIT.md','# Fuzzy 매칭 후보 분석\n\n'+header+'''판정: **PARTIAL** — 후보·충돌 탐색 완료, 독립적인 수동 동일성 검증은 미완료다. 최종 매칭 반영0건.

## 범위와 기존 매칭

Atrafshan source catalog1,369개 기존exact827/미승인542개, Basenotes 유효 catalog39,697개 기존exact7,686/미승인32,011개를 분석했다. **Basenotes7,686은 전체 Fragrantica catalog와의 기존 정확 매칭 수**로, 외부평가479후보의 rated source overlap64나 factor overlap70과 다르다. 외부 평점 파일은 읽지 않고 `perfumes/brand/notes/category/season` metadata 및 기존 `external_matching.csv`만 읽었다. 이 분석으로 외부 Test cohort/정답/479pool을 늘리지 않는다. Parfumo fuzzy는 선택사항으로 이번에는 수행하지 않았다.

## 후보 생성·안전 정책

`fuzzy_match_audit.py::ratio/classify`: 기존 normalize(농도 보존) 후 **exact-normalized 동일 브랜드** 안에서만 difflib.SequenceMatcher, autojunk=False로 이름순서·토큰정렬 두 문자열 ratio의 큰 값을 사용한다. minimum .72, high .94 및 차순위와 margin≥.08. 이 threshold는 identity 인증 정확도로 교정된 수치가 아니라 리뷰 우선순위 규칙이다. 유사 브랜드만 있으면 BRAND_CONFLICT로 분류하고 cross-brand 후보는 생성하지 않는다. 이름4자 미만은 safe후보 아님. 약어/새 브랜드 alias 사전을 추가하지 않았다.

EDT/EDP/EDC/Parfum/Extrait 명시 차이와 Elixir/Intense/Extreme/Sport/Limited 비대칭은 VERSION_CONFLICT. 명시농도가 한쪽에만 있으면 REVIEW_REQUIRED다. 숫자·연도 토큰을 삭제하지 않으며 Basenotes launch_date의 연도(분석 대상23,093개 알려짐)를 Fragrantica 알려진Year와 비교해 차이는 REVIEW_REQUIRED로 둔다. Atrafshan은 별도 출시연도 근거가 없어 UNKNOWN이다. 동점/작은 margin은 REVIEW_REQUIRED. explicit 농도·flanker 사전 외의 제품명 차이는 string score만으로 의미를 보장하지 못한다.

{mdtable(fs,allkeys)}

점수≥.72의 same-brand top후보는 **3,547개**(313+3,234), 그 중 HIGH_CONFIDENCE203개(19+184), VERSION_CONFLICT173개다. generated 수에는 짧은 이름 때문에 NO_SAFE인2개도 포함돼 상태별 ‘안전 후보’ 합과 같지 않다. 한 source당 top1 후보를 CSV에 기록하고 second-best gap을 저장한다. 대체 후보 전부의 검토나 최적 브랜드 매칭은 하지 않았다.

## 검증 상태·결과

모든행 `manual_status=NOT_MANUALLY_VERIFIED`, `applied_to_frozen_data=false`。HIGH_CONFIDENCE도 수동확정 아님. 대표 검토 목록 `outputs/proposal_completion/fuzzy_candidates_review.csv`에는 공개 향수명·브랜드·source연도·target이름·ratio/margin·판정·이유만 있고 사용자/리뷰는 없다. 542+32,011행이며 원본 평점 데이터 복제는 없다. `fuzzy_summary.json`, `figures/fuzzy_status.svg` 참조.

기존 exact는 high precision 지향이지만 missed aliases/reformulation이 있을 수 있다. fuzzy는 표기 차이 후보 탐색에 유용하지만 버전·동명이품·불명연도·잘못된 원본명을 해결하지 않는다. 전문/팀 수동검토와 별도 ground truth 없으므로 precision/recall·매칭확대 후 추천성능은 **N/A**다. 기존 map/train/model/Test에는 반영하지 않았으며, 반영하려면 동결 후 실험과 구분한 새 프로토콜을 승인받아야 한다.

`development_initial/`의 첫 개발 결과는 Basenotes 출시연도 사용 전 기록이다. 최종 근거는 최상위 fuzzy_summary/CSV/log이며 출시연도 확인으로 high후보가217→184로 줄었다. 이 수정은 새 후보 분석 코드에만 적용됐고 기존 매칭은 바뀌지 않았다.
''')
    report('SUPPLEMENTARY_METRICS_AUDIT.md','# 보조 지표·0점·Season/Price 감사\n\n'+header+'''판정: **PARTIAL** — 기존 지표 근거는 확인됐으나0의미와 신뢰할 개발 season/price는 해결되지 않았다. 수치 재평가 없이 저장 결과를 재사용했다.

## Global-Mean 및 observed-rating 오차

`models.py::Baseline.fit`는 train 평균 μ를 저장하고 `evaluation.py::rating_errors`는 normalized [0,1]에서 MAE=Σ|y−ŷ|/N, RMSE=sqrt(Σ(y−ŷ)²/N)을 계산한다. Global-Mean은 모든 관측에 μ를 예측하는 rating baseline이고 Popularity는 log1p(count) ranking baseline이다. Global-Mean 모든상품 동점 NDCG를 임의로 추가하지 않았다.

'''+mdtable(su['rating_errors'],['split','model','n','mae','rmse','source'])+'''

MF는 trained factor가 있는151개, Mean은 전체168개로 **분모가 달라 위 표만으로 같은 정답에서의 직접 오차 우열을 확정하면 안 된다**. 기존 `outputs/improvement/mf_diagnostics.csv`에는 validation 동일151개에서 MF RMSE .209817 / Mean .185777인 진단이 있다. 외부MAE/RMSE는 의미 동등성 미확인으로 N/A 유지. 원점수0–10/0–9와 normalized[0,1] 추천점수를 무변환 비교하지 않는다.

## 제약 만족률 (기존 기능 검증)

'''+mdtable(read_csv('outputs/proposal_completion/saved_constraint_satisfaction.csv'))+'''

조건별168요청, returned1680/satisfied1680/violation0/empty0, 만족률1.0. `outputs/validation/knowledge_rules.csv`의 **이전 단계 validation 기능검증**이며 최종 동결 성능의 새 재평가가 아니다. scripts/diagnostics.py는 당시 잠정선택 모델을 사용했으므로 이를 ‘최종모델168명재검증’으로 쓰지 않는다. CSR=satisfied/returned, returned0이면N/A; 개인 선호 정확도가 아니다. 웹의 4조건 합성 goldens는 별도 기존 증거다.

## Atrafshan0

기존원본README/논문 조사 기록은 `reports/ZERO_POLICY.md`/`REFERENCES.md`에 있다.0=최저선호 또는미평가를 확정한 수집코드는 확보되지 않았다. 6882scent평점 중1309개0, 나머지5573. 원래0의미를 확인하지 못한 상태에서 사용자가0제외를주분석 **가정**으로 승인했고 포함민감도를 유지했다. `zero_joint_distribution.json`의 다른 평가항목 동반패턴은 가설 근거이며 sentinel증명 아님. 이번에는 네트워크를 쓰지 않아 원본사이트/수집코드 추가검증 없음. 모델/정책은 변경하지 않는다.

## 479후보 season/price

Fragrantica 개발CSV 및 FrozenService 카탈로그 경로에서 **Season field없음 / Price field없음**. 신뢰할 개발값을 제공하는 후보 0/479(0%)이며, 관측된 값이0이 아니라 필드 미가용이라는 뜻이다. 통화·용량 N/A, 수집시점 UNKNOWN. Basenotes에는 seasons/price가 있으나 외부 테스트 metadata만으로 개발필터를 활성화하지 않는다. 사이트/통화/병용량/수집시점/동일상품 확인이 있는 독립 개발용 메타데이터를 확보하기 전에는 **계속 disabled**. 이번 웹에는 추가하지 않았다.

기존0포함 민감도 cohort 설명은 `ZERO_POLICY.md`에 공통비0≥5집단을 사용했다고 명시돼 있다. STEP4-1 팩트 시트의 ‘포함/제외 cohort가 달라 완전비교가 아님’ 문장은 그 문장만으로 현재 민감도 프로토콜을 설명하기에 부정확하다. **저장된 코드/manifest를 우선**해야 하며, 이 보조 단계의 kNN은0제외 min3 공통168명만 사용한다. 이전 보고서는 사용자 제한에 따라 덮어쓰지 않았다.
''')
    changes=[{'항목':r['항목'],'작업 전':r['작업 전'],'작업 후':({'Parfumo':'PARTIAL: 7456연결 및 comparable notes5996/accords6383 분석','User/Item kNN':'PASS: 각3개 k validation비교; 최종모델유지','K-means':'PASS: k3선택·84차원·24063개 탐색','Fuzzy':'PARTIAL: 3547후보/203high, 수동검증0·반영0'}.get(r['항목'],'기존근거 재사용/가용성 감사; 미확정 의미 유지')),'증거':r['이번 처리']} for r in baseline]
    report('PROPOSAL_COMPLETION_SUMMARY.md','# Proposal 보완 결과 요약\n\n'+header+'''## 1. 전체 결과

| 항목 | 판정 | 범위 |
|---|---|---|
| Parfumo cross-check | PARTIAL | 비교 실행완료, 농도/어휘/연도 동일성 제한 |
| User-Based kNN | PASS | train-only + validation 탐색 완료 |
| Item-Based kNN | PASS | train-only + validation 탐색 완료 |
| K-means | PASS | metadata-only 탐색 완료 |
| Fuzzy Matching | PARTIAL | 후보분석 완료, 수동 검증 미완료 |
| 추가 지표 | PARTIAL | 기존지표 재사용,0의미/season/price 미해결 |

PASS는 해당 보조 작업의 구현/실행/검증을 뜻하며 추천 성능 개선이나 교수 최종제출 전체준수를 뜻하지 않는다. Proposal 원본·기존 traceability/팩트 시트/최종Word/PPT는 수정하지 않았다.0처리 결정이나 최종 MF/Hybrid도 바꾸지 않았다.

## 2. Proposal 대비 변화

'''+mdtable(changes)+f'''

## 3. 실제 핵심 결과

- Parfumo59,325행 → 보수적exact7,456건(12.5681%). 노트비교5,996쌍 Jaccard .544477, exact8.2055%; 어코드6,383쌍 Jaccard .217660, exact.1410%. 농도양쪽명시98건뿐으로 semantic identity보장불가.
- kNN k5/10/20, overlap≥2, shrink5: User최고NDCG **{ks['selected']['user']['ndcg']:.6f}**(k5), Item **{ks['selected']['item']['ndcg']:.6f}**(k5). 기존 MF .023056/Hybrid .043185는 저장 validation값. User90.46%/Item93.70% 후보 fallback. Test 검증은 하지 않음.
- Accord K-means24,063개/84차원, 비교k3/4/5/6/8 중k3 silhouette **.106647**(고정800표본). sizes7693/7235/9135. aromatic/woody/fresh-spicy, sweet/fruity, 혼합woody/powdery/floral 빈도 패턴. PCA2축23.84%만설명. 실제 scent family정답 아님.
- Fuzzy: Atrafshan미승인542개와Basenotes32,011개 분석, score≥.72 후보313+3234=3547, high19+184=203, versionconflict31+142=173. 수동검증/기존반영 모두0.
- 기존 Global-Mean·MAE/RMSE·규칙별1680/1680 CSR 재사용. 최종후보479개 개발season/price가용값0, 계속비활성.0평점1309개 의미UNRESOLVED.

## 4. 기존 모델과의 관계·안전

기존 Hybrid .25Content+.75MF / min3 / MF4·160·.01·.01·seed12 및479pool **유지**. 기존Internal/ExternalTest 결과 **유지**. 새 kNN은 동결후 사후 탐색, Parfumo는 메타데이터 agreement, K-means는 탐색적 군집, fuzzy는 후보리뷰만이다. 다른모델·데이터의 새Test가 아니며 최종Hybrid를 새결과로 재선택하지 않았다. oldMF fit/score/fold-in/evaluation/diagnostics를 실행하지 않았다.

실험환경 Python3.12.14/NumPy2.3.5, 설치0, 네트워크0, 서버제어0, commit/push0. 실행명령/실행시간/seed/입력SHA는 `outputs/proposal_completion/*_run.json`。각독립명령및설명은 `experiments/proposal_completion/README.md`, 신규 API/수식/파라미터는 같은폴더 `METHODS_EXPLAINED.md`, 출처·차용범위는 `REFERENCES.md`。

`outputs/proposal_completion/integrity_after.json`은 기존모든snapshot(가상환경/cache 제외), protected19, manifest를검증한다. manifest SHA256 `3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130`。새테스트 로그 `tests.log`, 기존원본/웹/결과 변경경로가 있으면 즉시중단하도록guard한다.

## 5. Word·PPT 반영

| 등급 | 내용 | 이유 |
|---|---|---|
| MAIN | 최종동결성능·선택근거/한계 | 프로젝트코어; 새결과로대체금지 |
| MAIN(짧게) | kNN validation표+fallback비율 | memory/model CF차이 및 희소성 설명, post-freeze명시 |
| APPENDIX | Parfumo coverage/Jaccard/결측/농도98subset | consistency는보여주되정답품질로과장금지 |
| APPENDIX | k3 cluster빈도·size·PCA/silhouette | optional탐색, 약한분리명시 |
| APPENDIX | fuzzy상태표와버전충돌사례 | 수동미검증/반영0을설명 |
| APPENDIX | mean오차/CSR/zero/season-price | 기존있던근거와미가용항목구분 |
| OMIT | fuzzy정확도/매칭확대후성능/새kNNTest | 실행·검증안함 |
| OMIT | season/price작동·실사용만족·전문가군집 | 데이터나근거없음 |

## 6. 남은 작업·우선순위

1. **높음/팀입력**: 실제역할·기여율·개인학습·수업외기법·GitHubURL·발표일/제출경로확인. 기존모델변경필요없음.
2. **높음/최종자료**: STEP4-1 팩트시트+이번보조결과로 최종Word/PPT를새로작성. 기존Word/PPT는과거잠정수치가있어최종본아님. 기존모델변경필요없음.
3. **중간/수동매칭**: 버전·연도·브랜드를확인할 source상품근거및팀검토필요. 후보검토가능하나이번frozen학습/외부Test에소급반영금지.
4. **중간/Parfumo동일성**: 농도/연도 결측보완과정의일치·동의어사전이필요. 이번cross-check결과는그한계를유지하며 별도metadata연구만가능.
5. **낮음/zero**: 원본collector/form semantics가필요,현재로컬문서로미확정.새근거확보전제외가정유지;현재모델변경안함.
6. **낮음/season-price**: 개발/추론용신뢰필드,통화/용량/수집일·권한필요.기능추가는별도승인범위,이번미구현.
7. **후속발표준비**: 실제offline/projector/10분리허설,최종렌더QA와11/9제출증거확인.추가모델실험우선아님.

## 7. 신규 산출물 목록

'''+mdtable([{'path':str(q.relative_to(ROOT))} for folder in [ROOT/'experiments/proposal_completion',OUT] for q in sorted(folder.rglob('*')) if q.is_file() and 'development_initial' not in q.parts and q.name not in ['before_sha256.json']])+'''

이 문서 포함 신규 보고서7개: `PROPOSAL_COMPLETION_BASELINE_AUDIT.md`, `PARFUMO_CROSSCHECK_REPORT.md`, `KNN_SUPPLEMENTARY_EXPERIMENT.md`, `KMEANS_CLUSTERING_REPORT.md`, `FUZZY_MATCHING_AUDIT.md`, `SUPPLEMENTARY_METRICS_AUDIT.md`, `PROPOSAL_COMPLETION_SUMMARY.md`。각 상세 보고서와 README를 함께 읽는다. `development_initial/`은 새 코드 개발 중 첫 결과를 보존한 기록이며 최종 표는 최상위 CSV/JSON만 사용한다.
''')
    finalization_notice=REPORT/'PROPOSAL_COMPLETION_FINALIZATION.md'
    if finalization_notice.exists():
        p=REPORT/'PROPOSAL_COMPLETION_SUMMARY.md'
        p.write_text(p.read_text()+'\n\n최종확인·무결성예외: PROPOSAL_COMPLETION_FINALIZATION.md를반드시함께참조.\n')
    print('Seven new reports written; old reports guarded against overwrite.')
if __name__=='__main__':main()
