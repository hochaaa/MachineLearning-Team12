"""Explicit interaction schema only; reviews and aggregate ratings are not labels."""
import csv, json
from pathlib import Path
from .license_audit import verified_file

def read_original(path, evidence):
    """Read approved CSV/JSON/JSONL without remote loaders or executable scripts.

    Caller must explicitly map source columns to the canonical schema. No raw
    comments, names or profile URLs are carried to the processed representation.
    """
    verified_file(path, evidence)
    path = Path(path)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        if path.suffix == '.csv': rows = list(csv.DictReader(stream))
        elif path.suffix == '.json': rows = json.load(stream)
        elif path.suffix == '.jsonl': rows = [json.loads(x) for x in stream if x.strip()]
        else: raise ValueError('Unsupported format; no package or remote-code installation')
    if not isinstance(rows, list): raise ValueError('Expected records list')
    return rows

def validate(row):
    """Canonical row needs real user/item IDs, product brand/name and explicit rating."""
    if row.get('is_synthetic') is not False or row.get('explicit_rating') is not True:
        raise ValueError('Real explicit-rating provenance required')
    for k in ('user_id', 'item_id', 'brand', 'name'):
        if not isinstance(row.get(k), str) or not row[k].strip():
            raise ValueError('Missing canonical string: ' + k)
    if row.get('role') == 'independent' or row.get('source_kind') in ('aggregate', 'sentiment', 'generated'):
        raise ValueError('Independent evaluation or non-interaction input')
    if 'rating' not in row: raise ValueError('Missing rating field')
