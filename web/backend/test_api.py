"""Synthetic inference-only API checks. Never invoke training/evaluation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import numpy as np
from fastapi.testclient import TestClient
from .app import app
from .adapter import SCENTS, ROOT
from perfume.models import MatrixFactorization, Content, Baseline

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guards = [patch.object(c, 'fit', side_effect=AssertionError('training forbidden'))
                      for c in (MatrixFactorization, Content, Baseline)]
        for g in cls.guards: g.start()
        cls.client = TestClient(app); cls.client.__enter__()
        cls.service = app.state.service
        cls.synthetic = json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())
        cls.body = {'ratings':[{'perfume_id': i, 'rating': r*10} for i,r in cls.synthetic], 'top_k':5}
        cls.arrays = {k: v.copy() for k,v in vars(cls.service.mf).items() if isinstance(v,np.ndarray)}
    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None)
        for g in cls.guards: g.stop()
    def test_health(self):
        self.assertTrue(self.client.get('/api/health').json()['recommendation_ready'])
    def test_search(self):
        a=self.client.get('/api/perfumes?q=DIOR').json()['results']
        self.assertEqual(a,self.client.get('/api/perfumes?q=dior').json()['results'])
        self.assertTrue(0<len(a)<=10)
        self.assertTrue(all(p['id'] in self.service.allowed for p in a))
    def test_search_blank_and_unknown(self):
        for q in ('', 'zzzzzz-nonexistent'):
            self.assertEqual(self.client.get('/api/perfumes',params={'q':q}).json()['results'],[])
    def test_top5_and_fold_in(self):
        result=self.client.post('/api/recommend',json=self.body).json()['results']
        self.assertEqual(len(result),5)
        self.assertEqual(len({r['id'] for r in result}),5)
        self.assertFalse({i for i,_ in self.synthetic}&{r['id'] for r in result})
        self.assertTrue(all(np.isfinite(r['score']) for r in result))
    def test_rules(self):
        for scent in ('woody','floral','rose'):
            with self.subTest(scent=scent):
                response=self.client.post('/api/recommend',json={**self.body,'required_scent':scent})
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.json()['results'])
                for row in response.json()['results']:
                    self.assertIn(SCENTS[scent], self.service.catalog[row['id']]['tokens'])
    def test_exact_cli_parity(self):
        for scent in SCENTS:
            with self.subTest(scent=scent):
                command=[sys.executable,'-B','scripts/demo_frozen.py','--support','demos/stage2/synthetic_woody.json','--k','5']
                if SCENTS[scent]: command+=['--required',SCENTS[scent]]
                original=json.loads(subprocess.check_output(command,cwd=ROOT,text=True))['results']
                web=self.client.post('/api/recommend',json={**self.body,'required_scent':scent}).json()['results']
                self.assertEqual([(r['item'],r['score']) for r in original],[(r['id'],r['score']) for r in web])
    def test_reject_bad_ratings(self):
        for value in (-1,11,'9',True,None,'not-number'):
            with self.subTest(value=value):
                self.assertEqual(self.client.post('/api/recommend',json={'ratings':[{'perfume_id':self.synthetic[0][0],'rating':value}]}).status_code,422)
    def test_nonfinite(self):
        for value in ('NaN','Infinity','-Infinity'):
            raw='{"ratings":[{"perfume_id":'+json.dumps(self.synthetic[0][0])+',"rating":'+value+'}]}'
            self.assertEqual(self.client.post('/api/recommend',content=raw,headers={'Content-Type':'application/json'}).status_code,422)
    def test_request_bounds(self):
        self.assertEqual(self.client.post('/api/recommend',json={'ratings':[self.body['ratings'][0]]*51}).status_code,422)
        self.assertEqual(self.client.get('/api/perfumes',params={'q':'a'*101}).status_code,422)
    def test_duplicates(self):
        self.assertEqual(self.client.post('/api/recommend',json={'ratings':[self.body['ratings'][0]]*2}).status_code,422)
    def test_unknown_id(self):
        self.assertEqual(self.client.post('/api/recommend',json={'ratings':[{'perfume_id':'unknown','rating':7}]}).status_code,422)
    def test_empty(self):
        self.assertEqual(self.client.post('/api/recommend',json={'ratings':[]}).status_code,422)
    def test_low_count_and_zero(self):
        for n in (1,2):
            self.assertEqual(self.client.post('/api/recommend',json={'ratings':self.body['ratings'][:n]}).status_code,200)
        self.assertEqual(self.client.post('/api/recommend',json={'ratings':[{'perfume_id':self.synthetic[0][0],'rating':0}]}).status_code,200)
    def test_fixed_contract(self):
        for override in ({'top_k':10},{'top_k':True},{'required_scent':'price'},{'unexpected':'field'}):
            self.assertEqual(self.client.post('/api/recommend',json={**self.body,**override}).status_code,422)
    def test_cors(self):
        headers={'Origin':'http://127.0.0.1:5173','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type'}
        self.assertEqual(self.client.options('/api/recommend',headers=headers).headers['access-control-allow-origin'],headers['Origin'])
        headers['Origin']='https://unknown.invalid'
        self.assertNotIn('access-control-allow-origin',self.client.options('/api/recommend',headers=headers).headers)
    def test_metadata_only(self):
        r=self.client.get('/api/perfumes?q=dior')
        self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertTrue(all(set(p)=={'id','name','brand','accords','notes'} for p in r.json()['results']))
    def test_shared_intersection(self):
        tokens={t for i,_ in self.synthetic for t in self.service.catalog[i]['tokens']}
        for r in self.client.post('/api/recommend',json=self.body).json()['results']:
            self.assertEqual(r['shared_tokens'],sorted(tokens&set(self.service.catalog[r['id']]['tokens'])))
    def test_unhealthy(self):
        with patch.object(app.state,'service',None):
            self.assertFalse(self.client.get('/api/health').json()['model_loaded'])
            self.assertEqual(self.client.get('/api/perfumes?q=dior').status_code,503)
    def test_z_arrays_unchanged(self):
        self.client.post('/api/recommend',json=self.body)
        for k,v in self.arrays.items():
            np.testing.assert_array_equal(v,getattr(self.service.mf,k))
            self.assertFalse(getattr(self.service.mf,k).flags.writeable)

if __name__=='__main__': unittest.main(verbosity=2)
