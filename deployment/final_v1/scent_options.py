"""Extend the presentation API with exact accord filters."""
from typing import Literal

from fastapi import Request

from web.backend.app import Recommendation, recommend
from web.backend.adapter import SCENTS


class ExtendedRecommendation(Recommendation):
    required_scent: Literal[
        'none', 'woody', 'floral', 'rose', 'citrus', 'amber', 'vanilla'
    ] = 'none'


def recommend_with_extra_scents(body: ExtendedRecommendation, request: Request):
    return recommend(body, request)


def extend_scent_options(app):
    SCENTS.update({name: f'accord:{name}' for name in ('citrus', 'amber', 'vanilla')})
    original = next(route for route in app.routes if getattr(route, 'endpoint', None) is recommend)
    app.router.routes.remove(original)
    app.add_api_route('/api/recommend', recommend_with_extra_scents, methods=['POST'])
    return app
