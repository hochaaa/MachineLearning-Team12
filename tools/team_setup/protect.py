"""STEP10 preservation audit. Byte hashes/stat only; never parses dataset records.

before/after: save separate receipts; exclude only new STEP10 artifacts and
volatile dependency/process directories. Original freeze baseline stays unchanged.
"""
import hashlib,json,subprocess,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/step10_sharing'
SKIP={'.git','.venv','venv','node_modules','__pycache__','dist','.state','logs'}
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(name,obj):
    with (OUT/name).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def freeze():
    p=ROOT/'outputs/final/freeze.json';assert sha(p)=='3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130'
    d=json.loads(p.read_text());assert len(d['protected_sha256'])==19
    assert all(sha(ROOT/p)==s for p,s in d['protected_sha256'].items())
    return {'protected19_match':True,'manifest_sha256':sha(p)}
def snapshot():
    result={}
    for folder,dirs,names in os.walk(ROOT):
        rel=Path(folder).relative_to(ROOT)
        dirs[:]=[d for d in dirs if d not in SKIP and (rel/d).as_posix() not in ['outputs/step10_sharing','tools/team_setup']]
        for n in names:
            p=Path(folder)/n
            if p.is_symlink():continue
            s=p.stat();result[str(p.relative_to(ROOT))]={'sha256':sha(p),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
    return result
def main():
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip();assert branch=='development-v2'
    proof=freeze()
    if sys.argv[1]=='before':save('before.json',{'files':snapshot(),'freeze':proof,'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'step9_metadata_changes_are_preexisting':True});print('BEFORE: frozen19 PASS; STEP9 state preserved, not restored')
    else:
        before=json.loads((OUT/'before.json').read_text())['files'];after=snapshot();changed=[p for p,v in before.items() if after.get(p)!=v]
        save('after.json',{'status':'PASS' if not changed else 'FAIL','files_checked':len(before),'changes':changed,**proof,'branch':branch,'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'tracked_diff':subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True),'staged_diff':subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True)})
        assert not changed,changed;print('AFTER: all original bytes/size/mtime unchanged; frozen19 PASS')
if __name__=='__main__':main()
