"""Demo-only API: explicit synthetic catalog, no rating persistence or ML training."""
from contextlib import asynccontextmanager
import logging
import os
from typing import Literal
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .recommender import Recommender
from .schemas import Recommendation


def create_app():
    """Create isolated app. DEMO_CORS_ORIGINS: comma-separated browser origins."""
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine = None
        try:
            app.state.engine = Recommender()
        except Exception:
            logging.error('Synthetic catalog unavailable; check demo data installation')
        yield
        app.state.engine = None
    app = FastAPI(title='SCENT MATCH — Synthetic Demo', lifespan=lifespan)
    # Official middleware API: https://fastapi.tiangolo.com/tutorial/cors/ (2026-10-26); see demo/REFERENCES.md.
    app.add_middleware(CORSMiddleware, allow_origins=os.getenv(
        'DEMO_CORS_ORIGINS', 'http://127.0.0.1:5175,http://localhost:5175').split(','),
        allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def no_store(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(status_code=422, content={'detail': '입력을 확인하세요: 숫자 평점 0~10, 중복 없는 향수 1~50개, 지원 필터, 정수 Top-5.'})

    def engine(request):
        value = getattr(request.app.state, 'engine', None)
        if value is None:
            raise HTTPException(503, '합성 카탈로그가 준비되지 않았습니다. demo 데이터 파일을 확인하세요.')
        return value

    @app.get('/api/health')
    def health(request: Request):
        value = getattr(request.app.state, 'engine', None)
        return {'mode': 'demo', 'data_origin': 'synthetic', 'engine': 'content_tfidf_cosine',
                'server_running': True, 'model_loaded': False, 'recommendation_ready': value is not None,
                'candidate_count': len(value.rows) if value else 0}

    @app.get('/api/perfumes')
    def search(request: Request, q: str = Query(default='', max_length=100), mode: Literal['name', 'notes'] = 'name'):
        return engine(request).search(q, mode)

    @app.get('/api/perfumes/{perfume_id}')
    def detail(perfume_id: str, request: Request):
        row = engine(request).rows.get(perfume_id)
        if row is None:
            raise HTTPException(404, '가상 향수 ID를 찾을 수 없습니다.')
        return row

    @app.post('/api/recommend')
    def recommend(body: Recommendation, request: Request):
        current = engine(request)
        if any(r.perfume_id not in current.rows for r in body.ratings):
            raise HTTPException(422, '합성 카탈로그에 있는 향수 ID를 선택하세요.')
        try:
            return current.recommend(body.ratings, body.required_scent, body.required_scents)
        except Exception:
            logging.error('Demo recommendation error; request body omitted')
            raise HTTPException(500, '추천 계산 오류입니다. 데모 서버를 확인하고 다시 시도하세요.') from None
    return app
