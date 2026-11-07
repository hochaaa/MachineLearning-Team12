"""Post-run evidence checks only; no fits, scoring or final-label reads."""
import json,unittest
import numpy as np
from experiments.scent_v2.accuracy_optimization.core import OUT

class SavedTests(unittest.TestCase):
    def test13_final_once_after_freeze(self):
        self.assertEqual(json.loads((OUT/'final_opened_once.json').read_text())['final_open_count'],1)
        self.assertFalse(json.loads((OUT/'selection.json').read_text())['final_values_seen'])
        self.assertTrue(json.loads((OUT/'final_fit_complete.json').read_text())['final_users_excluded'])
    def test14_fit_budget(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());self.assertLessEqual(r['MF_fit_count'],5);self.assertEqual(len(r['fits']),r['MF_fit_count']);self.assertFalse(r['selection_uses_final'])
    def test15_no_user_factors_in_artifact(self):
        with np.load(OUT/'best_model.npz',allow_pickle=False) as data:
            self.assertNotIn('P',data.files);self.assertNotIn('users',data.files);self.assertTrue(np.isfinite(data['Q']).all())
    def test16_same_final_denominator(self):
        r=json.loads((OUT/'evaluation_results.json').read_text());self.assertEqual(len({s['users'] for s in r['final'].values()}),1);self.assertEqual(len({s['positive_users'] for s in r['final'].values()}),1)

if __name__=='__main__':unittest.main()
