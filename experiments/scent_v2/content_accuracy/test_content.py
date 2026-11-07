"""Focused synthetic checks before actual fits; no real evaluation labels."""
import unittest,tempfile,inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from perfume.models import Content,Baseline
from .core import profile_scores,cache_support,score_cached,predict,save_model,load_model
from .run import experiment_specs
from experiments.scent_v2.mf_cv_optimization.core import user_scores,ridge,folds

class ContentTests(unittest.TestCase):
    def context(self):
        ids=list('abcdefghijkl');c=Content();c.idf={'a':1.,'b':1.};c.vectors={i:{'a':1.} if n%2==0 else {'b':1.} for n,i in enumerate(ids)}
        rows=[('train',i,.1+.07*n) for n,i in enumerate(ids)];b=Baseline().fit(rows);m=SimpleNamespace(Q=np.random.default_rng(12).uniform(0,.2,(12,4)),items={i:n for n,i in enumerate(ids)},factors=4,reg=.01)
        return ids,c,m,b
    def support(self):return [('a',1.),('b',0.),('c',.5),('d',.5),('e',.5)]
    def test_weighted_signed(self):
        ids,c,m,b=self.context();v,d=profile_scores('rating_weighted',self.support(),['g','h'],c)
        self.assertGreater(v[0],v[1]);self.assertEqual(v[1],0.)
    def test_positive_negative_betas(self):
        ids,c,m,b=self.context();a,_=profile_scores('positive_negative_0.25',self.support(),['g','h'],c);z,_=profile_scores('positive_negative_0.50',self.support(),['g','h'],c)
        self.assertGreater(a[0],z[0]);self.assertEqual(z[1],0.)
    def test_no_negative(self):
        ids,c,m,b=self.context();support=[(i,.7+.05*n) for n,i in enumerate(ids[:5])];v,d=profile_scores('positive_negative_0.25',support,ids[5:],c)
        self.assertTrue(np.isfinite(v).all());self.assertEqual(d['negative_support'],0)
    def test_no_positive(self):
        ids,c,m,b=self.context();support=[(i,.05*n) for n,i in enumerate(ids[:5])];v,d=profile_scores('positive_negative_0.25',support,ids[5:],c)
        self.assertTrue(np.isfinite(v).all());self.assertEqual(d['positive_support'],0)
    def test_equal_fallback(self):
        ids,c,m,b=self.context();s=[(i,.5) for i in ids[:5]];v,d=profile_scores('rating_weighted',s,ids[5:],c)
        np.testing.assert_array_equal(v,c.score(s,ids[5:]));self.assertEqual(d['fallback'],'equal_ratings')
    def test_zero_profile(self):
        ids,c,m,b=self.context();c.vectors={i:{'a':1.} for i in ids};s=self.support();v,d=profile_scores('rating_weighted',s,ids[5:],c)
        self.assertEqual(d['fallback'],'zero_profile');np.testing.assert_array_equal(v,c.score(s,ids[5:]))
    def test_missing_vectors(self):
        ids,c,m,b=self.context();c.vectors={};v,d=profile_scores('rating_weighted',self.support(),ids,c)
        self.assertTrue(np.isnan(v).all());self.assertEqual(d['valid_support_vectors'],0)
    def test_cached_once(self):
        ids,c,m,b=self.context()
        with patch.object(c,'score',wraps=c.score) as cs,patch('experiments.scent_v2.content_accuracy.core.ridge',wraps=ridge) as mf:
            x=cache_support(self.support(),ids,c,m,b)
            for spec in experiment_specs().values():score_cached(spec,x)
            self.assertEqual(cs.call_count,1);self.assertEqual(mf.call_count,1);self.assertFalse(x['mf'].flags.writeable)
    def test_baseline_and_pure_content(self):
        ids,c,m,b=self.context();s=self.support();x=cache_support(s,ids,c,m,b)
        self.assertEqual(predict(dict(profile='original',alpha=.25),s,ids,c,m,b),user_scores(dict(alpha=.25,ridge_scale=1,center=False),s,ids,c,m,b))
        altered=dict(x,mf=np.zeros(len(x['pool'])));spec=dict(profile='original',alpha=1,pure='content');np.testing.assert_array_equal(score_cached(spec,x),score_cached(spec,altered))
    def test_top5_all_policies(self):
        ids,c,m,b=self.context()
        for spec in experiment_specs().values():
            top=predict(spec,self.support(),ids,c,m,b);self.assertEqual(len(top),len(set(top)));self.assertEqual(len(top),5);self.assertFalse(set(top)&set('abcde'))
    def test_restore_all_policies(self):
        ids,c,m,b=self.context()
        for spec in experiment_specs().values():
            with tempfile.TemporaryDirectory() as t:
                path=Path(t)/'model.npz';save_model(path,c,m,b,ids,spec);lc,lm,lb,meta=load_model(path);x=cache_support(self.support(),ids,c,m,b);y=cache_support(self.support(),ids,lc,lm,lb)
                np.testing.assert_array_equal(score_cached(spec,x),score_cached(meta['spec'],y));self.assertEqual(predict(spec,self.support(),ids,c,m,b),predict(meta['spec'],self.support(),ids,lc,lm,lb))
    def test_user_disjoint_folds(self):
        cohort=[dict(user=str(n),support=[(str(i),.2) for i in range(5)],answers=[('held',.8)]) for n in range(50)]
        for f in folds(cohort):
            self.assertEqual(len(f['evaluation']),10);self.assertEqual(len({u for u,i,r in f['train']}),40);self.assertFalse({u for u,i,r in f['train']}&{r['user'] for r in f['evaluation']})
    def test_support_only_api(self):
        self.assertNotIn('answers',inspect.signature(profile_scores).parameters);self.assertNotIn('answers',inspect.signature(cache_support).parameters)
        ids,c,m,b=self.context()
        with self.assertRaises(ValueError):profile_scores('rating_weighted',[('a',1)]*5,ids,c)

if __name__=='__main__':unittest.main()
