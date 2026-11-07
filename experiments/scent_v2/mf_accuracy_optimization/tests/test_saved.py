"""Post-training checks from V25 outputs only, no old final data reads or fits."""
import json,unittest
from pathlib import Path
import numpy as np
from experiments.scent_v2.mf_accuracy_optimization.core import OUT

class SavedTests(unittest.TestCase):
    def test11_budget_and_no_reserved_labels(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());self.assertEqual(r['MF_fit_count'],5);self.assertEqual(r['Content_fit_count'],1);self.assertEqual(r['V24_final_rating_tokens_decoded'],0);self.assertEqual(r['V24_output_files_read'],0)
    def test12_same_baseline_and_saved_selection(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());self.assertAlmostEqual(r['baseline']['ndcg'],.052812448558299224,places=12)
        self.assertTrue(r['saved_model_roundtrip_top5_exact']);self.assertEqual(r['selection']['alpha'],.05);self.assertEqual(r['independent_final'],'NOT_EVALUATED')
    def test13_npz_no_users_and_inference(self):
        from experiments.scent_v2.accuracy_optimization.run import load_model
        from experiments.scent_v2.mf_accuracy_optimization.core import components,hybrid
        from experiments.scent_v2.recommend import rank
        c,m,b,meta=load_model(OUT/'best_model.npz');self.assertFalse(hasattr(m,'P'))
        with np.load(OUT/'best_model.npz',allow_pickle=False) as v:self.assertNotIn('users',v.files)
        support=[(i,.7) for i in sorted(c.vectors)[:5]];x=components(support,sorted(c.vectors),c,m,b);values=hybrid(x['content'],x['mf'],meta['spec']['alpha'],b.score(x['pool']));top=rank(x['pool'],values)[:5]
        self.assertEqual(len(set(top)),5);self.assertFalse(set(top)&{i for i,r in support})



class FrozenTests(unittest.TestCase):
    def test14_frozen_V1_unchanged(self):
        import hashlib
        from experiments.scent_v2.mf_accuracy_optimization.core import ROOT
        from deployment.final_v1.config import SOURCE_FREEZE
        p=ROOT/'outputs/final/freeze.json';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),SOURCE_FREEZE)
        checks=json.loads(p.read_text())['protected_sha256'];self.assertEqual(len(checks),19)
        for path,value in checks.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),value)

if __name__=='__main__':unittest.main()
