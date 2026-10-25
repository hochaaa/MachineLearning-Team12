"""Portable read-only runtime checker; no model import, fitting or file writes.

--root: project directory. --manifest: explicit inventory JSON (default root manifest).
Reports only relative missing/changed paths; never prints file contents or user data.
"""
import argparse,hashlib,json
from pathlib import Path

def verify(root,manifest):
    """root: Path; manifest: dict with files[{path,bytes,sha256,required}]. Return issues."""
    root=root.resolve();issues=[]
    for entry in manifest['files']:
        if not entry['required']:continue
        name=entry['path'];path=(root/name).resolve()
        if Path(name).is_absolute() or root not in path.parents:issues.append({'path':name,'reason':'unsafe_path'});continue
        if not path.is_file():issues.append({'path':name,'reason':'missing'});continue
        h=hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        if path.stat().st_size!=entry['bytes'] or h.hexdigest()!=entry['sha256']:issues.append({'path':name,'reason':'hash_or_size_mismatch'})
    return issues

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--manifest',type=Path);a=p.parse_args()
    manifest=a.manifest or a.root/'RUNTIME_MANIFEST.json'
    try:issues=verify(a.root,json.loads(manifest.read_text(encoding='utf-8')))
    except (OSError,ValueError,KeyError) as exc:print('Runtime manifest unavailable or invalid:',type(exc).__name__);return 2
    print(json.dumps({'status':'PASS' if not issues else 'BLOCKED','issues':issues},ensure_ascii=False,indent=2));return bool(issues)
if __name__=='__main__':raise SystemExit(main())
