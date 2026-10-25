"""Read-only old-file/frozen audit; show Finder metadata separately, never hide it."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def main():
    """Write new final-demo integrity.json; never changes source/data/model hashes."""
    out=ROOT/'web/evidence/final-demo'
    before=json.loads((out/'before.json').read_text())
    missing=[p for p in before if not (ROOT/p).is_file()]
    changed=[p for p,h in before.items() if (ROOT/p).is_file() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    metadata=[p for p in changed if Path(p).name=='.DS_Store']
    freeze=json.loads((ROOT/'outputs/final/freeze.json').read_text())
    protected={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h==before[p]
               for p,h in freeze['protected_sha256'].items()}
    manifest=hashlib.sha256((ROOT/'outputs/final/freeze.json').read_bytes()).hexdigest()
    result={'snapshot_files':len(before),'unchanged':len(before)-len(changed)-len(missing),'changed':changed,
            'missing':missing,'platform_metadata_changes':metadata,
            'unexpected_changes':sorted(set(changed)-{'.gitignore'}-set(metadata)),'protected19':protected,
            'freeze_manifest_sha256':manifest,'manifest_unchanged':manifest==before['outputs/final/freeze.json']}
    result['status']='PASS' if not missing and not result['unexpected_changes'] and all(protected.values()) and result['manifest_unchanged'] else 'FAIL'
    (out/'integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='protected19'},ensure_ascii=False))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
