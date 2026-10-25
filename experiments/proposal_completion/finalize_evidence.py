"""Finish documentation/provenance from saved results only; no fit/score/evaluate calls."""
import ast,json,platform,sys
from pathlib import Path
from xml.etree import ElementTree as ET
from common import ROOT,OUT,load,save,sha,guard

def main():
    """Audit SVG syntax, index final source hashes and describe every new API parameter."""
    guard()
    base=Path(__file__).resolve().parent
    text='''# 보조 실험 방법·API·파라미터 설명

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

'''
    rows=[]
    def walk(nodes,prefix,filename):
        for n in nodes:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                name=prefix+n.name
                if isinstance(n,ast.ClassDef):
                    args='class';desc=ast.get_docstring(n) or '관련 상태·메서드를 묶는 클래스; 생성자는 아래 __init__ 항목 참조.'
                else:
                    args=ast.unparse(n.args) or '(없음)';desc=ast.get_docstring(n) or ('합성 입력의 해당 경계조건/불변성을 검증한다.' if n.name.startswith('test_') else '별도 보조 작업의 엔트리포인트 또는 내부 집계/목록 유틸리티. 위 수식과 호출 모듈 설명을 따른다.')
                rows.append((filename,name,args,desc))
                walk(n.body,name+'.',filename)
    for p in sorted(base.rglob('*.py')):
        walk(ast.parse(p.read_text()).body,'',str(p.relative_to(base)))
    for filename,name,args,desc in rows:
        text+=f'### {filename} — {name}\n\n인자: `{args}`\n\n{desc}\n\n'
    (base/'METHODS_EXPLAINED.md').write_text(text)
    images={}
    for p in sorted((OUT/'figures').glob('*.svg')):
        root=ET.fromstring(p.read_text());images[p.name]={'xml_valid':True,'svg_tag':root.tag,'sha256':sha(str(p.relative_to(ROOT)))}
    sourcepaths=sorted(str(p.relative_to(ROOT)) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    metadata={}
    for path in sorted(OUT.glob('*_run.json')):metadata[path.stem]=json.loads(path.read_text())
    # Current input hashes may be added to an already completed run, explicitly dated.
    fuzzy='fuzzy_match_audit'
    if 'inputs_sha256' not in metadata.get(fuzzy+'_run',{}):
        p=OUT/(fuzzy+'_run.json');d=json.loads(p.read_text())
        inputs=['Term-project-datasets/fra_cleaned.csv','outputs/audit/atrafshan_matching.csv','outputs/audit/external_matching.csv',*[f'Term-project-datasets/{n}.json' for n in ['perfumes','brand','notes','category','season']]]
        d['inputs_sha256']={p:sha(p) for p in inputs};d['provenance_note']='Added2026-10-25 from unchanged baseline inputs; no experiment rerun. Original seconds preserved.'
        save(fuzzy+'_run.json',d)
    save('provenance.json',{'finalized_date':'2026-10-25','python':sys.version,'numpy_version':__import__('numpy').__version__,'source_sha256':{p:sha(p) for p in sourcepaths},'new_api_entries':len(rows),'svg_structure_checks':images,'network_download_install_upload':False,'experiment_rerun_after_integrity_difference':False,'tests':'36 passed; saved tests.log, no test rerun at finalization','scope':'Final documentation/hash-only. Three nonprotected pre-existing runtime/Finder files differ; see integrity_classification.json. Do not claim globally unchanged.'})
    print('API entries',len(rows),'SVG XML checks',len(images),'documentation/provenance only')
if __name__=='__main__':main()
