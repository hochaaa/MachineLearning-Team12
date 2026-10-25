"""Private raw-data adapters and conservative catalog matching."""
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


def read_json(path):
    """Read UTF-8 JSON from path; callers validate expected fields."""
    with open(path, encoding='utf-8-sig') as stream:
        return json.load(stream)


def write_json(path, value):
    """Write serializable value to path, creating parent directories."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def write_csv(path, rows):
    """Write records sharing column names; empty rows produce an empty file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def normalize(text):
    """Normalize accents, punctuation and spacing, preserving version words/numbers."""
    text = ''.join(c for c in unicodedata.normalize('NFKD', str(text)).casefold()
                   if not unicodedata.combining(c))
    # Concentrations become equivalent tokens, never disappear.
    for phrase, token in [('eau de parfum', 'edp'), ('eau de toilette', 'edt'),
                          ('eau de cologne', 'edc')]:
        text = text.replace(phrase, token)
    return ' '.join(re.findall(r'[^\W_]+', text, flags=re.UNICODE))


def identity(brand, name):
    """Return exact normalized brand/name key without fuzzy or brand alias merges."""
    return normalize(brand), normalize(name)


def tokens(row):
    """Read comma-separated note phrases and accord values; ignore missing sentinels."""
    result = set()
    for key in ['Top', 'Middle', 'Base']:
        for value in row.get(key, '').split(','):
            value = normalize(value)
            if value not in ('', 'unknown', 'nan', 'na'):
                result.add('note:' + value)
    for key in [f'mainaccord{i}' for i in range(1, 6)]:
        value = normalize(row.get(key, ''))
        if value not in ('', 'unknown', 'nan', 'na'):
            result.add('accord:' + value)
    return sorted(result)


def fragrantica(path):
    """Parse semicolon CSV; use original URL as persistent item identity."""
    with open(path, encoding='cp1252', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter=';'))
    if not rows or not {'Perfume', 'Brand', 'Top', 'url'} <= rows[0].keys():
        raise ValueError('Unexpected Fragrantica schema')
    catalog = {}
    for row in rows:
        item = row['url']
        if item in catalog:
            raise ValueError('Duplicate Fragrantica URL requires review')
        catalog[item] = {'name': row['Perfume'], 'brand': row['Brand'], 'tokens': tokens(row)}
    return catalog, rows


def matcher(catalog):
    """Index all catalog keys; collision remains ambiguous rather than taking first."""
    index = defaultdict(list)
    for item, row in catalog.items():
        index[identity(row['brand'], row['name'])].append(item)
    return index


def match(index, brand, name):
    """Return (item or None, status); exact unique keys only are accepted."""
    hits = index.get(identity(brand, name), [])
    return (hits[0], 'accepted') if len(hits) == 1 else (None, 'ambiguous' if hits else 'rejected')


def atrafshan(path, zero_policy='unresolved'):
    """Extract unique user/item scent ratings. zero_policy is include/exclude/unresolved.

    Conflicting duplicate scores are excluded, not averaged; equal duplicates collapse.
    User identifiers are namespaced SHA256 pseudonyms; names/comments never leave adapter.
    unresolved is prohibited for model inputs; audit runs explicit sensitivity scenarios.
    """
    if zero_policy not in ('include', 'exclude'):
        raise ValueError('Zero semantics unresolved: explicitly choose include/exclude after review')
    raw = read_json(path)
    products, grouped = {}, defaultdict(list)
    stats = Counter(raw_comments=len(raw))
    for row in raw:
        item = str(row['perfume_id'])
        products[item] = {'name': row['perfume_name'], 'brand': row['perfume_brand']}
        votes = row.get('user_vote_on_perfume', {}).get('votes', {})
        if 'رایحه' not in votes:
            continue
        stats['scent_objects'] += 1
        try:
            rating = float(votes['رایحه'])
        except (ValueError, TypeError):
            stats['invalid'] += 1
            continue
        if not 0 <= rating <= 10:
            stats['invalid'] += 1
            continue
        stats['zero'] += rating == 0
        if rating == 0 and zero_policy == 'exclude':
            continue
        user = hashlib.sha256(('atrafshan:' + str(row['user_id'])).encode()).hexdigest()
        grouped[user, item].append(rating)
    interactions = []
    for (user, item), values in sorted(grouped.items()):
        stats['duplicate_rows'] += len(values) - 1
        if len(set(values)) > 1:
            stats['conflicting_pairs'] += 1
            continue
        interactions.append((user, item, values[0] / 10))
    stats['unique_interactions'] = len(interactions)
    stats['users'] = len({u for u, _, _ in interactions})
    stats['rated_items'] = len({i for _, i, _ in interactions})
    return products, interactions, dict(stats)


def aligned(interactions, mapping):
    """Map source items; quarantine conflicting duplicates caused by catalog alignment."""
    grouped = defaultdict(list)
    for user, item, rating in interactions:
        if item in mapping:
            grouped[user, mapping[item]].append(rating)
    return [(u, i, values[0]) for (u, i), values in sorted(grouped.items()) if len(set(values)) == 1]


def counts(rows):
    """Summarize a sparse edge list, including bipartite connected components."""
    parent = {}
    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for user, item, _ in rows:
        a, b = root(('u', user)), root(('i', item))
        parent[a] = b
    users, items = {r[0] for r in rows}, {r[1] for r in rows}
    return {'users': len(users), 'items': len(items), 'interactions': len(rows),
            'components': len({root(x) for x in parent}),
            'density': len(rows) / (len(users) * len(items)) if users and items else 0}


def laure_catalog(directory):
    """Restore numeric brand/note/category/season FKs; collect broken FK counts."""
    directory = Path(directory)
    lookups = {name: {r['pk']: r['fields']['name'] for r in read_json(directory / f'{name}.json')}
               for name in ('brand', 'notes', 'category', 'season')}
    catalog, errors = {}, Counter()
    raw_rows = read_json(directory / 'perfumes.json')
    seen_rows = {}
    conflicts = set()
    for row in raw_rows:
        if row['pk'] in seen_rows:
            if row != seen_rows[row['pk']]:
                errors['conflicting_duplicate_perfume_pk'] += 1
                conflicts.add(str(row['pk']))
                catalog.pop(str(row['pk']), None)
                continue
            errors['identical_duplicate_perfume_pk'] += 1
            continue
        seen_rows[row['pk']] = row
        fields = row['fields']
        brand = lookups['brand'].get(fields['brand'])
        errors['brand'] += brand is None
        restored = {}
        for field, lookup in [('top_notes', 'notes'), ('heart_notes', 'notes'), ('base_notes', 'notes'),
                              ('categories', 'category'), ('seasons', 'season')]:
            restored[field] = []
            for pk in fields.get(field, []):
                if pk not in lookups[lookup]:
                    errors[field] += 1
                else:
                    restored[field].append(lookups[lookup][pk])
        catalog[str(row['pk'])] = {'name': fields['name'], 'brand': brand or '', **restored}
    for pk in conflicts:
        catalog.pop(pk, None)
    return catalog, dict(errors)
