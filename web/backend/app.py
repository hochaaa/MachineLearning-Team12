"""Stateless local API. No training, evaluation endpoints or rating persistence."""
from contextlib import asynccontextmanager
from typing import Literal
import logging
import os
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .adapter import FrozenService, SCENTS


class Rating(BaseModel):
    """Strict finite numeric web score (0..10), with original catalog URL identity."""
    model_config = ConfigDict(extra='forbid')
    perfume_id: str = Field(min_length=1, max_length=500)
    rating: float = Field(ge=0, le=10, allow_inf_nan=False)

    @field_validator('rating', mode='before')
    @classmethod
    def numeric(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('rating must be a numeric 0..10 value')
        return value


class Recommendation(BaseModel):
    """Bounded request with one existing scent rule and fixed Top-5."""
    model_config = ConfigDict(extra='forbid')
    ratings: list[Rating] = Field(min_length=1, max_length=50)
    required_scent: Literal['none', 'woody', 'floral', 'rose'] = 'none'
    top_k: Literal[5] = 5

    @field_validator('top_k', mode='before')
    @classmethod
    def fixed_k(cls, value):
        if type(value) is not int or value != 5:
            raise ValueError('top_k is fixed at integer 5')
        return value

    @model_validator(mode='after')
    def unique(self):
        if len({r.perfume_id for r in self.ratings}) != len(self.ratings):
            raise ValueError('Duplicate perfume')
        return self


@asynccontextmanager
async def lifespan(app):
    """Integrity-checked singleton load; unhealthy API stays observable on failure."""
    app.state.service = None
    try:
        app.state.service = FrozenService()
    except Exception:
        logging.exception('Frozen model startup failed')
    yield
    app.state.service = None


app = FastAPI(title='SCENT MATCH · Team 12', lifespan=lifespan)
# Uses official CORSMiddleware API; origins are explicit, credentials disabled.
# Reference: https://fastapi.tiangolo.com/tutorial/cors/ (2026-10-22).
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv(
    'WEB_CORS_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173').split(',') if x.strip()],
    allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Do not echo ratings/URLs or non-JSON finite inputs back in error payloads.
    return JSONResponse(status_code=422, content={'detail': '입력을 확인하세요: 평점 0~10, 중복 금지, 고정 Top-5.'})


@app.middleware('http')
async def no_store(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response


def service(request):
    current = getattr(request.app.state, 'service', None)
    if current is None:
        raise HTTPException(503, '동결 모델을 불러오지 못했습니다. 서버 무결성 로그를 확인하세요.')
    return current


@app.get('/api/health')
def health(request: Request):
    ready = getattr(request.app.state, 'service', None) is not None
    return {'server_running': True, 'model_loaded': ready, 'recommendation_ready': ready,
            'candidate_count': 479 if ready else 0}


@app.get('/api/perfumes')
def perfumes(request: Request, q: str = Query(default='', max_length=100), mode: Literal['name', 'notes'] = 'name'):
    return service(request).search_response(q, mode)


@app.post('/api/recommend')
def recommend(body: Recommendation, request: Request):
    current = service(request)
    if any(r.perfume_id not in current.allowed for r in body.ratings):
        raise HTTPException(422, '검색 가능한 동결 후보군의 향수를 선택하세요.')
    try:
        return current.recommend(body.ratings, body.required_scent)
    except Exception:
        logging.exception('Frozen inference failed (request body omitted)')
        raise HTTPException(500, '추천 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.') from None
