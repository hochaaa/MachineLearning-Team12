"""Generate V2-15 evidence report only; no downloads, training, inference or evaluations."""
import argparse, csv, hashlib, json, platform, subprocess
from datetime import datetime, timezone
from pathlib import Path
from .dataset_discovery import CANDIDATES, SEARCH_SCOPE, PERMISSION_RECORDS
from .quality_report import summarize
from experiments.scent_v2.synthetic_data.boundary import evaluation_users, safe_train
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'outputs/scent_v2/external_real_data'

def write_json(name, value):
    """Write only this experiment's aggregate artifacts, never original rows."""
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def write_csv(name, rows):
    """Write administrative evidence tables; these are not acquired rating files."""
    with (OUT/name).open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
    """--snapshot: private pre-task SHA256 map, required to verify original-file preservation."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True);args=parser.parse_args()
    before=json.loads(args.snapshot.read_text())
    if not before: raise ValueError('Nonempty pre-task inventory required')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if branch!='development-v2' or head!='d92c59a379a278a94bf4ca149674abb841746d69':
        raise RuntimeError('Unexpected branch/HEAD')
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text())
    if len(candidates)!=479 or len(set(candidates))!=479:raise ValueError('Candidate invariant')
    # Only cohort identities are decoded; ALL other manifest fields are skipped.
    excluded, identity_audit=evaluation_users((ROOT/'outputs/scent_v2/baseline/split_manifest.private.json').read_text())
    safe, users, boundary=safe_train((ROOT/'outputs/validation/train_exclude_3.json').read_text(),excluded)
    # Full legacy 1805 histories are NOT decoded for an archive export.
    strict=[dict(user_id=u,perfume_id=i,normalized_rating=y*10) for u,i,y in safe if i in candidates]
    baseline=summarize(strict,candidates)
    OUT.mkdir(parents=True,exist_ok=True)
    write_csv('dataset_candidates.csv',CANDIDATES)
    provenance=[]
    for row in CANDIDATES:
        provenance.append(dict(dataset=row['dataset'],provider=row['source'],official_page=row['url'],
             evidence_page=row['evidence_url'],version=row['version'],status=row['status'],
             metadata_access_date='2026-10-29',raw_downloaded=False,raw_download_date=None,
             raw_filename=None,raw_bytes=None,raw_sha256=None,measured_rows=None,
             measured_users=None,measured_perfumes=None,redistribution_permission='NOT_ESTABLISHED',
             privacy='Raw user IDs/review text may be personal; pseudonymization is not anonymization',
             acquisition_method='Primary metadata pages/search only; no review scraper or remote code'))
    for source in provenance: source.update(PERMISSION_RECORDS[source['dataset']])
    write_json('source_provenance.json',dict(sources=provenance,search_scope=SEARCH_SCOPE,
        evidence_limits='Web page assertions recorded; no version-pinned raw file inspected. Counts labeled provider-reported are not measured.',
        public_page_snapshots_saved=False))
    write_json('acquisition_status.json',dict(status='BLOCKED_NO_ELIGIBLE_NEW_SOURCE',actual_acquired_external_ratings=0,
        actual_479_matched_external_ratings=0,actual_training_additional_ratings=0,new_external_users=0,
        investigated_candidates=len(CANDIDATES),raw_downloads=0,generated_rating_dataset_files=[],
        training_runs=0,inference_runs=0,ndcg_evaluation_runs=0,package_installs=0,
        reason='No investigated new source met both interaction suitability and documented usage conditions'))
    write_csv('perfume_match_report.csv',[dict(dataset=r['dataset'],stage='NOT_RUN_NO_ACQUIRED_DATA',
        external_perfumes='UNKNOWN',exact_matches='NOT_MEASURED',status=r['status']) for r in CANDIDATES])
    write_json('matching_summary.json',dict(status='NOT_RUN_NO_ACQUIRED_DATA',candidate_count=479,
        actual_matched_external_ratings=0,actual_matched_external_users=0,source_perfume_counts='UNKNOWN',
        exact_normalized_perfumes='NOT_MEASURED',manual_review_perfumes='NOT_MEASURED',unmatched_perfumes='NOT_MEASURED',
        newly_observed_candidates=0,additional_ratings_for_low_observation_items=0,
        user_activity_distribution='NOT_MEASURED',note='perfume_match_report.csv is a source-level status table, not item-level match output'))
    write_json('quality_report.json',dict(external=summarize([],candidates),
        strict_existing_train_baseline=baseline,boundary=boundary,identity_only_manifest_audit=identity_audit,
        quality_change='NOT_MEASURED_NO_EXTERNAL_ROWS',cross_source_person_overlap='UNKNOWN',
        independent_evaluation_claim=False,combined_archive='NOT_CREATED',training_ready='NOT_CREATED',
        v214_storage_access='No Store constructor, export, database query, participant API or independent rating parse'))
    license_lines=['# V2-15 이용 조건 감사','',
        'HOLD는 허용 범위가 입증되지 않았다는 작업 판정이며, 보편적 위법 판정이 아니다. 기존 로컬 사용 승인이나 저장소 코드 라이선스로 신규 원본의 다운로드·파생·재배포를 추정하지 않는다.', '',
        '| 자료 | 라이선스/근거 | 판정 |','|---|---|---|']
    for r in CANDIDATES:license_lines.append(f"| [{r['dataset']}]({r['url']}) | {r['license']} | {r['status']} |")
    license_lines += ['',
        'Amazon 2023: 공식 maintainer 답변은 연구 목적 공개를 설명하지만 이용 라이선스를 부여하지 못한다고 명시한다. 2018의 수업 프로젝트 다운로드 안내도 파생·상위 원본 권한의 확정 근거로 확대 해석하지 않았다.',
        'Fragrantica: 원본 약관 §5.3의 자동 수집 제한 및 §5.7의 ML·데이터셋 이용 사전 서면동의 조건을 확인했다. 현재 별도 권리자 증빙은 없다. FragDB의 HF 라이선스 표시와 샘플/코드 MIT 표시는 원본 권한을 해결하지 않는다.',
        'ParfumDB: 판매자의 작성자·평점 스키마 주장은 파일 실측이 아니다. 구매/이메일 등록/다운로드를 하지 않았고 원본 Parfumo 권한 및 전체 계약은 미확인이다.',
        '학술 이용/수정/재배포/상위 서비스 약관/개인정보를 각각 확인해야 한다. 이번에 신규 통합을 승인한 출처는 없다. 외부 전달은 모두 보류다.',
        '사용자명·프로필 URL·리뷰 본문을 처리 산출물로 복사하지 않았다. HMAC ID도 재식별 가능성이 남아 로컬 비공개로 취급한다.']
    (OUT/'license_audit.md').write_text('\n'.join(license_lines)+'\n')
    changed=[];missing=[]
    for rel,digest in before.items():
        p=ROOT/rel
        if not p.is_file():missing.append(rel)
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(rel)
    allowed={str(Path('docs/presentation')/name) for name in ('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md')}
    append_checks={}
    for rel in changed:
        if rel in allowed:
            original=Path(args.snapshot.parent/('scent-v215-'+Path(rel).name))
            append_checks[rel]=original.is_file() and (ROOT/rel).read_bytes().startswith(original.read_bytes()) and hashlib.sha256(original.read_bytes()).hexdigest()==before[rel]
    freeze=json.loads((ROOT/'outputs/final/freeze.json').read_text())
    frozen={r:hashlib.sha256((ROOT/r).read_bytes()).hexdigest()==h for r,h in freeze['protected_sha256'].items()}
    bad=[r for r in changed if r not in allowed or not append_checks.get(r,False)]
    status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    result=dict(status='PASS' if not missing and not bad and len(frozen)==19 and all(frozen.values()) else 'FAIL',
        original_files_checked=len(before),unchanged_original_files=len(before)-len(changed)-len(missing),
        modified_original_files=changed,unauthorized_modifications=bad,missing_original_files=missing,
        append_only_checks=append_checks,frozen19=frozen,
        freeze_manifest_sha256=hashlib.sha256((ROOT/'outputs/final/freeze.json').read_bytes()).hexdigest(),
        branch=branch,head=head,git_status=status,
        v214_files='Byte hashes included in original-file comparison, including SQLite/CSV/secrets; contents not copied',
        protected_hash_scope='Regular non-symlink files excluding .git/.local/.venv/node_modules/dist/caches; no claim to hash excluded environments',
        external_test_labels_parsed=False,original_nested_heldout_labels_parsed=False)
    write_json('integrity.json',result)
    command='SCENT_V215_BEFORE_SNAPSHOT=<private snapshot> PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s experiments/scent_v2/external_real_data/tests -v'
    log=[datetime.now(timezone.utc).isoformat(),f'Python {platform.python_version()}',f'Branch {branch}; HEAD {head}',
         'Public primary-page research through web tool; raw datasets downloaded: 0',
         f'Candidates479 verified; excluded original evaluation users: {len(excluded)}; excluded rows skipped structurally: {boundary["excluded_user_rows_skipped_before_rating_decode"]}',
         f'Existing strict baseline: users={baseline["users"]}, ratings={baseline["ratings"]}, items={baseline["perfumes"]}; unobserved={baseline["unobserved_candidates"]}; at_most_2={baseline["observed_at_most_2"]}',
         command,'See tests.log for actual unittest result; fixture records not integrated',
         'python3 -B -m experiments.scent_v2.external_real_data.run --snapshot <private snapshot>',
         f'Original file comparison: {result["status"]}; Frozen19 unchanged={sum(frozen.values())}/19',
         'Acquired real ratings=0; 479-matched=0; safe additional training=0; no data CSV generated',
         'No model fit, inference, NDCG evaluation, package install, Git mutation or V2-14 Store operation']
    (OUT/'execution.log').write_text('\n'.join(log)+'\n')
    if result['status']!='PASS':raise RuntimeError('Integrity violation; stop')
    print(json.dumps(dict(status=result['status'],acquired=0,matched=0,training_additional=0,old_files=len(before)),ensure_ascii=False))

if __name__=='__main__':main()
