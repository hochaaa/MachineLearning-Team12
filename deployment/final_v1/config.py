"""Stdlib-only configuration, integrity and permission checks; never loads models."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LOCAL = HERE / '.local'
MANIFEST_PIN = 'ff9a748e28cfc723aa972af705c07663827e82b1881291cecd2e5f1985ed3caa'
SOURCE_FREEZE = '3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130'
PAYLOADS = {'catalog.json', 'content.json', 'item_factors.npy', 'runtime.json'}
UI_FILES = ('index.html', 'package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts',
            'src/main.tsx', 'src/style.css', 'scripts/check-production.mjs', 'scripts/check-production.test.mjs')

class SetupError(ValueError):
    """Actionable setup error; no private data/absolute paths in public messages."""


def sha256(path):
    """path: local file; streaming digest without parsing its payload."""
    value = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def assets_path(value=None, root=ROOT):
    """value/env: asset directory; relative paths resolve against project root."""
    p = Path(value or os.getenv('SCENT_MATCH_STANDALONE_ASSETS', 'outputs/step12_runtime/assets')).expanduser()
    return (p if p.is_absolute() else root / p).resolve()


def authorization_path(value=None, root=ROOT):
    """Explicit/env local review path; resolve relative values against project root."""
    value = value or os.getenv('SCENT_MATCH_FINAL_AUTHORIZATION')
    if not value:return None
    p=Path(value).expanduser()
    return (p if p.is_absolute() else root/p).resolve()


def inspect_assets(directory, root=ROOT, expected_pin=MANIFEST_PIN):
    """Read metadata + hash five files and reused source; never parse Q/catalog.

    root/expected_pin are dependency-injection points for synthetic unit fixtures.
    Production CLI and app always use fixed ROOT/MANIFEST_PIN.
    """
    directory = Path(directory)
    manifest = directory / 'manifest.json'
    if not manifest.is_file() or manifest.is_symlink():
        raise SetupError('Missing/nonregular manifest.json. Obtain assets only after permission; no automatic download.')
    if sha256(manifest) != expected_pin:
        raise SetupError('Manifest SHA256 mismatch. Do not regenerate or bypass the trusted pin.')
    try:
        value = json.loads(manifest.read_text(encoding='utf-8'))
        entries = value['files']
        if value['schema'] != 1 or value['source_freeze_sha256'] != SOURCE_FREEZE:
            raise SetupError('Unexpected Frozen V1 provenance.')
        if len(entries) != 4 or {e['path'] for e in entries} != PAYLOADS:
            raise SetupError('Expected exactly four named payloads plus manifest.')
        result = []
        for entry in entries:
            p = directory / entry['path']
            if not p.is_file() or p.is_symlink():
                raise SetupError('Missing/nonregular runtime file: ' + entry['path'])
            if p.stat().st_size != entry['bytes'] or sha256(p) != entry['sha256']:
                raise SetupError('Runtime size/SHA256 mismatch: ' + entry['path'])
            result.append({'name': entry['path'], 'bytes': p.stat().st_size, 'sha256': entry['sha256']})
        sources = value['source_code_sha256']
        if not sources:
            raise SetupError('Missing reused-source fingerprints.')
        for name, digest in sources.items():
            p = (Path(root) / name).resolve()
            if Path(root).resolve() not in p.parents or not name.endswith('.py') or not p.is_file() or sha256(p) != digest:
                raise SetupError('Reused-source SHA256 mismatch; use the reviewed source version.')
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SetupError('Malformed runtime manifest.') from exc
    return {'status': 'PASS', 'files': sorted(result + [{'name': 'manifest.json', 'bytes': manifest.stat().st_size, 'sha256': expected_pin}], key=lambda x:x['name']),
            'total_bytes': manifest.stat().st_size + sum(r['bytes'] for r in result), 'reused_sources': len(sources),
            'model_loaded': False, 'inference_calls': 0}


def authorization(path, purpose='local_inference', today=None):
    """path: manually reviewed local rights record, NOT a rightsholder grant itself.

    Require documented evidence, unexpired review and all assets/scopes. No flag
    enables unverified inference. Do not fabricate this file to unblock execution.
    """
    if purpose not in ('local_inference', 'classroom_demo'):
        raise SetupError('Unsupported execution purpose.')
    if not path or not Path(path).is_file():
        raise SetupError('HOLD: missing reviewed permission evidence. Do not run real inference or share assets.')
    try:
        record = json.loads(Path(path).read_text(encoding='utf-8'))
        scopes = record.get('permitted_actions', [])
        valid = (record.get('schema') == 1 and record.get('status') == 'VERIFIED'
                 and record.get('asset_manifest_sha256') == MANIFEST_PIN
                 and record.get('review_reference', '').strip()
                 and record.get('reviewed_by', '').strip()
                 and isinstance(record.get('evidence_references'),list) and record.get('evidence_references')
                 and all(isinstance(x,str) and x.strip() for x in record['evidence_references'])
                 and set(PAYLOADS) <= set(record.get('covered_payloads', []))
                 and 'local_inference' in scopes and purpose in scopes
                 and date.fromisoformat(record['expires_on']) >= (today or date.today()))
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise SetupError('HOLD: invalid permission review record.') from exc
    if not valid:
        raise SetupError('HOLD: permission review is absent/incomplete/expired or excludes this purpose.')
    return {'status':'VERIFIED_BY_LOCAL_REVIEW','purpose':purpose,'expires_on':record['expires_on']}


def npm_argv(npm=None, node=None, windows=None):
    """Use Node + npm CLI on Windows to avoid cmd.exe quoting/batch ambiguity.

    npm/node/windows overrides are synthetic test dependency-injection only.
    Official Node Windows layout has node_modules/npm/bin/npm-cli.js beside npm.cmd.
    """
    windows = os.name == 'nt' if windows is None else windows
    npm = npm or shutil.which('npm.cmd' if windows else 'npm')
    if not npm:
        raise SetupError('npm missing; install Node.js and reopen terminal.')
    if not windows:return [npm]
    cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'
    node = node or shutil.which('node')
    if not node or not cli.is_file():
        raise SetupError('Unsupported Windows npm layout. Use official Node distribution or documented manual commands.')
    return [node,str(cli)]


def tools():
    """Require bootstrap Python3.12, supported Node, npm; report versions only."""
    if sys.version_info[:2] != (3,12):
        raise SetupError('Use Python 3.12 (macOS python3.12 / Windows py -3.12).')
    node = shutil.which('node'); npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not node or not npm:
        raise SetupError('Node.js/npm not found. Install Node20.20 or supported Node22.12+ and reopen terminal.')
    version = subprocess.check_output([node,'--version'],text=True).strip()
    numbers = tuple(map(int,re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)',version).groups()))
    if not ((numbers[0] == 20 and numbers >= (20,19,0)) or numbers >= (22,12,0)):
        raise SetupError('Unsupported Node version. Use Node20.20 or Node22.12+.')
    return {'python':sys.version.split()[0], 'node':version, 'npm':subprocess.check_output(npm_argv()+['--version'],text=True).strip()}


def python_path(local=LOCAL, windows=None):
    """local: workspace; windows: optional synthetic path-test selector."""
    return Path(local) / 'venv' / ('Scripts/python.exe' if (os.name == 'nt' if windows is None else windows) else 'bin/python')


def check_ui(root=ROOT, local=LOCAL):
    """Compare private local working copy to existing UI byte-for-byte."""
    for name in UI_FILES:
        source=Path(root)/'web/frontend'/name; copy=Path(local)/'frontend'/name
        if not copy.is_file() or sha256(source) != sha256(copy):
            raise SetupError('Frontend copy missing/changed. Run install; never edit original UI to repair setup.')
    return {'status':'PASS','identical_frontend_files':len(UI_FILES)}
