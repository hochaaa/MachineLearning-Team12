"""All fake respondents/ratings stay in TemporaryDirectory, never production DATA."""
import unittest,tempfile,json,csv,os,sqlite3,hashlib,uuid,threading,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
from unittest.mock import patch
from experiments.scent_v2.real_user_dataset.catalog import load_catalog,search
from experiments.scent_v2.real_user_dataset.storage import Store,atomic_write
from experiments.scent_v2.real_user_dataset.validation import validate_batch,ValidationError,csv_safe
from experiments.scent_v2.real_user_dataset.split_manager import assign_role,support_split
from experiments.scent_v2.real_user_dataset.dataset_builder import merge_rows,build,load_training_rows
from experiments.scent_v2.real_user_dataset.config import CONSENT_VERSION
from experiments.scent_v2.real_user_dataset.app import CollectorServer

class CollectionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.catalog=load_catalog();cls.ids=list(cls.catalog)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='scent-v214-unit-');self.root=Path(self.tmp.name);self.s=Store(self.root,self.catalog,dataset_kind='test_fixture');self.p=self.s.register(True,CONSENT_VERSION)
 def tearDown(self):self.s.lock.close();self.tmp.cleanup()
 def body(self,y=7.5,i=0,key='test_req_00001'):return dict(request_id=key,ratings=[dict(perfume_id=self.ids[i],rating=y,experience_type='sampled')])
 def save(self,body=None):return self.s.submit(self.p['token'],self.p['csrf'],body or self.body())
 def test_catalog479(self):self.assertEqual(len(self.catalog),479)
 def test_name_search(self):self.assertTrue(any('orchid'in r['name'].lower()for r in search(self.catalog,'Black Orchid')))
 def test_brand_search(self):self.assertTrue(all('ford'in r['brand'].lower()for r in search(self.catalog,'Tom Ford')))
 def test_query_limit(self):
  with self.assertRaises(ValueError):search(self.catalog,'x'*101)
 def test_invalid_id(self):
  b=self.body();b['ratings'][0]['perfume_id']='fake'
  with self.assertRaises(ValidationError):self.save(b)
 def test_consent_required(self):
  for consent,version in((False,CONSENT_VERSION),(1,CONSENT_VERSION),(True,'old')):
   with self.assertRaises(ValidationError):self.s.register(consent,version)
 def test_no_experience(self):
  b=self.body(0);b['ratings'][0]['experience_type']='no_experience'
  with self.assertRaises(ValidationError):self.save(b)
 def test_valid_zero_and_ten(self):
  self.save(self.body(0,key='zero_0001'));self.assertEqual(self.s.own_ratings(self.p['token'])[0]['rating'],0);self.save(self.body(10,key='ten_00001'));self.assertEqual(self.s.own_ratings(self.p['token'])[0]['rating'],10)
 def test_bad_values(self):
  for y in(-.5,10.5,.1,True,'7',None,float('nan'),float('inf')):
   with self.assertRaises(ValidationError):self.save(self.body(y))
 def test_duplicate_in_batch(self):
  b=self.body();b['ratings']*=2
  with self.assertRaises(ValidationError):self.save(b)
 def test_upsert_preserves_created(self):
  self.save();a=self.s.own_ratings(self.p['token'])[0];r=self.save(self.body(0,key='edit_0001'));b=self.s.own_ratings(self.p['token'])[0];self.assertEqual(a['created_at'],b['created_at']);self.assertEqual(r['updated'],1);self.assertEqual(len(self.s.own_ratings(self.p['token'])),1)
 def test_idempotent_retry(self):self.assertEqual(self.save()['unique_ratings'],1);self.assertEqual(self.save()['added'],1);self.assertEqual(len(self.s.own_ratings(self.p['token'])),1)
 def test_idempotent_key_conflict(self):
  self.save()
  with self.assertRaises(ValidationError):self.save(self.body(9))
 def test_bad_csrf(self):
  with self.assertRaises(PermissionError):self.s.submit(self.p['token'],'bad',self.body())
 def test_session_other_user(self):
  self.save();p=self.s.register(True,CONSENT_VERSION);self.assertEqual(self.s.own_ratings(p['token']),[])
 def test_empty_statistics(self):
  q=self.s.aggregate();self.assertIsNone(q['development_rating_distribution']['mean']);self.assertEqual(q['actual_new_real_ratings'],0);self.assertEqual(q['development']['unrated_items'],479)
 def test_csv_utf8_roundtrip(self):
  b=self.body();b['ratings'][0]['preference_reason']='따뜻한 나무 향';self.save(b)
  role=assign_role(self.p['user_id']);path=self.root/role/'real_user_ratings.csv'
  with path.open(encoding='utf-8',newline='')as f:rows=list(csv.DictReader(f))
  self.assertEqual(rows[0]['preference_reason'],'따뜻한 나무 향');self.assertEqual(float(rows[0]['rating']),7.5)
 def test_csv_formula_neutralized(self):
  b=self.body();b['ratings'][0]['preference_reason']='=1+1';self.save(b);role=assign_role(self.p['user_id'])
  with(self.root/role/'real_user_ratings.csv').open(encoding='utf-8',newline='')as f:row=next(csv.DictReader(f))
  self.assertEqual(row['preference_reason'],"'=1+1");self.assertEqual(self.s.own_ratings(self.p['token'])[0]['preference_reason'],'=1+1')
 def test_limits_and_pii(self):
  for reason in('x'*301,'a@example.com','010-1234-5678','a\nb'):
   b=self.body();b['ratings'][0]['preference_reason']=reason
   with self.assertRaises(ValidationError):self.save(b)
 def test_export_io_failure_recovery(self):
  original=(self.root/'real_user_ratings.csv').read_bytes()
  with patch('experiments.scent_v2.real_user_dataset.storage.atomic_write',side_effect=OSError('simulated full disk')):r=self.save()
  self.assertTrue(r['saved']);self.assertTrue(r['csv_sync_pending']);self.assertEqual((self.root/'real_user_ratings.csv').read_bytes(),original);self.assertEqual(len(self.s.own_ratings(self.p['token'])),1);self.s.export();meta=json.loads((self.root/'collection_metadata.json').read_text());self.assertEqual(meta['actual_ratings'],1)
 def test_atomic_replacement_failure(self):
  p=self.root/'safe.txt';atomic_write(p,b'old')
  with patch('experiments.scent_v2.real_user_dataset.storage.os.replace',side_effect=OSError('simulated')):
   with self.assertRaises(OSError):atomic_write(p,b'new')
  self.assertEqual(p.read_bytes(),b'old')
 def test_permissions(self):
  if os.name!='nt':
   self.assertEqual(self.root.stat().st_mode&0o777,0o700);self.assertEqual((self.root/'participants.csv').stat().st_mode&0o777,0o600)
 def test_uid_unique_and_role_fixed(self):
  ids={self.p['user_id']}
  for _ in range(12):ids.add(self.s.register(True,CONSENT_VERSION)['user_id'])
  self.assertEqual(len(ids),13);self.assertEqual(assign_role(self.p['user_id']),assign_role(self.p['user_id']))
 def test_legacy_id_collision_retry(self):
  fixed=uuid.UUID(int=1);self.s.legacy_ids={'testuser_'+fixed.hex}
  with patch('experiments.scent_v2.real_user_dataset.storage.uuid.uuid4',return_value=fixed):
   with self.assertRaises(RuntimeError):self.s.register(True,CONSENT_VERSION)
 def test_withdraw_clears_own_and_derived(self):
  self.save();(self.root/'training_ready_ratings.csv').write_text('test copy');r=self.s.withdraw(self.p['token'],self.p['csrf']);self.assertTrue(r['withdrawn']);self.assertFalse((self.root/'training_ready_ratings.csv').exists())
  with self.assertRaises(PermissionError):self.s.session(self.p['token'])
 def test_support_split_five_no_target(self):
  for n,status in((3,'insufficient_support'),(5,'no_target'),(6,'eligible')):
   r=support_split('person',[dict(perfume_id=i,rating=5)for i in self.ids[:n]]);self.assertEqual(r['status'],status)
   if n==6:self.assertEqual(len(r['support']),5);self.assertFalse({x['perfume_id']for x in r['support']}&{x['perfume_id']for x in r['heldout']})
 def test_support_selection_ignores_values(self):
  a=[dict(perfume_id=i,rating=0)for i in self.ids[:7]];b=[dict(x,rating=10)for x in a];self.assertEqual([r['perfume_id']for r in support_split('p',a)['support']],[r['perfume_id']for r in support_split('p',b)['support']])
 def test_role_physical_separation_and_dashboard_redaction(self):
  self.save();role=assign_role(self.p['user_id']);other='independent'if role=='development'else'development'
  with(self.root/other/'real_user_ratings.csv').open(encoding='utf-8',newline='')as f:self.assertEqual(len(list(csv.DictReader(f))),0)
  self.assertNotIn('rating_distribution',self.s.aggregate()['independent']);self.assertNotIn('user_id',json.dumps(self.s.aggregate()))
 def test_synthetic_store_merge_forbidden(self):
  with self.assertRaises(ValueError):build(self.root,candidates=self.catalog)
 def test_merge_zero_provenance_and_outside_candidate(self):
  old=[('legacy','outside',.8)];new=[dict(user_id='realuser_test',perfume_id=self.ids[0],rating='0',source='real_user_collection',experience_type='used')];r=merge_rows(old,new,self.catalog,{'realuser_test'});self.assertEqual(r[1]['normalized_rating'],0);self.assertFalse(r[0]['in_service_candidates']);self.assertNotEqual(r[0]['zero_policy'],r[1]['zero_policy'])
 def test_merge_independent_or_synthetic_rejected(self):
  row=dict(user_id='realuser_test',perfume_id=self.ids[0],rating=7,source='real_user_collection',experience_type='used')
  with self.assertRaises(ValueError):merge_rows([], [row],self.catalog,set())
  for source in('test_fixture','synthetic'):
   with self.assertRaises(ValueError):merge_rows([],[dict(row,source=source)],self.catalog,{'realuser_test'})
 def test_merge_collision_duplicate_and_legacy_zero(self):
  with self.assertRaises(ValueError):merge_rows([('legacy',self.ids[0],0)],[],self.catalog,set())
  with self.assertRaises(ValueError):merge_rows([('legacy',self.ids[0],.7)]*2,[],self.catalog,set())
  r=dict(user_id='realuser_x',perfume_id=self.ids[0],rating=7,source='real_user_collection',experience_type='used')
  with self.assertRaises(ValueError):merge_rows([('realuser_x',self.ids[0],.7)],[r],self.catalog,{'realuser_x'})

class HttpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='scent-v214-http-');cls.catalog=load_catalog();cls.store=Store(Path(cls.tmp.name),cls.catalog,dataset_kind='test_fixture');cls.server=CollectorServer(0,cls.store);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url=cls.server.origin
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.store.lock.close();cls.tmp.cleanup()
 def setUp(self):self.jar=http.cookiejar.CookieJar();self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
 def request(self,path,body=None,headers=None,method=None):
  h={'Origin':self.url,'X-Scent-Request':'1'}
  if body is not None:h['Content-Type']='application/json'
  h.update(headers or {});req=urllib.request.Request(self.url+path,data=json.dumps(body).encode()if body is not None else None,headers=h,method=method)
  try:
   with self.client.open(req)as r:return r.status,r.headers,r.read()
  except urllib.error.HTTPError as r:
   with r:return r.code,r.headers,r.read()
 def test_http_html_and479(self):
  st,h,b=self.request('/');self.assertEqual(st,200);self.assertIn('script-src',h['Content-Security-Policy']);st,h,b=self.request('/api/info');self.assertEqual(json.loads(b)['candidate_count'],479)
 def test_unauthorized_admin_and_no_file_serving(self):
  self.assertEqual(self.request('/api/admin/summary')[0],403);self.assertEqual(self.request('/data/independent/real_user_ratings.csv')[0],404);self.assertEqual(self.request('/../../config.py')[0],404)
 def test_host_and_origin_rejected(self):
  self.assertEqual(self.request('/api/info',headers={'Host':'evil.test'})[0],403);self.assertEqual(self.request('/api/register',dict(consent=True,consent_version=CONSENT_VERSION),{'Origin':'https://evil.test'})[0],403)
 def test_browser_registration_post_and_cookie(self):
  st,h,b=self.request('/api/register',dict(consent=True,consent_version=CONSENT_VERSION));self.assertEqual(st,201);self.assertIn('HttpOnly',h['Set-Cookie']);self.assertIn('SameSite=Strict',h['Set-Cookie']);p=json.loads(b)
  body=dict(request_id='http_0001',ratings=[dict(perfume_id=next(iter(self.catalog)),rating=0,experience_type='used')]);st,h,b=self.request('/api/ratings',body,{'X-CSRF-Token':p['csrf']});self.assertEqual(st,200);self.assertTrue(json.loads(b)['saved']);st,h,b=self.request('/api/me');self.assertEqual(len(json.loads(b)['ratings']),1)
 def test_admin_login_redacted(self):
  st,h,b=self.request('/api/admin/login',dict(token=self.store.admin_token));self.assertEqual(st,200);st,h,b=self.request('/api/admin/summary');self.assertEqual(st,200);d=json.loads(b);self.assertNotIn('rating_distribution',d['independent']);self.assertNotIn('auth_hash',b.decode())


class RecoveryAndSeparationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.catalog=load_catalog();cls.ids=list(cls.catalog)
 setUp=CollectionTests.setUp
 tearDown=CollectionTests.tearDown
 body=CollectionTests.body
 save=CollectionTests.save
 def test_sql_transaction_rollback(self):
  role=assign_role(self.p['user_id']);alias='dev'if role=='development'else'holdout'
  with self.s.connection()as c:c.execute(f"CREATE TRIGGER {alias}.fail_rating BEFORE INSERT ON ratings WHEN NEW.rating=9 BEGIN SELECT RAISE(ABORT,'simulated database error'); END")
  b=self.body(7);b['ratings'].append(dict(perfume_id=self.ids[1],rating=9,experience_type='used'))
  with self.assertRaises(sqlite3.IntegrityError):self.save(b)
  self.assertEqual(self.s.own_ratings(self.p['token']),[])
 def test_halfstep_float_is_canonical(self):
  self.save(self.body(7.500000000001));self.assertEqual(self.s.own_ratings(self.p['token'])[0]['rating'],7.5)
 def test_three_ratings_allowed(self):
  b=self.body(7);b['ratings']=[dict(perfume_id=i,rating=7,experience_type='sampled')for i in self.ids[:3]];self.assertEqual(self.save(b)['unique_ratings'],3)

if __name__=='__main__':unittest.main()
