"""Synthetic score diagnostics; zero training and no old answer access."""
import hashlib,json,unittest,inspect
from types import SimpleNamespace
import numpy as np
from perfume.models import Content,Baseline
from experiments.scent_v2.score_diagnostics.analysis import distribution,correlation,ranks_average,reconstruct,rank_info,user_means
from experiments.scent_v2.recommend import score
from experiments.scent_v2.lambda_tuning.evaluate import view
from experiments.scent_v2.score_diagnostics.config import ROOT


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.pool=list('abcdefghij')
        self.content=Content();self.content.idf={'x':1.}
        self.content.vectors={i:{'x':1.}for i in self.pool}
        self.mf=SimpleNamespace(Q=np.array([[.1,.2,.3,.4],[.2,.1,.4,.3],[.3,.2,.1,.4],[.4,.3,.2,.1],[.1,.3,.2,.4],[.2,.4,.1,.3],[.3,.1,.4,.2],[.4,.2,.3,.1]]),
                                items={i:n for n,i in enumerate(self.pool[:8])},reg=.01,factors=4)
        self.pop=Baseline();self.pop.counts={i:1 for i in self.pool};self.pop.maximum=1
        self.support=[(i,.8)for i in 'abcde']

    def test_percentiles_and_finite_filter(self):
        d=distribution([0,1,np.nan]);self.assertEqual(d['count'],2);self.assertEqual(d['p50'],.5);self.assertEqual(d['sd'],.5)

    def test_empty_distribution_undefined(self):
        d=distribution([np.nan]);self.assertEqual(d['count'],0);self.assertIsNone(d['mean'])

    def test_average_rank_ties(self):
        np.testing.assert_array_equal(ranks_average([3,1,1,2]),[4,1.5,1.5,3])

    def test_pearson_and_spearman(self):
        self.assertAlmostEqual(correlation([1,2,3],[3,2,1])[0],-1)
        self.assertAlmostEqual(correlation([1,1,2],[3,3,4],True)[0],1)

    def test_constant_not_zero(self):
        v,reason,n=correlation([1,1],[1,2]);self.assertIsNone(v);self.assertEqual(reason,'constant')

    def test_pairwise_missing(self):
        self.assertEqual(correlation([np.nan,1],[2,3])[1],'insufficient')

    def test_actual_hybrid_parity_all_lambdas(self):
        for lam in [.01,.1,1.]:
            d=reconstruct(self.support,self.pool,self.content,self.mf,self.pop,lam)
            a=score(self.support,self.pool,self.content,view(self.mf,lam),self.pop)
            self.assertEqual(d['orders']['hybrid'][:5],a['methods']['hybrid']['top'])
            lookup=dict(zip(d['pool'],d['arrays']['hybrid']))
            np.testing.assert_array_equal([lookup[i]for i in a['methods']['hybrid']['top']],a['methods']['hybrid']['top_scores'])

    def test_missing_factor_full_content_fallback(self):
        d=reconstruct(self.support,self.pool,self.content,self.mf,self.pop,.01)
        n=d['pool'].index('j');self.assertTrue(d['fallback'][n]);self.assertEqual(d['arrays']['hybrid'][n],1)
        self.assertEqual(d['arrays']['applied_content'][n],0)
        self.assertEqual(d['arrays']['fallback_contribution'][n],1)

    def test_missing_content_full_MF_fallback(self):
        self.content.vectors['f']={}
        d=reconstruct(self.support,self.pool,self.content,self.mf,self.pop,.01);n=d['pool'].index('f')
        self.assertAlmostEqual(d['arrays']['hybrid'][n],d['arrays']['mf_clipped'][n])

    def test_both_missing_popularity_fallback(self):
        self.content.vectors['j']={}
        d=reconstruct(self.support,self.pool,self.content,self.mf,self.pop,.01);n=d['pool'].index('j')
        self.assertEqual(d['arrays']['hybrid'][n],1)

    def test_no_support_factors_uses_content(self):
        self.mf.items={};self.mf.Q=np.empty((0,4))
        d=reconstruct(self.support,self.pool,self.content,self.mf,self.pop,.1)
        self.assertEqual(d['known_support'],0);self.assertTrue(np.isnan(d['arrays']['mf_raw']).all())
        np.testing.assert_array_equal(d['arrays']['hybrid'],d['arrays']['content'])

    def test_contribution_identity(self):
        d=reconstruct(self.support,self.pool,self.content,self.mf,self.pop,.01)['arrays']
        np.testing.assert_array_equal(d['applied_content']+d['applied_mf']+d['fallback_contribution'],d['hybrid'])

    def test_Q_unchanged_and_shared(self):
        h=hashlib.sha256(self.mf.Q.tobytes()).hexdigest()
        for lam in [.01,.1,1.]:
            self.assertIs(view(self.mf,lam).Q,self.mf.Q);reconstruct(self.support,self.pool,self.content,self.mf,self.pop,lam)
        self.assertEqual(h,hashlib.sha256(self.mf.Q.tobytes()).hexdigest())

    def test_seen_exclusion(self):
        d=reconstruct(self.support,self.pool,self.content,self.mf,self.pop,.01)
        self.assertEqual(len(d['pool']),5);self.assertFalse(set('abcde')&set(d['pool']))

    def test_ID_tie_and_clipping_counterfactual(self):
        p=['a','b','c','d','e','f'];raw=np.array([1.1,1.2,1.3,1.4,1.5,1.6])
        clipped=rank_info(p,np.clip(raw,0,1));virtual=rank_info(p,raw)
        self.assertEqual(clipped['top'],list('abcde'));self.assertEqual(virtual['top'],list('fedcb'))
        self.assertEqual(clipped['adjacent_ties'],5);self.assertEqual(virtual['adjacent_ties'],0)

    def test_repeated_user_macro(self):
        r=[dict(user='u',x=0),dict(user='u',x=2),dict(user='v',x=3)]
        self.assertEqual(user_means(r,'x'),{'u':1,'v':3})

    def test_no_answer_argument(self):
        self.assertNotIn('answers',inspect.signature(reconstruct).parameters)

    def test_frozen_and_v2_code_hashes(self):
        f=json.loads((ROOT/'outputs/final/freeze.json').read_text())
        for p,h in f['protected_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)
        for name,key in [('baseline/run_metadata.json','code_sha256'),('lambda_tuning/verification.json','source_sha256')]:
            m=json.loads((ROOT/'outputs/scent_v2'/name).read_text())
            for p,h in m[key].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)


if __name__=='__main__':unittest.main()
