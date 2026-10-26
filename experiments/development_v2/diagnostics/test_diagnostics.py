"""Synthetic checks for diagnostic metrics; no real evaluation labels used."""
import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from failure_diagnosis import avg_rank,spearman,jaccard,score_stats,coverage,cluster_bootstrap,metric_parity,deny_legacy,ROOT
class DiagnosticTests(unittest.TestCase):
    def test_aggregate_metric_parity(self):self.assertTrue(metric_parity()['synthetic_metric_parity'])
    def test_rank_ties_average(self):np.testing.assert_array_equal(avg_rank([1,1,3]),[1.5,1.5,3])
    def test_spearman_reversed(self):self.assertAlmostEqual(spearman(np.array([1,2,3]),np.array([3,2,1])),-1)
    def test_constant_rank_undefined(self):self.assertIsNone(spearman(np.array([1,1]),np.array([2,3])))
    def test_jaccard(self):self.assertAlmostEqual(jaccard(['a','b'],['b','c']),1/3)
    def test_uniform_gini_entropy(self):
        c={i:{'tokens':['note:'+i]} for i in ['a','b']};s,f=coverage({'x':['a'],'y':['b']},['a','b'],c)
        self.assertAlmostEqual(s['gini'],0);self.assertAlmostEqual(s['entropy_bits'],1)
    def test_concentrated_exposures(self):
        c={i:{'tokens':[]} for i in ['a','b']};s,f=coverage({'x':['a'],'y':['a']},['a','b'],c)
        self.assertAlmostEqual(s['max_item_request_incidence'],1);self.assertAlmostEqual(s['gini'],.5)
    def test_cluster_bootstrap_primary(self):
        d={str(n):{0:.1,1:.2,2:.3} for n in range(10)};s=cluster_bootstrap(d,set(d),draws=20)
        self.assertAlmostEqual(s['fold_macro_delta'],.2);self.assertAlmostEqual(s['interval_low'],.2)
    def test_clip_and_ties(self):
        s=score_stats([0.,0.,.5,1.]);self.assertAlmostEqual(s['clip_boundary_fraction'],.75);self.assertAlmostEqual(s['duplicate_score_fraction'],.25)
    def test_forbidden_legacy_open(self):
        for name in ['outputs/improvement/validation.json','outputs/final/internal_metrics.csv','outputs/final/external_answers_private.json']:
            with self.assertRaises(PermissionError):deny_legacy('open',(str(ROOT/name),'r',0))
if __name__=='__main__':unittest.main(verbosity=2)
