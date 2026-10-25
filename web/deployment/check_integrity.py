"""Audit only existing-file changes against STEP3-3 snapshot and original 19 hashes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    """path: local Path; return SHA256 without altering model or manifest."""
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def main():
    """Write only this stage's integrity evidence; fail on unauthorized old-file changes."""
    out = ROOT/'web/evidence/safe-deployment'
    before = json.loads((out/'before.json').read_text())
    allowed = {'.gitignore', 'web/frontend/.env.example', 'web/frontend/scripts/check-production.mjs',
               'web/frontend/scripts/check-production.test.mjs', 'web/frontend/vercel.json',
               'web/frontend/tsconfig.tsbuildinfo'}
    missing = [p for p in before if not (ROOT/p).is_file()]
    changed = [p for p,h in before.items() if (ROOT/p).is_file() and digest(ROOT/p)!=h]
    freeze = json.loads((ROOT/'outputs/final/freeze.json').read_text())
    checks = {p: digest(ROOT/p)==h==before[p] for p,h in freeze['protected_sha256'].items()}
    manifest = digest(ROOT/'outputs/final/freeze.json') == before['outputs/final/freeze.json']
    result = {'snapshot_files':len(before), 'unchanged':len(before)-len(missing)-len(changed),
              'changed':changed, 'missing':missing, 'unexpected_changes':sorted(set(changed)-allowed),
              'protected_19':checks, 'freeze_manifest_unchanged':manifest,
              'freeze_manifest_sha256':digest(ROOT/'outputs/final/freeze.json')}
    result['status'] = 'PASS' if not missing and not result['unexpected_changes'] and all(checks.values()) and manifest else 'FAIL'
    (out/'integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='protected_19'},ensure_ascii=False))
    return 0 if result['status']=='PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
