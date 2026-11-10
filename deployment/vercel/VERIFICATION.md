# Public deployment verification — 2026-11-10 (Asia/Seoul)

Deployment scope: **PASS**. This record does not audit professor submission or
presentation requirements, and no professor PDF was present in this checkout.

| Item | Observed result |
|---|---|
| Public URL | https://scent-match-team12.vercel.app |
| Target / state | Production / READY |
| Deployment | `dpl_Hsx7joLE9CzT3skYxShoevLs1trA` |
| Source commit | `fa9687da44a05a719d567c30929c55adefcda9ec` |
| Source PR | https://github.com/hochaaa/MachineLearning-Team12/pull/6 |
| Architecture | Vite static CDN + one FastAPI ASGI Python function |
| Runtime / region | Python 3.12, numpy 2.3.5, icn1 (Seoul) |
| Build | Vercel CLI 65.11.0; build completed in 12s; BUILDING→READY 27.3s |
| Model integrity | 5 files / 604,291 bytes; trusted manifest and 11 source hashes PASS |
| Data contract | 479 candidates; Q float64 `(479, 4)`; alpha .25; seven scent filters |
| Secrets | No custom environment variables; no API keys required |
| Runtime error scan | No error/fatal entries for the final deployment in the 10-minute window ending 14:28 KST |
| Monitoring | Vercel runtime logs; no external log drain configured |

## Executed checks

- `python -m unittest discover -s deployment/vercel -p 'test_*.py' -v`: 3 PASS,
  including exact full-response equality with the existing local presentation app
  for 4 synthetic rating profiles × 7 scent conditions (28 comparisons).
- `python -m unittest discover -s deployment/final_v1/tests -p 'test_*.py' -v`:
  27 existing setup/integrity tests PASS.
- `python -m pip check`: no broken requirements.
- `npm ci --prefix web/frontend`; `test:deployment`: 5 PASS;
  `check:production`: same-origin API; `build`: TypeScript and Vite PASS.
- Root requirements delegates to the existing lock; `pyproject.toml` contains
  exactly the same 18 pinned dependencies. Remote build selected pyproject.toml.
- `python -m deployment.vercel.verify_live --base https://scent-match-team12.vercel.app`:
  PASS on both initial and final releases, without authentication/cookies.
  Final release: 28/28 identical recommendation IDs and ranks, maximum absolute
  score difference **1.1102230246251565e-15** (atol 1e-12 / rtol 1e-10).
  Health, English/Korean name search, note search, discovery, invalid input (422),
  64 KiB body limit (413), no-store and model-file isolation all PASS.
- Chrome: public homepage → Find your scent → Tom Ford search → Bitter Peach,
  Black Orchid, Ebene Fume → ratings 9/7/2 → Open to discovery → five displayed
  matches. Rendered results: Xj 1861 Naxos, Coco Noir, Burberry Her, Hacivat,
  Encre Noire A L Extreme. Browser check used the first release; the final release
  has identical frontend/API/model bytes, with root dependency configuration added.
- `git diff --check`: PASS. All existing pinned inference/model files unchanged.

No model fitting, validation tuning, external test evaluation or held-out label
access was performed. Synthetic ratings were used only for inference checks.

## Operational constraints

The short production URL is public. Longer generated/team URLs remain protected
by Vercel Authentication. Model bytes are bundled on the server, not published as
frontend static assets. Ratings are request-local and not saved by the application.
Cold starts can add latency; the UI timeout is 20s and function duration is 30s.
The catalog is the existing 479-item universe; season and price filters are absent.
Ingress counters are per worker and do not provide a distributed quota.

The GitHub integration is not installed on this Vercel account. The release was
uploaded as 34 explicitly selected source/runtime files from the committed branch;
Git pushes do not automatically redeploy. Main is protected and remains unchanged;
PR #6 is open. Merge that PR and connect the existing project to the repository
to enable automatic Git deployments. No branch protections were bypassed.
