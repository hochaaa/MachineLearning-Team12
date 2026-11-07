"""Targeted tests, zero MF fits; reserved label poison and shared raw-score arrays."""
import json,tempfile,unittest,hashlib
from pathlib import Path
import numpy as np
from experiments.scent_v2.mf_accuracy_optimization.core import developer_data,digest,CONFIG,components,cache_scores,measure,Content,MatrixFactorization,Baseline,hybrid,tie_key
from experiments.scent_v2.recommend import score as original
from experiments.scent_v2.accuracy_optimization.run import load_model
from experiments.scent_v2.mf_accuracy_optimization.run import save_model

class MFTests(unittest.TestCase):
    def setUp(self):
        self.ids=list(map(str,range(10)));self.support=[(str(i),.7) for i in range(5)]
        self.c=Content();self.c.idf={'note:rose':1};self.c.vectors={i:{'note:rose':1.} for i in self.ids}
        self.m=MatrixFactorization(factors=4,regularization=.01);self.m.Q=np.asarray([[.1,.2,.15,.1]]*10);self.m.items={i:n for n,i in enumerate(self.ids)}
        self.b=Baseline();from collections import defaultdict
        self.b.counts=defaultdict(int,{i:1 for i in self.ids});self.b.maximum=1
        self.dev=[dict(user='test',support=self.support,answers=[('5',.9)])]
    def test01_reserved_poison_never_decoded(self):
        users=[f'u{u}' for u in range(36)];reserved=set(sorted(users,key=lambda u:digest('12:v224:role:'+u))[:12])
        records=['['+json.dumps(u)+','+json.dumps(str(i))+','+('FORBIDDEN_LABEL' if u in reserved else '.7')+']' for u in users for i in range(7)]
        records += [json.dumps(['short',str(i),.7]) for i in range(3)]
        # .7 is not JSON syntax; correct retained token explicitly, keeping poison opaque.
        records=[r.replace(',.7]',',0.7]') for r in records]
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'rows.json';path.write_text('['+','.join(records)+']');train,dev,blocked,summary=developer_data(path,self.ids)
            self.assertEqual(blocked,reserved);self.assertEqual(summary['reserved_rating_tokens_decoded'],0);self.assertEqual(len(dev),24)
            self.assertFalse(({u for u,i,r in train}|{r['user'] for r in dev})&reserved);self.assertEqual(len(train),3)
    def test02_original_hybrid_same(self):
        cache=cache_scores(self.dev,self.ids,self.c,self.m,self.b);_,r=measure(.25,cache,self.dev,self.ids)
        self.assertEqual(r[0]['top'],original(self.support,self.ids,self.c,self.m,self.b)['methods']['hybrid']['top'])
    def test03_all_alphas_same_arrays(self):
        cache=cache_scores(self.dev,self.ids,self.c,self.m,self.b);before=[(x['content'].tobytes(),x['mf'].tobytes()) for x in cache]
        for alpha in CONFIG['alphas']:measure(alpha,cache,self.dev,self.ids)
        self.assertEqual(before,[(x['content'].tobytes(),x['mf'].tobytes()) for x in cache]);self.assertFalse(cache[0]['mf'].flags.writeable)
    def test04_exact_raw_weight(self):
        c=np.array([.2,.8]);m=np.array([.9,.1])
        for alpha in CONFIG['alphas']:np.testing.assert_array_equal(hybrid(c,m,alpha,np.zeros(2)),alpha*c+(1-alpha)*m)
    def test05_missing_fallback_preserved(self):self.assertEqual(hybrid(np.array([.8]),np.array([np.nan]),0,np.array([.1]))[0],.8)
    def test06_top5_no_seen(self):
        cache=cache_scores(self.dev,self.ids,self.c,self.m,self.b)
        for alpha in CONFIG['alphas']:
            _,rows=measure(alpha,cache,self.dev,self.ids);top=rows[0]['top'];self.assertEqual(len(set(top)),5);self.assertFalse(set(top)&{i for i,r in self.support})
    def test07_tie_simple_baseline(self):self.assertLess(tie_key(0,.25),tie_key(0,.2));self.assertLess(tie_key(0,0),tie_key(3,.25))
    def test08_saved_inference(self):
        import experiments.scent_v2.mf_accuracy_optimization.run as run
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t,patch.object(run,'OUT',Path(t)):
            save_model(self.c,self.m,self.b,self.ids,dict(config_index=0,alpha=.1));c,m,b,meta=load_model(Path(t)/'best_model.npz')
            a,_=measure(.1,cache_scores(self.dev,self.ids,self.c,self.m,self.b),self.dev,self.ids);z,_=measure(.1,cache_scores(self.dev,self.ids,c,m,b),self.dev,self.ids)
            self.assertEqual(a,z);self.assertFalse(hasattr(m,'P'));self.assertEqual(meta['spec']['alpha'],.1)
    def test09_metrics_same_denominator(self):
        a,r=measure(.25,cache_scores(self.dev,self.ids,self.c,self.m,self.b),self.dev,self.ids);self.assertEqual(a['positive_users'],1);self.assertAlmostEqual(a['precision'],.2)
    def test10_fit_budget_scope(self):self.assertEqual(CONFIG['MF_fit_budget'],5);self.assertEqual({c['factors'] for c in CONFIG['mf_grid']},{4,8,16})

if __name__=='__main__':unittest.main()
