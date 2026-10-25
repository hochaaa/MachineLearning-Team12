"""Offline public-frontend and Git path inspection, not permission or secret clearance.

No upload, no Git mutation. JSON reports contain paths/counts only, not file contents.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def private_path(name):
    """name: repository-relative path; conservative deny policy for public source."""
    p = Path(name)
    return (any(x in p.parts for x in ('Term-project-datasets', 'outputs', 'evidence', '.venv', '.deps', 'node_modules', 'private-assets'))
            or p.suffix.lower() in ('.npz', '.csv', '.zip')
            or (p.name.startswith('.env') and p.name != '.env.example')
            or p.name in ('model.json', 'content.json', 'demo_support.json'))


def scan_frontend(directory):
    """directory: built static root. Return only flagged paths, bytes/count and digest."""
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    bad, digest = [], hashlib.sha256()
    markers = (b'/Users/', b'Term-project-datasets', b'train_exclude_', b'BEGIN PRIVATE KEY',
               b'BEGIN RSA PRIVATE KEY', b'"protected_sha256"', b'"popularity_counts"')
    for p in files:
        data = p.read_bytes()
        relative = str(p.relative_to(directory))
        digest.update(relative.encode()); digest.update(data)
        if p.is_symlink() or private_path(relative) or any(x in data for x in markers):
            bad.append(relative)
    return {'files': len(files), 'bytes': sum(p.stat().st_size for p in files),
            'flagged_paths': bad, 'content_sha256': digest.hexdigest(),
            'status': 'PASS' if files and not bad else 'FAIL',
            'limits': 'Conservative path/marker scan only; not exhaustive secret, PII or license clearance.'}


def git_inspection():
    """Inspect tracked and all-ref historical file paths. Never print blob contents."""
    probe = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, capture_output=True, text=True)
    if probe.returncode or Path(probe.stdout.strip()).resolve() != ROOT:
        return {'status': 'BLOCKED', 'reason': 'No Git repository at project root; tracked files and history cannot be cleared.'}
    current = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, capture_output=True).stdout.decode().split('\0')
    history = subprocess.run(['git', 'log', '--all', '--format=', '--name-only', '-z'], cwd=ROOT, check=True, capture_output=True).stdout.decode().split('\0')
    tracked = sorted({n.strip() for n in current if n.strip() and private_path(n.strip())})
    historical = sorted({n.strip() for n in history if n.strip() and private_path(n.strip())})
    return {'status': 'FAIL' if tracked or historical else 'PASS', 'tracked_flagged_paths': tracked,
            'historical_flagged_paths': historical, 'limits': 'Path policy only; blob contents/other refs/backups need a dedicated secret/PII review.'}


def main():
    """--dist: alternate local build; --output: audit JSON destination. No network."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=ROOT/'web/frontend/dist')
    parser.add_argument('--output', type=Path, default=ROOT/'web/evidence/safe-deployment/preflight.json')
    args = parser.parse_args()
    result = {'frontend': scan_frontend(args.dist), 'git': git_inspection(),
              'data_hosting_rights': 'NEEDS VERIFICATION', 'public_deployment': 'BLOCKED'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['frontend']['status'] == result['git']['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
