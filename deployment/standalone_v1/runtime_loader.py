"""Load a user-record-free V1 projection; reuse original recommendation/search code.

No original freeze/train/user mapping/P/CSV is read by this loader. New asset
hashes and reused code hashes are verified. Derived assets are NOT cleared for sharing.
"""
import hashlib,json,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from .runtime_config import ROOT,ASSET_NAMES,SOURCE_FREEZE_SHA256,asset_directory
sys.path.insert(0,str(ROOT/'src'))
from perfume.models import MatrixFactorization,Baseline
from perfume.improvements import ProfileContent
from web.backend.adapter import FrozenService
from web.backend.advanced_search import AdvancedCatalogSearch

class RuntimeAssetError(ValueError):
    """Missing, changed or invalid standalone assets; error contains no user records."""

def sha256(path):
    """path: local file; return streaming byte SHA256 without parsing private records."""
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def inspect_assets(directory,expected_manifest_sha256=None):
    """Validate exact four payload names, hashes, sizes and reused-source byte hashes.

    expected_manifest_sha256: optional separately trusted manifest fingerprint. Without
    it this is consistency checking, not a signature or proof of asset authenticity.
    Returns the parsed metadata-only manifest, never loads legacy private files.
    """
    directory=Path(directory).resolve();path=directory/'manifest.json'
    if not path.is_file():raise RuntimeAssetError('Missing standalone manifest')
    if expected_manifest_sha256 and sha256(path)!=expected_manifest_sha256:raise RuntimeAssetError('Manifest fingerprint mismatch')
    try:m=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise RuntimeAssetError('Invalid standalone manifest') from exc
    if m.get('schema')!=1 or m.get('source_freeze_sha256')!=SOURCE_FREEZE_SHA256:raise RuntimeAssetError('Unexpected runtime provenance')
    entries=m.get('files',[])
    if len(entries)!=4 or {e.get('path') for e in entries}!=set(ASSET_NAMES):raise RuntimeAssetError('Unexpected payload inventory')
    for entry in entries:
        name=entry['path'];p=directory/name
        if not p.is_file() or p.is_symlink():raise RuntimeAssetError('Missing standalone payload: '+name)
        if p.stat().st_size!=entry['bytes'] or sha256(p)!=entry['sha256']:raise RuntimeAssetError('Standalone payload fingerprint mismatch: '+name)
    for name,digest in m.get('source_code_sha256',{}).items():
        p=(ROOT/name).resolve()
        if ROOT not in p.parents or not name.endswith('.py') or not p.is_file() or sha256(p)!=digest:raise RuntimeAssetError('Reused source fingerprint mismatch')
    return m

class StandaloneService(FrozenService):
    """Replace initialization only. Inherited recommend/record/search are unchanged.

    directory: new standalone assets. expected_manifest_sha256: optional trusted pin.
    The MF object has Q/items only: no users mapping and no user-factor P.
    """
    def __init__(self,directory=None,expected_manifest_sha256=None):
        directory=asset_directory(directory);self.asset_manifest=inspect_assets(directory,expected_manifest_sha256)
        def read(name):return json.loads((directory/name).read_text(encoding='utf-8'))
        runtime=read('runtime.json');content=read('content.json');catalog=read('catalog.json')
        if set(runtime)!={'schema','selected','items','popularity_counts','popularity_maximum'}:raise RuntimeAssetError('Unexpected runtime metadata fields')
        selected=runtime['selected'];items=runtime['items']
        if len(items)!=479 or len(set(items))!=479 or selected['alpha']!=.25 or selected['mf']['kind']!='legacy' or selected['profile_mode']!='rating':raise RuntimeAssetError('Unexpected frozen inference contract')
        cfg={k:v for k,v in selected['mf'].items() if k!='kind'}
        self.mf=MatrixFactorization(**cfg,seed=selected['seed'])
        q=np.load(directory/'item_factors.npy',allow_pickle=False)
        if q.shape!=(479,self.mf.factors) or q.dtype!=np.float64 or not np.isfinite(q).all():raise RuntimeAssetError('Invalid item factors')
        q.flags.writeable=False;self.mf.Q=q;self.mf.items={i:n for n,i in enumerate(items)}
        self.content=ProfileContent(selected['profile_mode'],selected['relevance']);self.content.idf=content['idf'];self.content.vectors=content['vectors']
        if set(catalog)!=set(items) or set(self.content.vectors)!=set(items) or set(runtime['popularity_counts'])!=set(items):raise RuntimeAssetError('Catalog/content/item alignment mismatch')
        if any(set(row)!={'brand','name','tokens'} for row in catalog.values()):raise RuntimeAssetError('Unexpected catalog fields')
        self.baseline=Baseline();self.baseline.counts=defaultdict(int,runtime['popularity_counts']);self.baseline.maximum=runtime['popularity_maximum']
        self.freeze={'selected':selected};self.catalog=catalog;self.candidates=tuple(items);self.allowed=frozenset(items);self.search_index=AdvancedCatalogSearch(self.candidates,self.catalog)
