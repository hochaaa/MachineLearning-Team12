"""Isolated temporary test-fixture DBs, no real respondents or fake accuracy evidence."""
import csv,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from experiments.scent_v2.real_user_evaluation.storage import EvaluationStore,VERSION,preference,policy_ready
from experiments.scent_v2.real_user_evaluation.engine import Engine,concentration
ROOT=Path(__file__).resolve().parents[4]
TEST_POLICY=dict(retention_end='TEST_ONLY',deletion_method='TEST_ONLY',team_access='TEST_ONLY',confirmed_by='AUTOMATED_TEST_FIXTURE',confirmed=True,test_only=True)

class FakeEngine:
    model_version='TEST_FIXTURE_NOT_FROZEN';catalog_version='TEST_FIXTURE'
    def __init__(self):self.catalog={str(i):dict(id=str(i),brand='Test',name='Test '+str(i)) for i in range(30)};self.received=None
    def recommend(self,support):
        self.received=support;seen={r['product_id'] for r in support};return [dict(id=i,rank=n+1,score=.5,**{k:v for k,v in self.catalog[i].items() if k!='id'}) for n,i in enumerate([i for i in self.catalog if i not in seen][:5])]

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.e=FakeEngine();self.s=EvaluationStore(Path(self.tmp.name)/'fixture',self.e,TEST_POLICY,True);self.p=self.s.register_evaluation(True,VERSION);self.token=self.p['token'];self.csrf=self.p['csrf']
    def tearDown(self):self.s.lock.close();self.tmp.cleanup()
    def rating(self,i,y=7):return self.s.save_rating(self.token,self.csrf,dict(product_id=str(i),rating=y,concentration='CATALOG_UNSPECIFIED',experience='EXPERIENCED',identity_confirmed=True))
    def session(self):
        for i in range(8):self.rating(i)
        return self.s.recommend(self.token,self.csrf)
    def test01_store_real_zero(self):self.rating(0,0);self.assertEqual(self.s.state(self.token)['ratings'][0]['rating'],0)
    def test02_halfstep(self):
        with self.assertRaises(ValueError):self.rating(0,7.2)
    def test03_support_insufficient(self):
        for i in range(4):self.rating(i)
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_MATCHED_SUPPORT'):self.s.recommend(self.token,self.csrf)
    def test04_heldout_not_in_score(self):
        s=self.session();self.assertEqual(len(self.e.received),5);self.assertEqual({r['product_id'] for r in self.e.received},set(s['support_product_ids']))
    def test05_no_training(self):
        from perfume.models import MatrixFactorization
        with patch.object(MatrixFactorization,'fit',side_effect=AssertionError('Forbidden training')):self.session()
    def test06_top5(self):self.assertEqual(len(self.session()['results']),5)
    def test07_support_exclusion(self):
        s=self.session();self.assertFalse(set(s['support_product_ids'])&{r['id'] for r in s['results']})
    def test08_never_experienced_null(self):
        s=self.session();i=s['results'][0]['id'];self.s.feedback(self.token,self.csrf,s['session_id'],i,'NOT_EXPERIENCED',None)
        self.assertIsNone(self.s.state(self.token)['feedback'][0]['rating'])
        with self.assertRaises(ValueError):self.s.feedback(self.token,self.csrf,s['session_id'],i,'NOT_EXPERIENCED',0)
    def test09_unknown_null(self):self.assertIsNone(preference('UNKNOWN_EXPERIENCE',None))
    def test10_post_separated(self):
        s=self.session();free=next(i for i in self.e.catalog if i not in set(s['support_product_ids'])|{r['id'] for r in s['results']});r=self.rating(free);self.assertEqual(r['source'],'post_recommendation_feedback')
    def test11_comparison_sample(self):
        s=self.session();ids={r['id'] for r in s['results']};support=set(s['support_product_ids']);c=s['comparisons'];self.assertEqual(len(c),5)
        for r in c:self.assertNotIn(r['product_id'],ids|support);self.assertEqual(r['selection_probability'],5/20)
    def test12_model_versions(self):self.assertEqual(self.session()['model_version'],self.e.model_version)
    def test13_dedup_sessions(self):
        a=self.session();b=self.s.recommend(self.token,self.csrf);self.assertEqual(a,b);self.assertEqual(self.s.analyses()['collection']['sessions'],1)
    def test14_no_direct_identity_fields(self):
        with self.s.connection() as c:self.assertFalse({'name','email','phone'}&{r[1] for r in c.execute('PRAGMA table_info(participants)')})
    def test15_export_csv(self):
        self.rating(0);self.s.export_evaluation();rows=list(csv.DictReader((self.s.root/'v21_ratings.csv').open()));self.assertEqual(len(rows),1);self.assertNotIn('auth_hash',rows[0])
    def test16_old_db_preserved(self):self.check_prefix(('outputs/scent_v2/real_user_dataset/',))
    def test17_services(self):self.check_prefix(('web/','deployment/'))
    def test18_frozen19(self):
        f=json.loads((ROOT/'outputs/final/freeze.json').read_text())['protected_sha256'];self.assertEqual(len(f),19)
        for p,h in f.items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)
    def test19_v216to20(self):self.check_prefix(tuple('outputs/scent_v2/'+p+'/' for p in ['real_rating_retraining','perfume_catalog_expansion','expanded_content','shared_notes_content','multi_interest_hybrid']))
    def check_prefix(self,prefixes):
        for p,h in json.loads(Path('/tmp/scent-v221-before.json').read_text()).items():
            if p.startswith(prefixes):self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)
    def test20_determinism(self):
        s=self.session();a=self.e.recommend(self.e.received);b=self.e.recommend(self.e.received);self.assertEqual(a,b)
    def test21_unknown_product_no_fuzzy(self):
        r=self.s.save_rating(self.token,self.csrf,dict(product_id=None,original_name='Test Unknown EDP',rating=8,experience='EXPERIENCED'));self.assertFalse(r['matched'])
    def test22_concentration_mismatch(self):
        with self.assertRaises(ValueError):self.s.save_rating(self.token,self.csrf,dict(product_id='0',rating=8,experience='EXPERIENCED',concentration='EDP',identity_confirmed=True))
    def test23_concentration_no_inference(self):self.assertEqual(concentration('Test Brand Product'),'CATALOG_UNSPECIFIED');self.assertEqual(concentration('Example Eau de Parfum'),'EDP')
    def test24_duplicate_ratings(self):
        self.rating(0)
        with self.assertRaises(ValueError):self.rating(0)
    def test25_pending_policy_blocks_registration(self):
        self.s.policy={}
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_PENDING'):self.s.register_evaluation(True,VERSION)
    def test26_test_policy_not_real(self):self.assertFalse(policy_ready(TEST_POLICY));self.assertTrue(policy_ready(TEST_POLICY,True))
    def test27_no_fake_offline_accuracy(self):
        self.session();a=self.s.analyses();self.assertEqual(a['offline']['metrics'],'NOT_EVALUATED');self.assertFalse(a['offline']['training_exclusion_verified'])
    def test28_withdraw(self):
        self.session();self.s.withdraw_evaluation(self.token,self.csrf);self.assertEqual(self.s.analyses()['collection']['actual_new_participants'],0)
    def test29_foreign_session_denied(self):
        s=self.session();p=self.s.register_evaluation(True,VERSION)
        with self.assertRaises(PermissionError):self.s.feedback(p['token'],p['csrf'],s['session_id'],s['results'][0]['id'],'EXPERIENCED',8)
    def test30_support_cannot_be_feedback(self):
        s=self.session()
        with self.assertRaises(ValueError):self.s.feedback(self.token,self.csrf,s['session_id'],s['support_product_ids'][0],'EXPERIENCED',9)

class ActualFrozenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=Engine()
    def test31_actual_load479(self):self.assertEqual(len(self.engine.catalog),479)
    def test32_actual_results_parity(self):
        from deployment.standalone_v1.runtime_loader import StandaloneService
        from deployment.final_v1.config import assets_path,MANIFEST_PIN
        other=StandaloneService(assets_path(),MANIFEST_PIN);items=sorted(self.engine.catalog)[:5];s=[dict(product_id=i,rating=7) for i in items]
        a=self.engine.recommend(s);b=other.recommend([SimpleNamespace(perfume_id=i,rating=7) for i in items],'none')['results'];self.assertEqual(a,b)
    def test33_actual_repeat(self):
        support=[dict(product_id=i,rating=7) for i in sorted(self.engine.catalog)[:5]];self.assertEqual(self.engine.recommend(support),self.engine.recommend(support))
    def test34_reject497(self):
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_PRODUCT'):self.engine.recommend([dict(product_id='v218:'+str(i),rating=7) for i in range(5)])



class DeletionPolicyTests(unittest.TestCase):
    setUp=StoreTests.setUp
    tearDown=StoreTests.tearDown
    rating=StoreTests.rating
    session=StoreTests.session
    # Inherited tests run against the same fixture setup; extra privacy invariants.
    def test35_deletion_hash_only_and_once(self):
        code=self.p['deletion_code']
        with self.s.connection() as c:
            row=c.execute('SELECT * FROM v21_consents').fetchone();self.assertEqual(row['deletion_hash'],hashlib.sha256(code.encode()).hexdigest());self.assertNotIn(code,str(dict(row)))
        self.assertNotIn('deletion_code',self.s.state(self.token))
    def test36_delete_code_cascade_and_csv(self):
        s=self.session();self.s.feedback(self.token,self.csrf,s['session_id'],s['results'][0]['id'],'EXPERIENCED',8);self.s.export_evaluation()
        self.s.delete_by_code(self.p['deletion_code'])
        with self.s.connection() as c:
            for table in ('participants','v21_consents','v21_ratings','v21_sessions','v21_feedback','v21_comparisons'):self.assertEqual(c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0],0)
        self.assertFalse(list(self.s.root.glob('v21_*.csv')))
    def test37_expiration(self):
        from datetime import date
        self.rating(0)
        with self.s.connection() as c:c.execute('UPDATE v21_consents SET policy_json=?',(json.dumps(dict(TEST_POLICY,retention_end='2027-02-28')),))
        self.assertEqual(self.s.purge_expired(date(2027,2,28)),0);self.assertEqual(self.s.purge_expired(date(2027,3,1)),1)
    def test38_invalid_code(self):
        with self.assertRaises(ValueError):self.s.delete_by_code('z'*43)
    def test39_expired_policy_not_ready(self):self.assertFalse(policy_ready(dict(TEST_POLICY,test_only=False,retention_end='2000-01-01')))

if __name__=='__main__':unittest.main()
