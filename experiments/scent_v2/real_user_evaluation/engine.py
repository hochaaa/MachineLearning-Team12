"""Read-only Frozen adapter: receives exactly five Support records, never answers."""
import hashlib,json,re
from types import SimpleNamespace
from deployment.final_v1.config import assets_path,inspect_assets,MANIFEST_PIN
from deployment.standalone_v1.runtime_loader import StandaloneService

class Engine:
    """Load verified runtime5; existing recommend math/UI service remain unchanged."""
    def __init__(self):
        self.integrity=inspect_assets(assets_path());self.service=StandaloneService(assets_path(),MANIFEST_PIN)
        self.catalog={i:dict(id=i,brand=r['brand'],name=r['name']) for i,r in self.service.catalog.items()}
        self.model_version='frozen-v1:'+MANIFEST_PIN
        self.catalog_version=hashlib.sha256(json.dumps(sorted(self.catalog)).encode()).hexdigest()
    def recommend(self,support):
        """support: five canonical(product_id,rating) objects; no response-label input."""
        if len(support)!=5 or len({r['product_id'] for r in support})!=5:raise ValueError('INSUFFICIENT_MATCHED_SUPPORT')
        if any(r['product_id'] not in self.catalog for r in support):raise ValueError('UNSUPPORTED_PRODUCT')
        result=self.service.recommend([SimpleNamespace(perfume_id=r['product_id'],rating=r['rating']) for r in support],'none')['results']
        if len(result)!=5 or len({r['id'] for r in result})!=5:raise ValueError('MODEL_UNAVAILABLE')
        return result


def concentration(name):
    """Only explicit literal catalog tokens; no inferred concentrations or variants."""
    low=name.lower();found=[]
    for key,pattern in [('EDP',r'(?<![a-z])edp(?![a-z])|eau[- ]de[- ]parfum'),('EDT',r'(?<![a-z])edt(?![a-z])|eau[- ]de[- ]toilette'),('Parfum',r'(?<![a-z])parfum(?![a-z])')]:
        if re.search(pattern,low):found.append(key)
    if 'EDP' in found:return 'EDP'
    return found[0] if len(found)==1 else 'CATALOG_UNSPECIFIED'
