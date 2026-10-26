"""Local entry point to unchanged STEP12 inference; integrity checked, no Demo fallback.

This software does not certify data/model use or redistribution rights.
"""
import importlib
from pathlib import Path
from .config import assets_path, inspect_assets, MANIFEST_PIN, SetupError, ROOT


def create_app():
    """Check immutable assets and delegate to the existing standalone factory."""
    assets = assets_path()
    inspect_assets(assets)
    if Path.cwd().resolve() != ROOT:
        raise SetupError('Run the server from the project root.')
    factory = importlib.import_module('deployment.standalone_v1.app').create_app
    return factory(directory=assets, expected_manifest_sha256=MANIFEST_PIN)
