"""Independent optional ASGI app. Existing web.backend.app remains unchanged.

Only initialization differs; request models, route functions, validation errors,
CORS and no-store middleware are reused from the existing local V1 web app.
"""
from contextlib import asynccontextmanager
import logging,os
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from web.backend import app as original
from .runtime_loader import StandaloneService
from .runtime_config import asset_directory

def create_app(directory=None,expected_manifest_sha256=None):
    """directory: local standalone payload; optional manifest pin from trusted review.

    Defaults use SCENT_MATCH_STANDALONE_ASSETS and optional
    SCENT_MATCH_STANDALONE_MANIFEST_SHA256. No legacy loader monkeypatch or endpoint change.
    """
    directory=asset_directory(directory);pin=expected_manifest_sha256 or os.getenv('SCENT_MATCH_STANDALONE_MANIFEST_SHA256')
    @asynccontextmanager
    async def lifespan(app):
        app.state.service=None
        try:app.state.service=StandaloneService(directory,pin)
        except Exception:logging.error('Standalone assets unavailable; inspect local preflight; request data omitted')
        yield
        app.state.service=None
    app=FastAPI(title='SCENT MATCH · Team 12',lifespan=lifespan)
    app.add_exception_handler(RequestValidationError,original.validation_error)
    for middleware in reversed(original.app.user_middleware):app.add_middleware(middleware.cls,*middleware.args,**middleware.kwargs)
    app.add_api_route('/api/health',original.health,methods=['GET'])
    app.add_api_route('/api/perfumes',original.perfumes,methods=['GET'])
    app.add_api_route('/api/recommend',original.recommend,methods=['POST'])
    return app
