"""Read-only independent runtime preflight; never reads original private runtime."""
import argparse,json,platform,sys
from pathlib import Path
from .runtime_loader import StandaloneService,RuntimeAssetError,sha256
from .runtime_config import asset_directory

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',type=Path);p.add_argument('--expected-manifest-sha256');a=p.parse_args();directory=asset_directory(a.assets)
    try:s=StandaloneService(directory,a.expected_manifest_sha256)
    except (OSError,ValueError,KeyError) as exc:print(json.dumps({'status':'BLOCKED','reason':type(exc).__name__,'detail':'Missing/changed/invalid local assets; do not bypass fingerprints.'}));return 1
    print(json.dumps({'status':'PASS','python':platform.python_version(),'candidate_count':len(s.candidates),'shape':list(s.mf.Q.shape),'no_users_mapping':not hasattr(s.mf,'users'),'no_user_factors':not hasattr(s.mf,'P'),'manifest_sha256':sha256(directory/'manifest.json'),'sharing':'UNVERIFIED/HOLD'},ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
