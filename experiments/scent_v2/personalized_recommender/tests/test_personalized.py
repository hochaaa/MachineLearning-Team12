"""Focused math, actual old-mode equivalence and temporary feedback tests."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from experiments.scent_v2.personalized_recommender.engine import Engine,PERSONAL,DIVERSE,OLD_MODES,preferences,rerank,cosine
from experiments.scent_v2.personalized_recommender.storage import Store
from experiments.scent_v2.real_user_evaluation.storage import VERSION
from experiments.scent_v2.real_user_evaluation.engine import concentration

class PersonalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.e=Engine()
    def setUp(self):
        self.s=[dict(product_id=i,rating=7) for i in sorted(self.e.old)[:5]]
        self.v={str(i):{'note:rose' if i==0 else 'note:wood' if i==1 else 'note:neutral'+str(i):1.} for i in range(5)}
        self.v.update(a={'note:rose':1.},b={'note:wood':1.},c={'note:other':1.})
        self.toy=[dict(product_id=str(i),rating=10 if i==0 else 0 if i==1 else 5) for i in range(5)]
    def test01_old_modes_unchanged(self):
        from experiments.scent_v2.unified_recommender.engine import Engine as Old
        old=Old()
        for mode in OLD_MODES:
            a=self.e.recommend(self.s,mode);b=old.recommend(self.s,mode)
            self.assertEqual([(r['id'],r['score']) for r in a],[(r['id'],r['score']) for r in b])
    def test02_low_ratings_penalize(self):
        a,_=preferences(self.v,self.toy,['a','b','c']);b,_=preferences(self.v,[dict(r,rating=5) if r['product_id']=='1' else r for r in self.toy],['a','b','c'])
        self.assertEqual(a['b'],0);self.assertGreater(b['b'],a['b']);m,_=preferences(self.v,[dict(r,rating=3) if r['product_id']=='1' else r for r in self.toy],['a','b','c']);self.assertGreater(m['b'],a['b'])
    def test03_high_ratings_help(self):
        a,_=preferences(self.v,self.toy,['a','b','c']);b,_=preferences(self.v,[dict(r,rating=5) if r['product_id']=='0' else r for r in self.toy],['a','b','c'])
        self.assertEqual(a['a'],1);self.assertGreater(a['a'],b['a']);m,_=preferences(self.v,[dict(r,rating=7) if r['product_id']=='0' else r for r in self.toy],['a','b','c']);self.assertLess(m['a'],a['a'])
    def test04_mmr(self):
        vectors=dict(a={'x':1},b={'x':1},c={'y':1});values=dict(a=1,b=.99,c=.98)
        self.assertEqual(rerank(values,vectors,k=3,diversity=False)[0],['a','b','c'])
        self.assertEqual(rerank(values,vectors,k=3,diversity=True)[0],['a','c','b'])
        v={str(i):{'x' if i<5 else 'y':1} for i in range(6)};r={str(i):1-i*.001 for i in range(6)}
        plain,_=rerank(r,v,diversity=False);diverse,_=rerank(r,v,diversity=True)
        avg=lambda ids:sum(cosine(v[a],v[b]) for n,a in enumerate(ids) for b in ids[n+1:])/10
        self.assertLess(avg(diverse),avg(plain))
    def test05_top5_unique(self):
        for mode in (PERSONAL,DIVERSE):self.assertEqual(len({r['id'] for r in self.e.recommend(self.s,mode)}),5)
    def test06_seen_excluded(self):
        seen={r['product_id'] for r in self.s};extra=set(sorted(self.e.new)[:3])
        self.assertFalse({r['id'] for r in self.e.recommend(self.s,DIVERSE,extra)}&(seen|extra))
    def test07_evidence_real(self):
        for mode in [*OLD_MODES,PERSONAL,DIVERSE]:
            for r in self.e.recommend(self.s,mode):
                self.assertTrue(r['reasons']);self.assertTrue(set(r['evidence_tokens'])<=set(self.e.vectors[r['id']]))
                self.assertTrue(all(any(t in self.e.vectors[x['product_id']] for x in self.s if x['rating']>=7) for t in r['evidence_tokens']))
    def test08_feedback_and_toggle_versions(self):
        policy=dict(retention_end='2027-02-28',deletion_method='TEST_ONLY',team_access='TEST_ONLY',confirmed_by='TEST_FIXTURE',confirmed=True,test_only=True)
        with tempfile.TemporaryDirectory() as t:
            store=Store(Path(t)/'data',self.e,policy,True)
            try:
                p=store.register_evaluation(True,VERSION)
                for r in self.s:store.save_rating(p['token'],p['csrf'],dict(**r,concentration=concentration(self.e.catalog[r['product_id']]['name']),experience='EXPERIENCED',identity_confirmed=True))
                sessions=[]
                for mode in (PERSONAL,DIVERSE):
                    s=store.recommend_mode(p['token'],p['csrf'],mode);sessions.append(s['session_id'])
                    store.feedback(p['token'],p['csrf'],s['session_id'],s['results'][0]['id'],'NOT_EXPERIENCED',None)
                    self.assertEqual(store.recommend_mode(p['token'],p['csrf'],mode),store.recommend_mode(p['token'],p['csrf'],mode))
                self.assertEqual(len(set(sessions)),2);self.assertEqual(len(store.state(p['token'])['feedback']),2)
                store.delete_by_code(p['deletion_code'])
            finally:store.lock.close()
    def test09_neutral(self):
        v,p=preferences(self.v,[dict(r,rating=5) for r in self.toy],['a','b','c']);self.assertEqual(set(v.values()),{.5})
    def test10_conservative_relevance_bound(self):
        vectors={str(i):{'x'+str(i):1} for i in range(5)};scores={str(i):1-i*.1 for i in range(5)}
        top,trace=rerank(scores,vectors)
        self.assertEqual(len(top),5)
        for i in top:self.assertLessEqual(trace[i]['best_remaining_relevance']-scores[i],.05+1e-12)
    def test11_preservation(self):
        for p,h in json.loads(Path('/tmp/scent-v223-before.json').read_text()).items():self.assertEqual(hashlib.sha256(Path(p).read_bytes()).hexdigest(),h)
    def test12_repeat(self):self.assertEqual(self.e.recommend(self.s,DIVERSE),self.e.recommend(self.s,DIVERSE))

if __name__=='__main__':unittest.main()
