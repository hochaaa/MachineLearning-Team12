"""Conservative catalog identity; fuzzy results are review suggestions only."""
import re, unicodedata
from difflib import SequenceMatcher

def normalized(text):
    """NFC/casefold and punctuation/space normalization; retain all version tokens."""
    return ' '.join(re.findall(r'[^\W_]+', unicodedata.normalize('NFC', text).casefold()))

def match(row, catalog):
    """Unique exact normalized brand/name only, with supplied variant attributes checked.

    Catalog IDs are accepted only as the same Fragrantica URL identity, never a
    numeric ID belonging to another provider. Conflicting metadata blocks even IDs.
    """
    key = normalized(row['brand']), normalized(row['name'])
    hits = [i for i, c in catalog.items() if (normalized(c['brand']), normalized(c['name'])) == key]
    if row.get('id_system') == 'fragrantica_url' and row.get('item_id') in catalog:
        if row['item_id'] not in hits: return dict(status='AMBIGUOUS_ID_METADATA', item=None)
        hits = [row['item_id']]
    if len(hits) == 1:
        c = catalog[hits[0]]
        for k in ('concentration', 'year', 'gender', 'edition'):
            a, b = row.get(k), c.get(k)
            if a or b:
                if not a or not b or normalized(str(a)) != normalized(str(b)):
                    return dict(status='AMBIGUOUS_VARIANT', item=None)
        return dict(status='EXACT_NORMALIZED', item=hits[0])
    if hits: return dict(status='AMBIGUOUS_COLLISION', item=None)
    suggestions = sorted(((-SequenceMatcher(None, ' '.join(key), normalized(c['brand']+' '+c['name'])).ratio(), i)
                          for i,c in catalog.items()))[:3]
    return dict(status='UNMATCHED', item=None, suggestions=[i for score,i in suggestions if score <= -0.8])
