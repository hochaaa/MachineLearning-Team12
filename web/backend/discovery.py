"""Unpersonalized catalog browsing; no inference, rating access or model changes."""
import random
from collections import defaultdict


def discover(current, limit=10, rng=None):
    """Sample fixed candidates across brands, preferring new primary accords.

    current is the existing loaded service. rng is injectable for deterministic
    tests; production uses SystemRandom. No global seed/state or catalog mutation.
    This is a browsing sample, not a personalized recommendation or a uniform draw.
    """
    rng = rng or random.SystemRandom()
    brands = defaultdict(list)
    for item in sorted(current.allowed):
        brands[current.catalog[item]['brand']].append(item)
    pools = list(brands.values())
    rng.shuffle(pools)
    for pool in pools:
        rng.shuffle(pool)
    results, seen_accords = [], set()
    while pools and len(results) < limit:
        remaining = []
        for pool in pools:
            position = next((n for n, item in enumerate(pool)
                             if current.record(item)['accords'] and current.record(item)['accords'][0] not in seen_accords), 0)
            record = current.record(pool.pop(position))
            results.append(record)
            seen_accords.update(record['accords'][:1])
            if pool:
                remaining.append(pool)
            if len(results) == limit:
                break
        pools = remaining
    return {'results': results}


def add_discovery_route(app):
    """Extend a verified app without changing integrity-pinned original route code."""
    from fastapi import Request, Response
    from .app import service

    def browse(request: Request, response: Response):
        response.headers['Cache-Control'] = 'no-store'
        return discover(service(request))

    app.add_api_route('/api/perfumes/discover', browse, methods=['GET'])
    return app
