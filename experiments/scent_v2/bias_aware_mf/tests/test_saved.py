"""Post-run evidence only; no CV replay, actual-data training or old final read."""
import json,hashlib,unittest
from pathlib import Path
import numpy as np
from experiments.scent_v2.bias_aware_mf.core import ROOT,OUT

class SavedTests(unittest.TestCase):
    def test13_real_bias_learning(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());bias=[f for f in r['fits'] if f['family']=='bias'];self.assertEqual(len(bias),5)
        self.assertTrue(all(f['user_bias_norm']>0 and f['item_bias_norm']>0 and f['loss_last']<f['loss_first'] for f in bias))
    def test14_same_cv_boundary_and_prune(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());self.assertEqual(r['CV_user_count'],50);self.assertEqual(r['V24_output_reads'],0);self.assertEqual(r['reserved_rating_tokens_decoded'],0)
        self.assertFalse(r['additional_gate_passed']);self.assertEqual(r['actual_data_MF_fit_count'],11);self.assertEqual(r['selected'],'hybrid_baseline')
        self.assertAlmostEqual(r['models']['hybrid_baseline']['mean_ndcg'],.040963057685131546,places=12)
    def test15_actual_saved_inference(self):
        from experiments.scent_v2.bias_aware_mf.run import load_model
        from experiments.scent_v2.bias_aware_mf.core import predict
        c,m,b,meta=load_model(OUT/'best_model.npz');self.assertFalse(hasattr(m,'P'));self.assertFalse(hasattr(m,'users'))
        support=[(i,.7) for i in sorted(c.vectors)[:5]];top=predict(meta['spec'],support,sorted(c.vectors),c,m,b);self.assertEqual(len(set(top)),5);self.assertFalse(set(top)&{i for i,y in support})
    def test16_Frozen19_unchanged(self):
        from deployment.final_v1.config import SOURCE_FREEZE
        p=ROOT/'outputs/final/freeze.json';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),SOURCE_FREEZE)
        entries=json.loads(p.read_text())['protected_sha256'];self.assertEqual(len(entries),19)
        for n,h in entries.items():self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h)

if __name__=='__main__':unittest.main()
