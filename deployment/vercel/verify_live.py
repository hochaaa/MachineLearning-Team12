"""Check a real HTTPS deployment against locally verified Frozen V1 inference.

Run from the repository root with --base https://your-deployment.vercel.app.
No credentials, training users, evaluation labels or local model outputs are sent.
Only synthetic perfume ratings are submitted. Output is aggregate evidence.
"""
import argparse
import json
import math
from urllib.parse import urlsplit

import httpx
from fastapi.testclient import TestClient

from api.index import app


def verify(base):
    """base: deployment HTTPS origin; validate HTML, routes and 28 scoring cases."""
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.path not in ('', '/') or parsed.username:
        raise ValueError('Pass an HTTPS origin without credentials or path')
    max_difference = 0.0
    cases = 0
    with httpx.Client(base_url=base, timeout=45) as remote, TestClient(app) as local:
        page = remote.get('/')
        page.raise_for_status()
        assert 'SCENT MATCH' in page.text
        health = remote.get('/api/health')
        health.raise_for_status()
        assert health.json() == local.get('/api/health').json()
        assert health.json()['candidate_count'] == 479 and health.json()['model_loaded']
        for query, mode in (('Tom Ford', 'name'), ('디올', 'name'), ('rose', 'notes')):
            response = remote.get('/api/perfumes', params={'q': query, 'mode': mode})
            response.raise_for_status()
            assert response.json() == local.get('/api/perfumes', params={'q': query, 'mode': mode}).json()
        found = local.get('/api/perfumes', params={'q': 'Tom Ford'}).json()['results']
        for scores in ((9, 7, 2), (0, 0, 0), (10, 10, 10), (1, 5, 9)):
            for scent in ('none', 'woody', 'floral', 'rose', 'citrus', 'amber', 'vanilla'):
                body = {'ratings': [{'perfume_id': row['id'], 'rating': score}
                                    for row, score in zip(found[:3], scores)],
                        'required_scent': scent, 'top_k': 5}
                response = remote.post('/api/recommend', json=body)
                response.raise_for_status()
                actual = response.json()
                expected = local.post('/api/recommend', json=body).json()
                assert [r['id'] for r in actual['results']] == [r['id'] for r in expected['results']]
                for a, e in zip(actual['results'], expected['results']):
                    max_difference = max(max_difference, abs(a['score'] - e['score']))
                    assert math.isclose(a['score'], e['score'], abs_tol=1e-12, rel_tol=1e-10)
                    assert a['rank'] == e['rank'] and a['required_satisfied']
                assert response.headers['Cache-Control'] == 'no-store'
                cases += 1
        discovery = remote.get('/api/perfumes/discover')
        discovery.raise_for_status()
        assert len(discovery.json()['results']) == 10
        assert remote.post('/api/recommend', json={'ratings': []}).status_code == 422
        assert remote.post('/api/recommend', content=b' ' * 65537).status_code == 413
        # The SPA may return HTML here; model bytes and API docs must not be served.
        for path in ('/outputs/step12_runtime/assets/item_factors.npy', '/api/openapi.json'):
            response = remote.get(path)
            assert response.status_code == 404 or 'text/html' in response.headers.get('Content-Type', '')
    return {'status': 'PASS', 'url': base, 'candidate_count': 479, 'prediction_cases': cases,
            'ids_and_ranks_equal': True, 'max_absolute_score_difference': max_difference,
            'atol': 1e-12, 'rtol': 1e-10, 'training_calls': 0, 'evaluation_labels_read': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    print(json.dumps(verify(parser.parse_args().base), indent=2))
