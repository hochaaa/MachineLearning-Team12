"""Pre-fit synthetic CV/centered-ridge math and reserved/background label poison."""
import json,tempfile,unittest
from pathlib import Path
import numpy as np
from experiments.scent_v2.mf_cv_optimization.core import developer_cohort,folds,ridge,user_scores,digest,Content,MatrixFactorization,Baseline,validate_train
from experiments.scent_v2.mf_cv_optimization.run import save_model
from experiments.scent_v2.accuracy_optimization.run import load_model
from experiments.scent_v2.recommend import fold_in,score as old_score

class CVTests(unittest.TestCase):
    def setUp(self):
        self.ids=list(map(str,range(10)));self.s=[(str(i),(.2+i*.2)) for i in range(5)]
        self.c=Content();self.c.idf={'note:rose':1.};self.c.vectors={i:{'note:rose':1.} for i in self.ids}
        self.m=MatrixFactorization(factors=4,regularization=.01);self.m.Q=np.asarray([[.1,.2,.3,.4]]*10);self.m.items={i:n for n,i in enumerate(self.ids)}
        self.b=Baseline();from collections import defaultdict
        self.b.counts=defaultdict(int,{i:1 for i in self.ids});self.b.maximum=1
    def cohort(self):
        users=[f'u{n}' for n in range(75)];reserved=set(sorted(users,key=lambda u:digest('12:v224:role:'+u))[:25]);records=[]
        for u in users:
            for i in range(6):records.append('['+json.dumps(u)+','+json.dumps(str(i))+','+('DO_NOT_DECODE' if u in reserved else '0.7')+']')
        for i in range(3):records.append('["background",'+json.dumps(str(i))+',DO_NOT_DECODE]')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'source.json';p.write_text('['+','.join(records)+']');cohort,res,summary=developer_cohort(p,self.ids)
        return cohort,res,summary
    def test01_only50_labels(self):
        c,r,s=self.cohort();self.assertEqual(len(c),50);self.assertEqual(s['reserved_rating_tokens_decoded'],0);self.assertEqual(s['background_rating_tokens_decoded'],0);self.assertEqual(s['developer_ratings'],300)
    def test02_five_disjoint_user_folds(self):
        c,res,s=self.cohort();parts=folds(c);seen=[]
        for f in parts:
            test={r['user'] for r in f['evaluation']};validate_train(f['train'],test|res);self.assertEqual(len(test),10);self.assertEqual(len({u for u,i,y in f['train']}),40);seen.extend(test)
        self.assertEqual(len(seen),len(set(seen)))
    def test03_fold_reproducible(self):c,r,s=self.cohort();self.assertEqual(folds(c),folds(c))
    def test04_support_holdout_disjoint(self):
        c,r,s=self.cohort()
        for row in c:self.assertEqual(len(row['support']),5);self.assertFalse({i for i,y in row['support']}&{i for i,y in row['answers']})
    def test05_original_ridge_exact(self):
        p,mu=ridge(self.m,self.s);np.testing.assert_array_equal(p,fold_in(self.m,self.s));self.assertEqual(mu,0)
    def test06_regularization_scales(self):
        lo,_=ridge(self.m,self.s,.5);normal,_=ridge(self.m,self.s);hi,_=ridge(self.m,self.s,2)
        self.assertGreater(np.linalg.norm(lo),np.linalg.norm(normal));self.assertGreater(np.linalg.norm(normal),np.linalg.norm(hi))
    def test07_centered_support_only_math(self):
        p,mu=ridge(self.m,self.s,1,True);q=self.m.Q[:5];expected=np.linalg.solve(np.einsum('ni,nj->ij',q,q)+5*.01*np.eye(4),np.einsum('ni,n->i',q,np.asarray([y-mu for i,y in self.s])))
        self.assertAlmostEqual(mu,.6);np.testing.assert_array_equal(p,expected)
    def test08_baseline_top5(self):
        for alpha,method in ((.25,'hybrid'),(0,'mf_fallback')):
            top=user_scores(dict(alpha=alpha,ridge_scale=1,center=False),self.s,self.ids,self.c,self.m,self.b);ref=old_score(self.s,self.ids,self.c,self.m,self.b)['methods'][method]['top'];self.assertEqual(top,ref)
    def test09_no_answers_argument(self):
        import inspect
        self.assertNotIn('answers',inspect.signature(ridge).parameters);self.assertNotIn('answers',inspect.signature(user_scores).parameters)
    def test10_top5_no_duplicates_seen(self):
        for centered in (False,True):
            top=user_scores(dict(alpha=.05,ridge_scale=.5,center=centered),self.s,self.ids,self.c,self.m,self.b);self.assertEqual(len(set(top)),5);self.assertFalse(set(top)&{i for i,y in self.s})
    def test11_missing_support_no_fake_latent(self):
        self.assertEqual(ridge(self.m,[(str(i+20),.7) for i in range(5)],1,True),(None,0.))
    def test12_saved_model_predict(self):
        spec=dict(name='test',alpha=.05,ridge_scale=.5,center=True)
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'model.npz';save_model(path,self.c,self.m,self.b,self.ids,spec);c,m,b,meta=load_model(path)
            self.assertEqual(user_scores(spec,self.s,self.ids,self.c,self.m,self.b),user_scores(meta['spec'],self.s,self.ids,c,m,b))

if __name__=='__main__':unittest.main()
