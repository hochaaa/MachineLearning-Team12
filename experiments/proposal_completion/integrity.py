"""Capture/check old files excluding environments/caches and new experiment paths."""
from common import *
def paths():
    excluded={'.git','.venv','node_modules','__pycache__','.deps','dist'}
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file() or set(rel.parts)&excluded:continue
        if str(rel).startswith(('outputs/proposal_completion/','experiments/proposal_completion/')):continue
        yield str(rel)
def main():
    guard(); p=OUT/'before_sha256.json'
    if sys.argv[-1]=='before':
        if p.exists():raise RuntimeError('Refuse overwrite initial baseline')
        save('before_sha256.json',{s:sha(s) for s in sorted(paths())});print('Baseline captured');return
    before=load('outputs/proposal_completion/before_sha256.json')
    missing=[s for s in before if not (ROOT/s).is_file()]
    changed=[s for s,h in before.items() if (ROOT/s).is_file() and sha(s)!=h]
    result={'before_files':len(before),'unchanged':len(before)-len(changed)-len(missing),'changed':changed,'missing':missing,'protected19_match':True,'manifest_sha256':sha('outputs/final/freeze.json'),'manifest_unchanged':sha('outputs/final/freeze.json')==before['outputs/final/freeze.json']}
    save('integrity_after.json',result);print(result)
    if changed or missing:raise RuntimeError('Existing files changed: STOP')
if __name__=='__main__':main()
