"""Vercel ASGI entrypoint; initialize the verified, immutable service per worker.

Vercel imports this module on a cold start. Initialization deliberately does not
depend on ASGI lifespan, which is not guaranteed by all serverless adapters.
No training files, external downloads, writable disk or credentials are needed.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from deployment.final_v1.config import MANIFEST_PIN, ROOT, inspect_assets
from deployment.final_v1.scent_options import ExtendedRecommendation
from deployment.standalone_v1.runtime_loader import StandaloneService
from web.backend import app as original
from web.backend.adapter import SCENTS
from web.backend.discovery import add_discovery_route
from web.backend.production import IngressGuard, Settings


def create_app():
    """Load bundled assets with the existing trusted pin, then register API routes.

    An invalid asset fails readiness with 503 and is never replaced by a demo.
    The loaded service is read-only; fold-in vectors remain request-local.
    """
    api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    api.state.service = None
    try:
        directory = ROOT / 'outputs/step12_runtime/assets'
        inspect_assets(directory)
        api.state.service = StandaloneService(directory, MANIFEST_PIN)
    except Exception:
        logging.error('Frozen inference assets failed integrity/load checks.')

    # Match the current presentation app, including its three added accord rules.
    SCENTS.update({name: f'accord:{name}' for name in ('citrus', 'amber', 'vanilla')})
    api.add_exception_handler(RequestValidationError, original.validation_error)

    @api.get('/api/health')
    def readiness(request: Request):
        result = original.health(request)
        return JSONResponse(result, status_code=200 if result['model_loaded'] else 503)

    api.add_api_route('/api/perfumes', original.perfumes, methods=['GET'])
    add_discovery_route(api)

    @api.post('/api/recommend')
    def recommend(body: ExtendedRecommendation, request: Request):
        current = original.service(request)
        if any(row.perfume_id not in current.allowed for row in body.ratings):
            return JSONResponse({'detail': '검색 가능한 동결 후보군의 향수를 선택하세요.'}, status_code=422)
        try:
            return current.recommend(body.ratings, body.required_scent)
        except Exception:
            logging.error('Frozen inference failed; request and exception omitted.')
            return JSONResponse({'detail': '추천 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.'}, status_code=500)

    # Same-origin frontend: no CORS configuration or cross-origin API secret.
    # Counters are best-effort per worker, not a distributed rate limit.
    api.add_middleware(IngressGuard, settings=Settings(origins=()))

    @api.middleware('http')
    async def safe_headers(request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            logging.error('API request failed; request and exception omitted.')
            response = JSONResponse({'detail': 'Request failed.'}, status_code=500)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer'})
        return response

    return api


app = create_app()
