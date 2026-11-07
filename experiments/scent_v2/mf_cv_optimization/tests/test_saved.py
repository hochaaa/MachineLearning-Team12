"""Saved CV evidence only, no repeat training/evaluation or V24 final reads."""
import json,hashlib,unittest
import numpy as np
from experiments.scent_v2.mf_cv_optimization.core import ROOT,OUT,folds

class SavedTests(unittest.TestCase):
    def test13_user_boundary_and_fits(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());self.assertEqual(r['MF_fit_count'],6)
        self.assertEqual([f['users'] for f in r['fits']],[40]*5+[50]);self.assertEqual(r['reserved_final_users_used'],0);self.assertEqual(r['background_user_training_rows'],0);self.assertEqual(r['V24_output_reads'],0)
    def test14_common_evaluation(self):
        r=json.loads((OUT/'evaluation_results.json').read_text())
        for m,s in r['models'].items():self.assertEqual(len(s['fold_ndcg']),5);self.assertEqual(s['pooled_positive_user']['users'],50)
        self.assertEqual(len({s['pooled_positive_user']['positive_users'] for s in r['models'].values()}),1)
    def test15_roundtrip(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());self.assertTrue(r['roundtrip_inference_exact'])
        with np.load(OUT/'best_model.npz',allow_pickle=False) as m:self.assertNotIn('P',m.files);self.assertNotIn('users',m.files);self.assertTrue(np.isfinite(m['Q']).all())
    def test16_Frozen19(self):
        from deployment.final_v1.config import SOURCE_FREEZE
        p=ROOT/'outputs/final/freeze.json';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),SOURCE_FREEZE)
        checks=json.loads(p.read_text())['protected_sha256'];self.assertEqual(len(checks),19)
        for name,h in checks.items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h)

if __name__=='__main__':unittest.main()
