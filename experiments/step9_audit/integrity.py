"""STEP9 read-only protection snapshots; hashes only, never parses rating records."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/step9_audit'
MANIFEST='3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130'
SKIP={'.git','.venv','node_modules','__pycache__','dist','.state','logs'}
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def save(name,obj):
    p=OUT/name
    with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def frozen():
    p=ROOT/'outputs/final/freeze.json';assert sha(p)==MANIFEST
    record=json.loads(p.read_text());assert len(record['protected_sha256'])==19
    assert all(sha(ROOT/k)==v for k,v in record['protected_sha256'].items())
    return {'protected_files':19,'all_match':True,'manifest_sha256':MANIFEST}
def snapshot():
    hashes={};stats={}
    for folder in ['src','scripts','tests','configs','web','experiments/development_v2','experiments/development_v3','outputs/final','outputs/improvement','outputs/validation','outputs/development_v2','outputs/development_v3','reports','Term-project-datasets']:
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file() or SKIP&set(p.relative_to(ROOT).parts):continue
            rel=str(p.relative_to(ROOT));s=p.stat()
            stats[rel]={'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
            if folder not in ['Term-project-datasets','outputs/validation']:hashes[rel]=sha(p)
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in {'.md','.txt','.toml'} or p.name=='.gitignore':hashes[str(p.relative_to(ROOT))]=sha(p)
    return {'sha256':hashes,'stat_only':stats,'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),'main':subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip()}
def main():
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='development-v2'
    proof=frozen()
    if sys.argv[1]=='before':
        assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT)
        save('integrity_before.json',snapshot());save('frozen_before.json',proof);print('BEFORE PASS: protected19/manifest; snapshot saved')
    else:
        before=json.loads((OUT/'integrity_before.json').read_text());after=snapshot()
        changed=[p for p,h in before['sha256'].items() if after['sha256'].get(p)!=h]
        stat=[p for p,v in before['stat_only'].items() if after['stat_only'].get(p)!=v]
        assert not changed,changed
        # Report timestamp-only test side effects honestly; do not restore/reset metadata.
        assert before['branch']==after['branch'] and before['main']==after['main']
        assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT)
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT)
        save('integrity_after.json',{'status':'FAIL_METADATA_ONLY' if stat else 'PASS',**proof,'hash_files_checked':len(before['sha256']),'stat_files_checked':len(before['stat_only']),'changed':changed,'stat_changed':stat,'branch':after['branch'],'main':after['main'],'git_status':after['git_status'],'limitations':'Raw data/split files checked by size+mtime; private artifacts byte-hashed without parsing; excluded dependency/cache/log directories.'});print('AFTER: byte content unchanged; metadata changed',len(stat),'files; strict no-change criterion FAILED' if stat else 'PASS')
if __name__=='__main__':main()
