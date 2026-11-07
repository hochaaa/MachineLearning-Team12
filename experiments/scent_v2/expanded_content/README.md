# V2-18 isolated expanded Content experiment

See `outputs/scent_v2/expanded_content/REPORT.md` and `USAGE_REVIEW.md`. No service integration, fits, tuning or Git changes. Original V2-17 notes/accords/vectors are forbidden. The identity denylist is permitted QC input. New inference notes come only from the hash-verified pinned Scento CC BY 4.0 snapshot.

Use the existing project Python environment (no package installation was performed). Set `PYTHONPATH=src` and `PYTHONDONTWRITEBYTECODE=1`. The local approved ratings path is an argument, never embedded in shared code. Runtime assets and old private fold manifests must already exist locally; this is not a public-data-free reproduction package.

Commands actually used in this task:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.expanded_content.acquire_scento
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.expanded_content.run --csv "$LOCAL_APPROVED_RATINGS"
SCENT_V218_ORIGINAL_CSV="$LOCAL_APPROVED_RATINGS" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m unittest discover -s experiments/scent_v2/expanded_content/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.expanded_content.report
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src deployment/final_v1/.local/venv/bin/python -B -m experiments.scent_v2.expanded_content.verify --snapshot /tmp/scent-v218-before.json --ratings "$LOCAL_APPROVED_RATINGS"
```

`LOCAL_APPROVED_RATINGS` is a placeholder for the authorized local CSV. Main acquisition/run/report/verify create files exclusively; do not rerun into the completed output directory. A future independent version needs its own path and policy. Tests alone may be rerun without rerunning ranking evaluation. The snapshot verifier needs the original pre-task temporary snapshot and presentation copies; their absence is not permission to regenerate a purported pre-task record.

Track A reconstructs historical fold vectors with each fold's stored IDF for exact regression. Main B uses unchanged global Frozen IDF and 479 vectors plus 18 licensed Notes-only vectors. These protocols differ and are not a cross-track accuracy comparison. New-user cohort1 is below the predeclared reporting minimum3; no held-out accuracy, positives, hits or bootstrap CI was computed. The old 75-user cohort has been reused, so its result is regression evidence rather than an independent new final test.
