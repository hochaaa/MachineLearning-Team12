"""Pretraining synthetic tests. No MF.fit calls, no existing validation/Test files."""
import sys,unittest,inspect
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v3_data import digest,deny,ROOT,histories
from v3_config import verify_source,POLICIES,SETTINGS,V1
from split import outer_specs,inner_specs,user_evaluation
from mf_v3 import edge
from foldin_v3 import fold,score,normalize_support
from evaluate_v3 import assess,select_policy,ScoringContext
from fit_budget import FitBudget
from content_v2 import ContentV2
class PretrainingTests(unittest.TestCase):
    def fixture(self):return [(u,str(i),.2 if i%3==0 else .8) for u in 'abcdef' for i in range(6)]
    def model(self):return SimpleNamespace(Q=np.array([[.1,.2],[.3,.1],[.2,-.1],[.4,.3]]),P=np.ones((1,2)),bu=np.array([0.]),bi=np.array([.01,.02,-.03,.04]),mean=.7,items={str(i):i for i in range(4)},users={'x':0})
    def test_policies_match_original_report(self):self.assertTrue(verify_source()['six_policies_exact'])
    def test_six_policies_three_training_recipes(self):
        recipes={(p['factors'],p['bias_l2'],p['latent_l2'],p['epochs'],p['learning_rate']) for p in POLICIES};self.assertEqual(len(POLICIES),6);self.assertEqual(len(recipes),3)
    def test_budget_arithmetic(self):self.assertEqual(54+6+1,SETTINGS['caps']['total'])
    def test_budget_cap(self):
        b=FitBudget(SETTINGS['caps']);b.used['primary']=54
        with self.assertRaises(RuntimeError):b.check('primary')
    def test_cache_data_boundary(self):self.assertNotEqual(digest(self.fixture()),digest(self.fixture()[:-1]))
    def test_cache_seed_identity(self):self.assertNotEqual(digest(('seed',12)),digest(('seed',29)))
    def test_outer_users_removed(self):
        rows=self.fixture()
        for o,fit,held in outer_specs(rows):self.assertFalse(held&{u for u,_,_ in fit})
    def test_inner_users_removed(self):
        for o,ofit,oheld in outer_specs(self.fixture()):
            for j,fit,held in inner_specs(ofit,o):self.assertFalse((held|oheld)&{u for u,_,_ in fit});self.assertFalse(held&oheld)
    def test_support_answer_disjoint(self):
        rows=self.fixture();o,fit,held=outer_specs(rows)[0];s,a,_=user_evaluation(rows,fit,held,list(map(str,range(6))))
        self.assertTrue(s);self.assertTrue(all(len(v)==3 for v in s.values()));self.assertFalse({(u,i) for u,v in s.items() for i,_ in v}&{(u,i) for u,i,_ in a})
    def test_split_order_invariant(self):
        rows=self.fixture();a=outer_specs(rows);b=outer_specs(list(reversed(rows)))
        self.assertEqual([x[2] for x in a],[x[2] for x in b])
    def test_metric_formula_and_denominator(self):
        s,p=assess({'a':['x','y'],'b':['x']},[('a','y',1),('b','x',0)],['x','y'])
        self.assertEqual(s['positive_users'],1);self.assertEqual(s['no_positive_users'],1);self.assertAlmostEqual(s['ndcg'],1/np.log2(3));self.assertAlmostEqual(s['precision'],.1)
    def test_gradient_and_distinct_penalties(self):
        x=np.array([.1,.2,.3,-.1,.04,-.03]);loss,g=edge(x[:2],x[2:4],x[4],x[5],.8,.6,.01,.1)
        def objective(z):return edge(z[:2],z[2:4],z[4],z[5],.8,.6,.01,.1)[0]
        numeric=[]
        for n in range(len(x)):
            d=np.zeros(len(x));d[n]=1e-6;numeric.append((objective(x+d)-objective(x-d))/2e-6)
        np.testing.assert_allclose(np.r_[g[0],g[1],g[2],g[3]],numeric,rtol=1e-6,atol=1e-9)
    def test_fold_ridge_normal_equation(self):
        m=self.model();p=POLICIES[2];support=[('0',.9),('1',.1),('2',.6)];q=m.Q.copy();z=fold(m,support,p);a=np.c_[m.Q[:3],np.ones(3)];y=np.array([.9,.1,.6])-m.mean-m.bi[:3];pen=np.diag([.1,.1,1.])
        np.testing.assert_allclose(a.T@(a@z-y)+3*pen@z,0,atol=1e-12);np.testing.assert_array_equal(q,m.Q)
    def test_fold_order_repeat(self):
        s=[('0',.9),('1',.1),('2',.6)];np.testing.assert_array_equal(fold(self.model(),s,POLICIES[0]),fold(self.model(),list(reversed(s)),POLICIES[0]))
    def test_invalid_values(self):
        for s in [[('0',np.nan)],[('0',np.inf)],[('0',1.1)],[('0',-.1)],[('0',.1),('0',.9)]]:
            with self.assertRaises(ValueError):fold(self.model(),s,POLICIES[0])
    def test_missing_factor_nan(self):self.assertTrue(np.isnan(score(self.model(),np.zeros(3),['unknown'])[0]))
    def test_zero_inputs_finite(self):self.assertTrue(np.isfinite(fold(self.model(),[('0',0),('1',0),('2',0)],POLICIES[0])).all())
    def test_idf_fit_boundary(self):
        cat={'0':{'tokens':['note:a','accord:woody']},'1':{'tokens':['note:b','accord:floral']}}
        c=ContentV2({'kind':'split','mode':'neutral','accord_weight':.5}).fit(cat,{},['0']);self.assertNotIn('note:b',c.idfs['note'])
    def test_scorer_no_answers_parameter(self):self.assertNotIn('answers',inspect.signature(ScoringContext.predict).parameters)
    def test_deny_legacy(self):
        for name in ['outputs/improvement/validation.json','outputs/final/internal_metrics.csv','outputs/final/external_answers_private.json']:
            with self.assertRaises(PermissionError):deny('open',(str(ROOT/name),'r',0))
    def test_guardrail_retention(self):
        rows=[{'policy':'V1','ndcg':.1,'coverage':100,'top10_concentration':.3}]+[{'policy':p['id'],'ndcg':.2,'coverage':10,'top10_concentration':.9} for p in POLICIES]
        p,r=select_policy(rows,POLICIES,SETTINGS);self.assertEqual(p['id'],'V1')
    def test_integer_raw_zero_ten_boundary(self):
        s=normalize_support([('0',0),('1',10),('2',5)],10)
        self.assertEqual(s,[('0',0.),('1',1.),('2',.5)]);self.assertTrue(np.isfinite(fold(self.model(),s,POLICIES[0])).all())
    def test_float_raw_inputs(self):
        s=normalize_support([('0',9.5),('1',1.5),('2',5.)],10)
        np.testing.assert_allclose([r for _,r in s],[.95,.15,.5])
    def test_normalized_int_zero_one(self):
        s=normalize_support([('0',0),('1',1),('2',1)],1)
        self.assertTrue(np.isfinite(fold(self.model(),s,POLICIES[0])).all())
    def test_raw_out_of_range_nan_inf(self):
        for r in [-1,11,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):normalize_support([('0',r)],10)
    def test_hand_sgd_numeric_values(self):
        p=np.array([.1,.2]);q=np.array([.3,-.1]);bu=.04;bi=-.03
        loss,g=edge(p,q,bu,bi,.8,.6,.01,.1)
        np.testing.assert_allclose(p-.01*g[0],[.10053,.1998],atol=1e-12)
        np.testing.assert_allclose(q-.01*g[1],[.30015,-.09963],atol=1e-12)
        self.assertAlmostEqual(bu-.01*g[2],.04176);self.assertAlmostEqual(bi-.01*g[3],-.02817)
if __name__=='__main__':unittest.main(verbosity=2)
