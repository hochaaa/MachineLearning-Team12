"""Summarize fixed diagnostics only. No model fitting, validation labels, or model selection."""
import sys,json,csv
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from failure_diagnosis import ROOT,OUT,DOUT,guard,snapshot,sha

def csvrows(name):
    with (DOUT/name).open() as f:return list(csv.DictReader(f))
def number(row,key):return float(row[key])
def table(rows,keys):
    s='| '+' | '.join(keys)+' |\n|'+'---|'*len(keys)+'\n'
    for r in rows:s+='| '+' | '.join(f'{r[k]:.6f}' if isinstance(r.get(k),float) else str(r.get(k,'N/A')).replace('|','/') for k in keys)+' |\n'
    return s

def main():
    guard();report=ROOT/'reports/V2_HYBRID_FAILURE_DIAGNOSIS.md'
    if report.exists():raise RuntimeError('Do not overwrite report')
    aggregate=csvrows('aggregate_metrics.csv');rank=csvrows('rank_summary.csv');bias=csvrows('bias_decomposition_anonymous.csv');dist=csvrows('score_distributions_anonymous.csv');metrics=csvrows('metrics.csv');cov=csvrows('coverage.csv')
    ci=json.loads((DOUT/'paired_cluster_bootstrap.json').read_text());ridge=json.loads((DOUT/'ridge_stability.json').read_text());replay=json.loads((DOUT/'replay_checks.json').read_text())
    a={(r['protocol'],r['model']):r for r in aggregate};ranks={(r['protocol'],int(r['version'])):r for r in rank}
    bmeans={p:{k:float(np.mean([float(r[k]) for r in bias if r['protocol']==p])) for k in ['latent_to_itembias_sd','mf_itembias_spearman','clip_boundary_fraction']} for p in ['known','newuser']}
    hypotheses=[
      {'ID':'H1','hypothesis':'V1/V2 evaluation formula/cohort mismatch explains drop','status':'REJECTED','evidence':'same supports/candidates asserted for every user; synthetic NDCG/denominator parity;12 historical Hybrid fold scores reproduced'},
      {'ID':'H2','hypothesis':'RRF implementation has arithmetic/rank constant error','status':'REJECTED','evidence':'exact .25*61/(60+rankC)+.75*61/(60+rankM);offset60 and ID ties verified'},
      {'ID':'H3','hypothesis':'V2 MF ranks dominated by item bias, especially new users','status':'CONFIRMED','evidence':f"newuser latent/itembias SD={bmeans['newuser']['latent_to_itembias_sd']:.6f}, rank corr={bmeans['newuser']['mf_itembias_spearman']:.6f}"},
      {'ID':'H4','hypothesis':'RRF magnifies concentrated V2 MF ranking and reduces coverage','status':'CONFIRMED','evidence':'same V2 scores: newuser Linear coverage51.67 -> RRF29.67; top10 exposure share68.74% ->82.42%; fixed deterministic intervention'},
      {'ID':'H5','hypothesis':'RRF alone explains all Hybrid accuracy loss','status':'REJECTED','evidence':'same V2 Linear .034006 still below V1Linear .047663; V1components+RRF .052024 improves over V1Linear; not a universal RRF failure'},
      {'ID':'H6','hypothesis':'item-bias concentration + rank fusion contributes to loss','status':'SUPPORTED','evidence':'V2MF unique11.67/hottest100% users;V2Hybrid hottest99.33%;V2RRF .032505 vs same-componentLinear .034006; no bias-removal causal ablation'},
      {'ID':'H7','hypothesis':'V2 clipping/ties are primary cause','status':'REJECTED','evidence':'newuser MF clip boundary .004913%, exact duplicate score fraction0%; V1 clipping is larger'},
      {'ID':'H8','hypothesis':'popularity fallback dominates predictions','status':'REJECTED','evidence':'both hybrids popularity fallback0 across reconstructed folds'},
      {'ID':'H9','hypothesis':'Content coverage collapse causes Hybrid coverage loss','status':'REJECTED','evidence':'newuser Content coverage202 ->238; V2MF already collapses to11.67 products'},
      {'ID':'H10','hypothesis':'ridge numerical instability explains failure','status':'REJECTED','evidence':f"max condition={ridge['max_condition_number']:.6f};max normal residual={ridge['maximum_normal_residual']:.3g}; Q unchanged"},
      {'ID':'H11','hypothesis':'lambda1.0 over-shrinks personal factors relative to item bias','status':'SUPPORTED','evidence':'latent variance extremely small while stable solver; no new lambda ablation allowed, so coefficient causal effect not identified'},
      {'ID':'H12','hypothesis':'lower coverage necessarily lowers NDCG','status':'REJECTED','evidence':'known V2Linear82.33/.030247 ->RRF49/.038087: coverage down while NDCG up'},
      {'ID':'H13','hypothesis':'mechanism fully explains legacy Validation90 ->43 /accuracy gap','status':'INCONCLUSIVE','evidence':'no validation answers/predictions read/recomputed; training-only mechanisms cannot identify every validation failure'},
      {'ID':'H14','hypothesis':'statistically established independent generalization degradation/improvement','status':'INCONCLUSIVE','evidence':'both paired cluster intervals include0; selected setting CV+small sample; no independent Test access'},
    ]
    (DOUT/'hypotheses.json').write_text(json.dumps(hypotheses,ensure_ascii=False,indent=2))
    txt='''# STEP6 — V2 Hybrid 성능 하락 진단

**결론:** 평가식의 재현 오류보다, V2 MF의 item-bias 중심 순위와 RRF의 점수 크기 제거가 결합한 추천 집중 현상이 관찰됐다. 이 구조가 하락에 기여한다는 근거는 있지만 전체 원인을 입증한 것은 아니다. 기존 validation/Test를 재평가하거나 새 설정을 선택하지 않았다. V1·V2 모델/설정/원본 결과는 보존했다.

## 1. 범위·재현·보호

branch `development-v2`, main 기준 `aebd9abd85b175e6076d8b2d9c2445201d8b2602`. 기존 V2 untracked 디렉터리는 유지했다. 최초 검증에서 frozen19와manifest가일치했고 신규소스는 `experiments/development_v2/diagnostics/`만 추가했다. 결과는 `outputs/development_v2/diagnostics/hybrid_failure_step6/`에 새 이름으로만 저장한다.

STEP5는fold별점수/순위를저장하지않아 고정설정으로 train내부예측을재구성했다. Known CV의V2 epoch20은기존loss_curves기록을그대로사용했다. 신규사용자fold모델이저장되지않아원래설정·seed12·nestedstop절차를동일입력으로결정적으로재생했고epoch30/20/30이었다. 별도regularization/weight/architecture검색은없다. 기존STEP5 Hybrid12개fold점수가절대오차1e-12미만으로재현됐다. 모델복사본은메모리에서만사용하며기존model.npz등을쓰지않았다.

`deny_legacy` open hook로기존validation정답과V1Internal/External정답/결과접근을차단했다. validation90→43, NDCG.043185→.032808은기존집계배경으로만언급한다. 후보/정답성공실패목록은읽지않았다. Forbidden데이터파일은stat(size/mtime)만비교하며내용은열지않는다. V1freeze/model파일은19해시확인에만읽었다.

## 2. 평가 파이프라인 검증

| 항목 | 비교 결과 |
|---|---|
| 사용자·정답 | 같은fold안에서V1/V2동일; known187명/fold, new48/50/44명 |
| Positive | normalized>=.7, known155/154/154, new46/47/40 |
| 후보군 | 같은fold안에서동일. known479, new424/423/433 |
| Seen 제외 | 같은train/support ID제외, assertion으로일치확인 |
| K·지표 | Top10, P=hits/10, R=hits/positive, binary discountedNDCG |
| 평균 분모 | positive없는사용자제외, 수별도기록 |
| 동점 | canonicalID오름차순; RRFordinalrank도같은순서 |
| 미가용 | pureMF/Content는NaN제외;Hybrid는다른성분→trainpopfallback |
| cold items | known foldMF미학습은위fallback; new pool은모두factor존재 |
| 학습 범위 | 동일fold train만; new평가사용자는모든평점이학습에서제외 |

합성정답의수식손계산 NDCG=1/log2(3)=.63092975, V1evaluate와V2evaluate_arrays의값·분모가일치한다. 진단유틸리티10개합성테스트PASS. **재현 가능한 평가/산술 BUG는 발견하지 못했다.** 코드상 fit/점수계산에는답인자가없고진단labels는원래train내부heldout만사용한다. 이것은수행한경로의누수검증이며모든과거실행을절대증명하는보안인증은아니다.

Known-userCV와new-userCV는서로사용자/후보/정답수가달라수치를직접같은실험의변화로해석할수없다. 아래수치는각프로토콜내 V1/V2비교이며fold평균이다.

## 3. 실제 비교 수치

'''
    for protocol,title in [('known','Train 내부 기존 사용자 CV'),('newuser','Train 내부 신규 사용자 CV / support3')]:
        rr=[{'model':r['model'],'NDCG@10':float(r['ndcg']),'unique_Top10_mean':float(r['unique_top10']),'Top10_popular_slot_share':float(r['top10_item_slot_share']),'hottest_item_user_incidence':float(r['max_item_request_incidence']),'Gini':float(r['gini']),'Entropy_bits':float(r['entropy_bits'])} for r in aggregate if r['protocol']==protocol]
        txt+='### '+title+'\n\n'+table(rr,['model','NDCG@10','unique_Top10_mean','Top10_popular_slot_share','hottest_item_user_incidence','Gini','Entropy_bits'])+'\n'
    txt+='''
Counterfactual표시는같은성분점수에alpha.25로고정한fusion만바꾼**진단 대조**다. 더높은결과를새모델로선택/저장/적용하지않았다.

정의: Coverage=모든평가사용자의Top10고유상품수/해당fold후보수. no-positive도점수/노출집계에는포함한다. Top10 concentration은‘가장자주노출된10개상품의슬롯수/전체Top10슬롯수’; user간추천중복과같지않다. hottest incidence=가장자주노출된상품의사용자수/평가사용자수. Gini는후보전체(노출0포함), entropy는노출확률의Shannon bits. 위고유수는fold별평균이고여러fold를합한고유수가아니다. 각사용자의Top10 ID는모두중복없이10개였다.

## 4. 순위 충돌·RRF·점수 크기

`hybrid_v2.py::rank_scores/combine`의RRF는

`0.25 * 61/(60+rank_Content) + 0.75 * 61/(60+rank_MF)`

이다. 61배는양쪽공통상수이며둘다유효할때순위에영향없다. 원점수의간격/강도를버리고순위만사용한다. Spearman진단은동점평균순위를사용하며실제RRF는canonicalID로ordinalrank를부여한다. 이를혼동하지않았다.

'''+table([{k:(float(v) if k not in ('protocol','version') else v) for k,v in r.items()} for r in rank],['protocol','version','spearman','component_top10_overlap_fraction','linear_rrf_top10_jaccard','mf_top10_displaced_by_rrf','content_top10_displaced_by_rrf'])+'''

newuser V2는Content/MF전체순위상관−.012590, Top10교집합/10=2.7465%로서로대부분다른상품을추천한다. RRF는MF Top10의18.80%,Content Top10의92.11%를최종Top10밖으로밀어낸다. **순위불일치는확인됐지만그자체가실패의필연조건은아니다.** V1성분도낮은상관이면서fusion으로이득을보았다.

V2동일성분에서Linear→RRF는newuser NDCG .034006→.032505,coverage51.67→29.67이다. 그러나V2Linear도V1Linear .047663보다낮다. V1성분에RRF를적용하면newuser .052024로올랐다. 따라서‘RRF수식이틀림’이나‘RRF만없애면실패전체해결’은지지되지않는다. known V2에서RRF는coverage를줄이면서NDCG는.030247→.038087로올려CV가선택한이유도재현된다.

## 5. Fold-in과 MF 집중 현상

V1은latent만 ridge(AᵀA+nλI)^−1Aᵀy,λ.01. V2는A=[Q,1],y=r−μ−b_i에서latent와userbias를함께추정하고λ1.0을사용한다. 두모델의Q는고정이며userbias는후보들에공통상수이므로clipping이없다면순위자체를개인화하지않는다. 개인화순위변동은주로pᵀq항에의존한다.

'''+table([{'protocol':p,**v} for p,v in bmeans.items()],['protocol','latent_to_itembias_sd','mf_itembias_spearman','clip_boundary_fraction'])+f'''

newuser V2 latent SD는itembias SD의평균 **0.8659%**이고,rawMF와itembias순위상관은 **.999861**이다. MF Top10고유상품은fold평균 **11.67개**,노출상위10상품이전체슬롯 **97.83%**,최다상품은사용자 **100%**에등장한다. 이것은상품bias가잘못학습됐다는증명이아니라현재추천이거의공통상품순위가됐다는측정이다.

V2Hybrid는newuser 고유상품29.67개,상위10상품슬롯82.42%,hottest사용자99.33%다. V2Content는238개로V1Content202개보다넓어Content coverage붕괴가출발점이라는설명은맞지않는다. 상품bias중심MF와가중RRF가협력하는구조는실패기여요인으로SUPPORTED이나,bias제거/λ변경ablation은금지되어그각각의인과효과를분리하지못한다.

Ridge행렬의실측최대condition **{ridge['max_condition_number']:.6f}**,최소eigenvalue **{ridge['minimum_eigenvalue']:.6f}**,정상방정식residual최대 **{ridge['maximum_normal_residual']:.3g}**이다.3support에서nλ=3이므로안정적으로풀린다. 강한정규화로개인factor영향이작을가능성과수치불안정은다르며,후자는증거가없다.

신규V2MFclip경계비율은평균.004913%,정확한중복score비율은0%. V1신규MF는clip4.3154%/duplicate4.1658%로더높다. 따라서V2열화의주원인이clipping동점이라는가설은REJECTED다. 양쪽Hybrid의popularityfallback도0이므로itembias중심성향을‘fallback인기순위’와혼동하지않는다.

## 6. Coverage·다양성과 정확도의 관계

낮은catalogcoverage와높은노출집중은확인됐지만 **coverage감소가NDCG하락을일으켰다고단정하지않는다**. knownV2RRF의coverage/NDCG방향은반대이고,최종newuserV2는개별Content/MF가소폭개선돼도결합의상보성이유지되지않는다. aggregate개선은동일사용자·동일정답·동일순위에서모두개선됐다는뜻이아니다.

사용자한목록안의token-Jaccard다양성(1−평균쌍별Jaccard)은newuser V1Hybrid .877988/V2Hybrid .888367로오히려소폭높다. 이는user간카탈로그노출폭과다른개념이다. ‘사용자별모든다양성이붕괴’라고쓰면안된다. 실제선호다양성/만족도는측정하지않았다.

## 7. 불확실성·seed

'''+table([{'protocol':p,**v} for p,v in ci.items()],['protocol','cluster_users_including_no_positive','users_with_positive','fold_macro_delta','interval_low','interval_high'])+'''

bootstrap은seed12,3000draws,같은사용자의V1/V2차이를pair하고그사용자의3fold기록을함께resample한다. 매draw는각fold의positive사용자평균차이를구한후3fold평균하므로 **원래primaryfold-macro**와같은estimand다. STEP5의CVbootstrap은positivefold-user평균을사용한별도estimand였고,이번수치는이를덮어쓰지않는추가진단이다. 신규142명/positive133명, known187명/적어도한positive182명이며두프로토콜모두CI가0을포함한다. 탐색후선택bias·겹치는학습fold·작은집단이있어통계적유의성이나독립일반화의인과효과를주장하지않는다.

신규positive133명중9명은개선/23명은악화/101명은NDCG동일이었다. known의user평균은25/23/134명이다. 많은0차이와소수큰차이때문에평균변화의불확실성이크다. 기존seed29/47집계는기존V2_EXPERIMENT_RESULTS.md에있으며이번새seed탐색은없다. 알려진knownCV V1 .033573/.030573/.026967, V2 .038087/.036568/.039063만참고한다. 신규user여러seed의안정성은아직N/A다.

## 8. 가설별 판정

'''+table(hypotheses,['ID','hypothesis','status','evidence'])+'''

CONFIRMED는측정/코드행동에대한확인이지모든성능하락의인과원인을확정했다는뜻이아니다. 기존Validation개별정답·추천을보지않았으므로90→43coverage와validationNDCG하락의정확한사용자별원인은INCONCLUSIVE로남긴다.

## 9. 향후 제안만

1. 새연구계획이승인되면new-user MF에서개인latent대비itembias의영향을분리하고,regularization과rankingpersonalization의관계를검토한다. 이번λ·모델은그대로보존.
2. 같은성분/동일pool에서fusion의score간격손실·순위교란을검토하되단순히RRF를폐기하거나진단Counterfactual을새모델로선택하지않는다.
3. 신규user평가를개발목적에맞는사전선택기준에포함하고새독립평가를계획한다. 이미소비한validation/Test를추가튜닝에사용하지않는다.
4. 정확도·catalog노출·목록내다양성을분리보고하고다른splitseed/충분한표본을확보한다. 실제사용자만족도평가도별도다.

모델개선/하이퍼파라미터변경/웹연결은실행하지않았다. 사용자승인전추가실험·Git반영을하지않는다.

## 10. 산출물·무결성·Git

소스: `experiments/development_v2/diagnostics/failure_diagnosis.py`, `ridge_stability.py`, `test_diagnostics.py`, `write_diagnosis_report.py`, `README.md`。실행/수식/인자는README참조. 새결과는DOUT의metrics/coverage/rank_summary/score_distributions/bias_decomposition/public_product_frequency CSV, replay_checks/paired_cluster_bootstrap/ridge_stability/integrity/read receipts JSON과log. 사용자ID·원본개별평점은보고서에없으며anonymous요청별진단CSV도private출력으로유지한다.

기존V1/V2source·config·model·기존결과파일의시작/종료SHA변경0,금지된데이터/평가파일은내용없이stat비교변경0. protected19일치,manifest **3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130** 유지. 이전Finder/demo.log변경이력을이번에복원하거나baseline재설정하지않았다. 서버제어·외부네트워크·업로드0.

브랜치development-v2,예상Git상태는기존과같이 `?? experiments/development_v2/`만이다. 새진단소스만검토후Git대상이며모델/진단결과/보고서는현재ignore정책유지. 원래V2파일수정0,staging/commit/push/merge/rebase/tag/remote설정0. 보고서최종후검증은`final_verification.json`을근거로한다.
'''
    report.write_text(txt)
    print('New report written; no model/setting/result replaced.')
if __name__=='__main__':main()
