"""Focused synthetic checks, no historic final labels or real-data fits."""
import inspect,tempfile,unittest,warnings
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from perfume.models import Content,Baseline
from experiments.scent_v2.mf_cv_optimization.core import user_scores,ridge
from experiments.scent_v2.recommend import rank
from .core import SimilarityIndex,cache_support,rerank,predict,save_model,load_model,specs

class RerankingTests(unittest.TestCase):
    def context(self,n=80):
        ids=[f'i{k:03}' for k in range(n)];c=Content();c.idf={'wood':1.,'floral':1.};c.vectors={i:{'wood':1.} if k%2==0 else {'floral':1.} for k,i in enumerate(ids)}
        m=SimpleNamespace(Q=np.random.default_rng(12).uniform(0,.2,(n,4)),items={i:k for k,i in enumerate(ids)},factors=4,reg=.01);b=Baseline().fit([('train',i,.7) for i in ids]);return ids,c,m,b
    def support(self,ids):return list(zip(ids[:5],[1.,.8,.4,.1,.5]))
    def test_cosine_matrix(self):
        ids,c,m,b=self.context();index=SimilarityIndex(c,ids);self.assertEqual(index.matrix[0,2],1);self.assertEqual(index.matrix[0,1],0);np.testing.assert_array_equal(index.matrix,index.matrix.T);self.assertFalse(index.matrix.flags.writeable)
    def test_max_and_weighted_top2(self):
        ids,c,m,b=self.context();s,d=SimilarityIndex(c,ids).signals(self.support(ids),[ids[6],ids[7]])
        np.testing.assert_array_equal(s['max'],[1,1]);np.testing.assert_allclose(s['top2'],[.75,.45])
    def test_no_positive_exact_fallback(self):
        ids,c,m,b=self.context();support=[(i,.6) for i in ids[:5]];x=cache_support(support,ids,c,m,b,SimilarityIndex(c,ids));old=rerank(specs()['hybrid_baseline'],x)
        for spec in specs().values():self.assertEqual(rerank(spec,x),old)
    def test_weak_candidate_preserves_H(self):
        pool=['a','b','c'];x=dict(pool=pool,hybrid=np.array([.6,.5,.4]),baseline_order=pool,signals={'max':np.array([.01,np.nan,.049])})
        top,s=rerank(dict(signal='max',mode='full',**{'lambda':.2}),x);self.assertEqual(top,pool);np.testing.assert_array_equal(s,x['hybrid'])
    def test_top50_strict_and_outside_scores(self):
        pool=[f'{k:03}' for k in range(80)];H=np.linspace(1,.4,80);S=np.ones(80);S[:50]=.05;x=dict(pool=pool,hybrid=H,baseline_order=pool,signals={'max':S})
        top,values=rerank(dict(signal='max',mode='top50',**{'lambda':.2}),x,k=80);self.assertEqual(set(top[:50]),set(pool[:50]));self.assertEqual(top[50:],pool[50:]);np.testing.assert_array_equal(values[50:],H[50:])
        # The full method may promote outside items; Top50 cannot.
        full,_=rerank(dict(signal='max',mode='full',**{'lambda':.2}),x,k=80);self.assertNotEqual(top,full)
    def test_formula_when_active(self):
        x=dict(pool=['a','b'],hybrid=np.array([.6,.5]),baseline_order=['a','b'],signals={'max':np.array([.8,.2])});top,values=rerank(dict(signal='max',mode='full',**{'lambda':.1}),x)
        self.assertEqual(top,['a','b']);np.testing.assert_allclose(values,[.62,.47])
    def test_missing_features(self):
        ids,c,m,b=self.context();c.vectors[ids[7]]={}
        with warnings.catch_warnings():
            warnings.simplefilter('error');values,d=SimilarityIndex(c,ids).signals(self.support(ids),[ids[7]])
        self.assertTrue(np.isnan(values['max'][0]));self.assertTrue(np.isnan(values['top2'][0]))
    def test_single_valid_support_padding(self):
        ids,c,m,b=self.context()
        for i in ids[1:5]:c.vectors[i]={}
        values,d=SimilarityIndex(c,ids).signals(self.support(ids),[ids[6]]);self.assertEqual(values['max'][0],1);self.assertEqual(values['top2'][0],.5)
    def test_invalid_support(self):
        ids,c,m,b=self.context();index=SimilarityIndex(c,ids)
        for support in [[(ids[0],1)]*5,self.support(ids)[:4],[(i,np.nan) for i in ids[:5]],[(i,.8) for i in ['outside',*ids[:4]]]]:
            with self.assertRaises(ValueError):index.signals(support,ids[5:])
    def test_baseline_unchanged(self):
        ids,c,m,b=self.context();support=self.support(ids);top,scores=predict(specs()['hybrid_baseline'],support,ids,c,m,b)
        self.assertEqual(top,user_scores(dict(alpha=.25,ridge_scale=1.,center=False),support,ids,c,m,b))
    def test_all_policies_no_seen_duplicates(self):
        ids,c,m,b=self.context();index=SimilarityIndex(c,ids)
        for spec in specs().values():
            top,values=predict(spec,self.support(ids),ids,c,m,b,index);self.assertEqual(len(top),5);self.assertEqual(len(top),len(set(top)));self.assertFalse(set(top)&set(ids[:5]));self.assertTrue(np.isfinite(values).all())
    def test_support_cache_reused(self):
        ids,c,m,b=self.context();index=SimilarityIndex(c,ids)
        with patch.object(index,'signals',wraps=index.signals) as sim,patch.object(c,'score',wraps=c.score) as cs,patch('experiments.scent_v2.similarity_reranking.core.ridge',wraps=ridge) as rs:
            x=cache_support(self.support(ids),ids,c,m,b,index)
            for spec in specs().values():rerank(spec,x)
            self.assertEqual(sim.call_count,1);self.assertEqual(cs.call_count,1);self.assertEqual(rs.call_count,1)
    def test_save_restore_all_policies(self):
        ids,c,m,b=self.context();support=self.support(ids)
        for spec in specs().values():
            with tempfile.TemporaryDirectory() as t:
                path=Path(t)/'m.npz';save_model(path,c,m,b,ids,spec);lc,lm,lb,meta=load_model(path)
                self.assertEqual(predict(spec,support,ids,c,m,b),predict(meta['spec'],support,ids,lc,lm,lb))
                with np.load(path,allow_pickle=False) as z:self.assertFalse({'P','users','ratings'}&set(z.files))
    def test_answer_free_api_and_nonmutation(self):
        self.assertNotIn('answers',inspect.signature(SimilarityIndex.signals).parameters);self.assertNotIn('answers',inspect.signature(rerank).parameters)
        ids,c,m,b=self.context();index=SimilarityIndex(c,ids);q=m.Q.copy();matrix=index.matrix.copy();x=cache_support(self.support(ids),ids,c,m,b,index)
        x['answers']=object() # Arbitrary answer payload is never consulted.
        old=x['hybrid'].copy()
        for spec in specs().values():rerank(spec,x)
        np.testing.assert_array_equal(q,m.Q);np.testing.assert_array_equal(matrix,index.matrix);np.testing.assert_array_equal(old,x['hybrid'])

if __name__=='__main__':unittest.main()
