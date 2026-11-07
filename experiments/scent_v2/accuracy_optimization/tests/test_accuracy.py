"""Pre-fit synthetic split, scoring, serialization and final-access invariants."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from experiments.scent_v2.accuracy_optimization.core import split,validate_train,components,score_variant,Content,MatrixFactorization,Baseline,percent_array
from experiments.scent_v2.accuracy_optimization.run import open_final,save_model,load_model
from experiments.scent_v2.recommend import score as original

class AccuracyTests(unittest.TestCase):
    def setUp(self):
        self.rows=[(f'u{u}',str(i),.1*(i%10)) for u in range(36) for i in range(7)]
        self.ids=list(map(str,range(10)));self.support=[(str(i),.7) for i in range(5)]
        self.c=Content();self.c.idf={'note:rose':1.};self.c.vectors={i:{'note:rose':1.} for i in self.ids}
        self.m=MatrixFactorization(factors=2,regularization=.01);self.m.Q=np.asarray([[.2,.3]]*10);self.m.items={i:n for n,i in enumerate(self.ids)}
        self.b=Baseline();from collections import defaultdict
        self.b.counts=defaultdict(int,{i:1 for i in self.ids});self.b.maximum=1
    def test01_user_split_disjoint(self):
        train,dev,final=split(self.rows,self.ids);self.assertFalse({r['user'] for r in dev}&{r['user'] for r in final});validate_train(train,[r['user'] for r in dev+final])
    def test02_seed_reproducible(self):self.assertEqual(split(self.rows,self.ids),split(self.rows,self.ids))
    def test03_label_blind(self):
        a=split(self.rows,self.ids);b=split([(u,i,1-r) for u,i,r in self.rows],self.ids)
        for left,right in zip(a[1]+a[2],b[1]+b[2]):self.assertEqual(left['user'],right['user']);self.assertEqual([i for i,r in left['support']],[i for i,r in right['support']])
    def test04_pairs_disjoint(self):
        for row in sum(split(self.rows,self.ids)[1:],[]):self.assertEqual(len(row['support']),5);self.assertFalse({i for i,r in row['support']}&{i for i,r in row['answers']})
    def test05_fit_boundary(self):
        with self.assertRaises(ValueError):validate_train([('u','i',.7)],['u'])
    def test06_baseline_formula(self):
        a=score_variant(dict(method='baseline'),self.support,self.ids,self.c,self.m,self.b);b=original(self.support,self.ids,self.c,self.m,self.b)['methods']['hybrid']['top'];self.assertEqual(a,b)
    def test07_common_candidates_seen(self):
        for method in ('baseline','v22_unified','v23_personalized','v23_personalized_mmr','rank_hybrid'):
            s=dict(method=method,profile='rating',alpha=.5);top=score_variant(s,self.support,self.ids,self.c,self.m,self.b);self.assertFalse(set(top)&{i for i,r in self.support});self.assertEqual(len(top),5)
    def test08_missing_not_zero(self):
        a=percent_array(np.array([3,np.nan,3]),['a','b','c']);self.assertTrue(np.isnan(a[1]));self.assertEqual(a[0],a[2])
    def test09_final_locked(self):
        with tempfile.TemporaryDirectory() as t,patch('experiments.scent_v2.accuracy_optimization.run.OUT',Path(t)):
            with self.assertRaises(RuntimeError):open_final()
    def test10_final_once(self):
        with tempfile.TemporaryDirectory() as t,patch('experiments.scent_v2.accuracy_optimization.run.OUT',Path(t)):
            for name in ('selection.json','final_fit_complete.json'):(Path(t)/name).write_text('{}')
            (Path(t)/'sealed_final.private.json').write_text('[]');self.assertEqual(open_final(),[])
            with self.assertRaises(FileExistsError):open_final()
    def test11_saved_model_no_users(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'m.npz';cfg=dict(factors=2,epochs=1,learning_rate=.01,regularization=.01,seed=12)
            save_model(path,self.c,self.m,self.b,self.ids,dict(method='baseline'),cfg)
            c,m,b,meta=load_model(path);self.assertFalse(hasattr(m,'P'));np.testing.assert_array_equal(m.Q,self.m.Q)
            self.assertEqual(score_variant(meta['spec'],self.support,self.ids,c,m,b),score_variant(dict(method='baseline'),self.support,self.ids,self.c,self.m,self.b))
    def test12_no_answers_parameter(self):
        import inspect
        self.assertNotIn('answers',inspect.signature(score_variant).parameters)

if __name__=='__main__':unittest.main()
