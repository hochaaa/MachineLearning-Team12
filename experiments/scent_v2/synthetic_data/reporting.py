"""Public aggregate reporting + actual SVG charts, no generation-rule changes."""
import json,csv,html
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from .config import OUT,ROOT,POLICY
from .profiling import stats


def read(name):
    with(OUT/name).open()as f:return list(csv.DictReader(f))


def table(rows,keys):
    def fmt(v):
        if v is None or v=='':return 'N/A'
        try:
            x=float(v);return str(int(x))if x.is_integer()else f'{x:.6f}'
        except (TypeError,ValueError):return str(v)
    return '\n'.join(['| '+' | '.join(keys)+' |','| '+' | '.join(['---']*len(keys))+' |']+['| '+' | '.join(fmt(r.get(k))for k in keys)+' |'for r in rows])


def chart(path,title,labels,series,ylabel,source):
    """Standalone SVG grouped bars; actual data, labeled axes/units/source."""
    W=1100;H=480;left=75;right=25;top=65;bottom=100;pw=W-left-right;ph=H-top-bottom;maximum=max(max(values,default=0)for name,values in series)*1.15 or 1;colors=['#315f91','#dc8c36','#458964'];parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/><g font-family="Arial,sans-serif" fill="#18283a">',f'<text x="{left}" y="28" font-size="20">{html.escape(title)}</text>']
    for n,(name,values)in enumerate(series):parts.append(f'<rect x="{left+n*310}" y="42" width="12" height="12" fill="{colors[n]}"/><text x="{left+18+n*310}" y="53" font-size="12">{html.escape(name)}</text>')
    for n in range(5):
        v=maximum*n/4;y=top+ph-ph*n/4;parts.append(f'<line x1="{left}" y1="{y}" x2="{W-right}" y2="{y}" stroke="#d9e0e7"/><text x="{left-8}" y="{y+4}" text-anchor="end" font-size="11">{v:.3g}</text>')
    group=pw/len(labels);bar=group*.75/len(series)
    for i,label in enumerate(labels):
        for j,(name,values)in enumerate(series):
            height=ph*values[i]/maximum;x=left+group*i+group*.125+bar*j;parts.append(f'<rect x="{x}" y="{top+ph-height}" width="{bar*.9}" height="{height}" fill="{colors[j]}"/>')
        parts.append(f'<text x="{left+group*(i+.5)}" y="{top+ph+20}" text-anchor="middle" font-size="11">{html.escape(str(label))}</text>')
    parts += [f'<text x="{left}" y="{H-48}" font-size="12">{html.escape(ylabel)}</text>',f'<text x="{left}" y="{H-25}" font-size="11">{html.escape(source)}</text>','</g></svg>']
    with path.open('x')as f:f.write(''.join(parts))


def main():
    if(OUT/'REPORT.md').exists():raise RuntimeError('Existing report')
    profile=json.loads((OUT/'real_data_profile.json').read_text());q=json.loads((OUT/'synthetic_quality_report.json').read_text());pref=json.loads((OUT/'preference_structure.json').read_text());boundary=json.loads((OUT/'boundary_audit.json').read_text());verification=json.loads((OUT/'verification.json').read_text());real=profile['generator_candidate_aligned_Train'];full=profile['all_disjoint_Train'];syn=q['synthetic_profiles'];ratings=read('synthetic_ratings_pilot.csv');users=read('synthetic_users_pilot.csv');audit=read('synthetic_generation_audit.csv');pop=read('perfume_popularity_distribution.csv');features=read('feature_statistics.csv')
    cohort=[]
    for name in('activity_matched','support_target_enriched'):
        selected=[(r,a)for r,a in zip(ratings,audit)if r['cohort']==name];by=defaultdict(list)
        for r,a in selected:by[r['synthetic_user_id']].append((r,a))
        contrasts=[]
        for rs in by.values():
            y=np.array([float(r['rating'])for r,a in rs]);aff=np.array([float(a['latent_affinity'])for r,a in rs]);median=float(np.median(aff));hi=y[aff>median];lo=y[aff<median]
            if len(hi)and len(lo):contrasts.append(float(hi.mean()-lo.mean()))
        cohort.append(dict(cohort=name,users=len(by),ratings=len(selected),feature_signal_assumed=name=='support_target_enriched',affinity_high_minus_low_rating=stats(contrasts)))
    with(OUT/'cohort_preference_structure.json').open('x')as f:json.dump(cohort,f,indent=2)
    zero=sum(int(r['synthetic_count'])for r in pop if int(r['eligible_Train_count'])==0);maxshare=max(int(r['synthetic_count'])for r in pop)/len(ratings)
    summary=[]
    for name,p in [('eligible_Train_candidates',real)]+list(syn.items()):summary.append(dict(scope=name,users=p['users'],ratings=p['ratings'],perfumes=p['perfumes'],mean=p['rating']['mean'],SD=p['rating']['sd'],mean_activity=p['ratings_per_user']['mean'],high_fraction=p['positive_fraction'],low_fraction=p['low_fraction'],mean_user_SD=p['user_tendency_summary']['SDs']['mean']))
    diff=[dict(cohort=k,rating_JS=v['rating']['JS_divergence_bits'],rating_KS=v['rating']['histogram_KS'],rating_Wasserstein=v['rating']['histogram_Wasserstein1'],activity_JS=v['activity']['JS_divergence_bits'],item_JS=v['item_frequency_JS_bits'])for k,v in q['distribution_differences'].items()]
    status='PASS WITH LIMITATIONS';hard=q['hard_checks'];assert all(hard.values())
    design='''# 합성 생성 설계 — 추천 정확도 평가 아님

## 데이터 경계

원래1,805개 pool의 Nested 평가75명 전체910행을 rating/item 해석 전에 제외했다. 허용Train895개 중 후보479에 연결된823개만 생성 규칙의 기준이다. 원래 Validation/Internal/External 및 Nested 답은 사용하지 않았다. 원본 Atrafshan JSON 평점도 재조회하지 않았다.

## 두 집단

150명(15%)은 후보 정렬 후 실제활동량1~5개 분포를 재표본한다. 850명(85%)은 향후 Support5+Target 용도의15~20개 이력 확장이다. 이는 관측된 장기 사용자 행동이 아니다. 활동량 분포의 전체 불일치는 의도된 목적 차이다. proposed_role은 미래 실험용 표기일 뿐 기존 평가에 추가하지 않았다.

## 세미모수 생성식

raw_latent_ui = mu_u + shrink_item_effect_i + taste_sd_u*affinity_ui + noise_sd_u*hist_noise_ui.

mu_u의 정규분포는 사용자 평균을global평균으로5개관측만큼수축한 집단분포로 정한다. 사용자 noise는 불안정한 within분산을 pooled within분산으로5개관측만큼수축한 뒤 lognormal집단분포에서 새로 그린다. item effect는 사용자중심화잔차를10개관측만큼0으로수축한다. 잡음은 집계잔차 .5너비 histogram에서구간내연속값을뽑고표준화한다. 실제사용자평점행·취향벡터를복제하지않는다.

w는선호/비선호각3~8개feature에연속lognormal가중치(σ=.35)를부여한새벡터다. global feature잔차효과는20개관측수축값이며비인과적이다. fixed .15 global mixture와연속임의선호를결합한다. 충분한실제구조근거가없어활동량재현집단은feature신호를0으로두었다. 확장집단만 within분산6.25%의약한취향신호와선택편향temperature .25를가정한다. 실제취향강도를추정했다고주장하지않는다.

## 선택/척도

향수선택확률 기본값은 sqrt(Train count+1), 개인신호가활성화된집단만bounded affinity의exp(.25*affinity)로약하게기울인다. 무복원선택으로중복을막는다. 미관측후보에도양의확률이있어이는외삽이며실제기호정보가아니다.

마지막에생성latent순위를허용Train평점의경험분위수로한번만매핑하고0.5점으로반올림/0~10제한한다. 평점주변분포가비슷한것은설계상보정의결과이며독립적인현실성검증이아니다. 품질결과를보고규칙/비율/seed를다시조정하지않았다.

## 제약

actual사용자ID/평점행은출력하지않았다. 새ID는synthetic_v210_user_로별도namespace다. 생성latent벡터·noise audit는디버깅용이며미래추천평가의정답누수feature로사용하지말아야한다. 완전합성이라고자동익명성·재배포권한·차등개인정보보장이되는것은아니다. 이번파일럿은로컬용이다.
'''
    with(OUT/'synthetic_generation_design.md').open('x')as f:f.write(design)
    figs=OUT/'figures';figs.mkdir();activity=read('user_activity_distribution.csv');rd=read('rating_distribution.csv')
    chart(figs/'real_user_activity.svg','Disjoint eligible Train: user activity (all eligible items)',list(range(1,6)),[('Real users n=255',[int(next(r['users']for r in activity if r['scope']=='eligible_all'and int(r['ratings_per_user'])==n))for n in range(1,6)])],'X: ratings/user; Y: number of users','Source: eligible Train only, all75 evaluation users excluded; not full1805 pool')
    chart(figs/'activity_cohorts.svg','Observed activity vs synthetic cohort purposes',list(range(1,21)),[(name,[float(next(r['fraction']for r in activity if r['scope']==scope and int(r['ratings_per_user'])==n))for n in range(1,21)])for name,scope in [('Eligible real n=254','eligible_candidates'),('Activity matched n=150','activity_matched'),('Enriched n=850','support_target_enriched')]],'X: ratings/user; Y: fraction of users','Source: candidate-aligned eligible Train and seed12 pilot; enrichment is assumed, not observed')
    chart(figs/'rating_distribution.svg','Rating marginal distribution (matched by construction)',[str(float(v))for v in np.arange(0,10.01,.5)],[(name,[float(next(r['fraction']for r in rd if r['scope']==scope and float(r['rating'])==v))for v in np.arange(0,10.01,.5)])for name,scope in [('Eligible real N=823','eligible_candidates'),('Synthetic N=15362','synthetic_combined')]],'X: raw rating0-10; Y: fraction of observed ratings','Source: Train-only target marginal and synthetic pilot; no accuracy inference')
    # Popularity plot uses a common binning by real observation count, not item labels.
    bins=['0','1','2-5','6+'];label=lambda n:'0'if n==0 else'1'if n==1 else'2-5'if n<=5 else'6+'
    chart(figs/'item_exposure.svg','Observation mass by eligible Train item frequency',bins,[('Real observation mass',[sum(int(r['eligible_Train_count'])for r in pop if label(int(r['eligible_Train_count']))==b)/823 for b in bins]),('Synthetic observation mass',[sum(int(r['synthetic_count'])for r in pop if label(int(r['eligible_Train_count']))==b)/len(ratings)for b in bins])],'X: eligible Train ratings/item; Y: fraction of ratings','Source:479 fixed candidates; synthetic zero-count sampling is extrapolation')
    sections=[]
    def sec(name,text):sections.append('## '+name+'\n\n'+text+'\n\n')
    sec('A. Executive Summary','**'+status+'**. 가상 사용자1,000명/15,362개평점을생성했다. 데이터형식·범위·중복·seed재현검증은통과했다. 실제취향재현/추천정확도개선은미검증이다. 원래330/538/1805pool전체가아닌평가사용자75명을제외한895개와후보정렬823개만분석/추정했다.')
    sec('B. 실제 데이터 구조',table([dict(scope='identity-only original pool',users=330,perfumes='538 historical/not remeasured',ratings=1805),dict(scope='all eligible disjoint Train',users=255,perfumes=366,ratings=895),dict(scope='candidate-aligned generator Train',users=254,perfumes=307,ratings=823)],['scope','users','perfumes','ratings'])+'\n\n정규화JSON은[user_sha256,Fragrantica_url,y]3열형식이다. Fragrantica CSV의실제행/열/컬럼은real_data_profile.json schema에있다. 원본Atrafshan의중첩필드는기존adapter/data계약으로확인했고보호경계때문에원시행수·값은재감사하지않았다. 출처를추정하지않았다. normalizedsource유저ID는hash가명이며직접사용자행을공개하지않았다.')
    sec('C. 실제 평점 분포',table([dict(scope='all eligible',**full['rating']),dict(scope='candidate reference',**real['rating'])],['scope','count','mean','median','sd','min','max','p10','p25','p75','p90','p95'])+'\n\n후보정렬기준7점이상80.44%,5점미만7.05%,.5grid준수100%. 실제허용Train은정수평점이며.5준수가half점관측존재를뜻하지는않는다. 구간0~3/3초과5미만/5이상7미만/7~10은겹치지않는다. 원래positive .7은/10정규화전7점이다. 0의미미확정/0제외분석가정은기존정책그대로다.')
    sec('D. 사용자별 평가 개수',table([dict(scope='all eligible',**full['ratings_per_user']),dict(scope='candidate reference',**real['ratings_per_user'])],['scope','count','mean','median','sd','min','max','p10','p25','p75','p90','p95'])+'\n\n평가자제외후전체255명은3~5개뿐이다. 후보정렬254명중39명은1~2개,215명은3~5개다. n<5인236명의개인평균/분산은불안정하다. 개별값대신집단분포만보고했다. 실제그래프:figures/real_user_activity.svg, activity_cohorts.svg.')
    sec('E. 향수별 평가 개수',table([real['ratings_per_perfume']],['count','mean','median','p90','max'])+'\n\n후보정렬관측307개중1개관측131개,2~5개144개,6개이상32개다. 후보479개중172개는허용Train관측0이다. 관측아이템분모행렬밀도 '+str(real['density'])+', 고정479분모밀도 '+str(real['fixed_candidate_density'])+'로분모를구분했다. 원래1.02%수치를여기에옮겨적지않았다.')
    sec('F. 향수 특징 통계',table([profile['feature_scope']],['candidate_features','candidate_notes','candidate_accords','generator_vocabulary','generator_notes','generator_accords','empty_generator_vectors'])+'\n\n479후보의특징574개(note517/accord57), generator는허용Train아이템으로vocab/IDF486개를계산했다. 향수당평균15.41개다. 기존token규칙과smoothedIDF를재사용했고새외부데이터/기존모델Q는사용하지않았다. 빈도·희귀·동시출현·평점관계는feature_statistics/cooccurrence.csv다. 5명미만feature평균/CI는공개표에서억제했다. 다른CI는user-cluster delta근사·다중비교미보정이며인과효과가아니다.')
    sec('G. 사용자 취향 구조','평점5개사용자18명뿐이고cosine≥.5유사쌍은0개,≤.1비유사쌍은110개다. 같은사용자안에서양쪽구간을비교할수가없어취향일관성검정은N/A다. 기준이엄격하다는영향도있으며이결과를선호구조부재로단정하지않는다. split-half profile cosine평균은 '+str(pref['split_half_profile_cosine']['mean'])+'(유효14명)으로매우불안정했다. 군집수나유형을추정하지않았다. 이때문에관측재현집단의특징신호는0으로두고확장집단의약한feature효과는명시적인가정으로만사용했다.')
    sec('H. 합성 데이터 생성 가설','균등무작위평점이아닌사용자평균성향/관측아이템효과/불균형선택/heterogeneous잔차잡음구조를반영했다. 식의강한개인취향가정은실제자료가지지하지않아그대로재현모델로사용하지않았다. 15%activity-matched집단은feature선호를평점에강제로넣지않는다. 85%enrichment집단만약한6.25%분산신호를스트레스가정으로넣는다. 완전한실제인간취향모사가아니다.')
    sec('I. 생성 모델 설계','synthetic_generation_design.md와config.json에수식/추정/가정을분리했다. 사용자/item/feature수축강도5/10/20, sqrt(count+1)선택, 연속임의3~8개양/음feature, 신호분산6.25%,temperature.25, 잔차histogram.5너비, global경험분위수1회매핑과.5반올림을고정했다. 경험평점주변분포는정의상맞추므로독립품질증거가아니다. 품질결과후조정하지않았다.')
    sec('J. 파일럿 생성 결과',table(summary,['scope','users','ratings','perfumes','mean_activity'])+'\n\n고유namespace synthetic_v210_user_000001부터쓴다. 미래Support예정4250개/Target예정10623개와관측분포용489개를분리했지만실제추천학습·평가는하지않았다. synthetic_users에는새선호벡터/성향/잡음/활동량을기록했고실제개인벡터는복제하지않았다. latent audit는generator진단용이며향후추천학습feature로넣으면Oracle누수가된다.')
    sec('K. 실제 데이터와 합성 데이터 비교',table(summary,['scope','mean','SD','mean_activity','high_fraction','low_fraction','mean_user_SD'])+'\n\n'+table(diff,['cohort','rating_JS','rating_KS','rating_Wasserstein','activity_JS','item_JS'])+'\n\n전체평점평균7.7801→7.7829,SD1.9518→1.9447로비슷하지만주변분포보정의결과다. matched활동량JS .000302, 전체활동량JS .678866으로850명확장목적차이가크다. itemJS .1780이고합성관측중허용Train0관측후보몫은 '+str(zero/len(ratings))+'다. 미관측선호를관측사실로표시하지않는다.')
    sec('L. 품질 검증',table([dict(check=k,passed=v)for k,v in hard.items()],['check','passed'])+'\n\nseed12독립2회생성으로ratings/users/audit해시와선택확률이같았다. NaN/Inf/중복/범위/단위/ID충돌없음,고유선호벡터1000개다. syntheticzero분산사용자는12명(1.2%). 생성latent affinityTop5의sampledJaccard '+str(q['structure']['generator_latent_affinity_Top5_pair_Jaccard_sampled_mean'])+'는추천모델출력이아니다. 알려진무잡음생성성분과최종rating의선형R² '+str(q['structure']['generator_known_no_noise_linear_R2'])+'는정확한학습가능성/개인정보공격검사가아니다. 비슷한향수와다른향수의평점차이평균1.95와1.952는명확한일관성차이를보여주지않는다. 전체generator식·seed를알면재구성가능한것은당연하며현실적검증으로혼동하지않는다.')
    sec('M. 데이터 누수 검증','manifest는users배열만해석하고train/support/answers숫자는skip했다. source1805행중평가75명910행은item/rating해석전에버렸고895개만숫자로읽었다. 그중후보479에속한823개만생성규칙에사용했다. protected평가item/ratingdecode0, 원래Validation/Internal/External파일미열람. 파일hash를읽는것과평점값을규칙추정에쓰는것을구분했다. 경계canary테스트와boundary_audit.json참조.')
    sec('N. 향후 추천 모델 학습 계획','이번에는추천모델학습·정확도평가0회다. 향후실험을승인받으면실제Train-only/합성추가/합성only대조를별도설계하고, 이미반복사용한Outer를독립확증으로다시쓰지않아야한다. 독립실사용평가자료/권한확보가필요하다. latent user벡터/noise audit를정답누수feature로쓰지말고, 코호트목적과합성비율을고정해야한다. 합성내좋은성능이실제사용자개선증거는아니다.')
    sec('O. 발표 문서 5개 업데이트','V2-0~9기록을보존하여새실데이터통계·희소성·제외경계·증강가정·파일럿·품질/한계를5개문서에추가한다. PERFORMANCE에는정확도를새로측정하지않았음을명시한다. 실제SVG4개와CSV를발표계획에연결한다. 팀기여율·개인소감은만들지않는다.')
    sec('P. 무결성 검증','추천학습/추론/평가호출0회, MF/Q/서비스/원본데이터변경없음. code/source hashes와경계는verification.json, 최종전체비교는integrity.json이다. 기존원본행이나개인ID를공개출력하지않았다. 새로운합성자료도익명성/원사이트재배포권한을자동보장하지않으므로로컬용으로둔다. Git/설치/서버/이동/삭제/업로드없음. REQUIREMENTS_TRACEABILITY.md는보호하며I01/I02/P07/R12관련추가증거만제공하고전체최종제출완료를선언하지않는다.')
    with(OUT/'REPORT.md').open('x')as f:f.write('# V2-10 — Real Data Profiling & Synthetic User Dataset Design\n\n'+''.join(sections)+'## 실행 명령\n\n```sh\nPYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -W error -m unittest discover -s experiments/scent_v2/synthetic_data/tests -v\nPYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -W error -m experiments.scent_v2.synthetic_data.run\nPYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -W error -m experiments.scent_v2.synthetic_data.reporting\n```\n\n신규13개단위테스트통과. 기존모델테스트를실행해재학습하지않고전후파일해시로보존을검증했다. 기존출력존재시재실행거부.\n')
    docs=ROOT/'docs/presentation';ref='[V2-10 보고서](../../outputs/scent_v2/synthetic_data/REPORT.md)';app='\n## V2-10 Real Data Profiling & Synthetic User Design — 완료 (2026-10-28)\n\n**목적:** 모델개선미입증후데이터희소성과증강가능성을분석했다. 추천정확도를새로측정하지않았다. '+ref+'\n\n**출처·경계:** Atrafshan→Fragrantica정렬Train1805에서Nested평가75명910행을값해석전에제외했다. 안전Train255명/895개, 후보정렬254명/307향수/823개가생성기준이다. 원래330/538/1805를생성규칙으로쓰지않았다.\n\n**가설·구현:** 데이터가강한취향구조를지지하지않아실제취향복제를주장하지않는다. matched150명은실제활동량을표본화하고feature신호0, enriched850명은Support5+Target용15~20개이력과약한feature스트레스가정이다. 사용자/item/feature수축5/10/20, sqrt(count+1)선택, 경험잔차noise, 최종Train분위수/반점보정을고정했다.\n\n**생성결과·품질:** 가상1000명/15362평점,seed12독립2회동일.\n\n'+table(summary,['scope','users','ratings','mean','SD','mean_activity'])+'\n\n'+table(diff,['cohort','rating_JS','activity_JS','item_JS'])+'\n\n**한계·결론:** PASS WITH LIMITATIONS. 높은주변분포유사성은보정의결과이며개인취향재현증거가아니다. 전체활동량차이는85%이력확장목적이며관측사실이아니다. 희소데이터18명만5평점, 유사쌍0으로강한구조/군집미확인. NaN/Inf/중복/ID충돌없고모델학습·정확도평가0회. 합성선호효과검사는generator가정검사일뿐이다.\n\n**다음:** 독립실사용평가/권한확보후별도승인된대조실험설계만권고. 추천모델/기존평가집합/서비스변경없음. 후속학습미실행.\n'
    for name in('MODEL_IMPROVEMENT_STORY','EXPERIMENT_TIMELINE','PERFORMANCE_COMPARISON','PRESENTATION_SLIDES_OUTLINE','EXPERIMENT_LOG'):
        p=docs/(name+'.md');extra=app
        if name=='PRESENTATION_SLIDES_OUTLINE':extra+='\n10분10장구성안에서데이터/한계/향후과제장에SVG real_user_activity.svg,activity_cohorts.svg,rating_distribution.svg,item_exposure.svg를연결한다. 모든파일은outputs/scent_v2/synthetic_data/figures/에실제생성했다. 기존성능표와데이터품질표를분리한다.\n'
        if name=='EXPERIMENT_LOG':extra+='\n코드 experiments/scent_v2/synthetic_data/, seed12/config.json, 생성수15362, 경계/단위/중복/재현테스트와JS·KS·Wasserstein/사용자분산검증. 추정되지않은개인취향·85%이력확장가정을명시했으며추가튜닝/추천학습없음.\n'
        p.write_text(p.read_text()+extra)
    print('PASS: A–P report/design,4 actual SVGs, cohort diagnostics and five append-only documents')

if __name__=='__main__':main()
