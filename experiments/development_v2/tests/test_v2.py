"""Synthetic numerical/leakage checks; no legacy test/answer/result file is opened."""
import sys,unittest,inspect
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data import known_folds,newuser_folds,inner_stop,read_input
from content_v2 import ContentV2
from mf_v2 import BiasMF,edge_objective_gradient,train_mf
from foldin_v2 import fold_in,score_vector,validate_support
from hybrid_v2 import combine,normalize_scores,ranked,rank_scores
from evaluate_v2 import evaluate_arrays,component_scores
from perfume.models import MatrixFactorization
class MathTests(unittest.TestCase):
    def setUp(self):
        self.rows=[(u,str(i),.2+(i%3)*.3) for u in ['a','b','c','d','e','f'] for i in range(7)]
        self.catalog={str(i):{'brand':'synthetic','name':str(i),'tokens':['accord:woody' if i%2 else 'accord:floral','note:'+str(i)]} for i in range(8)}
        self.raw={i:{'Top':i,'Middle':'NA','Base':'rose' if int(i)%2 else 'vanilla'} for i in self.catalog}
        self.cfg={'biased':True,'factors':2,'regularization':.1,'learning_rate':.01,'epochs':10,'early':False}
    def model(self):return BiasMF(self.cfg).fit(self.rows)
    def test_v1_sgd_hand_calculation(self):
        seed=12;r=.8;reg=.01;lr=.01;rng=np.random.default_rng(seed);p=rng.uniform(0,.2,(1,2))[0];q=rng.uniform(0,.2,(1,2))[0];e=r-p@q
        model=MatrixFactorization(2,1,lr,reg,seed).fit([('u','i',r)])
        np.testing.assert_allclose(model.P[0],p+lr*(e*q-reg*p));np.testing.assert_allclose(model.Q[0],q+lr*(e*p-reg*q))
    def test_bias_gradient_finite_difference(self):
        x=np.array([.1,-.2,.3,.4,.05,-.04]);p,q=x[:2],x[2:4];loss,g=edge_objective_gradient(p,q,x[4],x[5],.8,.6,.1)
        analytic=np.r_[g[0],g[1],g[2],g[3]];numeric=[]
        def objective(z):return edge_objective_gradient(z[:2],z[2:4],z[4],z[5],.8,.6,.1)[0]
        for n in range(len(x)):
            d=np.zeros(len(x));d[n]=1e-6;numeric.append((objective(x+d)-objective(x-d))/2e-6)
        np.testing.assert_allclose(analytic,numeric,rtol=1e-6,atol=1e-9)
    def test_bias_sgd_update(self):
        c=dict(self.cfg,epochs=1);seed=12;rng=np.random.default_rng(seed);p=rng.normal(0,.05,(1,2))[0];q=rng.normal(0,.05,(1,2))[0]
        _,g=edge_objective_gradient(p,q,0,0,.8,.8,.1);m=BiasMF(c).fit([('u','i',.8)])
        np.testing.assert_allclose(m.P[0],p-.01*g[0]);np.testing.assert_allclose(m.Q[0],q-.01*g[1]);self.assertAlmostEqual(m.bu[0],-.01*g[2])
    def test_mf_determinism(self):
        a,b=self.model(),self.model();np.testing.assert_array_equal(a.Q,b.Q);self.assertTrue(np.isfinite(a.Q).all())
    def test_mf_unknown(self):self.assertTrue(np.isnan(self.model().score('unknown',['0'])[0]));self.assertTrue(np.isnan(self.model().score('a',['unknown'])[0]))
    def test_content_idf_train_only(self):
        c=ContentV2({'kind':'split','mode':'rating'}).fit(self.catalog,self.raw,['0','1'])
        self.assertNotIn('note:7',c.idfs['note']);self.assertAlmostEqual(c.idfs['note']['note:0'],np.log(3/2)+1)
    def test_content_cosine(self):
        c=ContentV2({'kind':'split','mode':'rating'}).fit(self.catalog,self.raw,['0','1']);self.assertAlmostEqual(c.score([('0',1)],['0'])[0],1)
    def test_dislike_changes_direction(self):
        c=ContentV2({'kind':'split','mode':'neutral'}).fit(self.catalog,self.raw,['0','1'])
        self.assertLess(c.score([('0',0)],['0'])[0],c.score([('0',1)],['0'])[0])
    def test_centered_equal_zero(self):
        c=ContentV2({'kind':'split','mode':'centered'}).fit(self.catalog,self.raw,['0','1']);self.assertTrue(np.isnan(c.score([('0',.5),('1',.5)],['0'])[0]))
    def test_positions_separate(self):
        c=ContentV2({'kind':'position','mode':'rating','position_weights':[2,3,5]}).fit(self.catalog,self.raw,['0','1']);self.assertEqual(set(c.matrices),{'accord','Top','Middle','Base'})
    def test_foldin_fixed_q_and_stationarity(self):
        m=self.model();before=m.Q.copy();support=[('0',.8),('1',.2),('2',.7)];z=fold_in(m,support,.1)
        a=np.array([np.r_[m.Q[m.items[i]],1.] for i,_ in support]);y=np.array([r-m.mean-m.bi[m.items[i]] for i,r in support])
        np.testing.assert_allclose(a.T@(a@z-y)+3*.1*z,0,atol=1e-12);np.testing.assert_array_equal(before,m.Q)
    def test_support_permutation(self):
        m=self.model();s=[('0',.8),('1',.2),('2',.7)];np.testing.assert_array_equal(fold_in(m,s),fold_in(m,list(reversed(s))))
    def test_input_contract(self):
        for bad in [[('0',.5),('0',.5)],[('0',np.nan)],[('0',np.inf)],[('0',1.1)],[('0',-.1)],[('0',True)],[('unknown',.4)],[]]:
            with self.assertRaises(ValueError):validate_support(bad,self.catalog)
        with self.assertRaises(ValueError):validate_support([('0',.5)],self.catalog,3)
        self.assertEqual(validate_support([('0',0)],self.catalog),[('0',0)])
    def test_no_known_factor(self):self.assertIsNone(fold_in(self.model(),[('new',.5)]))
    def test_normalization(self):np.testing.assert_array_equal(normalize_scores([2,4]),[0,1]);np.testing.assert_array_equal(normalize_scores([2,2]),[.5,.5])
    def test_rrf_ties(self):self.assertGreater(rank_scores([.5,.5],['a','b'])[0],rank_scores([.5,.5],['a','b'])[1])
    def test_hybrid_weight_fallback(self):
        s,f=combine([.8,np.nan,np.nan],[.4,.6,np.nan],[.1,.2,.3],['a','b','c'],{'method':'linear','alpha':.25},3)
        np.testing.assert_allclose(s,[.5,.6,.3]);self.assertEqual(f['popularity_fallback'],1)
    def test_tie_order(self):self.assertEqual(ranked(['b','a'],[1,1]),['a','b'])
    def test_metric_denominator(self):
        r,_=evaluate_arrays({'a':['x'],'b':['x']},[('a','x',1),('b','x',0)]);self.assertEqual(r['positive_users'],1);self.assertAlmostEqual(r['precision'],.1);self.assertEqual(r['ndcg'],1)
    def test_known_cv_disjoint(self):
        for _,fit,answer in known_folds(self.rows):self.assertFalse({(u,i) for u,i,_ in fit}&{(u,i) for u,i,_ in answer})
    def test_user_cv_disjoint(self):
        for _,fit,pool,support,answer,excluded,held in newuser_folds(self.rows,list(self.catalog)):
            self.assertFalse(set(support)&{u for u,_,_ in fit});self.assertFalse({(u,i) for u,v in support.items() for i,_ in v}&{(u,i) for u,i,_ in answer})
    def test_nested_split_no_outer_answer(self):
        _,fit,answer=next(known_folds(self.rows));inner,stop=inner_stop(fit)
        self.assertFalse({(u,i) for u,i,_ in answer}&{(u,i) for u,i,_ in inner+stop})
    def test_scoring_interface_no_answers(self):self.assertNotIn('answers',inspect.signature(component_scores).parameters)
    def test_input_deny(self):
        for name in ['test','external','reviews','split_manifest']:
            with self.assertRaises(ValueError):read_input(name)
    def test_access_policy(self):
        from run_experiments import access_policy
        from data import ROOT
        for path in ['outputs/final/internal_metrics.csv','outputs/final/external_answers_private.json','Term-project-datasets/reviews.json','outputs/validation/split_manifest.json']:
            with self.assertRaises(PermissionError):access_policy('open',(str(ROOT/path),'r',0))
if __name__=='__main__':unittest.main(verbosity=2)
