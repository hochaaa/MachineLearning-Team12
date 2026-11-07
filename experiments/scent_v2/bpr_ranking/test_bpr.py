"""Focused synthetic checks; no prior evaluation data opened."""
import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .model import build_pairs,fit,step,scores,fold_in
from .run import save_model,load_model,bpr_top,legacy_top
from perfume.models import Content,MatrixFactorization,Baseline
from experiments.scent_v2.pairwise_mf.training import pair_loss_gradient

class BPRTests(unittest.TestCase):
    def test_observed_pairs_only(self):
        pairs,s=build_pairs([('u','a',1),('u','b',0),('u','c',0)])
        self.assertEqual(set(pairs),{('u','a','b'),('u','a','c')});self.assertEqual(s['equal_pairs_excluded'],1)
    def test_excluded_user(self):
        with self.assertRaises(ValueError):build_pairs([('eval','a',1)],{'eval'})
    def test_duplicate(self):
        with self.assertRaises(ValueError):build_pairs([('u','a',1),('u','a',0)])
    def test_lazy_exact_global_L2(self):
        rng=np.random.default_rng(12);P=rng.uniform(0,.2,(2,4));Q=rng.uniform(0,.2,(3,4));A=P.copy();B=Q.copy();scale=1
        for u,i,j in [(0,0,1),(1,2,0),(0,2,1)]*3:
            p,q,r=A[u].copy(),B[i].copy(),B[j].copy();_,gp,gi,gj=pair_loss_gradient(p,q,r);A*=1-2*.01*.01/3;B*=1-2*.01*.01/3;A[u]-=.01*gp;B[i]-=.01*gi;B[j]-=.01*gj
            scale=step(P,Q,scale,u,i,j,.01,.01,3)
        np.testing.assert_allclose(A,scale*P,atol=1e-14);np.testing.assert_allclose(B,scale*Q,atol=1e-14)
    def test_training_loss(self):
        m,d=fit([('u','a',1),('u','b',0),('u','c',.5)],epochs=80)
        self.assertLess(d['history'][-1]['objective'],d['history'][0]['objective']);self.assertFalse(m.Q.flags.writeable)
        self.assertNotIn('user_pair_counts_private',d['pair_statistics']);self.assertFalse(hasattr(m,'P'))
    def model(self):
        q=np.array([[1.,0.],[0.,1.],[.5,.5],[-1,0],[0,-1]])
        return SimpleNamespace(Q=q,items={i:n for n,i in enumerate('abcde')},factors=2,variant='variant_a',reg=.01,temperature=1.)
    def test_foldin_fixed_Q(self):
        m=self.model();old=m.Q.copy();support=list(zip('abcde',[1.,0.,.5,.2,.4]));p,d=fold_in(m,support)
        self.assertIsNotNone(p);self.assertGreater(float(np.dot(p,m.Q[0]-m.Q[1])),0);np.testing.assert_array_equal(old,m.Q);self.assertTrue(np.isfinite(p).all())
    def test_equal_support_fallback(self):
        p,d=fold_in(self.model(),[(i,.7) for i in 'abcde']);self.assertIsNone(p);self.assertEqual(d['status'],'no_support_pairs')
    def test_unknown_support(self):
        p,d=fold_in(self.model(),[(i,.7) for i in 'fghij']);self.assertIsNone(p)
    def test_monotonic_calibration(self):
        m=self.model();s,d=scores(m,list(zip('abcde',[1,0,.5,.2,.4])),list('abcde')+['x']);self.assertTrue(np.isnan(s[-1]));self.assertGreater(s[0],s[1]);self.assertTrue(((s[:-1]>=0)&(s[:-1]<=1)).all())
    def context(self):
        ids=list('abcdefghijkl');rows=[('u',i,.1+.07*n) for n,i in enumerate(ids)];catalog={i:{'tokens':['rose' if n%2 else 'wood','floral']} for n,i in enumerate(ids)}
        c=Content().fit(catalog,set(ids));m=MatrixFactorization(factors=4,epochs=2,learning_rate=.01,regularization=.01).fit(rows);b=Baseline().fit(rows)
        return ids,c,m,b
    def test_whole_user_fallback_exact(self):
        ids,c,m,b=self.context();bm=self.model();support=[(i,.5) for i in 'abcde'];top,d=bpr_top(.1,support,ids,c,bm,b,m)
        self.assertEqual(top,legacy_top(support,ids,c,m,b));self.assertEqual(len(top),len(set(top)));self.assertFalse(set(top)&set('abcde'))
    def test_save_restore_bpr_and_legacy(self):
        ids,c,m,b=self.context();bm,_=fit([('u',i,.1+.07*n) for n,i in enumerate(ids)],epochs=2)
        for family,model in [('legacy',m),('bpr',bm)]:
            with tempfile.TemporaryDirectory() as t:
                path=Path(t)/'m.npz';save_model(path,c,model,b,ids,dict(family=family,alpha=.25),dict(factors=4,regularization=.01),m);lc,lm,lb,lf,meta=load_model(path)
                np.testing.assert_array_equal(model.Q,lm.Q);self.assertEqual(meta['spec']['family'],family)
                support=[(i,.1+.15*n) for n,i in enumerate(ids[:5])]
                if family=='bpr':self.assertEqual(bpr_top(.25,support,ids,c,model,b,m)[0],bpr_top(.25,support,ids,lc,lm,lb,lf)[0])
                else:self.assertEqual(legacy_top(support,ids,c,model,b),legacy_top(support,ids,lc,lm,lb))
                with np.load(path,allow_pickle=False) as data:self.assertFalse({'P','users','ratings'}&set(data.files))
    def test_no_pairs_training_rejected(self):
        with self.assertRaises(ValueError):fit([('u','a',1),('u','b',1)])

if __name__=='__main__':unittest.main()
