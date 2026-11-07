"""Posthoc summaries only: no inference, fitting, selection or score changes."""
import csv,json
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from .config import OUT,ROOT,TUNING
from .evaluation import user_metric
from experiments.scent_v2.score_diagnostics.analysis import mean_finite


def read(name):
    with (OUT/name).open()as f:return list(csv.DictReader(f))


def table(rows,keys):
    """Aggregate-only Markdown formatter; never emit private user histories."""
    def fmt(v):
        if v is None or v=='':return 'N/A'
        try:
            x=float(v);return str(int(x))if x.is_integer()else f'{x:.6f}'
        except (TypeError,ValueError):return str(v)
    return '\n'.join(['| '+' | '.join(keys)+' |','| '+' | '.join(['---']*len(keys))+' |']+['| '+' | '.join(fmt(r.get(k))for k in keys)+' |'for r in rows])


def main():
    """Read new private results into public aggregates + five authorized docs."""
    if (OUT/'REPORT.md').exists():raise RuntimeError('Existing report')
    inner=json.loads((OUT/'inner_results.private.json').read_text());outer=json.loads((OUT/'outer_results.private.json').read_text());training=json.loads((OUT/'training_diagnostics.json').read_text());selection=json.loads((OUT/'selection_locked.json').read_text());bootstrap=json.loads((OUT/'bootstrap_ci.json').read_text());rob=json.loads((OUT/'robustness.json').read_text());summary=json.loads((OUT/'summary.json').read_text());v=json.loads((OUT/'verification.json').read_text())
    trainrows=[];clean_train=[]
    for t in training['fits']:
        stats=t['pair_statistics'];start=t['history'][0];end=t['history'][-1]
        row=dict(stem=t['stem'],variant=t['variant'],users=stats['users'],ratings=stats['ratings'],pairs=stats['pairs'],users_without_pairs=stats['users_without_pairs'],pairs_median=stats['pairs_median'],pairs_p90=stats['pairs_p90'],pairs_max=stats['pairs_max'],equal_pairs_excluded=stats['equal_pairs_excluded'],factor_items=t['factor_items'],initial_loss=start['objective'],final_loss=end['objective'],rating_loss=end['rating_loss'],pair_loss=end['pairwise_loss'],pair_accuracy=end['pairwise_accuracy'],fitted_P_rating_rmse=end['train_rating_rmse'],train_ridge_rmse=t['train_ridge_rmse'],baseline_train_ridge_rmse=t['baseline_train_ridge_rmse'],Q_norm=end['Q_norm'],P_norm=end['P_norm'])
        trainrows.append(row);clean_train.append(dict(t,pair_statistics={k:x for k,x in stats.items()if k!='user_pair_counts_private'}))
    with (OUT/'training_diagnostics_public.json').open('x')as f:json.dump(dict(real_data_fit_calls=training['real_data_fit_calls'],fits=clean_train),f,indent=2)
    aa=[r for r in inner['accuracy']if r['track']=='A'];foldrows=[]
    for p in ('baseline','variant_a','variant_b'):
        rows=[r for r in aa if r['policy']==p and r['method']=='mf'];by=defaultdict(list)
        for r in rows:by[r['user']].append(r)
        counts=Counter(r['foldin']['status']for r in rows)
        keys=('support_pairs','known_support','P_norm','support_rmse','iterations','gradient_norm')
        d=dict(policy=p,users=len(by),contexts=len(rows),ok_contexts=counts['ok'],no_pair_contexts=counts['no_support_pairs'],no_known_contexts=counts['no_known_support'],failed_contexts=sum(n for k,n in counts.items()if k not in ('ok','no_support_pairs','no_known_support')))
        for key in keys:d[key]=mean_finite([mean_finite([r['foldin'][key]for r in rs])for rs in by.values()])
        for key in ('clipping_frequency','factor_candidates'):d[key]=mean_finite([mean_finite([r[key]for r in rs])for rs in by.values()])
        for channel in ('mf_raw_distribution','mf_mapped_distribution'):
            for key in ('mean','sd','p5','p50','p95'):d[channel+'_'+key]=mean_finite([mean_finite([r[channel][key]for r in rs])for rs in by.values()])
        foldrows.append(d)
    with (OUT/'foldin_diagnostics.json').open('x')as f:json.dump(dict(inner_trackA=foldrows,compatibility=[dict(outer=c['outer'],candidates=[dict(policy=x['policy'],**x['compatibility'])for x in c['candidates']])for c in selection['choices']]),f,indent=2)
    # Posthoc strata use baseline Support factor count so every arm shares users.
    base={(r['outer'],r['inner'],r['user']):r for r in aa if r['policy']=='baseline'and r['method']=='mf'}
    trainfreq={}
    for o in (1,2,3):
        for f in json.loads((TUNING/f'outer{o}_inner_splits.private.json').read_text()):
            counts=Counter(i for u,i,y in f['train'])
            for u in f['users']:
                positives=[i for i,y in f['answers'][u]if y>=.7]
                trainfreq[o,f['fold'],u]=mean_finite([counts[i]for i in positives])
    sub=[]
    for group in ('positive_answers','baseline_known_support','positive_item_train_count'):
        for p in ('baseline','variant_a','variant_b'):
            for method in ('mf','hybrid'):
                by=defaultdict(list)
                for r in aa:
                    if r['policy']!=p or r['method']!=method:continue
                    key=(r['outer'],r['inner'],r['user']);n=r['positive_answers']if group=='positive_answers'else base[key]['known_support']if group=='baseline_known_support'else trainfreq[key]
                    label=('none'if n is None else '0'if n==0 else '1'if n==1 else '2-4'if n<=4 else '5+')if group=='positive_answers'else('0'if n==0 else '1-2'if n<=2 else '3-4'if n<=4 else '5')if group=='baseline_known_support'else('no_positive'if n is None else '0'if n==0 else '(0,3]'if n<=3 else '>3')
                    by[label,r['user']].append(r)
                for label in sorted({k[0]for k in by}):
                    us=[rs for (l,u),rs in by.items()if l==label];values=[mean_finite([r['accuracy']['ndcg']for r in rs if r['accuracy']is not None])for rs in us]
                    sub.append(dict(group=group,bin=label,policy=p,method=method,users=len(us),positive_users=sum(x is not None for x in values),ndcg=mean_finite(values)))
    impacts=[]
    for p in ('variant_a','variant_b'):
        for method in ('mf','hybrid'):
            left=user_metric(inner['accuracy'],p,'A',method,'ndcg');right=user_metric(inner['accuracy'],'baseline','A',method,'ndcg');d=[left[u]-right[u]for u in sorted(left)]
            impacts.append(dict(policy=p,method=method,users=len(d),improved=sum(x>1e-12 for x in d),worsened=sum(x< -1e-12 for x in d),equal=sum(abs(x)<=1e-12 for x in d),mean_delta=float(np.mean(d))))
    def save(name,rs):
        with (OUT/name).open('x',newline='')as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
    save('training_summary.csv',trainrows);save('user_subgroups.csv',sub);save('user_changes.csv',impacts)
    a=[r for r in read('inner_results.csv')if r['track']=='A'];oa=[r for r in read('outer_results.csv')if r['track']=='A'];r=[x for x in rob['inner']if x['track']=='A'and x['method']=='hybrid'];ci=[x for x in bootstrap['inner']if x['track']=='A'and x['metric']=='ndcg'];choice=', '.join(f"Outer{x['outer']}={x['selected_policy']}"for x in selection['choices'])
    conclusion='정확도 개선 채택 조건을 충족한 Variant가 없어 기존 모델을 유지한다.'if all(x['selected_policy']=='baseline'for x in selection['choices'])else '사전 Inner 선택 결과를 기록한다. 실제 서비스는 변경하지 않는다.'
    acc=table(a,['policy','method','ndcg','precision','recall','hit_rate']);rt=table(r,['policy','amplitude','replacement','first','order_same','jaccard','rank_move','replacement_p90']);cit=table(ci,['policy','method','users','delta','low','high']);ft=table(foldrows,['policy','contexts','ok_contexts','no_pair_contexts','failed_contexts','support_pairs','support_rmse','P_norm','clipping_frequency'])
    sections=[]
    def sec(name,text):sections.append('## '+name+'\n\n'+text+'\n\n')
    sec('A. Executive Summary',conclusion+' '+choice+'.\n\n실제 데이터 Fit '+str(summary['new_real_data_fits'])+'회, 기준선 Fit0회, 사전 합성 Fit6회(첫 실패 테스트2회+통과 테스트4회)를 구분했다. A sigmoid Hybrid는 사전부터 진단용이며 채택 근거로 사용하지 않는다. 새로운 독립 확증 결과가 아니다.')
    sec('B. 학습 데이터',table(trainrows,['stem','variant','users','ratings','pairs','users_without_pairs','pairs_median','pairs_p90','pairs_max','equal_pairs_excluded','factor_items'])+'\n\n모든 strict unequal 관측 평점쌍을 사용했다. V2-6의354–475개는 high>=.7/low<.5 제한 쌍이었고, 이번 쌍 수와 정의가 다르다. 동일사용자만 연결, 동일평점 제외, 미평가 음성 없음, gap 가중치 없음. A는 쌍 참여자·아이템만 factor를 갖고 B는 모든 Train 평점 아이템을 유지한다. 큰 이력 사용자가 O(n²)쌍으로 학습에 더 큰 영향을 줄 수 있다.')
    sec('C. 학습 결과',table(trainrows,['stem','variant','initial_loss','final_loss','rating_loss','pair_loss','pair_accuracy','fitted_P_rating_rmse','train_ridge_rmse','baseline_train_ridge_rmse','Q_norm','P_norm'])+'\n\nA는 sumsoftplus+.01 global norm², B는 mean(.5error²+.5*.01 eventnorm²)+.1mean pairsoftplus다. 학습률.01/160epoch/dim4/seed12 고정, B의 pair SGD는 beta*nratings/npairs로 크기를 맞췄다. 두 목표 총손실은 서로 직접 비교 불가다. 같은epoch라도 업데이트 수·정규화 효과·계산량이 다르다. Train pair accuracy는 학습 적합도이며 신규 사용자 추천 정확도가 아니다. 원본 SGD의 실제 event-weighted gradient와 기존 logged loss가 다르다는 점도 METHODS에 설명했다.')
    sec('D. Fold-in 호환성',ft+'\n\nA는5개 Support의 알려진factor strict pair만 사용한 regularized convex 최적화다(Newton50/backtracking20/tol1e-8/λ.01). no-pair/no-factor/실패/zero는 MF미점수→원래Hybrid fallback이다. A의 support RMSE는 척도가 없는 진단이며 rating 예측 평가로 해석하지 않는다. B는 Ridge.01을 유지하고 Train ridgeRMSE/SupportRMSE/clip증가≤.05 및 norm10배 이내를 사전 guard로 검사했다. 이 guard 통과가 확률보정 입증은 아니다. 세부 gate는 selection_locked.json과 foldin_diagnostics.json 참조. Q를 바꾸지 않았다.')
    sec('E. Inner 정확도',acc+'\n\n고유75명/긍정69명, 반복문맥150개이며 사용자 안에서 먼저 평균했다. 무긍정6명은 정확도 평균 제외, Coverage/강건성에는 포함했다. TrackB는 baseline factor후보를 모든arm에 공유하고 A에 없는factor는 미점수로 남긴다. B_full5도 baseline Support 기준으로 cohort를 고정했다. 전체Track 결과는 inner_results.csv다.')
    sel=[]
    for x in selection['choices']:
        for e in x['candidates']:sel.append(dict(outer=x['outer'],policy=e['policy'],accepted=e['accepted'],ndcg=e['ndcg'],low=e['paired_ndcg']['low'],high=e['paired_ndcg']['high'],failed_gates=', '.join(k for k,z in e['gates'].items()if not z),selected=x['selected_policy']))
    sec('F. Outer 선택',choice+'\n\n'+table(sel,['outer','policy','ndcg','low','high','accepted','failed_gates','selected'])+'\n\n선택은 각Outer Inner에서만 수행했다. NDCG증가/paired95하한>0/Coverage손실0/Top1·5집중도증가0/±.5·1평균·P90교체율증가0·1위유지감소0 및 호환성으로 사전고정했다. A 변환미보정은 사전 채택불가gate다. 잠금후Outer만 열었고 미선택 Variant의 Outer Fit/평가는 하지 않았다.')
    sec('G. Outer 정확도',table(oa,['policy','method','users','positive_users','ndcg','precision','recall','hit_rate'])+'\n\n선택이기준선이면 결과가같은이유는 동일모델이기때문이다. 미선택A/B의동등성이나불가능성입증이아니다. 선택−기준선CI는bootstrap_ci.json outer에 저장했다.')
    sec('H. MF 단독 vs Hybrid','A의 pureMF는 raw pairwise순위, A Hybrid는 고정sigmoid(raw)이며 만족확률이 아니다. baseline/B는 clip(raw,0,1)점수다. pureMF의결측을fallback으로대체하지않았다. A/B MF와Hybrid의증감은E 및L표에서구분했다. A Hybrid가좋아져도 임의변환만으로확정적개선을주장할수없다.')
    sec('I. 강건성',rt+'\n\n원평점±.5/±1/범위밖제외, clamp없음. 유효변형→문맥→사용자 평균이다. P90은 사용자 평균교체율 분포의90백분위다. A는 순위관계가변하지않으면입력이동일해질수있지만, 관계가바뀌거나동점이되면벡터가변한다. 안정성은 정확도와다르다.')
    sec('J. Coverage·추천 집중도',table(a,['policy','method','coverage_items','top1_slot_share','top5_slot_share','fallback_candidates_mean','fallback_top5_mean'])+'\n\nCoverage는고유추천아이템수, 집중도는가장자주추천된상위1/5향수의Top5슬롯점유율이다. A의factor감소는아직gradient를받지않은초기랜덤벡터를유효factor로보여주지않기위한명시정책이다.')
    sec('K. 사용자별 개선·악화',table(impacts,['policy','method','users','improved','worsened','equal','mean_delta'])+'\n\n긍정수/공통baseline MF Support수/정답아이템Train평점빈도별사후분석은user_subgroups.csv다. 마지막빈도는정답으로조회한진단일뿐추천입력이나선택변수가아니다. 사용자/가명ID는공개표에없다. 개인기록과user_pair_counts는로컬전용이다. training_diagnostics.json에는가명사용자별쌍개수가있어공유하지않고, 공개용은training_diagnostics_public.json이다.')
    sec('L. 통계 검증',cit+'\n\nBootstrap20,000/seed12/사용자단위paired95%percentile. 다른지표와강건성CI는bootstrap_ci.json에있다. 작은표본/다중비교/학습집합중첩/같은Outer반복검토한계가있다. 이번Nested절차는실행내선택경계를지키지만과거적응적실험이력을지우지않는다. 독립확증으로보고하지않는다.')
    sec('M. 최종 채택 여부',conclusion+' 실제 Frozen V1·웹서비스·기존결과는변경하지않았다. 학습적합도증가와신규사용자정확도개선입증을구분했다.')
    sec('N. 다음 개선 실험 권고','평가결과를보고beta/학습률/반복수/변환을추가탐색하지않았다. 새독립사용자평가경계확보와명시적평점척도·순위척도의호환성을별도사전설계하는것을권고한다. 후속모델구현·실험·서비스연결은미실행이다.')
    sec('O. 발표 문서 업데이트','허용된docs/presentation5개에V2-6가설, pairwise목표와fold-in차이, 실제정확도/강건성/CI/미채택이유를누적한다. 그래프는새로생성하지않았고CSV/컬럼기반제작계획만추가한다. 개인기여율·소감은만들지않는다.')
    sec('P. 무결성 확인',f"실제 데이터 Fit{summary['new_real_data_fits']}회, 사전 합성 Fit6회. 새 Q는 각Train에서독립학습했고기준선Q/IDF는재사용만했다. baseline {v['baseline_comparisons']}개저장Top5비교의최대점수차이{v['maximum_baseline_top5_score_difference']}. 원래Validation/Internal/External정답접근없음, Q/mapping/Train경계·선택잠금검증PASS. 최종파일해시는integrity.json. Git/패키지/서비스변경없음. REQUIREMENTS_TRACEABILITY.md는보호하여수정하지않고I01/I02/P07/P17/R12의추가증거만제공한다. 전체최종제출준수를선언하지않는다.")
    with (OUT/'REPORT.md').open('x')as f:f.write('# V2-7 — Observed Pairwise Ranking MF\n\n'+''.join(sections)+'## 실행\n\n`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -W error -m experiments.scent_v2.pairwise_mf.run`\n\n학습 전test_pairwise14개와기존143개회귀통과. 최초합성fallback테스트의NaN sigmoid경고를finite마스크로수정한뒤통과했다. 실패·성공테스트와실제학습로그를보존했다. 신규보고는동일Python의`-m experiments.scent_v2.pairwise_mf.reporting`으로생성한다.\n')
    # Exactly five allowed documentation updates.
    docs=ROOT/'docs/presentation';ref='[V2-7 보고서](../../outputs/scent_v2/pairwise_mf/REPORT.md)';core='V2-7은 관측된 unequal 평점쌍만으로 A ranking MF/B rating+pairwise MF를 독립 학습했다. '+conclusion+' '+choice+'. '+ref
    appendix='\n## V2-7 Pairwise MF — 완료\n\n'+core+'\n\n**가설:** V2-6에서 양쪽Top20 밖314개였던 실패를 학습 목표 변경으로 줄일 수 있는가?\n\n**방법:** A전용pairwise Fold-in, B기존Ridge, beta.1고정, 새MF12회이내Inner학습. A의sigmoid Hybrid는진단용이며채택근거로쓰지않는다.\n\n**정확도:**\n\n'+acc+'\n\n**강건성:**\n\n'+rt+'\n\n**통계:**\n\n'+cit+'\n\n**해석/채택:** '+conclusion+' Train pair 적합도와 신규 사용자 정확도는 다르다. 동일 Outer 반복 사용·다중비교·작은표본 한계가 있다. 새 독립 확증자료가 필요하다. 서비스는 Frozen V1 유지.\n\n**다음:** 추가 beta/학습률 탐색은 미실행이다.\n'
    for name in ('MODEL_IMPROVEMENT_STORY','EXPERIMENT_TIMELINE','PERFORMANCE_COMPARISON','PRESENTATION_SLIDES_OUTLINE','EXPERIMENT_LOG'):
        p=docs/(name+'.md');text=p.read_text().replace('최신 누적 상태: V2-6 실패 진단 완료.','최신 누적 상태: V2-7 Pairwise MF 완료.');text+=appendix
        if name=='PRESENTATION_SLIDES_OUTLINE':text+='\n시각화계획(미생성): inner_results.csv(track=A; policy,method,ndcg/recall), training_summary.csv(stem,initial_loss,final_loss,pair_accuracy), robustness.json(inner; policy,method,amplitude,replacement,first), foldin_diagnostics.json(inner_trackA; support_pairs,support_rmse,clipping_frequency). 차이CI를개별모델점수CI로표시하지않는다.\n'
        if name=='EXPERIMENT_LOG':text+='\n기록: 고정변수λ=.01/α=.25/dim4/epoch160/lr.01/seed12/Support5/후보479. 실제Fit ledger와선택잠금은동일출력경로. 개인상세는private로컬전용. 후속미실행.\n'
        p.write_text(text)
    print('PASS: A–P report, aggregate diagnostics and five presentation docs updated')

if __name__=='__main__':main()
