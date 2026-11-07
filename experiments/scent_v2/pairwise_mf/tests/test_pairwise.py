"""Synthetic finite differences, Support-only inference, data and numerical guards."""
import unittest,inspect
from types import SimpleNamespace
import numpy as np
from experiments.scent_v2.pairwise_mf.pairwise_data import build_pairs
from experiments.scent_v2.pairwise_mf.training import pair_loss_gradient,sigmoid,fit
from experiments.scent_v2.pairwise_mf.fold_in import loss_grad_hessian,fold_in
from experiments.scent_v2.pairwise_mf.evaluation import predictions
from perfume.models import Content,Baseline


class PairTests(unittest.TestCase):
    def setUp(self):
        self.q=np.array([[1,0,0,0],[0,1,0,0],[.5,.5,0,0],[.2,.1,0,0],[.1,.2,0,0]],dtype=float)
        self.m=SimpleNamespace(Q=self.q,items={i:n for n,i in enumerate('abcde')},factors=4,reg=.01,variant='variant_a')
        self.support=list(zip('abcde',[1.,0.,.6,.3,.2]))

    def test_all_observed_strict_pairs(self):
        p,s=build_pairs([('u','a',1),('u','b',0),('u','c',0)])
        self.assertEqual(p,[('u','a','b'),('u','a','c')]);self.assertEqual(s['equal_pairs_excluded'],1)

    def test_duplicate_and_boundary_rejected(self):
        with self.assertRaises(ValueError):build_pairs([('u','a',1),('u','a',0)])
        with self.assertRaises(ValueError):build_pairs([('u','a',1)],['u'])
        with self.assertRaises(ValueError):build_pairs([('u','a',float('nan'))])

    def test_pairless_users_counted(self):
        p,s=build_pairs([('u','a',1),('v','b',.5),('v','c',.5)])
        self.assertEqual(s['users_without_pairs'],2);self.assertEqual(p,[])

    def test_pair_gradient_finite_difference(self):
        x=np.arange(12,dtype=float)/17-.2;p,qi,qj=x[:4],x[4:8],x[8:]
        _,gp,gi,gj=pair_loss_gradient(p,qi,qj);grad=np.r_[gp,gi,gj];numeric=[]
        for n in range(12):
            hi=x.copy();lo=x.copy();hi[n]+=1e-6;lo[n]-=1e-6
            numeric.append((pair_loss_gradient(hi[:4],hi[4:8],hi[8:])[0]-pair_loss_gradient(lo[:4],lo[4:8],lo[8:])[0])/2e-6)
        np.testing.assert_allclose(grad,numeric,atol=1e-9)

    def test_softplus_extremes(self):
        for v in [-1e6,1e6]:
            loss,*grads=pair_loss_gradient(np.array([v]),np.array([1.]),np.array([0.]));self.assertTrue(np.isfinite(loss));self.assertTrue(all(np.isfinite(g).all()for g in grads))
        np.testing.assert_allclose(sigmoid([-1e6,0,1e6]),[0,.5,1])

    def test_foldin_gradient_hessian(self):
        D=self.q[:3]-self.q[2:5];p=np.array([.1,-.2,.05,.3]);loss,g,H=loss_grad_hessian(p,D)
        numeric=[];columns=[]
        for n in range(4):
            hi=p.copy();lo=p.copy();hi[n]+=1e-6;lo[n]-=1e-6
            numeric.append((loss_grad_hessian(hi,D)[0]-loss_grad_hessian(lo,D)[0])/2e-6)
            columns.append((loss_grad_hessian(hi,D)[1]-loss_grad_hessian(lo,D)[1])/2e-6)
        np.testing.assert_allclose(g,numeric,atol=1e-8);np.testing.assert_allclose(H,np.array(columns).T,atol=1e-8)

    def test_foldin_converges_and_Q_fixed(self):
        pin=self.q.tobytes();p,d=fold_in(self.m,self.support)
        self.assertEqual(d['status'],'ok');self.assertIsNotNone(p);self.assertLessEqual(d['gradient_norm'],1e-8);self.assertEqual(pin,self.q.tobytes())

    def test_equal_support_fallback(self):
        p,d=fold_in(self.m,[(i,.8)for i in 'abcde']);self.assertIsNone(p);self.assertEqual(d['status'],'no_support_pairs')

    def test_no_factor_and_one_pair(self):
        m=SimpleNamespace(Q=self.q,items={},factors=4,reg=.01,variant='variant_a');self.assertIsNone(fold_in(m,self.support)[0])
        self.m.items={'a':0,'b':1};p,d=fold_in(self.m,self.support);self.assertEqual(d['support_pairs'],1);self.assertIsNotNone(p)

    def test_zero_difference_not_fake_vector(self):
        self.m.Q=np.ones((5,4));p,d=fold_in(self.m,self.support);self.assertIsNone(p);self.assertEqual(d['status'],'zero_vector')

    def test_exact5_and_no_answers(self):
        with self.assertRaises(ValueError):fold_in(self.m,self.support[:4])
        self.assertNotIn('answers',inspect.signature(fold_in).parameters)
        self.assertNotIn('answers',inspect.signature(predictions).parameters)

    def test_support_order_deterministic(self):
        p,d=fold_in(self.m,self.support);pp,dd=fold_in(self.m,list(reversed(self.support)));np.testing.assert_array_equal(p,pp)

    def test_synthetic_fit_deterministic_and_finite(self):
        # Exactly FOUR synthetic-data fits, separate from real-data fit ledger.
        rows=[('u','a',.9),('u','b',.1),('u','c',.5),('v','a',.2),('v','b',.8),('v','c',.6)]
        for variant in ('variant_a','variant_b'):
            m,d=fit(rows,['heldout'],variant);self.assertTrue(d['finite']);self.assertEqual(len(d['history']),161);self.assertFalse(m.Q.flags.writeable)
            self.assertLess(d['history'][-1]['objective'],d['history'][0]['objective'])
            again,_=fit(rows,['heldout'],variant);np.testing.assert_array_equal(m.Q,again.Q);np.testing.assert_array_equal(m.P,again.P)

    def test_fallback_without_A_pairs(self):
        c=Content();c.vectors={i:{'x':1.}for i in 'abcdef'};pop=Baseline();pop.counts={i:1 for i in 'abcdef'};pop.maximum=1
        base=SimpleNamespace(Q=self.q,items=self.m.items,factors=4,reg=.01,variant='baseline')
        r=predictions([(i,.8)for i in 'abcde'],list('abcdef'),c,{'baseline':base,'variant_a':self.m},pop)
        self.assertEqual(r['variant_a','mf']['top'],[]);self.assertEqual(r['variant_a','hybrid']['top_scores'],[1.])

if __name__=='__main__':unittest.main()
