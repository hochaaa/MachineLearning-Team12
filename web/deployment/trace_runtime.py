"""Record project file opens by stage without recording contents, user IDs or ratings.

CPython audit event API: https://docs.python.org/3/library/sys.html#sys.addaudithook
(2026-10-23). Original observation code; not a security sandbox.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STAGE = 'imports'
READS = {}


def observe(event, args):
    """event/args: CPython audit hook data. Keep unique relative read paths only."""
    if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    try:
        p = Path(os.fsdecode(args[0])).resolve()
        relative = p.relative_to(ROOT)
    except (ValueError, OSError):
        return
    if any(x in relative.parts for x in ('.venv', '__pycache__', 'node_modules', '.deps')):
        return
    mode = args[1]
    if isinstance(mode, str) and any(c in mode for c in 'wa+'):
        return
    READS.setdefault(STAGE, set()).add(str(relative))


def main():
    """Observe unmodified loader and synthetic-only search/inference, write new evidence."""
    global STAGE
    sys.addaudithook(observe)
    from web.backend.adapter import FrozenService
    from web.backend.app import Rating
    STAGE = 'startup_load_hash_catalog_search_index'
    start = time.perf_counter()
    service = FrozenService()
    seconds = time.perf_counter() - start
    STAGE = 'synthetic_fixture_read'
    support = json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())
    ratings = [Rating(perfume_id=i, rating=r*10) for i, r in support]
    STAGE = 'search'
    service.search_response('톰포 Black Orchid')
    service.search_response('바니라', 'notes')
    STAGE = 'fold_in_hybrid_rules_top5'
    results = {s: service.recommend(ratings, s) for s in ('none', 'woody', 'floral', 'rose')}
    STAGE = 'complete'
    before = json.loads((ROOT/'web/evidence/brand-search/recommendations-before.json').read_text())
    assert results == before
    output = {'method': 'CPython open audit events; unique project paths, no contents',
              'startup_seconds': seconds, 'stages': {s: sorted(paths) for s, paths in READS.items()},
              'recommendations_identical': True, 'search_and_inference_additional_file_reads':
              sorted(READS.get('search', set()) | READS.get('fold_in_hybrid_rules_top5', set())),
              'limits': 'Python open events only; not full OS syscalls or native-library tracing. Existing files unchanged.'}
    out = ROOT/'web/evidence/safe-deployment'
    (out/'runtime-trace.json').write_text(json.dumps(output, ensure_ascii=False, indent=2))
    (out/'recommendations-after.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
