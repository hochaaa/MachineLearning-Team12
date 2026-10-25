"""Search-only normalization and deterministic relevance over frozen catalog IDs.

Does not normalize IDs, mutate catalog rows, match datasets or influence recommendation.
All code is original; Python re/unicodedata are standard-library APIs.
"""
import re
import unicodedata


def normalize_search(value):
    """value: query/metadata string; return casefolded, accent-folded word string.

    Unicode NFKD handles compatibility characters; combining marks are removed.
    Punctuation/hyphens become spaces; whitespace collapses. No translation/fuzzy edits.
    """
    text = unicodedata.normalize('NFKD', value.casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[^\W_]+', text, flags=re.UNICODE))


class CatalogSearch:
    """Precompute search fields from candidates and catalog (both read-only inputs).

    candidates: original URL sequence; catalog: existing name/brand dictionary.
    Repeated IDs are deduplicated only in this display index; original pool is untouched.
    """
    def __init__(self, candidates, catalog):
        self.entries = []
        for item in dict.fromkeys(candidates):
            name = normalize_search(catalog[item]['name'])
            brand = normalize_search(catalog[item]['brand'])
            # If the entire brand phrase already occurs, do not repeat it (Dior Homme,
            # Bleu de Chanel, etc.). Brand and name remain separately searchable.
            full = name if f' {brand} ' in f' {name} ' else f'{brand} {name}'.strip()
            words = frozenset((brand + ' ' + name).split())
            self.entries.append((item, brand, name, full, words))

    @staticmethod
    def relevance(query, tokens, entry):
        """Return match tier or None. query/tokens are normalized; entry is index tuple.

        0 full exact, 1 name exact, 2 full prefix, 3 name prefix,
        4 full substring, 5 all whole tokens, 6 all token fragments.
        Every token must match for token-based tiers; OR-only matches are excluded.
        """
        _, brand, name, full, words = entry
        if query == full: return 0
        if query == name: return 1
        if full.startswith(query): return 2
        if name.startswith(query): return 3
        if query in full: return 4
        if tokens <= words: return 5
        if all(any(t in word for word in words) for t in tokens): return 6
        return None

    def ranked(self, query, limit=10):
        """query: raw string; limit: display cap, applied AFTER ranking all matches.

        Empty/punctuation-only queries return []. Ties use shorter full token count,
        normalized brand/name and unchanged URL. Return original IDs, never new items.
        API enforces query length<=100; no spelling/translation/metadata-note searching.
        """
        query = normalize_search(query)
        if not query: return []
        tokens = frozenset(query.split())
        ranked = []
        for entry in self.entries:
            tier = self.relevance(query, tokens, entry)
            if tier is not None:
                item, brand, name, full, _ = entry
                ranked.append(((tier, len(full.split()), brand, name, item), item))
        ranked.sort()
        return [item for _, item in ranked[:limit]]
