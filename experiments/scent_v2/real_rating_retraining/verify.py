"""Postflight integrity tests; hash original bytes without parsing held-out labels."""
import argparse,hashlib,json,subprocess,unittest
from pathlib import Path
from .run import ROOT,OUT,json_file
DOCS={'docs/presentation/'+name for name in ('MODEL_IMPROVEMENT_STORY.md','EXPERIMENT_TIMELINE.md','PERFORMANCE_COMPARISON.md','PRESENTATION_SLIDES_OUTLINE.md','EXPERIMENT_LOG.md')}

def verify(snapshot,csv_path):
    """snapshot: actual pre-task SHA256 map; csv_path: unchanged original local CSV."""
    before=json.loads(snapshot.read_text());changed=[];missing=[]
    for rel,digest in before.items():
        p=ROOT/rel
        if not p.is_file():missing.append(rel)
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(rel)
    append={}
    for rel in DOCS:
        original=snapshot.parent/('scent-v216-'+Path(rel).name)
        append[rel]=original.is_file() and hashlib.sha256(original.read_bytes()).hexdigest()==before[rel] and (ROOT/rel).read_bytes().startswith(original.read_bytes())
    f=json.loads((ROOT/'outputs/final/freeze.json').read_text())['protected_sha256']
    frozen={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in f.items()}
    validation=json.loads((OUT/'data_validation.json').read_text())
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    checks=dict(original_csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest()==validation['original_sha256'],
        original_files=len(before),unchanged=len(before)-len(changed)-len(missing),modified=changed,missing=missing,
        append_only=append,frozen19=frozen,branch=branch,head=head,status=status,
        freeze_manifest_unchanged=hashlib.sha256((ROOT/'outputs/final/freeze.json').read_bytes()).hexdigest()==before['outputs/final/freeze.json'],
        scope='Regular files; .git/.local/.venv/node_modules/dist/cache/symlinks excluded; original runtime integrity separately checked',
        protected_before_sha256_scope='Full pre-task regular file map in private local snapshot; no user data copied into report')
    class Postflight(unittest.TestCase):
        def test_01_real_schema_and_original(self):
            self.assertEqual((validation['users'],validation['rows'],validation['unique_product_ids']),(12,85,58))
            self.assertTrue(checks['original_csv_sha256'])
        def test_02_frozen19_and_manifest(self):
            self.assertEqual(len(frozen),19);self.assertTrue(all(frozen.values()));self.assertTrue(checks['freeze_manifest_unchanged'])
        def test_03_data_and_manifests_unchanged(self):
            self.assertFalse([p for p in changed+missing if p.startswith(('Term-project-datasets/','outputs/validation/','outputs/improvement/','outputs/final/'))])
        def test_04_services_unchanged(self):self.assertFalse([p for p in changed+missing if p.startswith(('web/','deployment/'))])
        def test_05_v214_v215_preserved(self):
            self.assertFalse([p for p in changed+missing if any(x in p for x in ('real_user_dataset/','external_real_data/'))])
        def test_06_append_only_presentation(self):self.assertEqual(set(changed),DOCS);self.assertTrue(all(append.values()))
        def test_07_git_unchanged(self):
            self.assertEqual(branch,'development-v2');self.assertEqual(head,'b2eb5455b0ae2bbb9ba0c6dd073ddb783bd6116b')
            self.assertEqual(status,'?? docs/presentation/\n?? experiments/scent_v2/\n')
            self.assertFalse(subprocess.check_output(['git','diff','--cached','--name-only'],text=True).strip())
        def test_08_all_original_and_no_training(self):
            self.assertFalse(missing);self.assertFalse(set(changed)-DOCS)
            cfg=json.loads((OUT/'training_config.json').read_text())
            self.assertEqual(cfg['model_fit_attempts'],0)
            self.assertEqual(json.loads((OUT/'dataset_integration_summary.json').read_text())['actual_added_training_ratings'],0)
    with (OUT/'tests.log').open('a') as stream:
        stream.write('\nPOSTFLIGHT REAL INPUT / PRESERVATION CHECKS\n')
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Postflight))
    checks['result']='PASS' if result.wasSuccessful() else 'FAIL'
    json_file('integrity.json',checks)
    json_file('post_checks.json',dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),result=checks['result']))
    if not result.wasSuccessful():raise RuntimeError('Integrity check failed; stop without changing originals')
    print(f'Postflight {result.testsRun} PASS; original files {len(before)}: {checks["unchanged"]} unchanged + {len(changed)} append-only; Frozen19 PASS')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--csv',type=Path,required=True)
    a=p.parse_args();verify(a.snapshot,a.csv)
