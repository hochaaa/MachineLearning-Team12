"""Generate only NEW STEP8 reports from saved V3 aggregates. Never retune/re-evaluate."""
import json,csv,ast
from pathlib import Path
import numpy as np
from v3_data import ROOT,OUT,save,guard,sha

def load(path):return json.loads((OUT/path).read_text())
def rows(path):
    with (OUT/'metrics'/path).open() as f:return list(csv.DictReader(f))
def avg(data,key):
    v=[float(r[key]) for r in data if r.get(key) not in ('',None)];return float(np.mean(v)) if v else None

def md(data,keys):
    text='| '+' | '.join(keys)+' |\n|'+'---|'*len(keys)+'\n'
    for row in data:text+='| '+' | '.join(f'{row[k]:.6f}' if isinstance(row.get(k),float) else str(row.get(k,'N/A')).replace('|','/') for k in keys)+' |\n'
    return text

def report(name,text):
    p=ROOT/'reports'/name
    if p.exists():raise RuntimeError('Do not overwrite an existing report')
    p.write_text(text)

def main():
    guard();run=load('configs/run_complete.json');locks=load('configs/selections_locked.json');ledger=load('diagnostics/fit_ledger.json');checks=load('diagnostics/post_checks.json');runtime=load('diagnostics/runtime.json');sensitivity=load('diagnostics/input_sensitivity.json');boot=load('diagnostics/paired_bootstrap.json');inner=rows('inner.csv');outer=rows('outer.csv');seed=rows('seed29.csv');known=rows('known_secondary.csv');receipts=load('diagnostics/fold_receipts.json')
    primary=[]
    for name in ['V1H','V2H','Nested']:
        rr=[r for r in outer if r['policy']==name];primary.append({'model':name,'ndcg':avg(rr,'ndcg'),'precision':avg(rr,'precision'),'recall':avg(rr,'recall'),'coverage':avg(rr,'coverage'),'concentration':avg(rr,'top10_concentration'),'gini':avg(rr,'gini'),'entropy':avg(rr,'entropy_bits'),'interuser_Jaccard':avg(rr,'interuser_top10_jaccard')})
    inner_candidates=[]
    for name in 'ABCDEF':
        rr=[r for r in inner if r['policy']==name];inner_candidates.append({'policy':name,'inner_mean_ndcg':avg(rr,'ndcg'),'inner_mean_coverage':avg(rr,'coverage'),'inner_mean_concentration':avg(rr,'top10_concentration'),'selected_outer_folds':','.join(k for k,p in locks['per_outer'].items() if p['id']==name) or 'none','outer_all3fold_ndcg':'N/A'})
    signal=[]
    for name in ['V2H','Nested']:
        rr=[r for r in outer if r['policy']==name and r.get('item_bias_sd')];signal.append({'model':name,'contributing_folds':len(rr),'item_bias_sd':avg(rr,'item_bias_sd'),'latent_sd':avg(rr,'mf_latent_sd'),'mean_SD_ratio':avg(rr,'latent_bias_sd_ratio'),'MF_bias_Spearman':avg(rr,'mf_itembias_spearman'),'MF_bias_Top10_Jaccard':avg(rr,'mf_bias_top10_jaccard')})
    seedtable=[]
    for sd,data in [(12,outer),(29,seed)]:
        for name in (['V1H','Nested'] if sd==12 else ['V1','Nested']):
            rr=[r for r in data if r['policy']==name];seedtable.append({'seed':sd,'model':name,'ndcg':avg(rr,'ndcg'),'coverage':avg(rr,'coverage')})
    final=load('models/final/metadata.json')
    save('metrics/final_summary.json',{'primary_outer':primary,'inner_candidates':inner_candidates,'biased_signal':signal,'seed_diagnostic':seedtable,'actual_mf_fits':run['actual_mf_fits'],'final_policy':final['policy'],'outer_workflow_policies':{k:p['id'] for k,p in locks['per_outer'].items()},'final_model_outer_accuracy':'N/A: all3fold evaluation of final fixedF not performed','recommend_website_change':False})
    header='STEP8. 승인된 61회 상한 내 신규 V3 실험. 기존 validation/Internal·External Test 정답은 접근하지 않았다. V1/V2·원본 설계·웹은 보존하며 최종 Word/PPT는 작성하지 않았다.\n\n'
    report('V3_IMPLEMENTATION_AUDIT.md','# Development V3 구현·검증 감사\n\n'+header+f'''## 구현과 설계 일치

`v3_config.py::verify_source`가원본STEP7보고서의A–F표와공통lr.01/latentL2.01/epoch40을파싱해6정책과일치함을검증했다. 원본report/blueprintSHA는승인전검토기록과같으며고치지않았다. 별도실행설정은`configs/execution.json`, preflight검토파일은그대로보존했다. 추가후보0개.

A:f2/biasL2.01/foldlatent1,bias1/Linear.25; B는biasL2.1; C는B의foldlatent.1; D는C의factor4; E는C의Contentα.75; F는C의candidate-minmax.25. 사용자·아이템bias는같은사전biasL2를쓰고latentL2와분리한다. 무제한Cartesian탐색은없다.

V3 목적은관측edge별1/2[e²+λp(||p||²+||q||²)+λb(bu²+bi²)],e=μ+bu+bi+pᵀq−r. update는p←p−η(eq+λp p),q←q−η(ep+λp q),bu←bu−η(e+λb bu),bi←bi−η(e+λb bi); oldp/q와같은e사용. 초기P/Q Normal(0,.05),bias0,μ는해당fit평균.40epoch고정이며outer평가로정지/튜닝하지않는다.

Fold-in은A=[qᵀ,1],y=r−μ−bi,z=(AᵀA+n diag(λlatent,…,λuserbias))^−1Aᵀy. Q·itembias·μ불변. V1baseline은원래bias-free식, V2baseline은원래biasedMF/nestedstop/neutral/RRF/λ1의새fold학습복사본이다. 기존저장전체train모델로outer평가를하지않았다.

Content는변경없는기존Content/ContentV2를호출하되IDF는현재fit의고유item문서만사용한다. 후보공개metadata는transform가능하지만heldout평점에서특성을만들지않는다. Popularity도현재fit만. 새선형/정규화fusion은기존`hybrid_v2.combine`을재사용하며minmax는현재사용자의unseen479candidate점수범위만사용한다. hard Woody/Floral/Rose필터는fusion후적용한다.

## 자동 디버깅 기록

최초사전테스트21개중20PASS/정수0입력1ERROR였다. 새`foldin_v3.py`에서y가int배열이되어floatbias를in-place로빼지못했다. 사용자추가승인후**np.asarray(...,dtype=np.float64)**로수정했다. 내부는0–1, UI/CLI는명시적scale10을/10하는adapter로분리했다. 자동scale추론은없다. 기존V2validation함수/모델은수정하지않았다.

기존21+정수/실수/0·10경계추가4=**25개사전테스트PASS후에만학습**했다. 최초실패로그와재검사로그를모두보존했다. 이후SGD손계산추가로최종회귀**26개PASS**, gradient유한차분·분리ridge정상조건·누수경계·guardrail·IDFfit범위검사포함. synthetic단일step수학검사는MF.fit실행이아니며실제MF테스트fit0이다. 실제실험외MFfit을감추지않는다.

독립CLI통합검증은정상48조합(high/low/mixed/equal/0/10×4필터×Top5/10),비정상8개거절,원시/정규화입력동일성,순서불변·재요청·재로딩·Q불변을통과했다. 실사용자만족도시험이아니다.

## 실제 Fit 집계와 재사용

**총 {run['actual_mf_fits']} /61회**, primary52/54,seed29진단5/6,final1/1. 실제MF.fit진입을profilehook이집계하며V2early-stop probe도포함한다. fitwrapper우회호출과상한초과는오류다. 각fit의phase/seed/설정/학습행digest/stopdigest/status를ledger에기록했다. Content IDFfit·fold-in solve·추천·지표계산은MFfit과구분한다.

cache는이번프로세스내에서만조회하며class/정확한입력순서digest/stopdigest/seed/config가같을때만쓴다. B/C/E/F는같은MF학습weights공유,차이는fold-in/fusion이다.21cachehit중18개는inner6fold의B모델재사용,3개는선택V1의outer/known/seedbaseline복사재사용이다. 그래서예산에서3fit줄었다.58개실제fit마다저장weights·연속IDmapping·actualtrainuser/item집합·rowdigest·user분리·finite상태를`post_checks.py`로검증했다. cachehit의train/stopdigest도원fit과일치한다.

V2probe의ledger epochs는best/selected epoch이며실제로거쳐간전체optimizer epoch수와같다고주장하지않는다. 최종V3는고정40epoch다. 최종모델학습도총계에포함됐고추가MF학습0회다.

## 보호·입력 경계

기존원본상호작용/validation정답/Test정답/oldTest결과접근을openhook으로차단했다. 허용train/metadata와보호해시검사용기존자산만읽는다. 기존V2결과의bytehash읽기는무결성용이며V3선택에쓰지않는다. snapshot은trackedV1·protected19·기존V2 source/output·기존보고서SHA와금지데이터/웹stat를비교했다. 원래단계별무결성기준을재설정하지않았다.

원래V1/V2파일변경0,원래보고서덮어쓰기0. Git반영·remote설정·네트워크·서버제어0. 새소스만experiments/development_v3,private모델/결과는outputs/development_v3에있고기존ignore를유지한다.
''')
    report('V3_EXPERIMENT_RESULTS.md','# V3 신규 사용자 중심 실험 결과\n\n'+header+'''## 프로토콜과 선택 순서

seed20261109,user outer3/inner2. 모든모델같은479후보·support3·heldout·seen제외·positive≥.7·Top10수식·분모를사용한다. 양성없는사용자는ranking평균에서제외하고노출집계에는포함한다. factor미가용heldout정답은분모에남고MF는NaN,Hybrid는Content→trainpopfallback이다.이정책은STEP5/6의foldfactor pool424/423/433과달라그과거점수와직접비교하지않는다.

Outerheld사용자전체를각outerfit에서제외하고,각innerheld사용자전체도innerfit에서제외했다. 학습IDF/mean/bias/popularity는fit범위만. 6개inner실험을모두끝낸후outer별정책과fulltrain정책을**outer평가전lock**했다. 각outer선택은그outer의2innerfold만보고,fulltrain정책은전체6inner의동일가중평균만사용했다. globalfulltrain정책을outer모델선택에사용하지않았다.

Guardrail: inner평균coverage≥같은fold V1의.8,상위10상품노출슬롯점유율≤V1+.10. 통과정책과V1retention의NDCG최고로부터.002이내면낮은factor→높은bias/fold정규화→정책ID순으로택한다. 기준은실험전실행설정에고정했다. 수치들은교수필수성능목표가아닌사전품질정책이다.

## Fold 규모

'''+md(receipts,['stage','outer','inner','fit_users','fit_ratings','evaluation_users','positive_users','heldout_ratings','unknown_factor_answers'])+'''

Outer사용자158명,positive145명,support474/heldout785개,미학습factor 정답191개. inner는304user-fold관측/positive278user-fold이며중복사용자를독립304명이라하지않는다. history3인143명은train전용이다. 후보는항상479이며보수적common-support적격화로29명은outer평가에서제외된다.

## A–F Inner 결과 — 전체6fold평균

'''+md(inner_candidates,['policy','inner_mean_ndcg','inner_mean_coverage','inner_mean_concentration','selected_outer_folds','outer_all3fold_ndcg'])+'''

비교Inner baseline은V1 .041849, V2 .044104. A–D는globalcoverageguard를통과하지못했고,E는coverage는넓지만NDCG가낮았다. F는globalInner .046228로선택됐다. outer별선택은**F / V1 / F**. 이것을보고Outer에서추가정책을열지않았다. F의전체3outer고정정책성능은측정하지않았으므로N/A다. 선택된0/2fold값만평균내전체F성능이라쓰지않는다.

## 동일조건 Primary Outer 비교

'''+md(primary,['model','ndcg','precision','recall','coverage','concentration','gini','entropy','interuser_Jaccard'])+'''

Nested는단일후보성능이아닌inner선택절차(F/V1/F)의outer추정치다. 전체고유상품수는fold별평균,concentration은가장자주추천된10개상품의슬롯비중이다. 후보모두를outer에서평가하지않았으므로A–F전체outer평균은N/A다. 컨트롤의구성요소단독점수는outer.csv에있다.

'''+md([{'outer':r['outer'],'model':r['policy'],'selected':r.get('selected_policy',''),'ndcg':float(r['ndcg']),'positive':r['positive_users']} for r in outer if r['policy'] in ['V1H','V2H','Nested']],['outer','model','selected','ndcg','positive'])+'''

## 개인화·노출 부작용

'''+md(signal,['model','contributing_folds','item_bias_sd','latent_sd','mean_SD_ratio','MF_bias_Spearman','MF_bias_Top10_Jaccard'])+'''

Nested의biased값은F가선택된2fold만의평균이다. fold1은bias없는V1이라N/A로빼며0으로메우지않는다. F에서latent/itembias SD비는약3.61%로V2 약.78%보다커졌지만직접적인기여율은아니며정확도개선으로이어지지않았다. MF/itembias순위상관도여전히.998수준이다.

Nestedcoverage103개는V2 66.67보다넓지만V1 102.33과거의같고,Top10집중도46.79%는V1 39.40%보다높다. F선택fold0은outer집중도차이가+.1236으로innerguard가outer에서항상보장되지않음을보인다. 결과를보고선택규칙을바꾸지않았다. popularityfallback은모든primaryHybrid0%,componentfallback은unknownfactor후보때문에발생하며모든모델에서동일pool을유지한결과다.

전체train최종F의합성입력6scenario는서로다른Top10을만들었고high/lowJaccard0이었다. 단일공개상품3개조합의감도검사이며‘실제사용자정확도가개선됐다’는근거가아니다. 자세한metrics·fallback·per-user목록유사도는CSV에있다.

## Seed·불확실성

'''+md(seedtable,['seed','model','ndcg','coverage'])+'\n'+md([{'reference':k,**v} for k,v in boot.items()],['reference','positive_users','fold_macro_delta','low','high','draws'])+f'''

두CI모두0을포함한다. bootstrap은동일사용자V1/V2/Nested차이를pair해사용자cluster로resample하고fold평균을유지한다. seed29에서Nested .035186/V1 .050483으로역시우위가없고,baseline의seed변동이상대적으로크다. V2seed29는승인된범위에서제외돼N/A다. 기존train은이미개발에사용됐으므로엄밀한독립Test의일반화/유의성주장을하지않는다.

## Known-user 보조 진단

V1 meanNDCG .041665 / Nested .037066. 각outerfit안에서known-user1평점holdout한보조진단이고일반newuserprimary와구별한다. settings는inner신규CV에서이미고정했고이결과로재선택하지않았다. V2보조진단추가fit은예산에없어실행하지않았다.

## 실제 비용·모델 저장

실제검색/학습시간 **{run['seconds']:.3f}초**, MF fit **58회**(52/5/1)로61이내. 초기25사전테스트·최종26회귀테스트는MFfit0. 최종정책F는inner6fold만으로lock했고전체원train1805평점으로별도1fit했다. final F모델은`models/final/weights.npz`, `metadata.json`, `input_recipe.json`。선택절차의Outer평균을이전체trainF단일모델정확도라고표현하지않는다.

비공개baseline/각fitcache모델도V3전용models아래저장했다. cache21회는정확데이터/config/seed/stop경계로검증했고old모델재사용아님. 모든실제fit의users/items집합·P/Qmapping·finite상태와분할행digest를58개모두검증했다.

CLIload {runtime['load_seconds']:.6f}s,Top5median {runtime['top5_seconds_median']:.6f}s,Top10median {runtime['top10_seconds_median']:.6f}s,fold-inmedian {runtime['foldin_seconds_median']:.8f}s,wholeprocesspeakRSS {runtime['peak_process_rss_bytes']}bytes. 로컬실측이며Mac기종성능보장이나최적화속도개선주장은아니다. 런타임이ledger를바꾸지않았고추가MFfit0.
''')
    report('V3_FINAL_COMPARISON.md','# V3 최종 비교·채택 판단\n\n'+header+'''**V1 웹사이트 유지 권고. V3 실험은 완료했지만 추천 정확도 개선은 확인하지 못했다.**

| 질문 | 판단 |
|---|---|
| 같은Outer에서V1보다개선? |아니오: .033557 <.038111|
| 같은Outer에서V2보다개선? |아니오: .033557 <.043615|
| 개인화신호강화? |F선택fold의latent변동·입력감도는커졌으나itembias지배가남고정확도개선은없음|
| Coverage개선? |V2보다는증가(66.67→103),V1과비슷(102.33)|
| 정확도비악화입증? |아니오. 점추정은낮고CI가넓어유의열화/비열등성모두확정못함|
| 안정적차이? |seed29도우위없음;작은표본·단일분할seed·재사용train한계|
| 웹적용가치? |현상태에서교체근거부족;연결하지않음|

A–F Inner 결과,동일Outer컨트롤비교와불확실성은V3_EXPERIMENT_RESULTS.md 및 metrics/*.csv에있다. 미선택정책전체Outer값은N/A다. 기존STEP5/6/7점수와후보/적격집단이달라직접성능증가라고비교하지않는다. 기존validation/Test를다시읽어새설정을선택하지않았다.

최종저장정책은**F: factor2,latentL2.01,biasL2.1,lr.01,40epochs,fold-in latentλ.1/biasλ1,neutral Content,미관측 후보 minmaxαContent.25**. 이는전체6inner집계에서외부평가전에고정한별도서비스용후보이지Outer에서고른best모델이아니다. globalF를3fold모두평가하지않았으므로그고정모델의Outer평균은N/A다.

## 완료·보호

사전25테스트/최종26회귀/48정상통합/8오류거절/재로딩·순서·Q불변PASS. 모델61fit상한내58회. 모든baseline재학습과V2nestedprobe·seed·final을포함했다. 기존설계JSON과보고서는그대로다. V3소스수학·분리규칙·guardrail은학습전확정됐으며Outer실패후튜닝하지않았다.

기존V1 protected19와manifest 3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130 유지. 기존V1/V2source/models/results/기존보고서SHA변경0,금지된데이터·평가파일·웹stat변경0. 실제서버조작·네트워크·Git반영없음. 전체client/date와무관한원본무결성기준을재설정하지않았다.

작업브랜치development-v2. 새source `experiments/development_v3/`와기존V2untracked디렉터리만보이며,모델/결과/보고서는기존ignore유지. raw/user평점/mapping/model을강제add하지않는다. Git commit/push/merge/rebase/tag/remote설정0,main변경0. 사용자확인전웹교체나추가실험을진행하지않는다.

## 남은 우선순위

1. V1유지,이번실패와불확실성을최종프로젝트설명에정직하게반영한다.
2. 추가연구가승인되면새독립평가·더많은사용자상호작용을우선검토한다. 같은train CV/기존validation의반복튜닝을하지않는다.
3. 설명가능한개인화목표와정확도/노출의상충관계를분리검토한다. latent진폭증가만으로개선이라고하지않는다.
4. 새코드공개전license/README/실행환경/사용권검토,팀역할·기여율·소감은별도확인한다. 최종Word/PPT는이번에작성하지않았다.

실행/디버깅/파라미터/API/모델파일목록은experiments/development_v3/README.md와METHODS_EXPLAINED.md,최종증거는outputs/development_v3/diagnostics/final_verification.json을참조한다.
''')
    print('Three NEW STEP8 reports written; no model fit or reevaluation.')
if __name__=='__main__':main()
