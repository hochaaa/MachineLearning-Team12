"""Standalone tests; fixture edits go ONLY to new temporary asset copies, never legacy files."""
import unittest,tempfile,shutil,json,hashlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
from deployment.standalone_v1.runtime_loader import StandaloneService,inspect_assets,RuntimeAssetError,sha256
from deployment.standalone_v1.runtime_config import ROOT
from perfume.models import MatrixFactorization,Content,Baseline
ASSETS=ROOT/'outputs/step12_runtime/assets'
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='scent-step12-unit-');self.assets=Path(self.temp.name)/'assets';shutil.copytree(ASSETS,self.assets)
    def tearDown(self):self.temp.cleanup()
    def rewrite_manifest(self,edit):
        p=self.assets/'manifest.json';m=json.loads(p.read_text());edit(m);p.write_text(json.dumps(m))
    def test_load_without_fit(self):
        with patch.object(MatrixFactorization,'fit',side_effect=AssertionError('No training')),patch.object(Content,'fit',side_effect=AssertionError('No training')),patch.object(Baseline,'fit',side_effect=AssertionError('No training')):
            s=StandaloneService(self.assets);self.assertEqual(len(s.candidates),479)
    def test_no_user_mapping_or_user_factors(self):
        s=StandaloneService(self.assets);self.assertFalse(hasattr(s.mf,'users'));self.assertFalse(hasattr(s.mf,'P'));self.assertEqual(s.mf.Q.shape,(479,4))
    def test_q_readonly_and_finite(self):
        s=StandaloneService(self.assets);self.assertFalse(s.mf.Q.flags.writeable);self.assertTrue(np.isfinite(s.mf.Q).all())
    def test_valid_manifest_pin(self):self.assertTrue(inspect_assets(self.assets,sha256(self.assets/'manifest.json')))
    def test_invalid_manifest_pin(self):
        with self.assertRaises(RuntimeAssetError):inspect_assets(self.assets,'0'*64)
    def test_missing_manifest(self):
        (self.assets/'manifest.json').unlink()
        with self.assertRaises(RuntimeAssetError):inspect_assets(self.assets)
    def test_missing_payload(self):
        (self.assets/'catalog.json').unlink()
        with self.assertRaises(RuntimeAssetError):inspect_assets(self.assets)
    def test_corrupt_payload(self):
        with (self.assets/'runtime.json').open('ab') as f:f.write(b' ')
        with self.assertRaises(RuntimeAssetError):inspect_assets(self.assets)
    def test_reject_path_traversal(self):
        self.rewrite_manifest(lambda m:m['files'][0].update(path='../runtime.json'))
        with self.assertRaises(RuntimeAssetError):inspect_assets(self.assets)
    def test_reused_code_fingerprint(self):
        self.rewrite_manifest(lambda m:m['source_code_sha256'].update({'src/perfume/models.py':'0'*64}))
        with self.assertRaises(RuntimeAssetError):inspect_assets(self.assets)
    def test_catalog_alignment(self):
        p=self.assets/'catalog.json';d=json.loads(p.read_text());d.pop(next(iter(d)));p.write_text(json.dumps(d));self.rewrite_manifest(lambda m:[e.update(bytes=p.stat().st_size,sha256=sha256(p)) for e in m['files'] if e['path']=='catalog.json'])
        with self.assertRaises(RuntimeAssetError):StandaloneService(self.assets)
    def test_exact_inherited_methods(self):
        from web.backend.adapter import FrozenService
        for method in ['recommend','record','search','search_response']:self.assertIs(getattr(StandaloneService,method),getattr(FrozenService,method))
    def test_payload_schema_no_users_or_rows(self):
        r=json.loads((self.assets/'runtime.json').read_text());self.assertEqual(set(r),{'schema','selected','items','popularity_counts','popularity_maximum'});self.assertEqual(len(r['items']),479)
    def test_user_ids_not_copied(self):
        # Local privacy audit only: no ID values ever leave this assertion or get logged.
        ids=json.loads((ROOT/'outputs/final/model.json').read_text())['users']
        text=b'\n'.join(p.read_bytes() for p in self.assets.glob('*.json'))
        self.assertTrue(all(i.encode() not in text for i in ids))
if __name__=='__main__':unittest.main(verbosity=2)
