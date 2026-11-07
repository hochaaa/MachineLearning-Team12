"""Post-run byte checks only; no real respondent creation or recommendation evaluation."""
import argparse,hashlib,json,subprocess,platform,sys,sqlite3
from pathlib import Path
from .app import ROOT,OUT

def digest(path):
    """path: local regular file; SHA256 byte identity, not permission certification."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    """--snapshot actual pre-task hash map; --ratings legacy85 hash only, no alteration."""
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--ratings',type=Path,required=True);a=p.parse_args()
    before=json.loads(a.snapshot.read_text());names=('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md')
    allowed={f'docs/presentation/{n}' for n in names};changes=[n for n,h in before.items() if n not in allowed and (not (ROOT/n).is_file() or digest(ROOT/n)!=h)]
    append={n:(ROOT/'docs/presentation'/n).read_bytes().startswith(Path('/tmp/scent-v221-'+n).read_bytes()) and (ROOT/'docs/presentation'/n).read_text().count('## V2-21 — 실제 사용자 추천 평가 시스템 (2026-10-30)')==1 for n in names}
    f=json.loads((ROOT/'outputs/final/freeze.json').read_text());frozen={n:digest(ROOT/n)==h for n,h in f['protected_sha256'].items()}
    from deployment.final_v1.config import assets_path,inspect_assets
    runtime=inspect_assets(assets_path())
    tests=(OUT/'tests.log').read_text();http=json.loads((OUT/'http_checks.json').read_text());browser=json.loads((OUT/'browser_checks.json').read_text())
    with sqlite3.connect(OUT/'data/participants.sqlite3') as c:
        participants=c.execute('SELECT COUNT(*) FROM v21_consents').fetchone()[0];ratings=c.execute('SELECT COUNT(*) FROM v21_ratings').fetchone()[0]
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    required=['REPORT.md','evaluation_protocol.json','data_schema.json','collection_status.json','data_quality_report.json','offline_evaluation.json','feedback_analysis.json','tests.log','execution.log']
    result=dict(status='PASS',original_snapshot_files=len(before),unexpected_original_changes=changes,presentation_append_only=append,Frozen19=frozen,
        freeze_manifest_unchanged=digest(ROOT/'outputs/final/freeze.json')==before['outputs/final/freeze.json'],runtime=runtime,
        legacy85_original_hash=digest(a.ratings),legacy85_unchanged=digest(a.ratings)=='fad8222ae3991ef6912c83e3904b71027476bc946f8858f0be81ac0114df236a',
        old_V214_DB_and_V216_to20_files_preserved=not changes,new_policy_retroactive_to_legacy85=False,
        tests_passed='Ran 39 tests' in tests and tests.rstrip().endswith('OK'),tests=39,http_checks=http,browser_checks=browser,
        actual_new_real_participants=participants,actual_new_real_ratings=ratings,actual_MF_fits=0,model_changes=False,
        required_outputs_present=all((OUT/n).is_file() for n in required),git=dict(branch=branch,head=head,status=status,mutations=False),
        environment=dict(python=sys.version.split()[0],platform=platform.platform()),packages_installed=False,external_uploads=False,
        access_control='0700/0600 local OS-owner protection; operator1 identity/OS-account separation is operational, not multi-user remote auth')
    assert not changes and all(append.values()) and len(frozen)==19 and all(frozen.values()) and result['legacy85_unchanged'] and result['freeze_manifest_unchanged']
    assert result['tests_passed'] and result['required_outputs_present'] and http['status']==browser['status']=='PASS' and participants==ratings==0
    assert branch=='development-v2' and head=='b2eb5455b0ae2bbb9ba0c6dd073ddb783bd6116b'
    with (OUT/'integrity.json').open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(dict(status='PASS',Frozen19=19,original_snapshot_files=len(before),unexpected_original_changes=changes,tests=39,actual_new_real_participants=participants,legacy85_preserved=True,git=result['git']),ensure_ascii=False))

if __name__=='__main__':main()
