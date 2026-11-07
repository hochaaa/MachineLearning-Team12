"""Read-only post-run audit; --snapshot is the pre-task path-to-SHA256 JSON."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from .catalog import ROOT, OUT

def digest(path):
    """path: regular local file; return SHA256 without modifying its payload."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--ratings',type=Path,required=True)
    args=parser.parse_args(); before=json.loads(args.snapshot.read_text())
    names=('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md')
    allowed={f'docs/presentation/{name}' for name in names}
    changed=[name for name,h in before.items() if name not in allowed and (not (ROOT/name).is_file() or digest(ROOT/name)!=h)]
    appended={name:(ROOT/'docs/presentation'/name).read_bytes().startswith(Path('/tmp/scent-v218-'+name).read_bytes()) and (ROOT/'docs/presentation'/name).read_text().count('## V2-18 — 확장 Content 독립 실험과 사용권 분리 (2026-10-30)')==1 for name in names}
    freeze=json.loads((ROOT/'outputs/final/freeze.json').read_text())
    frozen={name:digest(ROOT/name)==h for name,h in freeze['protected_sha256'].items()}
    from deployment.final_v1.config import assets_path,inspect_assets
    runtime=inspect_assets(assets_path())
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    source=json.loads((OUT/'licensed_source/provenance.json').read_text())
    source_ok=all(digest(OUT/'licensed_source'/r['path'])==r['sha256'] for r in source['files'])
    required=('REPORT.md','expanded_catalog.csv','expanded_feature_summary.json','rating_mapping_summary.json','evaluation_eligibility.json','model_comparison.csv','recommendation_examples.csv','recommendation_diagnostics.json','tests.log')
    tests=(OUT/'tests.log').read_text()
    result=dict(status='PASS',original_snapshot_files=len(before),unexpected_original_changes=changed,presentation_append_only=appended,
        frozen_protected_files=len(frozen),frozen_checks=frozen,freeze_manifest_unchanged=digest(ROOT/'outputs/final/freeze.json')==before['outputs/final/freeze.json'],runtime_integrity=runtime,
        original_rating_sha256=digest(args.ratings),original_ratings_unchanged=digest(args.ratings)=='fad8222ae3991ef6912c83e3904b71027476bc946f8858f0be81ac0114df236a',
        licensed_source_hashes_verified=source_ok,required_outputs_present=all((OUT/p).is_file() for p in required),tests_passed='Ran 35 tests' in tests and tests.rstrip().endswith('OK'),
        branch=branch,head=head,git_status=status,git_mutations_performed=False,packages_installed=False,
        MF_fits=0,IDF_fits=0,old_validation_internal_external_test_rerun=False)
    assert not changed and all(appended.values()) and len(frozen)==19 and all(frozen.values())
    assert result['freeze_manifest_unchanged'] and result['original_ratings_unchanged'] and source_ok and result['tests_passed'] and result['required_outputs_present']
    assert branch=='development-v2' and head=='b2eb5455b0ae2bbb9ba0c6dd073ddb783bd6116b'
    with (OUT/'integrity.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    (OUT/'integrity.json').chmod(0o600)
    print(json.dumps({k:result[k] for k in ('status','original_snapshot_files','unexpected_original_changes','frozen_protected_files','branch','head','git_status')},ensure_ascii=False))

if __name__=='__main__':main()
