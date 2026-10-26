"""Generate runtime metadata inventory only; never copies or shares private assets.

Run from original root before approval. Hashes bytes, never parses user records.
"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    freeze=json.loads((ROOT/'outputs/final/freeze.json').read_text());protected=set(freeze['protected_sha256'])
    paths=protected|{'outputs/final/freeze.json','web/backend/app.py','web/backend/adapter.py','web/backend/search.py','web/backend/advanced_search.py','web/backend/requirements.txt','web/backend/requirements-lock.txt','web/frontend/package.json','web/frontend/package-lock.json','web/frontend/tsconfig.json','web/frontend/vite.config.ts','web/frontend/index.html','web/frontend/.env.example'}
    paths|={str(p.relative_to(ROOT)) for p in (ROOT/'web/frontend/src').rglob('*') if p.is_file()}
    tracked={p.decode() for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0') if p}
    result=[]
    for name in sorted(paths):
        path=ROOT/name;private=name.startswith(('outputs/','Term-project-datasets/'))
        ignored=subprocess.run(['git','check-ignore','-q',name],cwd=ROOT).returncode==0
        role='freeze byte integrity dependency' if name in protected else 'web source or dependency installation'
        if name.endswith('freeze.json'):role='original protected-path and selection manifest'
        if name.endswith('model.npz'):role='fixed learned V1 factors'
        if name.endswith('model.json'):role='user/item mappings and frozen popularity statistics; private'
        if name.endswith('content.json'):role='frozen IDF and item vectors'
        if name.endswith('train_exclude_3.json'):role='pseudonymous individual ratings; hash check only at runtime; private'
        if name.endswith('fra_cleaned.csv'):role='display metadata and search catalog'
        if name.endswith('candidates.json'):role='479 allowed perfume IDs'
        if name.endswith('selection.json'):role='selected model settings; hash check dependency'
        result.append({'path':name,'filename':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'purpose':role,'required':not name.endswith('.env.example'),'git_tracked':name in tracked,'git_ignored':ignored,'sharing':'HOLD: local-use only; private team transfer not approved' if private else 'source candidate; review before staging','placement':name,'private_runtime':private})
    manifest={'schema':1,'service':'Frozen V1 Hybrid only','freeze_sha256':'3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130','permission':'User confirmed local use only; separate transfer on hold','packaged':False,'absolute_paths':False,'files':result}
    with (ROOT/'RUNTIME_MANIFEST.json').open('x') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
    print('Manifest only:',len(result),'entries, private runtime',sum(r['private_runtime'] for r in result),'files,',sum(r['bytes'] for r in result if r['private_runtime']),'bytes. No package created.')
if __name__=='__main__':main()
