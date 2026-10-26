"""Synthetic-only numerical, contract, failure and data-isolation tests."""
import json
import math
import unittest
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from fastapi.testclient import TestClient
from experiments.synthetic_demo.backend.generate_data import generate
from experiments.synthetic_demo.backend.recommender import Recommender, DATA, tokens
from experiments.synthetic_demo.backend.schemas import Rating
from experiments.synthetic_demo.backend.app import create_app


def ratings(values=(9, 7, 2)):
    return [Rating(perfume_id=i, rating=r) for i, r in zip(('DEMO-001', 'DEMO-014', 'DEMO-038'), values)]

class AlgorithmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Recommender()

    def test_catalog_generation_reproducible(self):
        self.assertEqual(generate(), json.loads(DATA.read_text()))

    def test_80_unique_complete_records(self):
        self.assertEqual(len(self.engine.rows), 80)
        self.assertEqual(set(Counter(r['family'] for r in self.engine.rows.values()).values()), {8})
        self.assertEqual(len({(tuple(sorted(r['notes'])), tuple(sorted(r['accords']))) for r in self.engine.rows.values()}), 80)
        for i, r in self.engine.rows.items():
            self.assertTrue(i.startswith('DEMO-'))
            self.assertEqual(r['notes'], r['top_notes'] + r['middle_notes'] + r['base_notes'])
            self.assertIn('Fictional', r['description'])

    def test_tfidf_norm_and_idf(self):
        for v in self.engine.vectors.values():
            self.assertAlmostEqual(sum(x*x for x in v.values()), 1.0)
        token = next(iter(self.engine.idf))
        df = sum(token in ts for ts in self.engine.features.values())
        self.assertAlmostEqual(self.engine.idf[token], math.log(81/(df+1))+1)

    def test_independent_dense_score_oracle(self):
        rs = ratings(); features = sorted(self.engine.idf)
        # Independent dense dot-product checks signed cosine, not the sorting code.
        dense = lambda i: [self.engine.vectors[i].get(t, 0) for t in features]
        profile = [sum((r.rating-5)/5 * dense(r.perfume_id)[j] for r in rs) for j in range(len(features))]
        norm = math.sqrt(sum(x*x for x in profile))
        for result in self.engine.recommend(rs)['results']:
            expected = sum(a*b for a,b in zip(profile, dense(result['id'])))/norm
            self.assertAlmostEqual(result['score'], expected, places=12)

    def test_deterministic_and_permutation(self):
        a = self.engine.recommend(ratings())
        self.assertEqual(a, self.engine.recommend(ratings()))
        self.assertEqual(a, self.engine.recommend(list(reversed(ratings()))))

    def test_cross_process_hash_seed_reproducibility(self):
        import subprocess, os, sys
        code = "from experiments.synthetic_demo.backend.recommender import Recommender; from experiments.synthetic_demo.backend.schemas import Rating; import json; print(json.dumps(Recommender().recommend([Rating(perfume_id='DEMO-001',rating=9),Rating(perfume_id='DEMO-014',rating=7),Rating(perfume_id='DEMO-038',rating=2)]),sort_keys=True))"
        outputs=[subprocess.check_output([sys.executable,'-B','-c',code],env={**os.environ,'PYTHONHASHSEED':seed},text=True) for seed in ('1','29')]
        self.assertEqual(outputs[0], outputs[1])

    def test_rating_sensitivity(self):
        a=self.engine.recommend(ratings()); b=self.engine.recommend(ratings((2,7,9)))
        self.assertNotEqual([(r['id'],r['score']) for r in a['results']], [(r['id'],r['score']) for r in b['results']])

    def test_dislike_reverses_direction(self):
        # One negative support must prefer less similar items; not positive weights.
        rs=[Rating(perfume_id='DEMO-001',rating=0)]
        out=self.engine.recommend(rs)
        self.assertTrue(all(r['score']<=0 for r in out['results']))
        sim=lambda i:sum(v*self.engine.vectors['DEMO-001'].get(t,0) for t,v in self.engine.vectors[i].items())
        expected=sorted(set(self.engine.rows)-{'DEMO-001'},key=lambda i:(sim(i),i))[:5]
        self.assertEqual([r['id'] for r in out['results']], expected)

    def test_neutral_profile_explicit(self):
        out=self.engine.recommend(ratings((5,5,5)))
        self.assertTrue(all(r['score']==0 for r in out['results']))
        self.assertIn('Neutral',out['notice'])
        self.assertEqual([r['id'] for r in out['results']], sorted(set(self.engine.rows)-{r.perfume_id for r in ratings()})[:5])

    def test_top5_seen_unique_finite(self):
        out=self.engine.recommend(ratings());ids=[r['id'] for r in out['results']]
        self.assertEqual(len(ids),5);self.assertEqual(len(set(ids)),5)
        self.assertFalse(set(ids)&{r.perfume_id for r in ratings()})
        self.assertTrue(all(math.isfinite(r['score']) and -1<=r['score']<=1 for r in out['results']))
        self.assertEqual(out['unseen_count'],77)

    def test_each_filter_and_counts(self):
        for rule,token in [('woody','accord:woody'),('floral','accord:floral'),('rose','note:rose')]:
            with self.subTest(rule=rule):
                out=self.engine.recommend(ratings(),rule)
                self.assertEqual(out['eligible_count'],sum(token in ts and i not in {r.perfume_id for r in ratings()} for i,ts in self.engine.features.items()))
                self.assertTrue(all(token in tokens(r) for r in out['results']))

    def test_combined_filters_and_shortage(self):
        out=self.engine.recommend(ratings(),required_scents=['woody','floral','rose'])
        expected=[i for i,ts in self.engine.features.items() if {'accord:woody','accord:floral','note:rose'}<=ts and i not in {r.perfume_id for r in ratings()}]
        self.assertEqual(out['eligible_count'],len(expected));self.assertEqual(len(out['results']),min(5,len(expected)))
        self.assertLess(len(expected),5);self.assertIn('Only',out['notice'])
        # Exclude all triple-rule survivors as seen: the real catalog can yield zero.
        all_matches=[i for i,ts in self.engine.features.items() if {'accord:woody','accord:floral','note:rose'}<=ts]
        self.assertTrue(all_matches)
        empty=self.engine.recommend([Rating(perfume_id=i,rating=7) for i in all_matches],required_scents=['woody','floral','rose'])
        self.assertEqual(empty['results'],[]);self.assertEqual(empty['eligible_count'],0)
        self.assertIn('Only 0',empty['notice'])

    def test_no_original_imports_or_paths(self):
        # Code-isolation gate: backend imports only stdlib, FastAPI and Pydantic.
        import ast
        allowed={'json','math','pathlib','collections','random','contextlib','logging','os','typing','fastapi','pydantic'}
        for path in (Path(__file__).resolve().parents[1]/'backend').glob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    self.assertTrue(all(a.name.split('.')[0] in allowed for a in node.names))
                if isinstance(node,ast.ImportFrom) and node.level==0:
                    self.assertIn(node.module.split('.')[0],allowed)
        text=DATA.read_text()
        self.assertNotIn('https://',text)
        self.assertNotIn('user_id',text)

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(create_app());self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None)
    def body(self):
        return {'ratings':[r.model_dump() for r in ratings()],'top_k':5}
    def test_health_mode(self):
        body=self.client.get('/api/health').json()
        self.assertEqual(body['mode'],'demo');self.assertEqual(body['data_origin'],'synthetic')
        self.assertTrue(body['recommendation_ready']);self.assertFalse(body['model_loaded']);self.assertEqual(body['candidate_count'],80)
    def test_search_name_brand_notes(self):
        for query,mode in [('DEMO-001','name'),('Imaginary Atelier','name'),('rose','notes')]:
            r=self.client.get('/api/perfumes',params={'q':query,'mode':mode})
            self.assertEqual(r.status_code,200);self.assertTrue(r.json()['results']);self.assertLessEqual(len(r.json()['results']),10)
    def test_search_empty_no_match_special(self):
        for q in ['','no-such-fiction','<script>']:
            self.assertEqual(self.client.get('/api/perfumes',params={'q':q}).status_code,200)
    def test_search_overlong_bad_mode(self):
        self.assertEqual(self.client.get('/api/perfumes',params={'q':'x'*101}).status_code,422)
        self.assertEqual(self.client.get('/api/perfumes?mode=unknown').status_code,422)
    def test_details(self):
        self.assertEqual(self.client.get('/api/perfumes/DEMO-001').json()['id'],'DEMO-001')
        self.assertEqual(self.client.get('/api/perfumes/unknown').status_code,404)
    def test_recommend_contract(self):
        r=self.client.post('/api/recommend',json=self.body());self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['engine'],'content_tfidf_cosine')
        for row in r.json()['results']:
            self.assertTrue({'id','brand','name','notes','accords','rank','score','shared_tokens','required_satisfied','description'}<=row.keys())
    def test_boundary_and_fractional(self):
        for values in [(0,10,7.5),(5,5,5),(0,0,0),(10,10,10)]:
            body={'ratings':[r.model_dump() for r in ratings(values)]}
            self.assertEqual(self.client.post('/api/recommend',json=body).status_code,200)
    def test_invalid_ratings(self):
        for v in [-1,11,'7',True,None,{},[]]:
            with self.subTest(value=v):
                b=self.body();b['ratings'][0]['rating']=v
                self.assertEqual(self.client.post('/api/recommend',json=b).status_code,422)
    def test_nonfinite_and_malformed_json(self):
        for value in ['NaN','Infinity','-Infinity']:
            raw='{"ratings":[{"perfume_id":"DEMO-001","rating":'+value+'}]}'
            self.assertEqual(self.client.post('/api/recommend',content=raw,headers={'Content-Type':'application/json'}).status_code,422)
        self.assertEqual(self.client.post('/api/recommend',content='{bad',headers={'Content-Type':'application/json'}).status_code,422)
    def test_unknown_duplicate_empty(self):
        for rows in [[],[{'perfume_id':'unknown','rating':7}],[{'perfume_id':'DEMO-001','rating':7}]*2]:
            self.assertEqual(self.client.post('/api/recommend',json={'ratings':rows}).status_code,422)
    def test_filter_and_topk_validation(self):
        for field,value in [('required_scent','summer'),('required_scents',['unknown']),('top_k',4),('top_k',5.0),('top_k',True),('extra',1)]:
            b=self.body();b[field]=value;self.assertEqual(self.client.post('/api/recommend',json=b).status_code,422)
    def test_combination_api(self):
        b=self.body();b['required_scents']=['woody','floral','rose']
        out=self.client.post('/api/recommend',json=b).json()
        self.assertLess(len(out['results']),5);self.assertIn('Only',out['notice'])
    def test_count_bounds(self):
        for n,code in [(1,200),(50,200),(51,422)]:
            rows=[{'perfume_id':f'DEMO-{i:03d}','rating':7} for i in range(1,n+1)]
            self.assertEqual(self.client.post('/api/recommend',json={'ratings':rows}).status_code,code)
    def test_internal_error_sanitized(self):
        with patch.object(self.client.app.state.engine,'recommend',side_effect=RuntimeError('PRIVATE-SENTINEL')):
            r=self.client.post('/api/recommend',json=self.body())
        self.assertEqual(r.status_code,500);self.assertNotIn('PRIVATE-SENTINEL',r.text)
    def test_unavailable(self):
        self.client.app.state.engine=None
        self.assertFalse(self.client.get('/api/health').json()['recommendation_ready'])
        self.assertEqual(self.client.get('/api/perfumes').status_code,503)
        self.assertEqual(self.client.post('/api/recommend',json=self.body()).status_code,503)
    def test_cors_and_no_store(self):
        h={'Origin':'http://127.0.0.1:5175','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
        r=self.client.options('/api/recommend',headers=h)
        self.assertEqual(r.status_code,200);self.assertEqual(r.headers['access-control-allow-origin'],h['Origin'])
        h['Origin']='https://untrusted.example';self.assertEqual(self.client.options('/api/recommend',headers=h).status_code,400)
        self.assertEqual(self.client.get('/api/health').headers['cache-control'],'no-store')

if __name__=='__main__':unittest.main(verbosity=2)
