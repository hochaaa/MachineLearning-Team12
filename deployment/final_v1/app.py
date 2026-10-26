"""Guarded entry point to the unchanged STEP12 app, with no fallback to Demo."""
import importlib
import os
from pathlib import Path
from .config import authorization, authorization_path, assets_path, inspect_assets, MANIFEST_PIN, SetupError, ROOT


def create_app():
    """Fail before importing the model loader unless local permissions are reviewed."""
    authorization(authorization_path(), os.getenv('SCENT_MATCH_FINAL_PURPOSE','local_inference'))
    assets=assets_path()
    inspect_assets(assets)
    if Path.cwd().resolve() != ROOT:
        raise SetupError('Run the guarded server from the project root.')
    # Same original factory/route functions; no subclass or changed arithmetic here.
    factory=importlib.import_module('deployment.standalone_v1.app').create_app
    return factory(directory=assets, expected_manifest_sha256=MANIFEST_PIN)
