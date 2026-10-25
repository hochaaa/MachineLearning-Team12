"""Synthetic verification of leakage, ambiguity and numerical invariants."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from perfume.data import atrafshan, identity, matcher, match, aligned, laure_catalog
from perfume.splits import partition, threshold_arms, assert_disjoint
from perfume.models import Content, MatrixFactorization, Baseline, hybrid, knowledge
from perfume.evaluation import ranking_metrics, score_users
from perfume.external import recommend_new_user


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {str(i): {'name': str(i), 'brand': 'demo',
                       'tokens': ['accord:woody' if i%2 else 'accord:floral', f'note:n{i}']} for i in range(8)}
        self.rows = [(f'u{u}', str(i), (i%4+1)/4) for u in range(4) for i in range(8)]
        self.train, self.val, self.test = partition(self.rows)

    def test_zero_requires_policy_and_preserves_other_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'raw.json'
            row = {'user_id':'x','perfume_id':'1','perfume_name':'demo','perfume_brand':'brand',
                   'user_vote_on_perfume': {'votes': {'رایحه':'0','ماندگاری':'7'}}}
            path.write_text(json.dumps([row]))
            with self.assertRaises(ValueError): atrafshan(path)
            self.assertEqual(len(atrafshan(path, 'include')[1]), 1)
            self.assertEqual(len(atrafshan(path, 'exclude')[1]), 0)

    def test_duplicate_conflicts_quarantined(self):
        self.assertEqual(aligned([('u','a',.1),('u','b',.2)], {'a':'x','b':'x'}), [])

    def test_concentration_version_collision(self):
        self.assertNotEqual(identity('Dior','Homme EDT'), identity('Dior','Homme EDP'))
        self.assertNotEqual(identity('Dior','Homme'), identity('Dior','Homme Elixir'))
        self.assertEqual(identity('Dior','Homme EDT'), identity('Dior','Homme Eau de Toilette'))
        index = matcher({'1': {'name':'x','brand':'a'}, '2': {'name':'x','brand':'a'}})
        self.assertEqual(match(index,'a','x'), (None,'ambiguous'))

    def test_splits_common_labels_and_training_expansion(self):
        rows = self.rows + [('low', str(i), .5) for i in range(3)]
        arms = threshold_arms(rows)
        self.assertEqual(arms[3][1:], arms[5][1:])
        self.assertEqual(sum(u=='low' for u,_,_ in arms[3][0]), 3)
        self.assertFalse(any(u=='low' for u,_,_ in arms[5][0]))
        self.assertEqual(partition(rows), partition(list(reversed(rows))))
        for train,val,test in arms.values(): assert_disjoint(train,val,test)
        with self.assertRaises(ValueError): assert_disjoint(self.train,self.train)

    def test_train_only_vocabulary(self):
        content = Content().fit(self.catalog, ['0'])
        self.assertNotIn('note:n1', content.idf)
        self.assertTrue(np.isnan(content.score([], ['1'])[0]))

    def test_mf_objective_reproducibility_and_learning(self):
        a = MatrixFactorization(epochs=60).fit(self.train)
        b = MatrixFactorization(epochs=60).fit(self.train)
        np.testing.assert_array_equal(a.Q,b.Q)
        self.assertLess(a.losses[-1],a.losses[0])
        self.assertTrue(np.isnan(a.score('unknown',['0'])[0]))
        self.assertTrue(np.isnan(a.score('u0',['unknown'])[0]))

    def test_foldin_fixed_factors_and_ridge_stationarity(self):
        mf = MatrixFactorization(epochs=10).fit(self.train)
        q = mf.Q.copy()
        known = list(mf.items)[:3]
        support = [(i,.8) for i in known]
        vector = mf.fold_in(support + [('unknown',1)])
        matrix = np.array([mf.Q[mf.items[i]] for i in known])
        residual = matrix.T@(matrix@vector-np.full(3,.8))+3*mf.reg*vector
        np.testing.assert_allclose(residual,0,atol=1e-12)
        np.testing.assert_array_equal(q,mf.Q)
        self.assertIsNone(mf.fold_in([('unknown',1)]))

    def test_cold_start_fallback(self):
        np.testing.assert_allclose(hybrid(np.array([.8,np.nan,np.nan]),np.array([np.nan,.6,np.nan]),.5,np.array([.1,.2,.3])),[.8,.6,.3])
        self.assertAlmostEqual(hybrid(np.array([.8]),np.array([.4]),.5,np.array([0]))[0],.6)

    def test_knowledge_constraints_and_unsupported_metadata(self):
        result = knowledge(self.catalog,list(self.catalog),np.zeros(8),required=['accord:woody'], forbidden=['note:n1'])
        self.assertTrue(result)
        for item,_,explanation in result:
            self.assertIn('accord:woody',self.catalog[item]['tokens'])
            self.assertNotIn('note:n1',self.catalog[item]['tokens'])
            self.assertTrue(explanation['required_satisfied'])
        with self.assertRaises(ValueError): knowledge(self.catalog,[],[],season='summer')

    def test_metrics(self):
        result = ranking_metrics(['a','b'],{'b'},2)
        self.assertAlmostEqual(result['ndcg'],1/np.log2(3))
        self.assertEqual(result['precision'],.5)
        self.assertIsNone(ranking_metrics([],set()))

    def test_answer_mutation_cannot_change_scoring(self):
        mf = MatrixFactorization(epochs=5).fit(self.train)
        content = Content().fit(self.catalog,mf.items)
        baseline = Baseline().fit(self.train)
        support=[('0',.8)]
        before=mf.Q.copy()
        first=recommend_new_user(support, sorted(self.catalog),content,mf,baseline,.5)
        # Answers live only in the evaluation harness; scorer accepts no answer argument.
        answers=[('new','7',0)]
        answers[0]=('new','6',1)
        second=recommend_new_user(support, sorted(self.catalog),content,mf,baseline,.5)
        self.assertEqual(first,second)
        self.assertNotIn('0',first)
        np.testing.assert_array_equal(before,mf.Q)

    def test_conflicting_laure_primary_key_quarantine(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            for name in ('brand','notes','season','category'):
                (directory/f'{name}.json').write_text(json.dumps([{'pk':1,'fields':{'name':name}}]))
            rows=[{'pk':7,'fields':{'name':name,'brand':1}} for name in ('first','second')]
            (directory/'perfumes.json').write_text(json.dumps(rows))
            catalog,errors=laure_catalog(directory)
            self.assertNotIn('7',catalog)
            self.assertEqual(errors['conflicting_duplicate_perfume_pk'],1)

    def test_laure_foreign_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            for name in ('brand','notes','season','category'):
                (directory/f'{name}.json').write_text(json.dumps([{'pk':1,'fields':{'name':name}}]))
            row={'pk':1,'fields':{'name':'x','brand':1,'top_notes':[1,99]}}
            (directory/'perfumes.json').write_text(json.dumps([row]))
            catalog,errors=laure_catalog(directory)
            self.assertEqual(catalog['1']['top_notes'],['notes'])
            self.assertEqual(errors['top_notes'],1)


if __name__ == '__main__': unittest.main()
