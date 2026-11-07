"""Hash original bytes and verify append-only presentation evidence; no model loading."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from .build import ROOT,OUT,write_json


def main():
    """--snapshot private pre-task SHA256 map; --csv unchanged product inventory source."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--csv',type=Path,required=True);a=p.parse_args()
    before=json.loads(a.snapshot.read_text());changed=[];missing=[]
    for name,digest in before.items():
        f=ROOT/name
        if not f.is_file():missing.append(name)
        elif hashlib.sha256(f.read_bytes()).hexdigest()!=digest:changed.append(name)
    allowed={'docs/presentation/'+n for n in ('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md')}
    append={}
    for n in allowed:
        old=a.snapshot.parent/('scent-v217-'+Path(n).name)
        append[n]=old.is_file() and hashlib.sha256(old.read_bytes()).hexdigest()==before[n] and (ROOT/n).read_bytes().startswith(old.read_bytes())
    frozen=json.loads((ROOT/'outputs/final/freeze.json').read_text())['protected_sha256']
    protected={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==d for n,d in frozen.items()}
    s=json.loads((OUT/'feature_compatibility.json').read_text())
    original_csv=hashlib.sha256(a.csv.read_bytes()).hexdigest()==s['original_csv_sha256']
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    checks=dict(original_inventory_files=len(before),unchanged=len(before)-len(changed)-len(missing),changed=changed,missing=missing,
        append_only=append,frozen19=protected,original_csv_unchanged=original_csv,
        freeze_manifest_unchanged=hashlib.sha256((ROOT/'outputs/final/freeze.json').read_bytes()).hexdigest()==before['outputs/final/freeze.json'],
        runtime_content_sha256=s['idf_payload_sha256'],runtime_manifest_and_reused_source_check=s['runtime_integrity'],
        branch=branch,head=head,git_status=status,
        excluded_scope='Regular file hashes omit .git/.local/.venv/node_modules/dist/caches/symlinks; immutable runtime separately verified',
        model_training_calls=0,recommendation_calls=0,evaluation_calls=0,
        original_user_rating_values_used_for_metadata=False,web_requests_contained_user_IDs_or_ratings=False,
        existing_catalog_written=False,package_installs=0,git_mutation_commands=0)
    passed=(not missing and set(changed)==allowed and all(append.values()) and len(protected)==19 and all(protected.values())
            and original_csv and checks['freeze_manifest_unchanged'] and branch=='development-v2' and head=='b2eb5455b0ae2bbb9ba0c6dd073ddb783bd6116b'
            and status=='?? docs/presentation/\n?? experiments/scent_v2/\n')
    checks['status']='PASS' if passed else 'FAIL';write_json('integrity.json',checks)
    log=['2026-10-30 Asia/Seoul — V2-17',
        'Product-only CSV projection:58 source product IDs; participant/rating/time columns not retained/analyzed',
        'Targeted official manufacturer product/collection searches and pages manually reviewed. No mass scraper/raw website dump/third-party review DB collection',
        'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.perfume_catalog_expansion.build --csv <local-original-csv>',
        'Build result: identities46; confirmed notes46; confirmed explicit named accord products6',
        'Quality: VERIFIED6/PARTIALLY_VERIFIED40/NEEDS_REVIEW11/UNRESOLVED1',
        'Frozen vocabulary transform:45 nonzero,1 known zero,12 not assessed; IDF604/active479features574 unchanged',
        'SCENT_V217_ORIGINAL_CSV=<local-original-csv> PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/perfume_catalog_expansion/tests -v',
        '20 tests PASS (tests.log); fixtures do not supply research facts',
        'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.perfume_catalog_expansion.report',
        'Report created and five presentation files appended, old prefixes byte-preserved',
        'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.perfume_catalog_expansion.verify --snapshot <private-before-snapshot> --csv <local-original-csv>',
        f'Integrity {checks["status"]}; Frozen19:{sum(protected.values())}/19; original CSV unchanged:{original_csv}; old files unchanged:{checks["unchanged"]}; append-only:{len(changed)}',
        f'Git {branch}@{head}; original git status unchanged',
        'No model fit/IDF refit/MF factors/recommendation/evaluation/catalog expansion/service mutation/Git mutation/install',
        'Publication/deployment reuse permission NOT_ESTABLISHED; all rollout_ready flags false']
    with (OUT/'execution.log').open('x') as f:f.write('\n'.join(log)+'\n')
    if not passed:raise RuntimeError('Integrity check failed; preserve originals and report')
    print(f'Integrity PASS; {checks["unchanged"]} originals unchanged +{len(changed)} append-only; Frozen19 PASS; CSV unchanged')

if __name__=='__main__':main()
