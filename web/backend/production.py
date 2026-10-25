"""Separate deployment app: unchanged frozen inference, bounded HTTP ingress.

No account, upload, model conversion or persistence. The local app stays unchanged.
ASGI/CORS interfaces: https://www.starlette.io/middleware/ (2026-10-23).
Original implementation using documented interfaces, not copied middleware code.
"""
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
import os
import re
import time
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from . import app as local


@dataclass(frozen=True)
class Settings:
    """origins: exact CORS origins; bounded ingress values are per worker, not per IP."""
    origins: tuple[str, ...]
    max_body_bytes: int = 65536
    requests_per_minute: int = 120
    max_inflight: int = 8

    @classmethod
    def from_environment(cls):
        """Require explicit origins. HTTP loopback only under explicit local simulation."""
        origins = tuple(x.strip() for x in os.getenv('WEB_CORS_ORIGINS', '').split(',') if x.strip())
        if not origins:
            raise ValueError('Set explicit WEB_CORS_ORIGINS for the deployment app')
        simulation = os.getenv('WEB_LOCAL_SIMULATION') == '1'
        for origin in origins:
            u = urlsplit(origin)
            loopback = u.hostname in ('localhost', '127.0.0.1', '::1')
            if (not u.hostname or u.username or u.password or u.path or u.query or u.fragment
                    or '*' in origin or u.scheme not in ('http', 'https')
                    or 'YOUR_' in origin.upper()
                    or not re.fullmatch(r'[A-Za-z0-9.:-]+', u.hostname or '')
                    or (u.scheme != 'https' and not (simulation and loopback))
                    or (loopback and not simulation)):
                raise ValueError('CORS requires exact HTTPS origins; loopback needs WEB_LOCAL_SIMULATION=1')
        return cls(origins)


class IngressGuard:
    """app: inner ASGI app; settings: limits; clock: injectable monotonic seconds.

    Global rolling-minute budget stores timestamps only (no IP/user/rating logs).
    Read bounded bodies before JSON validation, counting streamed chunks as well.
    Process-local counters are suitable for one worker; no distributed/DDoS guarantee.
    """
    def __init__(self, app, settings, clock=time.monotonic):
        self.app, self.settings, self.clock = app, settings, clock
        self.recent, self.active = deque(), 0

    async def __call__(self, scope, receive, send):
        """scope/receive/send: standard ASGI request interfaces, never logged."""
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        limit = self.settings.max_body_bytes
        try:
            declared = int(headers.get(b'content-length', b'0'))
            if declared < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({'detail': 'Invalid request length.'}, 400)(scope, receive, send)
        if declared > limit:
            return await JSONResponse({'detail': 'Request body too large.'}, 413)(scope, receive, send)
        # Cheap readiness checks do not consume the inference/search budget.
        if scope['method'] != 'OPTIONS' and scope['path'] != '/api/health':
            now = self.clock()
            while self.recent and self.recent[0] <= now - 60:
                self.recent.popleft()
            if len(self.recent) >= self.settings.requests_per_minute or self.active >= self.settings.max_inflight:
                return await JSONResponse({'detail': 'Too many requests.'}, 429,
                                          headers={'Retry-After': '60'})(scope, receive, send)
            self.recent.append(now)
        self.active += 1
        try:
            chunks, size = [], 0
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body = message.get('body', b'')
                size += len(body)
                if size > limit:
                    return await JSONResponse({'detail': 'Request body too large.'}, 413)(scope, receive, send)
                chunks.append(body)
                if not message.get('more_body', False):
                    break
            payload = b''.join(chunks)
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': payload, 'more_body': False}
                return await receive()

            await self.app(scope, bounded_receive, send)
        finally:
            self.active -= 1


def create_app(settings=None):
    """settings: Settings or explicit env validation; factory target for Uvicorn.

    Reuse exact validated API functions, service and arithmetic; expose no file mount
    or documentation endpoints. Invalid configuration stops before any model load.
    """
    settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(app):
        app.state.service = None
        try:
            app.state.service = local.FrozenService()
        except Exception:
            # Do not expose file names, exception text, mappings or ratings in logs.
            logging.error('Frozen startup integrity/load failed; readiness unavailable')
        yield
        app.state.service = None

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_exception_handler(RequestValidationError, local.validation_error)

    @app.get('/api/health')
    def readiness(request: Request):
        result = local.health(request)
        return JSONResponse(result, status_code=200 if result['model_loaded'] else 503)

    app.add_api_route('/api/perfumes', local.perfumes, methods=['GET'])

    @app.post('/api/recommend')
    def recommend(body: local.Recommendation, request: Request):
        current = local.service(request)
        if any(r.perfume_id not in current.allowed for r in body.ratings):
            return JSONResponse({'detail': '검색 가능한 동결 후보군의 향수를 선택하세요.'}, 422)
        try:
            return current.recommend(body.ratings, body.required_scent)
        except Exception:
            logging.error('Frozen inference failed; request body and exception omitted')
            return JSONResponse({'detail': '추천 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.'}, 500)

    # Added in reverse execution order: headers -> CORS -> ingress -> endpoints.
    app.add_middleware(IngressGuard, settings=settings)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.origins), allow_credentials=False,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def safe_headers(request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            logging.error('HTTP handling failed; request and exception omitted')
            response = JSONResponse({'detail': 'Request failed.'}, 500)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer'})
        return response
    return app
