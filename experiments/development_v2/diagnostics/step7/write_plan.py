"""Create V3 design document from STEP7 aggregates. No new model, fitting or search."""
import sys,json,csv,ast
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_feasibility import ROOT,OUT,DEST,guard,describe,sha

def read(name):return json.loads((DEST/name).read_text())
def mdtable(rows,keys):
    s='| '+' | '.join(keys)+' |\n|'+'---|'*len(keys)+'\n'
    for r in rows:s+='| '+' | '.join(f'{r[k]:.6f}' if isinstance(r.get(k),float) else str(r.get(k,'N/A')).replace('|','/') for k in keys)+' |\n'
    return s

def main():
    guard();target=ROOT/'reports/V3_PERSONALIZATION_FEASIBILITY.md'
    if target.exists():raise RuntimeError('Do not overwrite existing report')
    d=read('train_distribution.json');m=read('fixed_fullmodel_personalization.json');nu=read('stored_newuser_cv_evidence.json');syn=read('fixed_fullmodel_synthetic_support3.json')
    with (DEST/'proposed_v3_split_feasibility.csv').open() as f:counts=list(csv.DictReader(f))
    priorities=[
      {'priority':1,'method':'低차원 bias-aware MF + bias/latent 분리 정규화 + 고정 Linear Hybrid','benefit':'3개support에서식별해야할차원축소·bias/latent 균형을분리검증','risk':'bias는유용할수있음;표본부족으로과적합/성능저하가능','complexity':'중간'},
      {'priority':2,'method':'latent/user-bias 별도 fold-in penalty','benefit':'userbias와latent를같은λ로축소하는가정검토','risk':'작은ridge는수치/추정분산을키움;개인화강화≠정확도개선','complexity':'낮음~중간'},
      {'priority':3,'method':'Content 중심 profile·confidence fallback','benefit':'미학습item/희박support에도metadata로취향반영','risk':'현실제Content단독NDCG는V1Hybrid보다낮음','complexity':'낮음'},
      {'priority':4,'method':'같은성분의Linear/minmax 제한비교','benefit':'RRF에서버린score간격과component분포검토','risk':'candidate별정규화는outlier/후보변화에민감','complexity':'낮음'},
      {'priority':5,'method':'side-information cold-start/잔차latent 구조','benefit':'평점1~2개향수의추정분산을줄일가능성','risk':'복잡도와튜닝폭확대,새metadata의권한/의미정합필요','complexity':'높음·이번우선범위밖'}]
    hypotheses=[
      {'hypothesis':'현재train이매우희소하고co-rating근거가적다','level':'CONFIRMED','evidence':'98.9833% sparsity; singleton190/538; overlap>=2 userpairs523/54285'},
      {'hypothesis':'개인별취향차이가전혀없다','level':'REJECTED','evidence':'co-rating>=2쌍평균절대차.167920; fullmodel Top10set98.79% user변화;단,효과적일반화증거는아님'},
      {'hypothesis':'3support로8factor+1bias를data만으로유일식별가능','level':'REJECTED','evidence':'3equations vs9unknowns; ridge가해를정해줄뿐데이터식별성을증가시키지않음'},
      {'hypothesis':'희소성·편향된평점·bias학습구조가latent약화에기여','level':'SUPPORTED','evidence':'80.39%고평점/3.43%저평점,평균적은관측·bias 우세·작은latent;독립ablation없음'},
      {'hypothesis':'많은평점을받은item만bias가커진다','level':'INCONCLUSIVE','evidence':'absbias-vsdegree Spearman.242750, bias-vsmeanrating.880458;빈도만의인과효과분리불가'},
      {'hypothesis':'0.87%는개인화기여율이다','level':'REJECTED','evidence':'142request별SD(pq)/SD(bi)의단순평균;공분산/순위비선형을무시한비율'},
      {'hypothesis':'fold-in이수치적으로불안정하다','level':'REJECTED','evidence':'기존held-userCVcondition<=2.016947;문제는신호/추정목표이지solver발산아님'},
      {'hypothesis':'CF가약할때Content는조건부보완수단이된다','level':'SUPPORTED','evidence':'metadata train coverage높음/학습모델없는item에도가능,하지만Content단독정확도우위아님'},
      {'hypothesis':'특정λ/epoch/bias제어가V3정확도를향상시킨다','level':'INCONCLUSIVE','evidence':'STEP7은학습·탐색을하지않음;계획은검증전가설'}]
    text=f'''# STEP7 — 개인화 가능성 분석 및 V3 실험 설계

**현재 데이터에는 취향 차이 신호가 있으나, 향수 3개만으로 안정적인 latent 개인화를 충분히 학습했다고 볼 근거는 부족하다. V3는 승인 전 계획이며 구현·학습·하이퍼파라미터 탐색을 하지 않았다.** Frozen V1은 계속 웹사이트에 연결된 기존 모델이고 V2는 독립 실험 상태를 유지한다.

## 1. 데이터 분포 — 기존 train만

데이터범위는변경하지않은 `outputs/validation/train_exclude_3.json`이다. Fragrantica는상품메타데이터분석에만읽었다. 기존validation/Test정답·사용자별평가결과는열지않았다.0제외는계속분석가정이며0의의미를새롭게확정하지않는다.

| 항목 | 실측 |
|---|---:|
| 학습 사용자 / 향수 / 평점 |330 /538 /1805|
| 행렬 크기 / 전체가능pair |330×538 /177540|
| 관측밀도 /희소도 |1.016672% /98.983328%|
| 사용자 평점수 평균 /중앙 /범위 |5.4697 /4 /3–38|
| 향수 평점수 평균 /중앙 /범위 |3.3550 /2 /1–29|
| 평점1개 향수 |190/538 =35.3160%|
| long-tail(평점≤2) |321/538 =59.6654%|
| long-tail(평점≤5) |450/538 =83.6431%|
| 평점이모두같은사용자 |15/330 =4.5455%|
| 거의같음(std≤.05) |66/330 =20.0000%|
| 모든평점고평점(≥.7) |154/330 =46.6667%|
| 전체고평점≥.7 /저평점≤.3 |80.3878% /3.4349%|
| 정규화평점 평균/std |.773573 /.186065|
| 학습평점상위10상품점유율 |10.8587%|
| 상위20%상품의평점점유율 |54.1274%|
| item관측수 Gini |.470310|
| bipartite 연결성 |1component,330users+538items|
| 두향수이상공동평가userpair |523/54285 =.9634%|

long-tail·near-same은이번진단의명시적기준이지교수필수정의나기존평점정책이아니다. std는관측평점의population std(ddof0). singletonitem의std0은여러사용자합의가아니라관측1개라는뜻이다.

사용자별평균/표준편차/고저평점비율과향수별평균/표준편차분포, 평점수전체histogram은`train_distribution.json`에집계로저장했다. 사용자ID/개별평점은보고서에없다. 사용자브랜드고유수평균4.6333/중앙3, 관측향수쌍metadata Jaccard거리평균.887794. 이는향구성이넓다는지표이며평점기반취향분별/실제만족도를뜻하지않는다. 상품노트/accordcoverage수치는동일JSON참조.

서로2개이상공동평가한523userpair의공통상품평점절대차평균.167920(중앙.15)로실제차이는있다. 그러나90.93%userpair는공동평가0개이고,≥2개는.96%에불과해이를모든사용자취향을안정적으로학습할근거로확대할수없다. 그래프전체는연결돼있으므로단절component만으로현재현상을설명하는것도맞지않는다.

## 2. 저장된 V2 전체-train MF 분해

다음은**전체train으로학습된저장모델**이며STEP6의사용자제외CV모델과다르다. `model.npz`는allow_pickle=False로읽고배열을read-only로설정했다. fit/SGD update는0회다. 알려진330명의P를사용하여각사용자seen을제외한479후보범위의156337개 user-candidate latent항을분석했다.

| 항목 | 값 |
|---|---:|
| itembias 평균/std(538개) |−.002323 /.056561|
| itembias절대값 평균/중앙 |.041815 /.031413|
| latent항 전체pair평균/std |.00000890 /.006850|
| latent절대값 평균/중앙 |.005309 /.004276|
| 사용자별latent SD평균 |.006658|
| 사용자별SD(latent)/SD(itembias) 평균 |.114899|
| 전체rawMF vsitembias 순위상관평균 |.989121|
| latent포함후Top10순서변경사용자 |100%|
| latent포함후Top10집합변경사용자 |98.7879%|
| bias-only/전체MF Top10 Jaccard평균 |.622808|
| candidate평균순위이동 |14.1224positions|
| 사용자쌍MF Top10 Jaccard평균 |.507218|

사용자간 Top10 Jaccard에는 서로 다른 seen-item 제외의 영향도 포함된다. 작은항도상위상품들의점수간격이작으면순위를바꿀수있다. 따라서높은전체순위상관·작은SD비율을‘개인화없음’또는직접적인기여율로해석하면안된다. Top10집합이변했다는것도정답품질이좋아졌다는증거는아니다. 후보별itembias와latent는공분산이있고,clipping과TopK선택은비선형이다.

itembias와상품평균평점Spearman .880458,|bias|와관측수.242750, Qnorm과관측수.042784. 관측수1개향수의평균|bias|.02994, >10개향수는.06743이지만단조/인과라고확정할수없다. 관련그룹표는다음과같다.

'''+mdtable(m['degree_bands'],['observations','items','mean_abs_bias','mean_factor_norm'])+f'''

## 3. 학습 구조·신호 크기

실제V2는μ={m['mean']:.6f}, biasedfactor8, Gaussian(0,.05)P/Q초기화, bias0초기화, per-edgeL2.01, lr.01, fulltrain30epoch다. b와latent를같은SGD에서학습한다. biasgradient는e+λb, latentgradient는eq+λp/ep+λq라작은상대vector가초기/최종gradient크기에영향을준다. 높은평점비중·작은co-rating·mean/bias만으로설명되는성분이많다는조건과함께latent학습이약할가능성을지지한다.

저장상태에서만계산한factor좌표gradient RMS평균.004431, itembias절대gradient평균.091384. Pnorm평균.135777, Qnorm평균.133973. 이숫자는서로다른차원/단위의**최종상태스냅샷**이며‘bias가20배빨리학습됐다’는시간추론에사용하면안된다. 실제gradient trajectory와초기/중간P/Qnorm기록은없다. 학습속도차이는INCONCLUSIVE다.

기존loss_curves에는fold별train loss와nestedstopRMSE만있다. STEP6기록처럼knownfold20epoch후train loss는더내리지만stopRMSE는악화했다. 이정지기준이latent를너무일찍멈췄는지는후속고정프로토콜ablation전까지가설이다. 이번에는재학습하지않았다.

## 4. 신규 사용자 support3 신호와 데이터 가용성

기존STEP6의142명honest user-heldoutCV기록만재사용했다. 개인latent SD/itembias SD **.008659=약.87%**는각request에서계산한 `SD_candidate(pq)/SD_candidate(b_i)`의142명동일가중평균이다. pooledSD비율도,정확도나분산기여율도아니다. 위전체trainknownuser11.49%와는모델/사용자/학습범위가달라직접적인처리효과비교가아니다.

기존142명support평점mean의평균.775352, support std평균.101702; fold-in개인vector norm평균.009114/중앙.007289, userbias평균−.003539/std.062113. 예측은여전히itembias순위상관.999861이다. 조건수≤2.016947로solver는안정적이다. equation3개로factor8+userbias1의9개unknown을data만으로유일하게정할수는없다. ridgeprior가유일한수치해를만들어주지만충분한식별신호를새로만들지는않는다.

Train의support3+heldout적격은최대187명이나STEP5factor/후보coverage후142명만남았다(45명제외). 그142명은구성상support모두foldtrainedfactor와일치하며,이사실을모든신규사용자coverage100%로표현하면안된다. 전체catalog나사용자가임의로선택한향수에대한factor가용성은별도다. 신규fold의Q배열은저장되지않았으므로supportQ분포·새fold예측은**N/A**로남긴다. 이번재학습금지와충돌하지않도록STEP6처럼fold모델을복원학습하지않았다.

대신현재저장된fullmodel에공개candidate첫3개와합성high/low/mixed/equal/zero평점을넣는**비평가용입력민감도**를검사했다. λ1.0고정,5경우MF Top10집합은모두같고high/lowJaccard1.0이었다. p와userbias·score는달라지지만공통item순위를극복하지못한예시다. 단1개의상품조합이며일반화/새사용자정확도실험이아니다. supportQnorm/특이값과각scenario통계는fixed_fullmodel_synthetic_support3.json참조.

## 5. 가설 판정

'''+mdtable(hypotheses,['hypothesis','level','evidence'])+'''

‘데이터희소성→현재itembias지배’의상관/구조근거는있지만희소성만조작한실험이없어인과는SUPPORTED까지만이다. itembias제거를정답으로정하지않는다. Content는cold-item/차별적인노트입력/약한협업증거에유리한조건이있지만기존신규Content .023386은V1Hybrid .047663보다낮아순수Content우월의근거가아니다.

## 6. V3 사전 평가 설계 — 아직 학습하지 않음

### 역할 분리

기존train1805평점밖으로나가지않는다. 유효history≥4인187명을seed **20261109**의hash순으로outer3개usergroup으로고정한다. 최소3평점인143명은train전용이며정답을억지로만들지않는다.

- **탐색/epoch정지자료:** 각inner-fit부분안에서만사용한다. V1/V2control의원래stop정책을복원할때도outer/inner선택정답을보지않는다. 새V3후보의epoch40은사전고정해별도epoch검색을막는다.
- **후보선택:** 각outertrain에서남은eligible사용자를inner2userfold로나눠support3신규사용자NDCG로선택한다. MFfactor와IDFfit에서innerheld사용자전체를제외한다.
- **신규사용자중심확인:** outerheldgroup은선택설정lock후1회확인한다. outer결과로동일실험후속fold의grid/규칙을바꾸지않는다. outer는선택workflow평가이며최종성능을본후best모델을재선택하지않는다.

이는V2에서이미학습·진단에사용된train의재사용이다. seed/분할이달라져도완전히독립적인검증데이터가된것은아니다. 기존validation·InternalTest·ExternalTest는전부V3선택에서제외한다. 새독립데이터가없으면개발근거로만표현한다.

### 공통 candidate·support·heldout

입력은 웹의 명시적0–10평점을 /10하여 [0,1]로 통일한다. 명시 입력0점은 유효하며 Atrafshan 원자료0점의 미확정 의미와 구분한다. support는 Content프로필과 fold-in의 추론 입력에만 사용하고 학습에는 넣지 않는다.

candidate는모든fold/모델에서원래 **479개**로고정한다. MF미학습item을몰래pool에서삭제하지않는다. support는해당fit에서factor가생길것으로예상되는observeditem중seed로선택한3개; 전체479내history≥4가필요하다. 나머지candidate내평점은모두heldout이며factor미가용정답도분모에남긴다. unknownMF는NaN,Hybrid는같은명시적Content→trainpopfallback정책을사용한다. pureMF가못맞힌정답은miss,추천이10개미만이어도P분모는10이다.

STEP5는각foldtrained후보424/423/433으로제한하고4개availablehistory를요구했다. 새blueprint는479고정·3knownsupport+heldoutunknown허용이라**프로토콜이다르며과거NDCG와직접비교금지**다. V1/V2control도새fold에서공정하게재평가해야한다. 이번에그학습/평가는하지않고아래**가용성숫자만**계산했다. factor생성가능성은‘MF가모든observedfititem에factor를만든다’는현재구현가정이지실제학습완료결과가아니다.

'''+mdtable(counts,['stage','outer_fold','inner_fold','train_users','train_ratings','held_users_before_coverage','evaluation_users','positive_users','unknown_factor_heldout'])+'''

outer평가가능158명(55/52/51),positive145명(51/47/47). inner가능43–57명/positive38–53명으로층을더추가하면표본이작아질가능성이높다. unknownfactorheldout은outer48/69/74개이므로Contentfallback성능과coverage를반드시같이보고한다. 분할수·평가자수를성능을보고조절하지않는다. feasibility에서innerpositive<20또는outerpositive<30이면모델튜닝전에설계를중단/승인요청한다. 현재blueprint숫자는그기준을통과한다.

### 지표·선택·중단

Primary=신규support3 NDCG@10, positive≥.7, empty-positive사용자는평균에서제외하고분모를보고. Secondary=같은fold조건의P@10/R@10/known-user보조NDCG/Top5행동검증/catalogcoverage/상위10상품노출비중/Gini/entropy/목록내token다양성/fallback/latency. score가개인화돼달라졌다는것과정확도개선을분리한다. itembias-vsMF순위상관·support입력변화에대한Top10민감도도진단지표다.

Inner선택은세부점수차가.002이내이면단순모델을택하는**권고tie-rule**를사전등록한다. .002는교수성능목표나통계검정기준이아니며실행승인시에확정해야한다. coverage가V1의.8미만또는top10노출점유율이V1대비+.10이상인후보는정확도최고여도운영후보로승격하지않는품질guardrail을권고한다. 이기준도제품의실측효용함수가아닌투명한설계가정이다. paireduser bootstrap은outerfold반복구조를보존하고독립일반화유의성주장에쓰지않는다.

NaN/Inf·누수·데이터/보호해시차이·표본부족이면즉시중단. 제한된grid가V1을일관되게개선하지못하면범위확대없이‘미개선’으로끝낸다. outer결과를보고추가grid를열지않는다.

## 7. 우선 모델과 제한된 실험 예산

먼저구현할모델은 **factor2 bias-aware MF + bias/latent 분리 L2 + 고정Linear Hybrid**다. 3support의unknown수를줄이고bias를유지한상태로역할을분리하려는최소변경가설이다. factor2+userbias3unknown이어도A가fullrank/잡음충분성을보장하지않으므로ridge는유지한다. 역수SD로약한latent를무조건증폭하는방식은권하지않는다.

'''+mdtable(priorities,['priority','method','benefit','risk','complexity'])+'''

### 사전등록 후보6개 (아래는 계획이며 코드·학습 없음)

공통μ=trainmean,lr.01,latentL2.01,epoch40고정,Content=기존neutral accord/note.5/.5,새foldin은latent/userbias별penalty를분리한다.40epoch는이계획의고정예산이며최적이라고측정한값이아니다.

| 후보 | factor | bias L2 | fold-in latentλ / biasλ | fusion |
|---|---:|---:|---|---|
| A |2|.01|1 /1|Linear Content.25|
| B |2|.1|1 /1|Linear Content.25|
| C |2|.1|.1 /1|Linear Content.25|
| D |4|.1|.1 /1|Linear Content.25|
| E |2|.1|.1 /1|Linear Content.75|
| F |2|.1|.1 /1|candidate-minmax Content.25|

A→Bはbias処理、B→Cはfold-in、C→Dはdimension、C→E/Fはfusionの限定比較だ。rankfusionは既存V2controlとして残し、今回は新しいRRF係数を探さない。全組合せCartesian探索はしない。6政策に必要なMF学習設定は3種だけ(A・B/C/E/F共通・D)で、fold-in/fusion差は同じ学習weightsを再利用する。

controlsはV1Hybrid(元のf4/160)、固定V2Hybrid、純Contentneutral。各outerのinner2fold6回でMF本学習5種×6=30、outer固定候補+V1/V2control3種×3=9、計39本学習。V2controlのnestedstopprobeはinner6回+outer3回の追加9本なので、primaryseed12は**最大48SGD fit**。全選択終了後modelseed29の固定outer診断12fit追加なら合計**最大60fit**。追加seedでモデルを再選択しない。step8開始時にこの上限を確定して保存する。

MacBook Air M1級CPUの見積もりはprimary+stabilityで約5–15分、20分上限・peakRAM1GBを目安に計測する。STEP5の実測111.7秒/単一processpeak約125MBを参考にした**未実行の概算**であり、環境/実装/threadsにより変わる。最悪単純上限1805edges×160epochs×60fit≈1733万SGDupdateだがinnerfitは約850–920edgesで実際は小さい。batch/並列化最適化で結果を変えず、まず説明可能な小規模実装を優先する。

## 8. 次段階の実行順序と未完了

1. ユーザーがprotocol/6候補/guardrail/予算を承認し、別V3ソースとprivate出力場所を確定。
2. 同じfold・candidate・user境界のcontrolsとリークテストを先に実装。
3. 分離正規化MF/9unknown→低dimension・fold-in・Linear/minmaxの段階比較。新しい個人化指標とgradient/ベクトルtrajectoryも保存。
4. inner選択をlockしてouter確認を一度だけ実行。既存validation/Test不使用。
5. 改善が不確実ならV1を保持して終了。ウェブ接続・Git反映・独立Test消費は別承認。

**今回未実施:** V3実装/学習、係数探索、新しい精度評価、独立Test、web接続。foldQがなく追加解析不能な項目はN/A。既存train再利用の限界は解消していない。今回の候補/閾値は設計案であり、次段階承認前の完成モデルではない。

## 9. エビデンス・保護・Git

新コードは`experiments/development_v2/diagnostics/step7/`、新結果はignored `outputs/development_v2/diagnostics/step7/`。実行中profileguardでproject fit/train_mfを禁止し、実行記録fit0。既存V1/V2ソース・設定・models・既存結果は変更しない。protected19/manifestは元基準のまま、manifest **3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130**。旧禁制データ/評価/webは内容を開かずsize/mtimeも比較した。過去Finder/demo.logの変更を今回の変更として扱わない。

branch development-v2、expected status `?? experiments/development_v2/`。新ソースはレビュー対象、結果/モデル/報告書は既存ignoreを維持。staging/commit/push/merge/rebase/tag/remote設定/ネットワーク/サーバ制御0。元のV1・V2レポートは上書きしない。統計はaggregateのみでuserID・個別rawratingを報告書に含めない。
'''
    # Keep the user-facing document in Korean; model/formula notation remains unchanged.
    text=text.replace('低차원','저차원').replace('A→Bはbias処理、B→Cはfold-in、C→Dはdimension、C→E/Fはfusionの限定比較だ。rankfusionは既存V2controlとして残し、今回は新しいRRF係数を探さない。全組合せCartesian探索はしない。6政策に必要なMF学習設定は3種だけ(A・B/C/E/F共通・D)で、fold-in/fusion差は同じ学習weightsを再利用する。','A→B는 bias 처리, B→C는 fold-in, C→D는 차원, C→E/F는 fusion의 제한 비교다. RRF는 기존 V2 control로 남기고 새 계수를 찾지 않는다. Cartesian 전체조합 탐색 없이 6개 정책에 필요한 3개 MF 학습 설정만 사용하고 fold-in/fusion 차이는 같은 weights를 재사용한다.')
    # Remaining sections are rewritten below in Korean for clarity.
    marker='controlsはV1Hybrid'
    text=text[:text.index(marker)]+'''Controls는 V1 Hybrid(기존 f4/160), 고정 V2 Hybrid, 순수 Content neutral이다. outer3×inner2=6개의 내부 fit 조건에서 MF 본학습5종×6=30, outer 확인에 고정 후보+V1/V2 control3종×3=9로 총39본학습이다. V2 control의 nested stop probe가 추가9회이므로 중첩 신규 사용자 평가까지48fit이다. 선택된 V3와 V1의 known-user 보조 진단3fold(6fit)를 추가해 primary seed12 총 **54fit**으로 제한한다. 선택을 모두 고정한 뒤 seed29 outer 진단12fit을 추가하면 **총 최대66fit**이다. 그 seed 결과로 재선택하지 않는다. 다음 구현 단계 시작 전에 예산을 확정·기록해야 한다.

Known-user 보조 진단은 각 outer-fit 안에서 history≥4인 사용자별1평점을 hash로 가리고 V1/선택된 V3를 동일 조건으로 비교한다. 설정은 inner 신규사용자 CV에서 이미 고정하며 이 보조 결과로 재선택하지 않는다. 이 정답 역시 이전 개발에 사용된 train이므로 독립 일반화 평가가 아니다. outer 신규사용자 정답은 계속 접근하지 않는다.

MacBook Air M1급 CPU 추정 예산은 약5–15분,20분 상한/peakRAM1GB 목표다. STEP5 실측111.7초/독립process peak 약125MB를 참고한 **미실행 추정**이며 보장 수치가 아니다. 단순 최악 상한1805edges×160epochs×66fit≈1906만SGDupdate이나 innerfit은850–920edges로 더 작다. 실제시간/메모리는 다음 단계에서 측정하고 예산을 넘기면 범위를 늘리지 않는다.

## 8. 다음 단계 순서·미완료

1. 사용자가 protocol·6후보·guardrail·예산을 승인하고 별도 V3 소스/비공개 출력 경로를 확정한다.
2. 동일fold·candidate·사용자 경계의 controls와 누수 테스트를 먼저 구현한다.
3. 분리 정규화/저차원MF, 별도 fold-in penalty, 제한된 fusion 비교를 실행한다. gradient/latent trajectory도 저장한다.
4. inner 선택을 lock하고 outer를 한 번 확인한다. 기존 validation/Test는 사용하지 않는다.
5. 개선이 불확실하면 V1 유지로 끝낸다. 웹 연결·Git 반영·독립Test 사용은 별도 승인이다.

**이번에 하지 않은 것:** V3 구현/학습, 하이퍼파라미터 탐색, 새 정확도 평가, 독립Test, 웹 연결. 저장된 fold Q가 없어 추가 분석할 수 없는 항목은 N/A다. 기존 train 재사용에 따른 개발 편향은 해결되지 않았다. 후보·예산·임계값은 다음 단계 승인 전 설계안이다.

## 9. 증거·무결성·Git

새 소스는 `experiments/development_v2/diagnostics/step7/`, 새 결과는 ignored `outputs/development_v2/diagnostics/step7/`에 있다. 실행 중 profile guard가 project fit/train_mf 호출을 금지하며 실제0회다. V1/V2 소스·설정·모델·기존 결과를 수정하지 않는다. protected19와 manifest는 원래 기준을 유지한다: **3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130**. 금지된 원본/평가 파일과 웹은 내용 접근 없이 size/mtime도 비교한다. 과거 Finder/demo.log 이력을 이번 변경으로 간주하거나 기준을 재설정하지 않았다.

브랜치 development-v2, 예상 Git 상태는 기존처럼 `?? experiments/development_v2/`다. 새 소스만 향후 검토 대상이며 결과/모델/보고서는 기존 ignore 정책 유지다. staging/commit/push/merge/rebase/tag/remote 설정·네트워크·서버 제어0, 원본 V1/V2 보고서 덮어쓰기0이다. 보고서는 집계값만 포함하고 사용자ID·개별 원본 평점을 기재하지 않는다. 최종 보존 증거는 step7/final_verification.json을 참조한다.
'''
    distribution_rows=[{'분포':label,**d[key]} for key,label in [('user_mean_rating','사용자평균평점'),('user_rating_std','사용자평점std'),('user_high_fraction','사용자고평점비율'),('user_low_fraction','사용자저평점비율'),('item_mean_rating','향수평균평점'),('item_rating_std','향수평점std')]]
    text=text.replace('사용자별평균/표준편차/고저평점비율',mdtable(distribution_rows,['분포','mean','median','p25','p75','min','max'])+'\n사용자별평균/표준편차/고저평점비율',1)
    target.write_text(text)
    plan={'implemented':False,'trained':False,'selection_data':'original train only; nested user CV design','split_seed':20261109,'outer_user_folds':3,'inner_user_folds':2,'support':3,'candidate_pool':479,'primary_metric':'new-user NDCG@10','policies':6,'unique_v3_mf_training_recipes':3,'primary_model_seed':12,'optional_fixed_diagnostic_seed':29,'max_sgd_fits_primary':54,'max_sgd_fits_including_optional':66,'wall_clock_budget_minutes_estimate':[5,15],'hard_budget_minutes_proposed':20,'approval_required_before_implementation':True}
    p=DEST/'v3_design_blueprint.json'
    if p.exists():raise RuntimeError('Do not overwrite design')
    p.write_text(json.dumps(plan,indent=2))
    print('New Korean feasibility/design report written; V3 model implementation/training absent.')
if __name__=='__main__':main()
