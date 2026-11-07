"""Pre-fit tests: lambda isolation, inner boundaries, selection and reproducibility."""
import inspect,json,unittest,hashlib
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from experiments.scent_v2.recommend import score,fold_in
from experiments.scent_v2.splits import build
from experiments.scent_v2.train import fit_fold
from experiments.scent_v2.lambda_tuning.evaluate import view,select_inner,bootstrap_delta,summarize
from experiments.scent_v2.lambda_tuning.run import make_inner
from experiments.scent_v2.lambda_tuning.config import ROOT,LAMBDAS,POLICY
from perfume.models import Content,Baseline


def selection_records():
    """Synthetic equal-accuracy records: tie must keep .01, never tune on outer."""
    aa=[];rr=[]
    for lam in LAMBDAS:
        for u in ['a','b']:
            aa.append(dict(phase='inner',outer=1,track='A',method='hybrid',user=u,
                **{'lambda':lam},accuracy=dict(ndcg=.1,recall=.1,precision=.1,hit_rate=1),
                top=['p1','p2','p3','p4','p5'],pool=474,scorable=474,fallback_candidates=0,fallback_top5=0))
            for amp in [.5,1.]:
                rr.append(dict(phase='inner',outer=1,track='A',method='hybrid',user=u,
                    **{'lambda':lam},amplitude=amp,variants=10,replacement=.1,jaccard=.8,
                    first=.9,set_same=.7,order_same=.5,rank_move=.2))
    return aa,rr


class LambdaTests(unittest.TestCase):
    def setUp(self):
        self.mf=SimpleNamespace(Q=np.arange(24,dtype=float).reshape(6,4)/40,
            items={i:n for n,i in enumerate('abcdef')},factors=4,reg=.01)
        self.support=list(zip('abcdz',[0.,.3,.7,1.,.9]))

    def test_lambda_views_share_Q_without_mutation(self):
        for lam in LAMBDAS:
            v=view(self.mf,lam);self.assertIs(v.Q,self.mf.Q);self.assertEqual(v.reg,lam)
        self.assertEqual(self.mf.reg,.01)

    def test_registered_only(self):
        with self.assertRaises(ValueError):view(self.mf,.5)

    def test_exact_ridge_all_lambdas_known_n(self):
        q=self.mf.Q[:4];y=np.array([0.,.3,.7,1.])
        for lam in LAMBDAS:
            v=fold_in(view(self.mf,lam),self.support)
            gram=np.einsum('ni,nj->ij',q,q);rhs=np.einsum('ni,n->i',q,y)
            np.testing.assert_allclose(v,np.linalg.solve(gram+4*lam*np.eye(4),rhs))
            self.assertTrue(np.isfinite(v).all())

    def test_baseline_exact_parity(self):
        np.testing.assert_array_equal(fold_in(view(self.mf,.01),self.support),fold_in(self.mf,self.support))

    def test_zero_known_support_returns_none(self):
        self.assertIsNone(fold_in(view(self.mf,.1),[(i,.5)for i in 'vwxyz']))

    def test_integer_boundary_ratings(self):
        for r in [0,1]:
            for lam in LAMBDAS:self.assertTrue(np.isfinite(fold_in(view(self.mf,lam),[(i,r)for i in 'abcde'])).all())

    def test_inference_unchanged_content_fallback(self):
        catalog={i:{'tokens':['note:'+i,'accord:woody']}for i in 'abcdefz'}
        c=Content().fit(catalog,list('abcdef'));b=Baseline().fit([('u',i,.8)for i in 'abcdef'])
        support=[(i,.8)for i in 'abcde'];out=[]
        for lam in LAMBDAS:out.append(score(support,list('abcdefz'),c,view(self.mf,lam),b))
        self.assertEqual(out[0]['methods']['content'],out[1]['methods']['content'])
        for r in out:
            self.assertEqual(r['methods']['hybrid']['fallback_candidates'],1)
            self.assertEqual(r['methods']['mf']['scorable'],1)

    def test_inner_excludes_both_user_sets(self):
        pool=list('abcdefgh');rows=[(f'u{u}',i,.8)for u in range(12)for i in pool]
        for outer in build(rows,pool):
            for inner in make_inner(outer,pool):
                train={u for u,i,r in inner['train']}
                self.assertFalse(train&set(inner['users']));self.assertFalse(train&set(outer['users']))
                for u in inner['users']:
                    self.assertEqual(len(inner['support'][u]),5)
                    self.assertFalse({i for i,r in inner['support'][u]}&{i for i,r in inner['answers'][u]})

    def test_inner_reproducible_and_rating_blind(self):
        p=list('abcdefgh');r=[(f'u{u}',i,.8)for u in range(12)for i in p];o=build(r,p)[0]
        self.assertEqual(make_inner(o,p),make_inner(o,p))
        modified=dict(o,train=[(u,i,.1)for u,i,r in o['train']])
        a=make_inner(o,p);b=make_inner(modified,p)
        self.assertEqual([f['users']for f in a],[f['users']for f in b])
        self.assertEqual([{u:[i for i,r in h]for u,h in f['support'].items()}for f in a],
                         [{u:[i for i,r in h]for u,h in f['support'].items()}for f in b])

    def test_selection_tie_retains_baseline(self):
        aa,rr=selection_records();self.assertEqual(select_inner(aa,rr)['selected_lambda'],.01)

    def test_selection_rejects_outer_records(self):
        aa,rr=selection_records();aa[0]['phase']='outer'
        with self.assertRaises(ValueError):select_inner(aa,rr)

    def test_selection_rejects_accuracy_gain_with_stability_loss(self):
        aa,rr=selection_records()
        for a in aa:
            if a['lambda']==.1:a['accuracy']['ndcg']=.5
        for r in rr:
            if r['lambda']==.1:r['replacement']=.3
        self.assertEqual(select_inner(aa,rr)['selected_lambda'],.01)

    def test_selection_accepts_clear_gain_without_stability_loss(self):
        aa,rr=selection_records()
        for a in aa:
            if a['lambda']==.1:a['accuracy']['ndcg']=.5
        self.assertEqual(select_inner(aa,rr)['selected_lambda'],.1)

    def test_bootstrap_reproducible_and_user_paired(self):
        a={'u1':.1,'u2':.2};b={'u1':0.,'u2':.1}
        self.assertEqual(bootstrap_delta(a,b,100),bootstrap_delta(a,b,100))
        with self.assertRaises(ValueError):bootstrap_delta(a,{'x':0},100)

    def test_repeated_contexts_are_not_independent_users(self):
        aa,rr=selection_records();a,r=summarize(aa+aa,rr+rr)
        for row in a:self.assertEqual(row['users'],2);self.assertEqual(row['contexts'],4)
        for row in r:self.assertEqual(row['users'],2)

    def test_no_outer_argument_in_selection(self):
        self.assertEqual(list(inspect.signature(select_inner).parameters),['accuracy','robust'])

    def test_v1_v20_protected(self):
        f=json.loads((ROOT/'outputs/final/freeze.json').read_text())
        for p,h in f['protected_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)
        m=json.loads((ROOT/'outputs/scent_v2/baseline/run_metadata.json').read_text())
        for p,h in m['code_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)

    def test_policy_fixed(self):
        self.assertEqual(LAMBDAS,(.01,.1,1.));self.assertEqual(POLICY['max_new_mf_fits'],6)
        self.assertEqual(POLICY['training_regularization'],.01)


if __name__=='__main__':unittest.main()
