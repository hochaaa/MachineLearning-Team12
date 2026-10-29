"""Synthetic catalog tests for browse diversity and unchanged search contract."""
import random
import unittest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from fastapi import FastAPI
from .discovery import discover, add_discovery_route
app = add_discovery_route(FastAPI())


def fixture():
    catalog = {f'{b}-{n}': {'brand': f'Brand {b}', 'name': f'Perfume {n}',
                           'accords': ['woody' if n == 0 else 'floral'], 'notes': []}
               for b in range(12) for n in range(2)}
    return SimpleNamespace(allowed=frozenset(catalog), catalog=catalog,
                           record=lambda i: {'id': i, **catalog[i]})


class DiscoveryTests(unittest.TestCase):
    def test_fixed_candidates_unique_and_brand_variety(self):
        current = fixture()
        result = discover(current, rng=random.Random(4))['results']
        self.assertEqual(len(result), 10)
        self.assertEqual(len({r['id'] for r in result}), 10)
        self.assertEqual(len({r['brand'] for r in result}), 10)
        self.assertTrue(all(r['id'] in current.allowed for r in result))
        self.assertEqual({a for r in result for a in r['accords']}, {'woody', 'floral'})
    def test_shuffle_and_immutable_catalog(self):
        current = fixture(); original = repr(current.catalog)
        a = discover(current, rng=random.Random(1))
        b = discover(current, rng=random.Random(2))
        self.assertNotEqual(a, b)
        self.assertEqual(repr(current.catalog), original)
    def test_small_catalog_and_empty(self):
        current = fixture(); current.allowed = frozenset(['0-0', '0-1'])
        self.assertEqual(len(discover(current)['results']), 2)
        current.allowed = frozenset()
        self.assertEqual(discover(current)['results'], [])
    def test_endpoint_uses_loaded_service_without_inference(self):
        old = getattr(app.state, 'service', None)
        try:
            app.state.service = fixture()
            response = TestClient(app).get('/api/perfumes/discover')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()['results']), 10)
            self.assertEqual(response.headers['cache-control'], 'no-store')
        finally: app.state.service = old
    def test_unavailable_service(self):
        old = getattr(app.state, 'service', None)
        try:
            app.state.service = None
            self.assertEqual(TestClient(app).get('/api/perfumes/discover').status_code, 503)
        finally: app.state.service = old
