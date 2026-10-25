"""Read-only SHA256 comparison against this stage's pre-change snapshot.

No training/evaluation is invoked. Only a new stage-specific audit JSON is written.
"""
import hashlib
import json
from .adapter import ROOT


def digest(path):
    """path: local file Path; return streaming SHA256 hex digest."""
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    """Compare existing files and 19 frozen hashes; write only this stage's evidence."""
    out = ROOT / 'web/evidence/brand-search'
    before = json.loads((out / 'before.json').read_text())
    missing = [p for p in before if not (ROOT / p).is_file()]
    changed = [p for p, h in before.items()
               if (ROOT / p).is_file() and digest(ROOT / p) != h]
    freeze = json.loads((ROOT / 'outputs/final/freeze.json').read_text())
    checks = {p: digest(ROOT / p) == h
              for p, h in freeze['protected_sha256'].items()}
    manifest = digest(ROOT / 'outputs/final/freeze.json') == before['outputs/final/freeze.json']
    unexpected = sorted(set(changed) - {'web/backend/advanced_search.py'})
    result = dict(snapshot_files=len(before), unchanged=len(before)-len(changed)-len(missing),
                  changed=changed, missing=missing, unexpected_changes=unexpected,
                  frozen_checks=checks, freeze_manifest_unchanged=manifest)
    result['status'] = 'PASS' if not missing and not unexpected and manifest and all(checks.values()) else 'FAIL'
    (out / 'integrity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'frozen_checks'}, ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
