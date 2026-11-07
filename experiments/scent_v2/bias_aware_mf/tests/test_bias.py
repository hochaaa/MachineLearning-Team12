"""Focused bias SGD/joint ridge math; synthetic labels only, no CV training here."""
import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from experiments.scent_v2.bias_aware_mf.model import BiasAwareMF,freeze_user_state
from experiments.scent_v2.bias_aware_mf.core import Content,MatrixFactorization,Baseline,predict
from experiments.scent_v2.bias_aware_mf.run import save_model,load_model
from experiments.scent_v2.recommend import score as old_score

class BiasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[(u,'i'+str(n),r) for u,ys in [('high',[.9,.8,.85,.95,.9,.8]),('low',[.3,.2,.25,.35,.3,.2])] for n,r in enumerate(ys)]
        cls.cfg=dict(factors=4,epochs=80,learning_rate=.02,regularization=.01,seed=12,bias_regularization=.01)
        cls.trained=BiasAwareMF(**cls.cfg).fit(cls.rows) # one synthetic fit per test process
    def setUp(self):
        self.ids=['i'+str(i) for i in range(10)];self.support=[(i,.8) for i in self.ids[:5]];self.m=copy.deepcopy(self.trained)
        self.c=Content();self.c.idf={'note:rose':1.};self.c.vectors={i:{'note:rose':1.} for i in self.ids}
        self.b=Baseline();from collections import defaultdict
        self.b.counts=defaultdict(int,{i:1 for i in self.ids});self.b.maximum=1
    def test01_real_sgd_learning(self):self.assertLess(self.m.losses[-1],self.m.losses[0]);self.assertTrue(np.isfinite(self.m.Q).all())
    def test02_mu_train_only(self):self.assertAlmostEqual(self.m.mean,np.mean([r for u,i,r in self.rows]))
    def test03_user_and_item_bias(self):
        self.assertGreater(self.m.user_bias[self.m.users['high']],self.m.user_bias[self.m.users['low']]);self.assertGreater(self.m.item_bias[self.m.items['i0']],self.m.item_bias[self.m.items['i1']])
    def test04_joint_ridge_exact(self):
        theta=self.m.fold_in(self.support);a=np.asarray([np.r_[self.m.Q[self.m.items[i]],1] for i,y in self.support]);y=np.asarray([y-self.m.mean-self.m.item_bias[self.m.items[i]] for i,y in self.support])
        penalty=np.diag([5*.01]*5);expected=np.linalg.solve(np.einsum('ni,nj->ij',a,a)+penalty,np.einsum('ni,n->i',a,y));np.testing.assert_array_equal(theta,expected)
    def test05_bias_and_mean_prediction(self):
        theta=np.zeros(5);theta[-1]=.1;expected=np.clip(self.m.mean+self.m.item_bias[self.m.items['i0']]+.1,0,1);self.assertAlmostEqual(self.m.score_vector(theta,['i0'])[0],expected)
    def test06_shrinkage_bias(self):self.assertLessEqual(abs(self.m.fold_in(self.support,10)[-1]),abs(self.m.fold_in(self.support,.1)[-1]))
    def test07_fixed_items(self):
        q=self.m.Q.copy();bias=self.m.item_bias.copy();mu=self.m.mean;self.m.fold_in(self.support,.1);np.testing.assert_array_equal(q,self.m.Q);np.testing.assert_array_equal(bias,self.m.item_bias);self.assertEqual(mu,self.m.mean)
    def test08_unknown_no_fake_factor(self):self.assertIsNone(self.m.fold_in([('unknown'+str(i),.8) for i in range(5)]));self.assertTrue(np.isnan(self.m.score_vector(None,self.ids)).all())
    def test09_top5_unique_seen(self):
        spec=dict(family='bias',alpha=.25,bias_shrinkage=1)
        top=predict(spec,self.support,self.ids,self.c,self.m,self.b);self.assertEqual(len(set(top)),5);self.assertFalse(set(top)&{i for i,y in self.support})
    def test10_no_answers_and_invalid(self):
        import inspect
        self.assertNotIn('answers',inspect.signature(self.m.fold_in).parameters)
        with self.assertRaises(ValueError):self.m.fold_in(self.support[:4])
    def test11_legacy_unchanged(self):
        old=MatrixFactorization(factors=4,regularization=.01);old.items={i:n for n,i in enumerate(self.ids)};old.Q=np.asarray([[.1,.2,.3,.4]]*10)
        self.assertEqual(predict(dict(family='legacy',alpha=.25),self.support,self.ids,self.c,old,self.b),old_score(self.support,self.ids,self.c,old,self.b)['methods']['hybrid']['top'])
    def test12_save_restore_bias(self):
        spec=dict(name='test',family='bias',alpha=.1,bias_shrinkage=10)
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'m.npz';save_model(path,self.c,freeze_user_state(self.m),self.b,self.ids,spec,self.cfg);c,m,b,meta=load_model(path)
            self.assertFalse(hasattr(m,'P'));self.assertFalse(hasattr(m,'user_bias'));np.testing.assert_array_equal(m.item_bias,self.m.item_bias)
            self.assertEqual(predict(spec,self.support,self.ids,self.c,self.m,self.b),predict(meta['spec'],self.support,self.ids,c,m,b))

if __name__=='__main__':unittest.main()
