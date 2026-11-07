"""Aggregate real-empty store status, protocol and A–P documentation. No model eval."""
import json,sqlite3
from pathlib import Path
from .app import OUT,ROOT
from .engine import Engine
from .storage import EvaluationStore,VERSION


def write(name,value):
    """Create new finite audit output exclusively; no overwrite of existing studies."""
    with (OUT/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)


def main():
    policy=json.loads((OUT/'operating_policy.json').read_text());engine=Engine();store=EvaluationStore(OUT/'data',engine,policy);data=store.analyses()
    assert data['collection']['actual_new_participants']==0 and data['collection']['ratings']==0
    store.export_evaluation()
    write('collection_status.json',dict(**data['collection'],collection_enabled=True,operating_policy_confirmed=True,actual_new_data=0,fixture_data_excluded=True))
    write('data_quality_report.json',data['quality']);write('offline_evaluation.json',data['offline']);write('feedback_analysis.json',data['feedback'])
    schema={}
    with store.connection() as c:
        for table in ('participants','v21_consents','v21_ratings','v21_sessions','v21_feedback','v21_comparisons'):
            schema[table]=[dict(name=r[1],type=r[2],primary_key=r[5]) for r in c.execute(f'PRAGMA table_info({table})')]
    write('data_schema.json',dict(tables=schema,authority='SQLite in new V2-21/data only',raw_exports='CLI private snapshots, never HTTP download',consent_policy_snapshot=True,deletion_code='256-bit random bearer, SHA256 hash only, shown once'))
    protocol=dict(version='V2-21',mode='FROZEN_479_HYBRID',model_version=engine.model_version,catalog_version=engine.catalog_version,
        alpha=.25,MF_weight=.75,top_k=5,rating_range=[0,10],rating_step=.5,
        offline=dict(min_matched=6,support=5,seed=12,support_policy='sha256(12:v221:support:participantID:canonicalID) first5; label-blind',
            eligible_source='pre_recommendation_rating only; no post-exposure feedback',
            answer_exclusion='Support never an answer; post feedback never an independent answer',
            training_exclusion_gate='No participant train data used by collector. Frozen identity overlap remains unverified; offline accuracy blocked until actual membership/training-exclusion evidence exists.',
            minimum_reporting_users=10,goal_not_statistical_sufficiency=True,positive_threshold=7,metrics=['NDCG@5','Recall@5','HitRate@5'],
            candidate_policy='fixed479 minus Support; never held-out-only candidates',selection='No tuning/train performed'),
        feedback=dict(source='post_recommendation_feedback',unexperienced='NOT_EXPERIENCED with null rating',unknown='UNKNOWN_EXPERIENCE with null rating',
            dedup='one immutable session per participant/model; multiple browser/device identities remain unverified',bias='exposure bias, volunteered item selection, nonresponse and experience bias; not independent offline accuracy'),
        comparison=dict(policy='Uniform simple random sample without replacement,5 of fixed479 minusSupport5 minusTop5',inclusion_probability='5/469 conditional on recorded Support and Top5, when all479 valid',
            scores_or_answer_values_used=False,seed='SHA256(12:v221:comparison:random sessionID)',note='Excluding Top5 makes the eligible set model-dependent; this is a logged nonrecommendation exposure control, not unbiased full-catalog effectiveness estimation'),
        consent=dict(version=VERSION,policy=policy,raw_access='single designated operator OS account; no per-team-user remote auth',withdrawal='same browser or hash-only deletion code',
            retention='purge at startup/requests and CLI purge; if server off operator must run after2027-02-28; no OS job installed',backup_scope='No automatic backups created. Operator must include any manually made raw copies in retention/deletion handling.'),
        catalog_limits='CATALOG_UNSPECIFIED means no concentration in original catalog; participant affirms exact displayed item; variants not guessed or fuzzy merged',
        independent_evidence=False,new497_content='NOT_IMPLEMENTED_OPTIONAL_NOT_SAME_MODEL',MF_fit_calls=0)
    write('evaluation_protocol.json',protocol)
    write('browser_checks.json',dict(status='PASS',environment='TEMPORARY_TEST_FIXTURE_WITH_ACTUAL_FROZEN',
        consent_UI=True,pre_ratings_saved_via_UI=6,actual_Frozen_top5_rendered=5,comparison_cards=5,unexperienced_score_disabled=True,
        saved_feedback_persisted_after_reload='NOT_EXPERIENCED',mobile_width=390,horizontal_overflow=False,browser_console_errors=0,
        actual_real_responses_created=0,production_origin='http://127.0.0.1:8021',windows='UNVERIFIED'))
    report='''# SCENT MATCH V2-21 — Real-User Recommendation Evaluation System

2026-10-30. **PASS WITH LIMITATIONS — 로컬 시스템 구현·Frozen 연동 검증 완료, 실제 신규 응답0, 정확도 NOT_EVALUATED_NO_NEW_DATA.**

## A. Executive Summary

기존 서비스·학습모델을 수정하지 않고 V2-14를 재사용한 독립 로컬 평가 UI를 구축했다. 실제 Frozen Hybrid479를 로드해 Support5→Top5→경험/선호 피드백→비추천 비교평가를 저장한다. 동의 운영방침·한 번만 표시하는 해시 삭제 코드·보관 만료 삭제를 검증한 뒤 실제 등록을 활성화했다. **실제 참여자0명/평점0개**, 모델 정확도나 성능 개선은 계산하지 않았다. 테스트 응답은 임시 test_fixture DB에서만 저장/폐기했다.

실행: `sh experiments/scent_v2/real_user_evaluation/run-macos.sh start --policy outputs/scent_v2/real_user_evaluation/operating_policy.json`, http://127.0.0.1:8021. 패키지 설치·외부배포·외부DB·참여자초대·Git변경·MF학습없음.

## B. 기존 V2-14 분석 및 재사용

`real_user_dataset/storage.py`의 익명 cookie/해시 auth·CSRF·역할분리·SQLite connection·FileRLock·원자 CSV 쓰기, `validation.py`의 경험/0.5점 검증과 CSV formula escaping, `catalog.py` 검색, `app.py`의 loopback Host/Origin/JSON 검증·무로그 Handler·보안 헤더, 기존 반응형 CSS를 재사용했다. 새 UI/session/feedback 개념만 확장했다. 기존 앱·DB·CSV는 열어서 마이그레이션하지 않았다.

V2-21의 `outputs/.../data`만 생성한다. V2-14 participant table의 consent_version은 호환용이며 실질적인 V2-21 동의문 버전·정확한 운영방침 snapshot은 `v21_consents`에 별도로 저장한다. V2-14의 과거 보관기간/동의 문구를 V2-21 운영 방침으로 재사용하지 않는다.

## C. 사용자 평가 흐름

1. 목적·자발성·직접식별정보 비필수·중단/삭제·운영방침을 읽고 동의한다. 보관 종료2027-02-28, 원시 접근은 데이터관리담당자1명, 다른팀원은 집계통계만 공유한다.
2. 가입 시256bit 고엔트로피 삭제코드를 한 번만 표시한다. 서버는 SHA256만 보관하며 state/CSV/로그에 원본코드를 내보내지 않는다. 분실 시 개인 확인이 제한된다는 안내를 표시한다.
3. 실제 경험한 향수를 검색해 정확한 원본 상품/판본을 확인하고0~10/.5점으로 입력한다. 추천 전8~10개를 권장하지만 매칭5개면 추천 가능하다. 미등록은검토용custom ID이며 추천Support로 쓰지 않는다.
4. 제품ID hash로 label-blind Support5를 선택해 기존 Frozen을 호출한다. 부족하면 INSUFFICIENT_MATCHED_SUPPORT, 다른제품/497모드는 UNSUPPORTED_PRODUCT/MODEL_MODE, 모델오류는 MODEL_UNAVAILABLE로 처리하며 가짜추천은 없다.
5. Top5각각 경험있음/없음/기억불명을 먼저 선택한다. 없거나 불명이면 점수 입력 비활성·DB null. 경험한0점은 유효하다.
6. 별도 비교후보5개 또는 검색한 추가경험향수에 응답한다. 이후입력은 서버가 post_recommendation_feedback으로 분류한다.
7. 저장완료 후 같은브라우저로 다시 확인하거나 삭제코드로 연결응답을 삭제한다. 새로운 기기/쿠키삭제로 실제인물이 중복될 위험은 남아 있다.

## D. 데이터베이스 구조

- Participant: 기존 익명 ID/auth hash/CSRF/고정 development·independent 역할. 이름·이메일·전화번호 필드없음.
- v21_consents: V2-21 consent version/운영방침JSON/동의시각/deletion_hash. 삭제코드 원본없음.
- v21_ratings: user+product+source unique, original name, 농도, score, 실제경험, 서버결정 source와UTC시각. pre/post는 덮어쓰지 않는다.
- v21_sessions: participant당 immutable1개, model/catalog version, SupportIDs, 추천IDs/순위/점수/시각. 재요청은 동일세션반환.
- v21_feedback: session+product unique, rank/경험/nullable rating/시각. 자신의 추천상품만응답.
- v21_comparisons: session+product unique, 추출정책/조건부포함확률/경험/nullable rating/시각.

`data_schema.json`은 실제 PRAGMA table_info 결과다. SQLite가 원장이고 CSV는 CLI 전용0600 원자스냅샷이다. HTTP파일다운로드경로없음. CSV에는 사용자별기록이 있으므로 **로컬원시데이터**이며 공유용집계가아니다. 이번collector는 어떤행도학습으로내보내지않는다. 향후V2-22는새동의목적·고정역할·별도개발데이터 경계를검토해야한다.

## E. 기존 Hybrid 연동

`engine.Engine`이 `deployment/standalone_v1/runtime_loader.StandaloneService`를 검증된manifest pin으로 로드한다. runtime5 hash·원본코드 hash 유지, 후보479·alpha.25/.75·기존Content/MF/RidgeFold-in/정렬 그대로. scorer에는 정확히5개 ID/평점만 전달한다. 나머지 pre-held-out·피드백·비교선택값은 전달하지 않는다.

원래StandaloneService 직접호출과 추천ID·순서·점수가 동일함을 검사했다. 모든실제모델검사 입력은 합성Support이고 임시fixture밖에 저장하지않았다. 497Content모드는선택적이므로 구현하지않았고API가다른mode를거부한다. 신규18 factor를임의생성하거나Hybrid라고부르지않는다.

## F. 실제 평점 수집과 제품 식별

기존479canonical ID만 정확연결한다. 농도는 원본명에 EDP/EDT/Eau de Parfum/Parfum 등 명시된경우만표시한다. 없으면 CATALOG_UNSPECIFIED로남기며 EDP/EDT를추정하지않는다. 사용자가다른판본을경험했으면미등록검토제품으로기록하도록안내한다. catalog자체의판본모호성을완전히해결한것은아니며identity는참여자확인에의존한다.

사전평점은 실제경험필수,중복키거부,숫자범위/유한값/.5단위검증. 미등록제품명에는기본이메일/전화패턴을거부하지만자유텍스트의PII완전차단을보장하지않으므로제품명만입력안내·관리자검토가필요하다. 실제0점과미경험null은구분한다.

## G. 추천 결과 피드백 분석

독립offline정확도가아닌노출기반분석이다. `feedback_analysis.json`은현재NOT_EVALUATED_NO_NEW_DATA다. 향후응답분모/노출분모를구분해응답률,응답자중경험률,전체노출중경험확인률,경험하고점수를준응답만평균·positive≥7비율을계산한다. 미응답/미경험을0점·부정선호로채우지않는다.

한참여자당동일모델immutable1세션이므로재클릭이독립사용자로늘지않는다. 실제동일인이다른쿠키/기기에서재가입하는것은확인불가하다고기록했다. 모델버전별집계를구분하며현재모드는Frozen479하나뿐이다. 노출·자발적선택·기억·미응답편향때문에일반사용자정확도라고부르지않는다.

## H. 추천되지 않은 향수 비교

Support5+Top5를뺀469개에서5개단순무작위비복원추출한다. seed는SHA256(12:v221:comparison:sessionID); 한세션에서는고정재현된다. **조건부 포함확률5/469**와정책을저장한다. 점수·평점·held-outID/라벨로선택하지않으며모든해당후보를균등하게취급한다. 브랜드층화는이번에추가하지않았다.

Top5를제외하므로표본틀은모델결과에조건부라는한계가있고모델독립인전체모집단무편향성능을보장하지않는다. 비교후보도미경험이면null,검색자발평가는별도post행으로남겨선택편향을명시한다. 비교응답을기존사전정답으로변환하지않는다.

## I. Offline 평가 프로토콜

사전고유정확매칭6개이상일때5Support/나머지held-out후보를구성할수있다. 하지만**Frozen학습사용자와동일인인지확인할수없어현재실제offline평가를자동실행하지않는다.** 실사용자0이므로현재status는NOT_EVALUATED_NO_NEW_DATA이며,응답이생겨도학습멤버십/사용자배제증거가없으면BLOCKED_FROZEN_TRAIN_MEMBERSHIP_UNVERIFIED다. 허위신규사용자확인·학습배제기록을만들지않았다.

향후실제학습배제·모델동결·사전정답독립성증거와표본을확보하면고정479−Support에서NDCG@5/Recall@5/HR@5를계산할수있다. relevance≥7/10,accuracy는양성정답사용자macro,양성없는사용자분모와후보밖정답정책을명시해야한다. 이번코드는그미래평가를실행했다고주장하지않는다. 보고최소10명은1차운영목표를보수적으로적용한규칙이지통계충분성이나교수요구가아니다. 모델학습자체는0회다.

## J. 누수 방지

추천입력함수는5Support만받는다. 서버가첫노출전/후를결정해source를고정하고,추천후입력으로사전행을수정하지않는다. 이미Support인상품은정답/피드백이될수없다. 추천후추가평가에서Top5는별도피드백화면을쓰게한다. 모델/카탈로그버전과세션추천snapshot은변경하지않는다. 기존final평가정답·V2-17metadata를로드하지않았다.

학습데이터추가·MF재학습은이앱에없고,실제학습사용자독립성을검증하지못하면offline점수를차단한다. 향후평가피드백을같은모델의학습에재사용하려면새버전·평가정책이필요하다. 현재Frozen유저맵을추가수집해참여자실명을대조하지도않는다.

## K. 데이터 품질·삭제·보관

user/item/source unique와session unique; range/step/experience/concentration/Support5/held-out·Top5중복/모델버전/UTC타임스탬프를검사한다. `data_quality_report.json`은원시행으로실제invalid/중복/매칭률을계산한다. person동일성·catalog농도미표기·미등록제품은자동보정하지않고검토한계로남긴다.

삭제코드는256bit난수+SHA256으로저장하고한번만표시한다. 쿠키없이코드로삭제하며연결participant/consent/rating/session/feedback/comparison 및CSV잔존을검사했다. master/attachedDBsecure_delete를사용한다. 보관종료후시작/요청시자동purge하고CLI purge도제공한다. **서버가꺼져있으면자동실행되지않으므로담당자가기한후purge를실행해야한다.** OS예약작업·외부백업은생성하지않았다. 관리자가별도복사/백업한원시자료도삭제기한과요청처리에포함해야한다.

신규data디렉터리0700·원시파일0600,관리자1명전용OS계정에서운영해야한다. 다른팀원을원격인증해서통제하는시스템이나disk암호화가아니다. 같은OS계정/관리자권한을공유하면파일접근을분리할수없다는한계를문서화한다. 담당자의실명은팀이정해야하며임의지정하지않았다. 공개Git/외부전송없음.

## L. 테스트와 브라우저 검증

최종unit/source/실제모델/삭제정책 **39개PASS**. actualFrozen로드/직접호출동일결과,479/497구분,제품농도,평점,Support5,held-out미전달,학습없음,Top5,seen제외,미경험/불명null,post분리,비교확률,버전·중복참여집계,PII최소,CSV,기존DB/서비스/Frozen19/기존실험보존,삭제코드해시·연쇄삭제·만료를검사했다.

`http_checks.json`은임시test_fixture DB+actualFrozen에서HTTP전구간PASS다. 등록→합성pre6개→Top5→비교5개→피드백→삭제검증했고실제참여자로집계하지않았다. 브라우저에서도동일흐름·reload후NOT_EXPERIENCED보존·390px가로overflow없음·consoleerror0을확인했다(`browser_checks.json`). Windows실행은미검증이다.

첫loopbackbind는sandbox PermissionError였고로그를숨기지않았다. 로컬서버권한을허용한후동일HTTP검사가PASS했다. 외부인터넷으로bind하거나업로드하지않았다. 기존서비스포트는건드리지않았다.

## M. Frozen V1 무결성

`integrity.json`은작업전2373개regular파일snapshot과Frozen19/manifest/runtime5,기존V2-14DB·CSV·V2-16~20·서비스/API·실제평점원본을검사한다. 발표문서5개append만허용하고원문bytesprefix를비교한다. GitbranchHEAD불변·commit/push/checkout/reset/merge없음,설치없음,모델변경없음.

## N. 발표 문서 업데이트

V2-16평점확보→17metadata조사→18허가신규18→19Notes표현비교→20복수취향Hybrid개선미확인→21실사용자평가인프라구축을끝에만추가했다. 수집시스템완성과실제데이터확보·정확도개선은다른성과다. 기존traceability를덮어쓰지않았고교수요구전체완료를선언하지않는다.

## O. 실제 사용자 데이터 수집 현황

**참여자0/평점0/추천세션0/피드백0**. collection_status와offline_evaluation/feedback_analysis는실제빈저장소에서생성했다. 과거12명85개를신규응답으로복사하지않았으며test_fixture는별도임시디렉터리다. 실제참여자등록은운영방침·삭제정책·통합검사후활성화했지만외부초대/공개배포는하지않았다.

## P. V2-22 권고

데이터관리담당자1명실제지정·전용OS계정운영,운영기한삭제실행책임을확정한다. 실경험매칭6개이상사용자10명→20명,권장8~10개평점을목표로하되통계충분성으로오해하지않는다. 참여자독립성/학습배제증거와최종정답접근경계를확보한뒤에만offline개선검증을설계한다. 피드백은노출분석으로따로보고한다. catalog농도모호성과낮은경험커버리지를실제수집으로점검하고새모델/497확장은별도사전계획으로분리한다.
'''
    with (OUT/'REPORT.md').open('x') as f:f.write(report)
    extra='''\n\n## V2-21 — 실제 사용자 추천 평가 시스템 (2026-10-30)

V2-16실제평점→17metadata조사→18허가신규18→19Notes-only비교→20복수취향Hybrid개선미확인→21실사용자평가인프라구축. V2-14검색/검증/익명SQLite/CSV/반응형CSS를새디렉터리에서재사용하고Frozen479 Hybrid Top5·추천후경험/선호·비추천비교노출을추가했다. 기존모델/서비스/DB/결과는변경없음.

보관종료2027-02-28,원시접근데이터담당자1명,원본대신해시를보관하는1회표시삭제코드·연결응답삭제·만료purge를구현검증했다. 같은브라우저만이아니라코드로철회가능하다. 담당자의별도백업/종료시purge운영책임과OS계정분리한계는남는다.

39개테스트PASS,임시합성응답+실제Frozen브라우저/HTTP검증PASS. **실제신규참여자0/평점0/세션0**,offline/feedback결과NOT_EVALUATED_NO_NEW_DATA다. Frozen학습동일인여부미확인인상태에서독립offline성능을계산하지않고BLOCKED로유지한다. 추천후피드백과미경험null을별도보존하며미경험0점화없음. 기존479 Hybrid와497 Content를혼동하지않는다.

근거:`outputs/scent_v2/real_user_evaluation/REPORT.md`, `evaluation_protocol.json`, `data_schema.json`, `collection_status.json`, `data_quality_report.json`, `offline_evaluation.json`, `feedback_analysis.json`, `tests.log`, `http_checks.json`, `browser_checks.json`, `integrity.json`. 다음단계는실제평가자확보·학습배제증거·독립평가설계이며정확도개선을이미달성했다고쓰지않는다.
'''
    names=('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md')
    for name in names:assert (ROOT/'docs/presentation'/name).read_bytes()==Path('/tmp/scent-v221-'+name).read_bytes()
    for name in names:
        with (ROOT/'docs/presentation'/name).open('a') as f:f.write(extra)
    store.lock.close();print('Real data0, protocol/schema/analyses and A–P report/five append-only sections created')

if __name__=='__main__':main()
