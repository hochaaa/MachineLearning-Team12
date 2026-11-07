"""Publish aggregate implementation evidence, never register or fabricate responses."""
import json,csv,hashlib,os,subprocess,ast
from pathlib import Path
from .config import ROOT,OUT,DATA,HEAD,POLICY
from .storage import atomic_write


def main():
 before=json.loads(Path('/tmp/scent-v214-before.json').read_text());q=json.loads((OUT/'dataset_quality.json').read_text());meta=json.loads((DATA/'collection_metadata.json').read_text());merge=json.loads((DATA/'merge_report.json').read_text());http=json.loads((OUT/'production_http_checks.json').read_text())
 assert meta['actual_ratings']==meta['actual_participants']==q['actual_new_real_ratings']==0;assert http['status']=='PASS'
 for p in(DATA/'real_user_ratings.csv',DATA/'participants.csv',DATA/'independent/real_user_ratings.csv'):
  with p.open(encoding='utf-8',newline='')as f:assert len(list(csv.DictReader(f)))==0
 testlog=Path('/tmp/scent-v214-tests-verified.log').read_text();assert 'Ran 40 tests' in testlog and '\nOK\n'in testlog
 status=dict(status='READY_LOCAL_COLLECTION',message='실제 데이터 수집 시스템 구축 완료. 신규 실제 평점 수집은 아직 진행되지 않음.',actual_new_participants=0,actual_new_ratings=0,actual_new_rated_perfumes=0,candidate_perfumes=479,test_ratings_in_production=0,collection_url='http://127.0.0.1:8014',admin_url='http://127.0.0.1:8014/admin',server_running_verified=True,consent_text='LOCAL_DRAFT_OPERATOR_REVIEW_BEFORE_EXTERNAL_PARTICIPANTS',retention_end_planned='2026-11-30',automatic_retention_deletion=False,model_training_runs=0,new_accuracy_measurement='NOT_RUN')
 atomic_write(OUT/'collection_status.json',json.dumps(status,ensure_ascii=False,indent=2).encode())
 split=dict(seed=12,development_fraction=.60,assignment_time='at anonymous registration, before ratings',method='sha256(12:realuser-split:ID) first64bits /2^64; <.6development, otherwiseindependent',roles_persisted=True,rebalancing=False,development_users=0,independent_users=0,Support5_users=0,Support5_plus_Target_users=0,independent_labels_in_training_merge=0,independent_label_value_distributions_in_dashboard=False,independence_limit='ID-level split only; cookie deletion/device change/old website identity overlap cannot be resolved without additional information',future_protocol=dict(support=5,heldout='remaining observed ratings only',candidates=479,k=5,positive_raw=7,n_lt5='insufficient_support',n_equal5='no_target'),evaluation_not_run=True)
 atomic_write(OUT/'split_summary.json',json.dumps(split,ensure_ascii=False,indent=2).encode())
 browser=dict(status='PASS',test_origin='http://127.0.0.1:8015',test_data_root='/private/tmp/scent-v214-browser-data',test_source='test_fixture',checks=['consent unchecked -> begin disabled','registered only temporary testuser','Black Orchid search -> original black-orchid/tom-ford candidate','no_experience -> rating disabled','sampled -> rating enabled','explicit0 review and submit','edit0 to7.5 -> one row, created timestamp preserved by upsert tests','reload -> same own rating restored','mobile anonymous-ID linewrap corrected'],real_responses_created=0,test_server_stopped=True,production_browser_opened_without_consent=True,screenshot='browser-test.png')
 atomic_write(OUT/'browser_checks.json',json.dumps(browser,ensure_ascii=False,indent=2).encode())
 story='''## V2-14: 실제 평점 수집 시스템 구축 (완료 · 실제 응답 0건)

V2-13의 희소성·불완전 평가 진단 이후, 모델 실험 대신 기존 479개 향수의 실제 경험 평점을 수집하는 독립 로컬 도구를 구현했다. 이름·브랜드 검색, 사용/시향 확인, 0~10점·0.5단위, 동의 후 등록, 검토·제출·수정·재방문·철회와 관리자 집계를 제공한다. 기존 서비스와 별도인127.0.0.1:8014에서 실행하며 기존 모델·React UI는 변경하지 않았다.

SQLite 트랜잭션을 원장으로 두고 UTF-8 CSV를 원자적으로 내보낸다. 사용자ID/향수 중복은 upsert와 제출ID로 처리하며, 디스크·DB 오류 시 rollback/복구와 CSV 세대 검사를 제공한다. 등록 시 seed12 해시로 개발60%/독립평가40%를 고정 배정한다. 평가 평점은 별도 DB/CSV에 두고 개발용 결합에는 읽거나 포함하지 않는다. 신뢰도·이유는 선택사항이며 실제 경험은 자기신고라는 한계가 있다.

신규 경험자의 명시적0은 유효값으로 보존하고, 기존0제외 분석가정과 source/zero_policy를 구분했다. 기존1805행을 수정하지 않고 별도 merged1805행(신규0)을 생성했다. 후보밖72평점·59향수는 표시해 보존하고 명시적479후보 학습뷰는1733행이다. 기존 source와 신규 source를 추적하며 과거 합성은 통합하지 않는다.

40개 테스트 및 임시 브라우저0점→7.5수정·재방문을 검증했다. 테스트는/tmp의 test_fixture 저장소만 사용했고 실제 수집 파일은 헤더뿐이다. **“실제 데이터 수집 시스템 구축 완료. 신규 실제 평점 수집은 아직 진행되지 않음.”** 정확도 개선은 측정·주장하지 않는다. 다음 실제 모델 학습은 충분한 개발용 응답과 고정된 프로토콜 확보 후 별도 실험으로 진행해야 한다.

동의 문구는 로컬 운영용 초안이며 외부 참여자 모집 전 운영자 검토가 필요하다. 보관 종료 예정2026-11-30의 삭제는 운영자가 수행해야 하며 자동기간삭제는 없다. 쿠키삭제·다른기기의 동일인/기존사이트사용자 중복을 완전히 검출하지 못한다. 역할분리는 앱/API 경계와 로컬 권한이며 같은OS계정의 직접파일접근을 막는 sandbox는 아니다. Windows 실행/ACL과 공개배포는 미검증·범위외다.

근거: `experiments/scent_v2/real_user_dataset/README.md`, `outputs/scent_v2/real_user_dataset/{REPORT.md,collection_status.json,dataset_quality.json,split_summary.json,integrity.json,execution.log}`. 기존V2-0~13 기록과 원본 데이터·Q·manifest·서비스를 보존했다.
'''
 timeline='\n| 버전 | 목적 | 구현 | 실측·테스트 | 성능·다음 단계 |\n|---|---|---|---|---|\n| V2-14 구축 완료 | 실제 경험 평점 수집·검증·분리 | 별도 로컬UI+SQLite/CSV+개발/평가 역할 | 실제0명/0평점,40테스트+브라우저검증 | 정확도미측정, 실제응답 확보 후 별도실험 |\n'
 performance='\nV2-14는 추천 모델 성능 비교가 아니다. 실제 신규 평점0, 모델 학습·추론·정확도 평가0회. 기존 NDCG를 새 수집 도구의 성과로 재사용하지 않는다. 현재 품질 지표는 데이터0건을 명시하고 평균·비율을null로 표시한다. 기존1805행/후보정렬1733행은 기존 관측이며 신규실적으로 세지 않는다.\n'
 slides='''\n발표 보완 슬라이드: **“실제 데이터로 이어지는 다음 단계”**. 핵심 메시지는 수집 가능한 도구를 실제 구현했으며 아직 실제 평점은0건이라는 것이다. 흐름은 동의→경험확인→479후보검색→검토/제출→SQLite원장→역할별CSV→개발전용통합이다. `browser-test.png`는 임시 테스트 응답의 수정·재방문 증거이며 실제 수집자료가 아니다. `collection_status.json`, `dataset_quality.json`, `split_summary.json`, `data/merge_report.json`의 source/건수/분리 근거를 사용한다. 현재는 정확도향상 그래프를 만들 수 없다. 발표자는 데이터 목표300~500개와 실제0개, 계정ID 분리와 사람의 실제독립성, 명시적 신규0점과 기존0가정을 구분한다.\n'''
 log='''\n실험ID V2-14 / 구축 완료. 목적: 실제 사용·시향 평점을 수집·검증·저장하고 안전한개발용 통합을 제공한다. 변경: 신규수집코드/새출력/허용발표추가뿐. 고정: 기존479/기존모델·Q·정답·manifest·서비스. 결과: 실제0명/0평점,40테스트통과, 임시브라우저에서검색/0점/수정/재방문 확인. 저장은원자적CSV+SQLite권위/오류복구,등록시seed12 역할고정. 채택: 수집도구 로컬실행준비; 모델채택·성능평가없음. 다음: 운영자동의문·보관계획 검토 및 실제응답 수집, 충분한개발자료/독립Test확보 후 별도모델실험. 참조: 새 README와 outputs/scent_v2/real_user_dataset/.\n'''
 additions={'MODEL_IMPROVEMENT_STORY.md':'','EXPERIMENT_TIMELINE.md':timeline,'PERFORMANCE_COMPARISON.md':performance,'PRESENTATION_SLIDES_OUTLINE.md':slides,'EXPERIMENT_LOG.md':log};prefix={}
 for name,extra in additions.items():
  p=ROOT/'docs/presentation'/name;rel=str(p.relative_to(ROOT));original=p.read_bytes();assert hashlib.sha256(original).hexdigest()==before[rel]
  with p.open('ab')as f:f.write(('\n'+story+extra).encode())
  assert p.read_bytes().startswith(original);prefix[rel]=dict(original_sha256=before[rel],original_bytes=len(original),prefix_preserved=True)
 changed=[]
 for rel,h in before.items():
  p=ROOT/rel;assert p.is_file(),rel
  if hashlib.sha256(p.read_bytes()).hexdigest()!=h:changed.append(rel)
 assert set(changed)==set(prefix)
 freeze=ROOT/'outputs/final/freeze.json';protected=json.loads(freeze.read_text())['protected_sha256'];assert len(protected)==19 and all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in protected.items());assert hashlib.sha256(freeze.read_bytes()).hexdigest()==before['outputs/final/freeze.json']
 assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='development-v2';assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==HEAD
 sensitive=[str(p.relative_to(ROOT))for p in DATA.rglob('*')if p.is_file()];ignored=subprocess.run(['git','check-ignore','--stdin'],input='\n'.join(sensitive)+'\n',text=True,capture_output=True,check=True).stdout.splitlines();assert set(ignored)==set(sensitive)
 permissions={str(p.relative_to(OUT)):oct(p.stat().st_mode&0o777)for p in DATA.rglob('*')if p.is_file()};assert all(int(m,8)&0o077==0 for m in permissions.values())
 for p in Path(__file__).parent.rglob('*.py'):ast.parse(p.read_text())
 atomic_write(OUT/'config.json',json.dumps(POLICY,ensure_ascii=False,indent=2).encode());atomic_write(OUT/'protected_before_sha256.private.json',Path('/tmp/scent-v214-before.json').read_bytes())
 tests=['catalog479','name search','brand search','valid item IDs','random ID collision retry','consent required','experience required','rating0..10','half-step/canonical float','duplicate batch rejected','idempotent retry and upsert','empty stats','CSV UTF8 save/read','DB rollback + atomic replace + export recovery','legacy ID/source checks','synthetic fixture merge rejected','development/independent split','Support5 / Target eligibility','independent/unknown IDs blocked from dev merge','admin authentication/Host/Origin/private files','Frozen19 hashes','old service unchanged','old data unchanged','V2-0..13 unchanged','test data isolated']
 atomic_write(OUT/'test_summary.json',json.dumps(dict(status='PASS',tests_run=40,test_groups=tests,test_data_location='TemporaryDirectory and /private/tmp/scent-v214-browser-data only',test_data_source='test_fixture',production_responses_created_by_tests=0,Mac='VERIFIED',Windows='NOT_VERIFIED',public_deployment='OUT_OF_SCOPE'),ensure_ascii=False,indent=2).encode())
 integrity=dict(status='PASS',Frozen19=True,freeze_manifest_sha256=hashlib.sha256(freeze.read_bytes()).hexdigest(),old_files_checked=len(before),old_files_unchanged=len(before)-5,old_files_changed=changed,old_files_deleted=[],presentation_original_prefixes=prefix,existing_root_gitignore_unchanged=True,all_sensitive_outputs_git_ignored=True,data_file_permissions=permissions,branch='development-v2',HEAD=HEAD,git_status=subprocess.check_output(['git','status','--short'],text=True),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path(__file__).parent.rglob('*')if p.is_file()and'__pycache__'not in p.parts},actual_new_real_users=0,actual_new_real_ratings=0,new_model_training=0,new_model_inference=0,new_evaluation=0,tests_passed=40,Git_mutations=False,package_installation=False,external_upload=False,runtime_or_raw_data_shared=False,only_intended_runtime='new loopback collector8014; test collector8015 stopped')
 atomic_write(OUT/'integrity.json',json.dumps(integrity,ensure_ascii=False,indent=2).encode())
 logs=[('initial sandbox HTTP bind failure','/tmp/scent-v214-tests.log'),('HTTP integration verified','/tmp/scent-v214-tests-http.log'),('final40 tests','/tmp/scent-v214-tests-verified.log'),('actual empty init','/tmp/scent-v214-init.log'),('merge1805 / training1733 / new0','/tmp/scent-v214-merge.log'),('quality empty data','/tmp/scent-v214-quality-final.log'),('Mac launcher init','/tmp/scent-v214-launcher-check.log'),('recover command','/tmp/scent-v214-recover.log'),('final production server startup','/tmp/scent-v214-server-final.log')]
 text=[]
 for label,path in logs:text.append('\n### '+label+'\n'+Path(path).read_text())
 atomic_write(OUT/'execution.log','\n'.join(text).encode())
 report='''# SCENT MATCH V2-14 — Real-User Perfume Rating Dataset Construction

2026-10-29. **구현·로컬 실행 검증 PASS. 실제 신규 참여자0명, 실제 신규 평점0개. 모델 학습·추론·정확도 평가0회.**

## A. Executive Summary

보고서만이 아니라 독립 실행 수집 페이지·원장·CSV·검증·결합 도구를 구현했다. 현재 `http://127.0.0.1:8014`에서 실제 빈 저장소를 사용하며 바로 참여할 수 있다. 테스트는 임시 저장소에서만 수행했다. “실제 데이터 수집 시스템 구축 완료. 신규 실제 평점 수집은 아직 진행되지 않음.”

## B. 구현된 수집 시스템

Python3.12 표준 라이브러리만 사용했다. `app.py`의 loopback HTTP 서버, `catalog.py`의 원래479개 검색, `validation.py`, `storage.py`의SQLite 원장/CSV snapshot, `split_manager.py`, `dataset_builder.py`, `quality_report.py`, 별도 HTML/CSS/JS와 실행 스크립트로 구성했다. 기존 서비스·FastAPI·React·MF·Q는 수정하지 않았고 새 패키지 설치도 없다.

```mermaid
flowchart LR
 U[로컬 참여자 UI] --> V[동의·경험·입력 검증]
 V --> P[익명ID·등록시 역할 고정]
 P --> D[개발용 SQLite / CSV]
 P --> E[독립 평가용 SQLite / CSV]
 D --> M[기존Train + 개발용만 결합]
 E --> C[건수·적격인원만 관리자 집계]
```

## C. 사용자 UI

동의 전 시작버튼 비활성화, 원래 이름·브랜드 검색/최대10결과, 중복없는 선택 목록, 경험 없음 입력 비활성화, 0~10/.5점, 선택 신뢰도/이유, 제출 검토, 완료 메시지, 내기록 수정·재방문·철회를 제공한다. 기본 가짜 평점을 채우지 않으며, 경험한3개만 제출해도 된다. 후보 밖 브랜드·향수는 생성하지 않는다. 본인 경험은 자기신고이며 실제 시향 진위까지 검증하지 않는다.

브라우저 테스트는8015의 `/private/tmp/scent-v214-browser-data`에서 수행했다. 실제 black-orchid/tom-ford를 검색해0점 제출,7.5점으로수정,새로고침 후한행을 확인했다. `browser-test.png`는 테스트 응답이며 실제 수집자료가 아니다. 익명ID의 모바일 줄바꿈을 수정했다. 실제8014에서는 동의·응답을 입력하지 않았고 빈 참여 화면을 확인했다.

## D. 데이터셋 스키마

CSV 고정 필드: user_id, perfume_id, rating, experience_type, confidence, preference_reason, created_at, updated_at, source. rating raw0..10/.5, experience used/sampled, confidence 선택 empty/low/medium/high, reason 선택300자, 시각 server UTC, source real_user_collection. 동의 버전/시각·고정역할은 participants 원장에 별도 저장한다. ID·출처·scope가 다른 test_fixture를 실제 자료에 섞지 않는다.

동의에는 연구 목적·로컬 저장·비공유·철회·보관종료 예정2026-11-30·운영자 삭제 책임을 표시했다. 이는 **운영용 초안**이며 외부참여자 모집 전 운영자 검토가 필요하다. 자동기간삭제는 없고 파일은 자동암호화되지 않는다. 공유권한을 확보했다고 표시하거나 허위승인기록을 만들지 않았다.

## E. 사용자 ID 및 중복 처리

realuser_UUID4와 난수 인증 세션/CSRF를 사용하고 DB unique·충돌 재시도를 적용했다. 기존330사용자 ID는64hex로 확인되어 namespace가 다르며 merge에서도 충돌을 검사한다. 브라우저에는 HttpOnly/SameSiteStrict 포트별 세션쿠키를 쓰고 역할은 보여주지 않는다. 세션 인증정보는 CSV에 내보내지 않는다.

같은 user/item은 upsert, 최초created_at 보존, updated_at 변경. 같은 request_id/body 재시도는 한 번의효과, 다른body로 key재사용은 거부한다. 쿠키삭제·다른기기·기존사이트 신원연결을 하지 않으므로 사람의 중복참여를 완벽히 막지 못하고, 등록ID 단위 분리 이상의 실제 사람 독립성을 보장하지 않는다.

## F. 저장 구조 및 오류 복구

새 `outputs/scent_v2/real_user_dataset/data/`만 사용한다. participants.sqlite3와 development/independent의별도 ratings.sqlite3가 권위원장이다. 로컬 프로세스간 파일락, BEGIN IMMEDIATE, DELETE journal/synchronousFULL의disk multi-DBtransaction으로 반영한다. UTF-8 CSV는0600임시파일→flush/fsync→replace, metadata revision/checksum을 마지막에 게시한다.

root real_user_ratings.csv는 **개발용만**이고 독립 평점은 independent/real_user_ratings.csv에만 있다. 여러CSV전체가동시에원자교체되는것은아니므로 부분실패시 metadata/checksum검사로 stale/incomplete를거부한다. DB쓰기오류는rollback, CSV쓰기오류는확정DB를보존하고csv_sync_pending을표시한다. recover/재시작으로CSV를재구성한다. old CSV 손상·데이터유실을성공처럼표시하지않는다.

기본POSIX디렉터리0700/파일0600을실측했다. 실제DB/평점/동의/secret 모두기존 outputs/ignore에포함,원래.gitignore는수정하지않았고신규소스안에보조규칙만추가했다. 이유CSV는수식시작을무력화하며UI는textContent를사용한다. 기본이름·이메일·전화번호필드를수집하지않고이유에이메일/전화번호패턴을거부하나모든개인정보탐지가가능한것은아니다.

철회는본인활성원장·동의·세션·receipt와현CSV를삭제반영하고collector파생통합뷰를폐기한다. 오류시복구가필요하며외부복사본/OS백업·포렌식영구삭제는보장하지않는다. 같은OS계정사용자가직접파일을읽지못하게하는sandbox는아니다.

## G. 기존 데이터 통합

실제로 builder를 실행했다. 기존1,805개/330사용자 Train은읽기전용,신규개발평점0. merged_real_ratings.csv는기존1805행,training_ready_ratings.csv는479후보내1733행. 후보밖72평점/59향수는merged에플래그로보존하고명시적학습뷰에서만제외했다. 원본행삭제/후보군확장은없다.

source와zero_policy,raw와normalized를함께기록한다. 기존0제외는분석가정,신규실제경험자의명시적0은유효하므로정규화0으로보존한다. 기존MF함수는0을허용하지만신규CSV를옛Atrafshan zero-exclude rawETL에넣으면안된다. 기존ETL·모델을수정하지않았다. 개인ID충돌/중복/척도/경험/결측/후보/출처를검증하고synthetic/test/unknown/independent사용자는거부한다. **독립평점파일·과거합성파일은빌더에서열지않는다.** 최신revision/checksum검증을통과한development view만load_training_rows로제공한다. 응답수정후rebuild없이는stale view가거부된다.

## H. 개발·독립 평가 분리

Seed12 해시의고정.60cutoff로등록시배정,DB에저장하고새사용자수/평점으로재배정하지않는다. 실제분할사용자는개발0/평가0.60/40은확률적해시분포이지소표본에서정확명수보장이아니다. 개발코드의기본입력은root개발CSV이고독립자료는별도하위DB/CSV다.

향후Support5+나머지observedTarget을ID해시로선택하는함수를구현했다.5미만은Support부족,정확히5는Target없음,6이상은구조상가능으로분리집계한다. 후보479/Top5/positive7은미래평가계약이지이번에평가를실행한것이아니다. 독립정답의release/평가실행은모델·프로토콜선택완료후별도절차에서고정해야한다. 관리자화면도독립평점값·평균·분포를조회/노출하지않고건수·적격인원만보여준다.

## I. 데이터 품질 검사·관리자

동의한활성참여자/제출자/역할별건수,개발용사용자평점수·다양성·아이템빈도·기존strictTrain tail관측,범위/격자오류,개발용평점평균/중앙/SD/7이상/5미만/0비율과eligibility를집계한다. 현재0건이므로평균/비율null,평가된향수0/미평가479. null을0점이라고오인하지않는다. 독립label분포는보류한다.

관리자페이지는로컬code로그인후집계만표시한다. 미인증403,Host/Origin/customheader/CSRF와CSP를검증하고raw파일HTTP다운로드는404다. IP/쿼리/평점을request로그에저장하지않는다. Secret은data/.admin_token(0600)으로유지하며코드·보고서·로그에노출하지않았다.

## J. 실행·사용 방법

Mac 프로젝트루트:

```sh
sh experiments/scent_v2/real_user_dataset/run-macos.sh start
```

참여 **http://127.0.0.1:8014**, 관리자 **http://127.0.0.1:8014/admin**. 실행터미널Ctrl+C로종료,같은명령으로재시작한다. 실제실행/종료/재시작을확인했고최종서버를켜두었다. quality/recover/merge/admin-code명령·저장경로·철회는신규README에있다.

Windows PowerShell(직접미검증):

```powershell
powershell -File experiments/scent_v2/real_user_dataset/run-windows.ps1 -Command start -Port 8014
```

실행경로는프로젝트상대,개인절대경로·.venv필수의존없음. Python3.10+표준라이브러리만사용한다. 다만원래479후보/메타데이터는로컬파일이필요하고공유HOLD가그대로라Git Clone만으로원본자산까지재현된다고주장하지않는다. 공개인터넷수집서비스배포는하지않았다.

## K. 실제 테스트 결과

**최종40개테스트통과.** 479로딩·이름/브랜드검색·ID·동의·경험·격자/경계·중복·수정·빈통계·CSV왕복·DBrollback·replace오류·CSV복구·legacy/synthetic차단·역할·Support/Target·관리자인증·Host/Origin/비공개파일차단을검증했다. 최종테스트상세는tests-final.log/test_summary.json,원래보호파일검사는integrity.json.

초기샌드박스에서는HTTP포트bind PermissionError로통합테스트시작이차단됐다. 로컬서버검증의승인된범위로실행권한을전환한뒤37개,이후rollback/3개허용/부동소수격자검사를추가한40개를통과했다. 브라우저에서는모바일익명ID줄바꿈을수정하고검색·경험게이트·0점·수정·재방문을확인했다. 초기실패를성공으로숨기지않고execution.log에보존했다. Windows/공개서비스보안은검증하지않았다.

## L. 현재 실제 수집 현황

**실제신규참여0명/동의0명/평점0개/평가된향수0개.** 실제수집CSV는헤더뿐이다. 자동테스트는TemporaryDirectory,브라우저테스트는/tmp/test_fixture에서만기록하며원래실제저장소에넣지않았다. 테스트용0점과7.5점수정은실제실적이아니다. 기존merged1805행도신규수집으로세지않는다.30~50명/300~500평점은향후목표이지확보결과가아니다.

## M. 향후 학습 준비 상태·한계

검증된개발용 normalized triple을내보내는함수와독립역할/eligibility 구조는준비됐다. 실제개발자료가쌓이면출처·0의미·중복/역할·최신snapshot을확인한뒤새실험에서학습해야한다. 기존Frozen의학습·추론·α/Q/후보·평가결과는변경하지않았다. 정확도개선은미측정/미입증이다.

실제경험은자기신고,익명중복참여완전차단불가,같은OS계정의원시파일접근가능,Windows/ACL미검증,동의초안운영자검토/보관종료삭제필요,자동기간삭제없음,기존metadata재배포권한HOLD를명시한다. 공개배포시TLS·인증/접근계정·속도제한·백업/암호화·동의/보관/삭제·운영보안/공유권한검토가별도로필요하다.

## N. 발표 문서 업데이트

허용5개MD에수집목적/구조/스키마/검증/통합/역할/실제0건/향후학습계획/정확도미측정을추가했다. 기존V2-0~13기록전체byte prefix를보존했다. 팀역할·기여율·개인소감·허위권한승인은작성하지않았다. 기존보고서/PPT/서비스는덮어쓰지않았다.

## O. 무결성 검증

'''+f'''작업전{len(before)}파일중{len(before)-5}개불변,변경5개는허용발표MDappend뿐,삭제0. Frozen19+manifest SHA256일치,기존data/Q/평가정답/manifest/서비스/V2-0~13보존. branch development-v2/HEAD {HEAD}유지. Git초기화·stage·commit/push/checkout/reset/merge0,패키지설치0,외부업로드0. 신규민감자료전부Gitignore확인,POSIX파일권한실측. 원시자산/런타임공유없음.

`integrity.json`에전체기준hash검사/허용prefix/소스hash/ignored/permissions, `production_http_checks.json`에실제endpoint200·479·관리자403·비공개파일404·실제0건을저장했다. 구현검증PASS이며실제평점확보·모델개선·프로젝트전체교수요건완료를뜻하지않는다.
'''
 atomic_write(OUT/'REPORT.md',report.encode());atomic_write(OUT/'tests-final.log',testlog.encode())
 print(f'PASS: collector ready, real0 users/0 ratings,40tests, required artifact evidence, Frozen19 and {len(before)} old hashes/prefixes retained',flush=True)

if __name__=='__main__':main()
