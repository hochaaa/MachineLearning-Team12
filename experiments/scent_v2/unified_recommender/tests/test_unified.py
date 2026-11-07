"""Targeted core tests only; real weights, synthetic inputs, temporary DB."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from experiments.scent_v2.unified_recommender.engine import Engine,MODES,percentiles
from experiments.scent_v2.unified_recommender.storage import Store
from experiments.scent_v2.real_user_evaluation.storage import VERSION

class UnifiedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.e=Engine()
    def setUp(self):self.support=[dict(product_id=i,rating=7) for i in sorted(self.e.old)[:5]]
    def test01_frozen_exact(self):
        a=self.e.recommend(self.support,MODES[0]);b=self.e.frozen.recommend(self.support)
        self.assertEqual([(r['id'],r['score']) for r in a],[(r['id'],r['score']) for r in b])
    def test02_expanded497(self):self.assertEqual(self.e.recommend(self.support,MODES[1])[0]['candidate_count'],497)
    def test03_unified497(self):self.assertEqual(self.e.recommend(self.support,MODES[2])[0]['candidate_count'],497)
    def test04_new_top5(self):
        s=[dict(product_id=i,rating=7) for i in sorted(self.e.new)[:5]]
        self.assertEqual(len(self.e.catalog),497);self.assertEqual(len(self.e.new),18)
        for mode in MODES[1:]:self.assertTrue(any(r['id'] in self.e.new for r in self.e.recommend(s,mode)))
    def test05_seen_excluded(self):
        seen={s['product_id'] for s in self.support};other=set(sorted(self.e.old)[5:10])
        for mode in MODES:self.assertFalse({r['id'] for r in self.e.recommend(self.support,mode,other)}&(seen|other))
    def test06_modes_distinct(self):self.assertEqual(len({self.e.version(m) for m in MODES}),3)
    def test07_mapping_previous_kept(self):
        prev=self.e.expanded['canonical_mapping'];self.assertEqual(len(prev),18);self.assertTrue(set(prev.values())<=set(self.e.catalog))
    def test08_sessions_per_mode_and_feedback(self):
        policy=dict(retention_end='2027-02-28',deletion_method='TEST_ONLY',team_access='TEST_ONLY',confirmed_by='TEST_FIXTURE',confirmed=True,test_only=True)
        with tempfile.TemporaryDirectory() as t:
            s=Store(Path(t)/'data',self.e,policy,True)
            try:
                p=s.register_evaluation(True,VERSION)
                from experiments.scent_v2.real_user_evaluation.engine import concentration
                for r in self.support:s.save_rating(p['token'],p['csrf'],dict(**r,experience='EXPERIENCED',identity_confirmed=True,concentration=concentration(self.e.catalog[r['product_id']]['name'])))
                ids=[]
                for mode in MODES:
                    a=s.recommend_mode(p['token'],p['csrf'],mode);b=s.recommend_mode(p['token'],p['csrf'],mode);self.assertEqual(a,b);ids.append(a['session_id'])
                    s.feedback(p['token'],p['csrf'],a['session_id'],a['results'][0]['id'],'NOT_EXPERIENCED',None)
                    comp=a['comparisons'][0];s.feedback(p['token'],p['csrf'],a['session_id'],comp['product_id'],'EXPERIENCED',8,True)
                self.assertEqual(len(set(ids)),3);self.assertEqual(len(s.state(p['token'])['sessions']),3);self.assertEqual(len(s.state(p['token'])['feedback']),3)
                s.delete_by_code(p['deletion_code']);self.assertEqual(s.analyses()['collection']['actual_new_participants'],0)
            finally:s.lock.close()
    def test09_search_ko_en(self):
        for q in ('바이레도','딥티크','톰포','Tom Ford','Black Orchid'):
            self.assertTrue(self.e.search(q),q)
        self.assertEqual(len({r['id'] for r in self.e.search('바이레도')}),len(self.e.search('바이레도')))
    def test10_percentile_ties(self):self.assertEqual(percentiles(dict(a=1,b=1,c=0)),dict(a=.75,b=.75,c=0))
    def test11_existing_data_preserved(self):
        for p,h in json.loads(Path('/tmp/scent-v222-before.json').read_text()).items():self.assertEqual(hashlib.sha256(Path(p).read_bytes()).hexdigest(),h,p)
    def test12_repeat_and_zero_profile(self):
        for m in MODES:self.assertEqual(self.e.recommend(self.support,m),self.e.recommend(self.support,m))
        with self.assertRaisesRegex(ValueError,'NO_USABLE_PROFILE'):self.e.recommend([dict(r,rating=0) for r in self.support],MODES[1])

if __name__=='__main__':unittest.main()
