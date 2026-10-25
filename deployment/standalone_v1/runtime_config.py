"""Independent V1 runtime paths; no original private asset is a runtime dependency."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ASSET_NAMES=('runtime.json','item_factors.npy','content.json','catalog.json')
SOURCE_FREEZE_SHA256='3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130'
def asset_directory(value=None):
    """value: explicit local asset directory; otherwise env or project-local default."""
    return Path(value or os.getenv('SCENT_MATCH_STANDALONE_ASSETS',str(ROOT/'outputs/step12_runtime/assets'))).resolve()
