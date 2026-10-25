"""Read new V2 aggregates only, write minimal new reports; never open V1 Test files."""
import json,csv,ast
from pathlib import Path
from collections import defaultdict
import numpy as np
from data import ROOT,OUT,write,sha,guard

def read(name):return json.loads((OUT/name).read_text())
def rows(name):
    with (OUT/'metrics'/name).open() as f:return list(csv.DictReader(f))
def avg(data,name,ridge=None):
    v=[float(r['ndcg']) for r in data if r['name']==name and (ridge is None or float(r.get('ridge',-1))==ridge)]
    return float(np.mean(v)) if v else None

def mdtable(data,keys):
    out='| '+' | '.join(keys)+' |\n|'+'---|'*len(keys)+'\n'
    for row in data:
        out+='| '+' | '.join(f'{row[k]:.6f}' if isinstance(row.get(k),float) else str(row.get(k,'N/A')).replace('|','/') for k in keys)+' |\n'
    return out

def save_report(name,text):
    p=ROOT/'reports'/name
    if p.exists():raise RuntimeError('Do not overwrite an existing report: '+name)
    p.write_text(text)

def main():
    guard();meta=read('models/model.json');sel=meta['config'];recipe=sel['selected_recipe'];name=recipe['name'];cn,mn=recipe['content'],recipe['mf'];ridge=sel['foldin_regularization']
    content=rows('content_cv.csv');mf=rows('mf_cv.csv');hybrid=rows('hybrid_cv.csv');val=rows('legacy_validation.csv');nu=rows('newuser_cv.csv');stable=rows('seed_stability.csv');runtime=read('diagnostics/runtime_checks.json');folds=read('audit/fold_receipts.json');run=read('experiments/run_complete.json')
    cv=[];validation=[];newusers=[]
    specs=[('V1 Content','v1_content','v1_content','v1_content',.01),('Content V2',cn,cn,name+'__content',.01),('V1 MF','v1_mf','v1_mf','v1_mf',.01),('MF V2',mn,mn,name+'__mf',ridge),('V1 Hybrid','v1_hybrid','v1_hybrid','v1_hybrid',.01),('Hybrid V2',name,name,name,ridge)]
    for label,cvname,valname,nuname,nureg in specs:
        source=content if 'Content' in label else mf if 'MF' in label else hybrid
        cv.append({'model':label,'mean_fold_NDCG@10':avg(source,cvname)})
        validation.append({'model':label,'NDCG@10':float(next(r['ndcg'] for r in val if r['name']==valname))})
        newusers.append({'model':label,'mean_fold_NDCG@10':avg(nu,nuname,nureg),'ridge':nureg if 'Content' not in label else 'N/A'})
    write('metrics/final_comparison.json',{'known_user_cv':cv,'legacy_validation':validation,'newuser_cv':newusers,'not_generalization_test':True,'adopt_for_v1_website':False})
    base=next(r for r in validation if r['model']=='V1 Hybrid')['NDCG@10'];v2=next(r for r in validation if r['model']=='Hybrid V2')['NDCG@10']
    cvbase=avg(hybrid,'v1_hybrid');cvv2=avg(hybrid,name)
    audit=[
      {'ID':'L1','type':'LIMITATION','evidence':'models.py::Content.score','finding':'max(0,r) means low positive rating still attracts related notes;0 means no content evidence'},
      {'ID':'L2','type':'LIMITATION','evidence':'models.py::hybrid','finding':'common[0,1] bounds do not align score variances; alpha.25 is not25% of ranking influence'},
      {'ID':'L3','type':'LIMITATION','evidence':'models.py::MatrixFactorization.fit','finding':'bias-free positive initialization and very sparse data limit residual representation; not incorrect SGD'},
      {'ID':'L4','type':'LIMITATION','evidence':'models.py::MatrixFactorization.fit','finding':'L2 applied per observation, degree-weighted aggregate penalty; mathematical definition must be explicit'},
      {'ID':'L5','type':'LIMITATION','evidence':'models.py::score_vector','finding':'clipping may create tied ranks, deterministic URL tie break can dominate'},
      {'ID':'L6','type':'LIMITATION','evidence':'evaluation.py::ranking_metrics/evaluate','finding':'positive-only macro metrics on479candidate pool, incomplete feedback; conditional denominator'},
      {'ID':'L7','type':'LIMITATION','evidence':'models.py::fold_in + web/backend/app.py','finding':'primitive ignores unknown factor items/does not reject duplicates; API rejects duplicate/catalog-invalid requests before fold-in'},
      {'ID':'I1','type':'IMPROVEMENT','evidence':'content_v2.py','finding':'independent accord/note and top/middle/base channels'},
      {'ID':'I2','type':'IMPROVEMENT','evidence':'content_v2.py','finding':'signed neutral(.5)/user-mean preference profiles and explicit zero norm'},
      {'ID':'I3','type':'IMPROVEMENT','evidence':'mf_v2.py','finding':'global mean+user/item bias; nested-stop epochs, bounded factors/L2 grid'},
      {'ID':'I4','type':'IMPROVEMENT','evidence':'hybrid_v2.py','finding':'candidate-only minmax/RRF/history-weight fusion with explicit fallbacks'},
      {'ID':'I5','type':'IMPROVEMENT','evidence':'foldin_v2.py/data.py','finding':'joint bias/factor ridge and strict normalized3support contract; entire-user holdout tuning'},
    ]
    write('audit/v1_findings.json',{'BUG':0,'LIMITATION':7,'IMPROVEMENT':5,'scope':'No reproducible arithmetic bug found in audited paths; not a proof of all-code bug absence','findings':audit})
    header='STEP5, Development V2。既存V1/Test/웹은변경하지않았으며 최종Word/PPT는작성하지않았다. 이문서는새V2aggregate만읽어작성했다. 사용자ID·개별평점은기재하지않는다.\n\n'
    save_report('V2_IMPLEMENTATION_AUDIT.md','# V1 정밀 감사 및 V2 구현\n\n'+header+'''## 판정과 핵심5가지

**실제 BUG0 / LIMITATION7 / IMPROVEMENT5**. 추측을 BUG로 분류하지 않았다. 특히1)낮은평점의양의기여,2)score분포미보정,3)bias없는희소MF,4)clipping동점,5)3support 신규사용자와 기존사용자 학습차이가 중요하다. SGD부호·동시업데이트·ridge nλ는 손계산/유한차분/정상조건 테스트와 일치했다. V1은 유효한 구현이며 일부 설계가 제한적이라는 결론이다.

'''+mdtable(audit,['ID','type','evidence','finding'])+'''

## 실제 수식·입력 경계

V1 IDF=ln((1+N)/(1+df))+1, binaryTF×IDF 후 itemL2정규화. support 가중합 profile을 L2정규화해 cosine. TFIDF fit은train상품만, 하위평점도 r>0이면같은토큰방향으로더해진다. 빈/OOVprofile은NaN이다. V1 MF는 per-observation e²+λ(||p||²+||q||²), oldp/q로η(eq−λp)/η(ep−λq); loss에비해gradient상수2는η에흡수됐다. V1 fold-in=(AᵀA+nλI)^−1Aᵀy, Q불변. V1 API는평점0–10을/10, 중복/범위/ID를검증하고479후보만사용한다. primitive를APIvalidation과구분해야한다.

V2는각accord/note또는accord/Top/Middle/Base채널을train-only IDF로각각정규화한후channelcosine가중평균. rating은 r, neutral은r−.5, centered는r−mean(r). signedcosine은(1+cos)/2. profile norm<1e-12면해당채널미가용, 이용가능channelweight합으로다시나눔. 전체미가용이면NaN/fallback. equal.5 neutral/centered는zero이며 임의좋아함을만들지않는다.

BiasMF 예측 μ+b_u+b_i+pᵀq, μ=train평균. 목적1/2[e²+λ(||p||²+||q||²+b_u²+b_i²)], gradient(e q+λp,e p+λq,e+λb_u,e+λb_i) with e=prediction−rating. Gaussian(0,.05)초기화. 예측에만[0,1]clip. bias도per-edgeλ. nestedtrain split의RMSE로10epoch마다검사, min_delta1e-5/patience3, max120; bestepoch를정한후outerfit전체로refit. outerCV정답·기존validation·Test는epoch선택에들어가지않는다.

V2 fold-in의A=[qᵀ,1], y=r−μ−b_i, z=(AᵀA+nλI)^−1Aᵀy. Q/item bias/μ고정이며 latentp와userbias만추정한다. V1/새MFuser-IDmapping을신규ID에이식하지않는다. duplicates/unknown/out-of-range/bool/NaN/Inf/입력부족을ValueError처리하고sort하여입력순서bitwise불변이다.

Fusion은 linear / finitecandidate별minmax / weightedRRF61/(60+rank) / alpha=3/(3+history_count). rank동점은canonicalID. history3에서는alpha=.5. 평가정답 없이현재unseencandidate점수만사용한다. 양쪽유효fusion, 한쪽미가용이면다른성분, 둘다미가용이면trainpopularity. minmaxconstant→.5. score는확률아니다.

## 독립성·테스트

`experiments/development_v2/`만새소스, `outputs/development_v2/`만새모델/실험. V1소스/웹/구성/.gitignore/원본/기존분할/manifest수정0. 구체적입력allowlist와Pythonopen audit hook가기존Test정답/평가결과를차단한다. 기존freeze/model/content파일의read는19보호해시계산용이며기존model을복원/재학습한것이아니다. V1기준방식은독립CV/validationtrain으로별도복제학습해비교한다.

`tests/test_v2.py`:25합성단위테스트PASS(손계산SGD, finite-differencegradient, IDF/cosine, profilezero/dislike, 정규화/RRF, ridge정상조건/Q불변, 분할/허용입력/분모). `check_runtime.py`:20정상scenario×condition,8비정상입력거절, reload동일성/입력순서불변/Q불변. 기록 `audit/unit_tests.log`, `audit/runtime_tests.log`, `diagnostics/runtime_checks.json`。실제사용자만족도연구는아님. train전체학습모델에서syntheticCLI동작을검사한것이지Test정확도검사가아니다.

V1감사범위에서재현되는산술BUG는없으므로BUG재현입력표는N/A이다. rootV1문서와코드는고치지않았다. 사용한NumPy/표준라이브러리 및각새API인자는새폴더METHODS_EXPLAINED.md참조.
''')
    byseed=[]
    for seed in [12,29,47]:
        src=hybrid if seed==12 else [r for r in stable if int(r['seed'])==seed]
        byseed.append({'seed':seed,'V1_Hybrid':avg(src,'v1_hybrid'),'V2_Hybrid':avg(src,name)})
    save_report('V2_EXPERIMENT_RESULTS.md','# V2 실제 실험 결과\n\n'+header+f'''## 탐색 범위·선택 시점

seed12,3fold. Content9설정→27fold평가, MF9설정(기준1+bias8)→27fold평가. factor2/4/8/16×L2.01/.1, lr.01, biasmax120/nestedstopping, V1f4/160固定。Content상위2와biasMF상위2만fusion10설정각각비교(40후보+V1baseline). 모든선택은train-CV이고 legacyvalidation을반복사용하지않는다. bias/별도채널V2challenger를의도적으로비교하는탐색으로, baseline수식을복잡한것으로강제교체할근거가아니다.

CV선택 **{name}**: Content=neutral/accord.5+note.5, MF=bias factor8/lr.01/L2.01, fulltrainnested선택epoch**{sel['final_epochs']}**, fusionRRF Content.25+MF.75. ridge는전체사용자제외CV로**{ridge}** 선택. 원래최대epoch120과실제로refit한30을구분한다. 모델/레시피는models/model.npz·model.json·content_recipe.json에저장했다.

## Fold 조건

'''+mdtable(folds,['protocol','fold','train_users','train_items','train_ratings','evaluation_users','positive_users','candidates','heldout_ratings'])+'''

Known CV는trainhistory≥4의187명, 각fold서로다른1개정답/최소3train. 143명은3평점뿐이어서train전용. train1618평점/330명,479고정후보. fold별trainedcandidate469/467/471, 후보밖positive6/6/11은miss처리, 미학습MFitem은NaN(순수MF제외, hybrid다른성분fallback). denominator155/154/154명. fold별train item520–522개에서만IDFfit한다. 세fold같은사용자이므로서로독립인561사용자처럼해석금지.

신규user CV는187eligible사용자를hash순3그룹으로나누어그룹전체평점을MF/Content/Popularity학습에서완전히제외한다. fold별candidate는479∩해당foldtraineditems424/423/433. candidate 내history≥4인경우hash순support3/나머지heldout, 142명(48/50/44)생존,133명(46/47/40)이positive.45명은factor/candidatecoverage후4개미만이라제외. support426개·heldout603개. support는inferenceprofile/fold-in에만, heldout은harness에만. ‘support는fold-in에만’은학습금지경계로해석하며Hybrid Content프로필에도동일known support를사용한다. 공정한Content/Hybrid비교에필요한추론입력이지MF학습에포함되는것이아니다. 143lowhistory사용자는이평가적격집단에서제외되지만foldfit에는남는다. support1–2보조실험은142명확보되어미실행.

## 비교표 — 서로다른프로토콜을분리

### Train내부 known-user CV (fold평균)

'''+mdtable(cv,['model','mean_fold_NDCG@10'])+'''

### 기존 validation (168명중positive137명,479후보)

'''+mdtable(validation,['model','NDCG@10'])+'''

### Train내부 신규사용자CV / support3 (fold평균)

'''+mdtable(newusers,['model','mean_fold_NDCG@10','ridge'])+f'''

표의ContentV2/MFV2는최종challengerHybrid의구성요소이고, MFV2신규평가는선택된ridge1.0을사용한다. ContentV2신규점수는ridge와무관하다. 개별모델·Hybrid·각grid의P@10/R@10/NDCG/coverage/fallback은metrics/*.csv。knownCV와신규CV는pool과사용자가다르므로열사이숫자를동일실험처럼직접차감하지않는다.

## Validation 접근과 Test 방화벽

knownCV+newuserCV가끝난후selection_locked.json작성, seed29/47검사도고정설정만사용. 그후배타적legacy_validation_started.json을만들어기존validation파일을**1번**읽었다. final run의read receipt는experiments/run_complete.json. primary **.032808**보다secondary position_neutral **.035865**가높아도validation을보고교체하지않았다. V1 .04318527363105539 /Content .028903258240656326 /MF .023056323965736755가재현됐다. legacyTest정답/개별결과파일은열지않았다. 기존집계Test숫자는알려진배경일뿐V2선택에사용하지않았다.

## Seed 안정성과 불확실성

'''+mdtable(byseed,['seed','V1_Hybrid','V2_Hybrid'])+'''

knownCV primaryfold평균은+0.004514, legacyvalidation은−0.010377, 신규userCV는−0.015157이다. seed별알고리즘초기화변화만측정했으며splitseed는고정했다. 신규user시뮬레이션의여러seed추가검증은미실행이다. 반응이좋아보이는seed로선택을바꾸지않는다.

CV bootstrap파일은각사용자의positivefold평균을동일가중으로계산한**별도estimand**다.182명user-macrodelta+.000404,95%descriptive interval[−.017709,.017301]로0을포함. 이것을primaryfold-macro+0.004514의CI로제시하면안된다. validation paired137명delta−.010377, interval[−.035621,.011901]. 이미사용한validation·다중CV탐색후선택이라는한계가있어유의한일반화개선/비열등성을주장할수없다. outerknownCV RMSE/MAE는별도산출하지않았고nestedstop RMSE만loss_curves에있다. 이들의분모가다름을명시한다.

## 실행·런타임

학습/검색 실제시간 {run['seconds']:.3f}초. Python3.12.14/NumPy2.3.5, 추가설치없음, 원본재다운로드없음. 입력/codehash·seed/lock/receipt가저장됐다. `run_experiments.py`의run_startedreceipt가불필요한재탐색/overwrite를거절한다. 실행실패시기존V1파일을수정해서해결하지않는다.

Modelload {runtime['load_seconds']:.6f}s, 추천median {runtime['recommend_seconds_median']:.6f}s/p95 {runtime['recommend_seconds_p95']:.6f}s, fold-in median {runtime['foldin_seconds_median']:.8f}s, peakprocessRSS {runtime['peak_process_rss_bytes']}bytes(별도모델만의메모리크기아님).20정상/8비정상행동테스트통과. 최적화이전V2성능baseline은없고동일scalar산술의일치만확인했으므로‘속도개선’이라쓰지않는다.
''')
    save_report('V2_FINAL_COMPARISON.md','# Frozen V1 / Development V2 최종 판단\n\n'+header+f'''**권고: V1 웹사이트/동결모델 유지. V2는 독립 실험 모델로만 보관.**

- train내부known-userCV: V1 {cvbase:.6f} → V2 {cvv2:.6f}, 관측개선있음.
- 기존validation: V1 {base:.6f} → V2 {v2:.6f}, 개선없음.
- 신규user support3: V1 .047663 → V2 .032505, 악화. Content/MF구성요소는소폭올랐어도fusion이개선을보장하지않는다.
- seed12/29/47 knownCV경향은일관적이지만신규사용자·재사용validation실패를상쇄하지않는다.
- 통계적으로충분한일반화개선은확인하지못했다. 독립Test를V2에서실행하지않았다.

가능한가설은knownuser latent학습과newuser ridge차이,rankfusion의절대선호강도손실/동점,채널profile의분포차이,희소성·매칭pool선택이다. 인과분리ablation을추가로하지않았으므로실패원인으로확정하지않는다. validation실패후추가튜닝을하지않는다.

세비교표와P/R/coverage/분모/seed는V2_EXPERIMENT_RESULTS.md및outputs/development_v2/metrics/참조. 기존동결Test성능은재확인하거나선택에사용하지않았으므로새V1–V2Test비교표는N/A다. V2기준모델파일은저장됐지만V1대체승인은별도다.

## 보호·Git

작업브랜치development-v2, 기준commit aebd9abd85b175e6076d8b2d9c2445201d8b2602。trackedV1소스와protected19의시작/종료SHA동일, manifest 3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130 유지. 기존데이터/평가결과/웹은stat-only비교도변경0(금지된정답/결과내용은열지않음). 이전단계.DS_Store/demo.log변경이력을이번변경으로소급하지않았다. baseline재설정아님. 기존보고서는덮어쓰지않았다.

새소스experiments/development_v2/는검토후Git대상, outputs/development_v2/의모델·사용자매핑·새CV/실험결과는ignore유지·강제추가금지. reports/V2_*.md도기존ignore유지. commit/push/merge/rebase/tag/remote설정/외부업로드0, 기존서버종료0. 최종Git상태는untracked V2소스만이어야하며승인전스테이징하지않는다.

## 남은 문제 우선순위

1. 웹교체보류: 신규사용자·validation개선이없어적용근거부족. 이번validation을다시튜닝에사용하지말것.
2. 다음연구는새사전계획하에새개발분할/새독립평가를확보하고rankfusion/평점정규화/신규사용자calibration가설을검토. 기존Test를더읽지말것.
3. smallcohort·single splitseed·knownCV선택편향·colditemcoverage를명시. outerCV MAE/RMSE/각user다양성은추가공정프로토콜로만분석가능.
4. 실제사용자입력은synthetic행동검증까지이며실제만족도연구/웹연결아님. seed별newuser추가평가도미실행.
5. 공개소스license/README·팀역할/개인소감·Git승인은별도과제로남음. 최종Word/PPT는이번범위아님.
''')
    # Explain all newly introduced APIs without modifying root methods/provenance documents.
    api='''# V2 메서드·파라미터 설명\n\n새알고리즘은직접구현했으며외부구현코드를복사하지않았다. V1 normalize/fragrantica, Content/MatrixFactorization/Baseline, ranking_metrics는수정없이호출한다. 수식은reports/V2_IMPLEMENTATION_AUDIT.md에있다. NumPy는array/RNG/linalg.solve/norm으로행렬·ridge를구현하고표준json/csv/pathlib/hashlib는입출력·해시,unittest는합성검증,subprocess는읽기Git명령,sys.addaudithook는금지된파일open차단,resource/time은process메모리/시간에사용한다. 라이브러리참조주소는https://numpy.org/doc/ 와https://docs.python.org/3/library/ 이며이번에네트워크조회하지않았다. 추가패키지/인터넷자료를설치·다운로드하지않았다.\n\n주요공통인자: rows/train=(가명user,canonicalperfume,normalizedrating)관측목록; pool/candidates=정답독립ID목록; catalog/raw=공개향수특성/위치노트; support=알려진향수·평점; answers=평가harness에만허용하는별도정답; config=사전격자/선택receipt; seed=초기화/분할salt; regularization=per-observationL2(새fold-in은n배); k=TopK또는군집과다른이웃수혼동금지; stop_rows=outerfit내별도earlystop정답. self는인스턴스다. 함수signature아래docstring과결과report를함께읽는다.\n\nnp.linalg.solve(A,b)는ridge선형시스템해,np.linalg.norm는L2,clip는예측범위,default_rng(seed)는결정초기화,permutation는epoch순서,mean/std/quantile는aggregate및bootstrap,savez/load(allow_pickle=False)는수치모델저장,read_input(kind)는allowlist종류만받는다. apply후V1전역값을monkeypatch하지않는다.\n'''
    for path in sorted(Path(__file__).parent.rglob('*.py')):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
                params=ast.unparse(node.args) if isinstance(node,ast.FunctionDef) else '클래스(생성자별도참조)';doc=ast.get_docstring(node) or ('가상입력으로이름에표시된조건을검증한다.' if node.name.startswith('test_') else 'V2모듈의구성/점수/집계유틸리티. 상위수식과호출부참조.')
                api+=f'\n## {path.name}::{node.name}\n\n인자: `{params}`\n\n{doc}\n'
    (Path(__file__).parent/'METHODS_EXPLAINED.md').write_text(api)
    print('Three NEW V2 reports and local API explanations written; no V1 reports/results opened.')
if __name__=='__main__':main()
