"""Project original frozen state to local standalone assets; no fit, no shared archive.

Reads item mappings and aggregate counts from original metadata locally, but never
exports its users field. Reads Q only from NPZ, never P. Train labels not parsed.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
from .runtime_config import ROOT,ASSET_NAMES,SOURCE_FREEZE_SHA256
from .runtime_loader import sha256
sys.path.insert(0,str(ROOT/'src'))
from perfume.data import fragrantica

def export(directory):
    """directory: new project outputs/ child only; refuse any existing output directory."""
    directory=Path(directory).resolve()
    if ROOT/'outputs' not in directory.parents or directory.exists():raise ValueError('Fresh local outputs directory required')
    freeze_path=ROOT/'outputs/final/freeze.json'
    if sha256(freeze_path)!=SOURCE_FREEZE_SHA256:raise ValueError('Original frozen manifest mismatch')
    freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
    if len(freeze['protected_sha256'])!=19 or not all(sha256(ROOT/p)==h for p,h in freeze['protected_sha256'].items()):raise ValueError('Protected19 mismatch')
    selected={k:freeze['selected'][k] for k in ['mf','profile_mode','alpha','seed','relevance']}
    if selected['mf']['kind']!='legacy':raise ValueError('Bias-free frozen V1 required')
    items=json.loads((ROOT/freeze['candidates_path']).read_text(encoding='utf-8'));assert len(items)==479 and len(set(items))==479
    metadata=json.loads((ROOT/'outputs/final/model.json').read_text(encoding='utf-8'))
    indices=[metadata['items'][i] for i in items]
    with np.load(ROOT/'outputs/final/model.npz',allow_pickle=False) as archive:q=archive['Q'][indices].copy()
    content=json.loads((ROOT/'outputs/final/content.json').read_text(encoding='utf-8'))
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
    runtime={'schema':1,'selected':selected,'items':items,'popularity_counts':{i:metadata['popularity_counts'].get(i,0) for i in items},'popularity_maximum':metadata['popularity_maximum']}
    slim_content={'idf':content['idf'],'vectors':{i:content['vectors'][i] for i in items}}
    slim_catalog={i:{k:catalog[i][k] for k in ['brand','name','tokens']} for i in items}
    # No users, P, individual ratings or full selection/evaluation metadata are exported.
    directory.mkdir(parents=True)
    for name,obj in [('runtime.json',runtime),('content.json',slim_content),('catalog.json',slim_catalog)]:
        with (directory/name).open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,separators=(',',':'))
    with (directory/'item_factors.npy').open('xb') as f:np.save(f,q,allow_pickle=False)
    code=['src/perfume/models.py','src/perfume/improvements.py','src/perfume/data.py','src/perfume/frozen.py','web/backend/adapter.py','web/backend/app.py','web/backend/advanced_search.py','web/backend/search.py','deployment/standalone_v1/runtime_config.py','deployment/standalone_v1/runtime_loader.py','deployment/standalone_v1/app.py']
    manifest={'schema':1,'source_freeze_sha256':SOURCE_FREEZE_SHA256,'sharing':'UNVERIFIED/HOLD: local verification only','files':[{'path':n,'bytes':(directory/n).stat().st_size,'sha256':sha256(directory/n)} for n in ASSET_NAMES],'source_code_sha256':{n:sha256(ROOT/n) for n in code},'projection':'479 item factors/content/catalog; no user records/mapping/P; aggregates still potentially sensitive'}
    with (directory/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
    return {'files':5,'bytes':sum(p.stat().st_size for p in directory.iterdir()),'manifest_sha256':sha256(directory/'manifest.json'),'items':479,'factors':list(q.shape),'user_rows_or_mapping_exported':False,'user_factors_exported':False,'training_calls':0,'sharing':'UNVERIFIED/HOLD'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'outputs/step12_runtime/assets');a=p.parse_args();print(json.dumps(export(a.output),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
