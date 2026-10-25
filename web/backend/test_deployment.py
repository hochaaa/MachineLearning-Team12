"""Synthetic-only production wrapper checks; no ML fits or held-out evaluation."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from .production import create_app, Settings, IngressGuard
from .adapter import ROOT
from web.deployment.preflight import private_path, scan_frontend


class ProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(Settings(('https://frontend.unit-check.dev',), requests_per_minute=10000))
        cls.client = TestClient(cls.app); cls.client.__enter__()
        cls.golden = json.loads((ROOT/'web/evidence/brand-search/recommendations-before.json').read_text())
        support = json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())
        cls.body = {'ratings': [{'perfume_id': i, 'rating': r*10} for i, r in support]}

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_four_condition_parity(self):
        for scent, expected in self.golden.items():
            r = self.client.post('/api/recommend', json={**self.body, 'required_scent': scent})
            self.assertEqual(r.status_code, 200); self.assertEqual(r.json(), expected)

    def test_all_name_and_note_goldens(self):
        for file, mode in [('name-before.json', 'name'), ('notes-before.json', 'notes')]:
            for q, expected in json.loads((ROOT/'web/evidence/brand-search'/file).read_text()).items():
                with self.subTest(q=q, mode=mode):
                    self.assertEqual(self.client.get('/api/perfumes', params={'q': q, 'mode': mode}).json(), expected)

    def test_new_brand_examples_unchanged(self):
        for case in json.loads((ROOT/'web/evidence/brand-search/brand-cases.json').read_text()):
            r = self.client.get('/api/perfumes', params={'q': case['query'], 'mode': 'name'})
            self.assertEqual(r.status_code, case['http_status'])
            if r.status_code == 200:
                data = r.json()
                self.assertEqual([x['id'] for x in data['results']], case['ids'])
                self.assertEqual(data['suggestions'], case['suggestions'])
                self.assertEqual(data.get('hint'), case['hint'])

    def test_cors_exact_allowed_and_denied(self):
        for origin, allowed in [('https://frontend.unit-check.dev', True), ('https://evil.invalid', False),
                                ('http://127.0.0.1:5173', False), ('https://frontend.unit-check.dev.evil.invalid', False)]:
            r = self.client.options('/api/recommend', headers={'Origin': origin,
                'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type'})
            self.assertEqual('access-control-allow-origin' in r.headers, allowed)

    def test_invalid_inputs_safe(self):
        item = self.body['ratings'][0]['perfume_id']
        for payload in [{'ratings': []}, {'ratings': [{'perfume_id': item, 'rating': -1}]},
                        {'ratings': [{'perfume_id': item, 'rating': 11}]},
                        {'ratings': [self.body['ratings'][0]]*2}, {**self.body, 'top_k': 10},
                        {'ratings': [{'perfume_id': 'PRIVATE_UNKNOWN_ID', 'rating': 5}]},
                        {'ratings': self.body['ratings']*20}, {**self.body, 'unexpected': 'secret'}]:
            r = self.client.post('/api/recommend', json=payload)
            self.assertEqual(r.status_code, 422)
            self.assertNotIn('PRIVATE_UNKNOWN_ID', r.text)
            self.assertNotIn('/Users/', r.text)
        self.assertEqual(self.client.post('/api/recommend', content='{INVALID_SECRET', headers={'Content-Type':'application/json'}).status_code, 422)
        self.assertEqual(self.client.get('/api/perfumes', params={'q':'a'*101}).status_code, 422)

    def test_files_and_docs_not_served(self):
        for path in ['/outputs/final/model.npz', '/Term-project-datasets/fra_cleaned.csv',
                     '/.env', '/src/perfume/models.py', '/docs', '/redoc', '/openapi.json']:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_safety_headers(self):
        r = self.client.get('/api/health')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers['cache-control'], 'no-store')
        self.assertEqual(r.headers['x-content-type-options'], 'nosniff')

    def test_oversize_body(self):
        r = self.client.post('/api/recommend', content='x'*65537)
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.headers['cache-control'], 'no-store')

    def test_inference_error_has_no_sensitive_logs(self):
        with patch.object(self.app.state.service, 'recommend', side_effect=RuntimeError('PRIVATE_VALUE /Users/private')):
            with self.assertLogs(level='ERROR') as captured:
                r = self.client.post('/api/recommend', json=self.body)
            self.assertEqual(r.status_code, 500)
            self.assertNotIn('PRIVATE_VALUE', r.text + str(captured.output))
            self.assertNotIn('/Users/', r.text + str(captured.output))

    def test_unhealthy_readiness_503(self):
        with patch.object(self.app.state, 'service', None):
            self.assertEqual(self.client.get('/api/health').status_code, 503)
            self.assertEqual(self.client.get('/api/perfumes?q=dior').status_code, 503)

    def test_restart_loads_same_results(self):
        with TestClient(create_app(Settings(('https://frontend.unit-check.dev',)))) as client:
            self.assertEqual(client.get('/api/health').status_code, 200)
            self.assertEqual(client.post('/api/recommend', json=self.body).json(), self.golden['none'])


class IngressTests(unittest.TestCase):
    def test_production_env_rejects_missing_and_invalid_origins(self):
        for value in ['', '*', 'http://frontend.dev', 'https://u:p@frontend.dev', 'https://frontend.dev/path',
                      'http://127.0.0.1:4173', 'https://YOUR_FRONTEND_DOMAIN']:
            with patch.dict(os.environ, {'WEB_CORS_ORIGINS':value, 'WEB_LOCAL_SIMULATION':'0'}):
                with self.assertRaises(ValueError): Settings.from_environment()

    def test_exact_https_and_explicit_local_simulation(self):
        with patch.dict(os.environ, {'WEB_CORS_ORIGINS':'https://frontend.unit-check.dev','WEB_LOCAL_SIMULATION':'0'}):
            self.assertEqual(Settings.from_environment().origins, ('https://frontend.unit-check.dev',))
        with patch.dict(os.environ, {'WEB_CORS_ORIGINS':'http://127.0.0.1:4173','WEB_LOCAL_SIMULATION':'1'}):
            self.assertEqual(Settings.from_environment().origins, ('http://127.0.0.1:4173',))

    def test_default_budget_and_streamed_body(self):
        async def run():
            async def inner(scope, receive, send):
                await send({'type':'http.response.start','status':200,'headers':[]})
                await send({'type':'http.response.body','body':b'OK'})
            guard = IngressGuard(inner, Settings(('https://frontend.unit-check.dev',)), clock=lambda:100.)
            async def request(chunks=None, headers=None):
                messages = iter(chunks or [{'type':'http.request','body':b'','more_body':False}]); sent=[]
                async def receive(): return next(messages)
                async def send(m): sent.append(m)
                await guard({'type':'http','path':'/api/perfumes','method':'GET','headers':headers or []}, receive, send)
                return sent[0]['status']
            for _ in range(120): self.assertEqual(await request(), 200)
            self.assertEqual(await request(),429)
            guard.recent.clear()
            self.assertEqual(await request([{'type':'http.request','body':b'x'*40000,'more_body':True},
                                            {'type':'http.request','body':b'x'*40000,'more_body':False}]),413)
            self.assertEqual(await request(headers=[(b'content-length',b'bad')]),400)
        asyncio.run(run())

    def test_inflight_limit_and_window_expiry(self):
        async def run():
            from starlette.responses import Response
            async def inner(scope, receive, send): await Response('OK')(scope,receive,send)
            now=[100.]; guard=IngressGuard(inner, Settings(('https://frontend.unit-check.dev',), requests_per_minute=1), clock=lambda:now[0])
            async def request():
                sent=[]
                async def receive(): return {'type':'http.request','body':b''}
                async def send(m): sent.append(m)
                await guard({'type':'http','path':'/api/perfumes','method':'GET','headers':[]},receive,send)
                return sent[0]['status']
            guard.active=8; self.assertEqual(await request(),429)
            guard.active=0; self.assertEqual(await request(),200); self.assertEqual(await request(),429)
            now[0]+=61; self.assertEqual(await request(),200)
        asyncio.run(run())

    def test_failed_startup_does_not_log_paths(self):
        with patch('web.backend.production.local.FrozenService',side_effect=RuntimeError('PRIVATE_STARTUP')):
            with self.assertLogs(level='ERROR') as logs:
                with TestClient(create_app(Settings(('https://frontend.unit-check.dev',)))) as client:
                    self.assertEqual(client.get('/api/health').status_code,503)
            self.assertNotIn('PRIVATE_STARTUP',str(logs.output))

    def test_public_path_policy(self):
        for p in ['outputs/final/model.npz','web/evidence/foo.json','.env.production','data/demo_support.json']:
            self.assertTrue(private_path(p))
        self.assertFalse(private_path('web/frontend/.env.example'))
        self.assertFalse(private_path('web/frontend/src/main.tsx'))

    def test_static_scan_catches_forbidden_content(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); (p/'index.html').write_text('safe')
            self.assertEqual(scan_frontend(p)['status'],'PASS')
            (p/'index.html').write_text('/Users/private')
            self.assertEqual(scan_frontend(p)['flagged_paths'],['index.html'])


if __name__ == '__main__': unittest.main(verbosity=2)
