"""Synthetic analysis sanity checks only; no fit, no legacy validation/Test data."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_feasibility import describe,gini,histogram,data_analysis,planned_split_counts,prevent_training,deny,ROOT
class AnalysisTests(unittest.TestCase):
    def test_describe(self):
        d=describe([1,2,3]);self.assertEqual(d['mean'],2);self.assertEqual(d['median'],2)
    def test_zero_uniform_gini(self):self.assertAlmostEqual(gini([2,2]),0)
    def test_histogram(self):self.assertEqual(histogram([1,1,2]),{'1':2,'2':1})
    def fixture(self):
        rows=[(u,str(i),.8 if i%2 else .2) for u in ['a','b','c','d','e','f'] for i in range(6)]
        catalog={str(i):{'brand':'synthetic','tokens':['note:'+str(i),'accord:woody']} for i in range(6)}
        return rows,catalog
    def test_complete_matrix_density(self):
        rows,catalog=self.fixture();d,_,_=data_analysis(rows,catalog);self.assertEqual(d['density'],1);self.assertEqual(d['graph_components'],1)
    def test_blueprint_determinism(self):
        rows,catalog=self.fixture();a=planned_split_counts(rows,list(catalog));b=planned_split_counts(list(reversed(rows)),list(catalog));self.assertEqual(a,b)
    def test_training_guard(self):
        def fit():raise AssertionError('must not execute')
        sys.setprofile(prevent_training)
        try:
            with self.assertRaises(RuntimeError):fit()
        finally:sys.setprofile(None)
    def test_no_legacy_answer_open(self):
        for name in ['outputs/improvement/validation.json','outputs/final/internal_metrics.csv','outputs/final/external_answers_private.json']:
            with self.assertRaises(PermissionError):deny('open',(str(ROOT/name),'r',0))
if __name__=='__main__':unittest.main(verbosity=2)
