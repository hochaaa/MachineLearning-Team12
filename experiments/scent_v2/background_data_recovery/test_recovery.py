"""Focused restoration/serialization checks; no final25 labels or real-data fits."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from perfume.models import Content,Baseline
from experiments.scent_v2.mf_cv_optimization.core import user_scores
from .core import CONFIG,developer_data,digest,validate_data,pack_state,save_bank,load_model,predict,SimilarityIndex,cache_support,rerank
from .run import counts_coverage

class RecoveryTests(unittest.TestCase):
    def cohort(self):return [dict(user=f'd{n}',support=[(str(i),.2+.1*i) for i in range(5)],answers=[('5',.8)]) for n in range(5)]
    def test_disjoint_background_union(self):
        bg=[('bg','0',.8),('bg','1',.4)];parts=validate_data(bg,self.cohort(),{'reserved'},list(map(str,range(6))))
        for f in parts:
            self.assertEqual(len({u for u,i,r in f['train']}),5);self.assertEqual(len(f['train']),26);self.assertFalse({u for u,i,r in f['train']}&{r['user'] for r in f['evaluation']})
    def test_background_developer_overlap_rejected(self):
        with self.assertRaises(ValueError):validate_data([('d0','0',.8)],self.cohort(),{'reserved'},list(map(str,range(6))))
    def test_background_reserved_overlap_rejected(self):
        with self.assertRaises(ValueError):validate_data([('reserved','0',.8)],self.cohort(),{'reserved'},list(map(str,range(6))))
    def test_duplicate_edges_rejected(self):
        with self.assertRaises(ValueError):validate_data([('bg','0',.8),('bg','0',.8)],self.cohort(),{'reserved'},list(map(str,range(6))))
    def test_invalid_normalization_rejected(self):
        with self.assertRaises(ValueError):validate_data([('bg','0',1.1)],self.cohort(),{'reserved'},list(map(str,range(6))))
    def test_original_reader_skips_reserved_numeric_labels(self):
        eligible=[f'u{n}' for n in range(30)];reserved=set(sorted(eligible,key=lambda u:digest('12:v224:role:'+u))[:10]);rows=[[u,str(i),'DO_NOT_DECODE' if u in reserved else .8] for u in eligible for i in range(6)]+[[f'bg{n}',str(i),.5] for n in range(3) for i in range(3)]
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'train.json';path.write_text(json.dumps(rows));bg,dev,r,source=developer_data(path,list(map(str,range(6))))
            self.assertEqual(r,reserved);self.assertEqual(len(bg),9);self.assertEqual(len(dev),20);self.assertEqual(source['reserved_rating_tokens_decoded'],0)
    def test_unchanged_MF_and_policies(self):
        self.assertEqual(CONFIG['mf'],dict(factors=4,epochs=160,learning_rate=.01,regularization=.01,seed=12));self.assertEqual(CONFIG['model_B'],dict(signal='max',mode='top50',**{'lambda':.2}));self.assertEqual(CONFIG['max_actual_MF_fits'],5)
    def context(self):
        ids=[f'i{n:03}' for n in range(80)];c=Content();c.idf={'a':1.,'b':1.};c.vectors={i:{'b':1.} if n%2 else {'a':1.} for n,i in enumerate(ids)};m=SimpleNamespace(Q=np.random.default_rng(12).uniform(0,.2,(80,4)),items={i:n for n,i in enumerate(ids)},factors=4,reg=.01);b=Baseline().fit([('train',i,.8) for i in ids]);return ids,c,m,b
    def test_fold_bank_restore_exact_and_private_state_absent(self):
        ids,c,m,b=self.context();s=list(zip(ids[:5],[.9,.1,.7,.3,.5]));state=pack_state(c,m,b,ids)
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'best.npz';save_bank(path,[state]*5,CONFIG['model_B'])
            for fold in range(1,6):
                lc,lm,lb,meta=load_model(path,fold);self.assertEqual(meta['default_fold'],1)
                for name in ['A','B']:self.assertEqual(predict(CONFIG['model_'+name],s,ids,c,m,b),predict(CONFIG['model_'+name],s,ids,lc,lm,lb))
            with np.load(path,allow_pickle=False) as z:self.assertFalse(any(k.endswith('_P') or k.endswith('_users') or k.endswith('_ratings') for k in z.files))
    def test_invalid_stored_fold(self):
        ids,c,m,b=self.context()
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'m.npz';save_bank(path,[pack_state(c,m,b,ids)]*5,CONFIG['model_A'])
            with self.assertRaises(ValueError):load_model(path,6)
    def test_original_H_preserved(self):
        ids,c,m,b=self.context();s=list(zip(ids[:5],[.9,.1,.7,.3,.5]));self.assertEqual(predict(CONFIG['model_A'],s,ids,c,m,b)[0],user_scores(dict(alpha=.25,ridge_scale=1.,center=False),s,ids,c,m,b))
    def test_top50_scope_and_recall_set_invariance(self):
        ids,c,m,b=self.context();s=list(zip(ids[:5],[.9,.1,.7,.3,.5]));x=cache_support(s,ids,c,m,b,SimilarityIndex(c,ids));q=m.Q.copy();h=x['hybrid'].copy();a,_=rerank(CONFIG['model_A'],x,100);z,_=rerank(CONFIG['model_B'],x,100)
        self.assertEqual(set(a[:50]),set(z[:50]));self.assertEqual(a[50:],z[50:]);self.assertEqual(len(z),len(set(z)));self.assertFalse(set(z)&set(ids[:5]));np.testing.assert_array_equal(q,m.Q);np.testing.assert_array_equal(h,x['hybrid'])
    def test_coverage_counts_include_zero_candidate(self):
        s=counts_coverage([('u','a',.8),('u','b',.2)],['a','b','c'],['a','c'])
        self.assertEqual(s['candidate_zero_rating_fraction'],1/3);self.assertEqual(s['positive_heldout_seen_train_fraction'],.5)

if __name__=='__main__':unittest.main()
