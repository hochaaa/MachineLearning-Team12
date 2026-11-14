"""Compare the serverless HTTP boundary with the unchanged presentation app.

Synthetic inputs only: never load training users or external evaluation labels.
"""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.index import app, create_app
from deployment.final_v1.app import create_app as local_app


class ServerlessAPI(unittest.TestCase):
    def test_predictions_equal_local_app_for_all_scents(self):
        with TestClient(app) as deployed, TestClient(local_app()) as local:
            found = local.get('/api/perfumes', params={'q': 'Tom Ford'}).json()['results']
            for scores in ((9, 7, 2), (0, 0, 0), (10, 10, 10), (1, 5, 9)):
                for scent in ('none', 'woody', 'floral', 'rose', 'citrus', 'amber', 'vanilla'):
                    body = {'ratings': [{'perfume_id': row['id'], 'rating': score}
                                        for row, score in zip(found[:3], scores)],
                            'required_scent': scent, 'top_k': 5}
                    expected = local.post('/api/recommend', json=body)
                    actual = deployed.post('/api/recommend', json=body)
                    self.assertEqual(actual.status_code, 200)
                    self.assertEqual(actual.json(), expected.json())

    def test_search_discovery_validation_and_private_files(self):
        with TestClient(app) as client:
            self.assertTrue(client.get('/api/health').json()['recommendation_ready'])
            self.assertEqual(len(client.get('/api/perfumes/discover').json()['results']), 10)
            self.assertTrue(client.get('/api/perfumes', params={'q': 'rose', 'mode': 'notes'}).json()['results'])
            for body in ({'ratings': []}, {'ratings': [{'perfume_id': 'unknown', 'rating': 7}]},
                         {'ratings': [{'perfume_id': 'unknown', 'rating': True}]}):
                response = client.post('/api/recommend', json=body)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
            self.assertEqual(client.post('/api/recommend', content=b' ' * 65537).status_code, 413)
            for path in ('/docs', '/openapi.json', '/outputs/step12_runtime/assets/item_factors.npy'):
                self.assertEqual(client.get(path).status_code, 404)

    def test_modified_assets_fail_readiness(self):
        with patch('api.index.inspect_assets', side_effect=ValueError('modified')):
            with TestClient(create_app()) as client:
                self.assertEqual(client.get('/api/health').status_code, 503)
                self.assertEqual(client.get('/api/perfumes').status_code, 503)


if __name__ == '__main__':
    unittest.main()
