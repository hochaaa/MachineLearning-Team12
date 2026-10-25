"""Numerical and inference-boundary tests before any final test run."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from perfume.improvements import ProfileContent,BiasedMatrixFactorization,make_mf
from perfume.models import Baseline


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.rows=[(u,i,r) for u,delta in [('a',0),('b',-.1),('c',.1)]
                   for i,r in [('x',.8+delta),('y',.5+delta),('z',.7+delta)]]
        self.catalog={i:{'tokens':['note:'+i]} for i in ['x','y','z','unseen']}

    def test_biased_learning_and_reproducibility(self):
        a=BiasedMatrixFactorization(factors=4,epochs=60).fit(self.rows)
        b=BiasedMatrixFactorization(factors=4,epochs=60).fit(self.rows)
        self.assertLess(a.losses[-1],a.losses[0])
        np.testing.assert_array_equal(a.Q,b.Q)
        self.assertGreater(a.item_bias[a.items['x']],a.item_bias[a.items['y']])
        self.assertTrue(np.isnan(a.score('unknown',['x'])[0]))

    def test_augmented_foldin_stationarity_and_frozen_state(self):
        mf=BiasedMatrixFactorization(factors=4,epochs=10).fit(self.rows)
        before=[x.copy() for x in [mf.P,mf.Q,mf.user_bias,mf.item_bias]]
        support=[('x',.9),('y',.3),('unknown',.1)]
        vector=mf.fold_in(support)
        design=np.array([np.r_[mf.Q[mf.items[i]],1] for i in ['x','y']])
        y=np.array([r-mf.mean-mf.item_bias[mf.items[i]] for i,r in support[:2]])
        np.testing.assert_allclose(design.T@(design@vector-y)+2*mf.reg*vector,0,atol=1e-12)
        for previous,current in zip(before,[mf.P,mf.Q,mf.user_bias,mf.item_bias]):np.testing.assert_array_equal(previous,current)
        self.assertIsNone(mf.fold_in([('untrained',.9)]))

    def test_profile_modes_and_oov(self):
        liked=ProfileContent('liked').fit(self.catalog,['x','y','z'])
        scores=liked.score([('x',.9),('y',.2)],['x','y','unseen'])
        self.assertGreater(scores[0],scores[1]);self.assertTrue(np.isnan(scores[2]))
        self.assertTrue(np.isnan(liked.score([('x',.2)],['x'])[0]))
        centered=ProfileContent('centered').fit(self.catalog,['x','y'])
        scores=centered.score([('x',.9),('y',.1)],['x','y'])
        self.assertGreater(scores[0],.5);self.assertLess(scores[1],.5)
        self.assertTrue(np.isnan(centered.score([('x',.5),('y',.5)],['x'])[0]))

    def test_external_identity_split_and_cold_start_exclusion(self):
        from perfume.external_protocol import external_partition
        pairs=[('u',str(i)) for i in range(6)]+[('short','x')]
        first,excluded=external_partition(pairs,set(map(str,range(6))))
        second,_=external_partition(list(reversed(pairs)),set(map(str,range(6))))
        self.assertEqual(first,second)
        support,answers=first['u']
        self.assertEqual(len(support),3)
        self.assertFalse(set(support)&set(answers))
        self.assertEqual(set(support+answers),set(map(str,range(6))))
        self.assertEqual(excluded['insufficient_history'],1)
        blocked,reasons=external_partition(pairs,set())
        self.assertFalse(blocked);self.assertEqual(reasons['no_support_factor'],1)

    def test_scoring_uses_support_without_fit(self):
        from perfume.frozen import score_frozen
        mf=BiasedMatrixFactorization(factors=4,epochs=5).fit(self.rows)
        content=ProfileContent('rating').fit(self.catalog,['x','y','z'])
        baseline=Baseline().fit(self.rows)
        before=mf.Q.copy()
        with patch.object(mf,'fit',side_effect=AssertionError('No refitting')):
            result=score_frozen([('x',.8)],['x','y','z'],mf,content,baseline,.25)
        self.assertNotIn('x',result['hybrid'])
        np.testing.assert_array_equal(before,mf.Q)

    def test_no_test_or_external_data_in_search_script(self):
        # A whitelist of data reads protects the tuning entrypoint from answer loading.
        import ast
        tree=ast.parse(Path('scripts/improve.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                self.assertNotIn('reviews.json',node.value)
                self.assertNotIn('test.json',node.value)
                self.assertNotIn('split_manifest.json',node.value)


if __name__=='__main__':unittest.main()
