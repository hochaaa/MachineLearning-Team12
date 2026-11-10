# SCENT MATCH on Vercel

Use the **repository root** as the Vercel Root Directory. The root `vercel.json`
builds the existing React/Vite frontend to the CDN and routes `/api/*` to a single
Python 3.12 FastAPI function (`api/index.py`). The framework override is `null` so
Python auto-detection does not replace the frontend build. No beta Services,
containers, external model host, database, credentials or paid add-ons are needed.

Leave `VITE_API_BASE_URL` **unset**: the UI uses the same HTTPS origin for `/api`.
The existing frontend-only `web/frontend/vercel.json` is not used by this project.
Python dependencies in `pyproject.toml` copy the exact existing runtime lock,
including numpy 2.3.5. `.python-version` also selects Python 3.12.

## Frozen predictions and assets

The five existing runtime files total **604,291 bytes**. They remain unchanged,
with manifest SHA256 `ff9a748e28cfc723aa972af705c07663827e82b1881291cecd2e5f1985ed3caa`.
At worker initialization the loader checks this trusted pin, all four payload
hashes/sizes, 11 source hashes, float64 Q shape `(479, 4)` and catalog alignment.
Invalid assets return 503 readiness; there is no demo or retraining fallback.
The 479 candidates, alpha .25, content profiles, ridge fold-in, ranking and seven
scent options are identical to `deployment.final_v1.app`.

Only the model projection already tracked in Git is used. Raw datasets, user
mapping, user-factor P, original training ratings and external held-out labels
are neither needed nor exposed. This deployment does not determine third-party
data rights or modify historical rights statements in the frozen manifest.

## HTTP settings

- Public production website; retain default protection for preview deployments.
- API docs disabled; no file mount, uploads, accounts or saved rating history.
- API responses use `Cache-Control: no-store`; errors omit ratings and exceptions.
- Input remains 1–50 distinct perfumes, numeric 0–10 ratings, fixed Top-5.
- Existing ingress guard limits request bodies to 64 KiB and applies 120 requests
  per rolling minute / 8 in flight per worker. It is best-effort, **not a global
  quota** across independently scaled instances.
- Same-origin requests require no CORS wildcard or browser API key.
- Function max duration is 30 seconds. Cold starts may add latency after idle;
  the frontend currently times requests out after 20 seconds.
- No persistent disk or background training. Vercel usage/plan quotas still apply.

## Verification

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r web/backend/requirements-lock.txt
.venv/bin/python -m unittest discover -s deployment/vercel -p 'test_*.py' -v
npm ci --prefix web/frontend
npm --prefix web/frontend run test:deployment
npm --prefix web/frontend run check:production
npm --prefix web/frontend run build
.venv/bin/python -m deployment.vercel.verify_live --base https://YOUR_DEPLOYMENT.vercel.app
```

The local parity test compares full JSON responses for 28 synthetic profiles /
scent combinations against the existing local presentation app. Live checks
compare IDs/ranks exactly and floating scores at atol 1e-12 / rtol 1e-10 to allow
normal ARM macOS versus x86 Linux numerical differences. They also check health,
name/note search, discovery, validation, body limits and model-file isolation.
These are inference checks, not new validation/test dataset evaluations.

## Methods and sources

`create_app()` in `api/index.py` builds a worker-local FastAPI instance, loading
the immutable service during import instead of relying on ASGI lifespan.
`IngressGuard(app, settings)` is the existing bounded ASGI request wrapper;
`Settings(origins=())` needs no CORS list in this same-origin deployment.
`verify(base)` takes one HTTPS origin, submits synthetic ratings, and compares
remote output with the verified local service. No requests contain credentials.
The pinned source code and model assets are not edited.

Configuration follows official documentation (accessed 2026-11-10); the adapter
and verification code are original implementations using documented interfaces:

- [Vercel Python /api functions](https://vercel.com/docs/functions/runtimes/python/api-directory)
- [Python runtime and bundle configuration](https://vercel.com/docs/functions/runtimes/python)
- [Python version selection](https://vercel.com/docs/functions/runtimes/python/python-version)
- [Vite SPA rewrites](https://vercel.com/docs/frameworks/frontend/vite)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
