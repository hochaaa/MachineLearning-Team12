"""Compare every pre-existing project file with STEP3 baseline; never repair anything."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
baseline = json.loads((root/'web/evidence/before.json').read_text())
changed = []
missing = []
for name, expected in baseline.items():
    path = root/name
    if not path.is_file():
        missing.append(name)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        changed.append(name)
freeze = json.loads((root/'outputs/final/freeze.json').read_text())
protected = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() == expected
             for name, expected in freeze['protected_sha256'].items()}
result = {'baseline_files':len(baseline),'unchanged':len(baseline)-len(changed)-len(missing),
          'changed':changed,'missing':missing,'frozen_checks':protected,
          'status':'PASS' if not changed and not missing and all(protected.values()) else 'FAIL'}
(root/'web/evidence/integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if result['status']=='PASS' else 1)
