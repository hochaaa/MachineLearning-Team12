"""TF-IDF/cosine on synthetic metadata only, with signed preference weights.

Original Team12 implementation for this demo. No imports from research/web loaders.
All public methods accept values only; only __init__ reads the explicit demo JSON.
"""
import json
import math
from pathlib import Path
from collections import Counter

DATA = Path(__file__).parent / 'data' / 'synthetic_perfumes.json'
RULES = {'woody': 'accord:woody', 'floral': 'accord:floral', 'rose': 'note:rose'}
EPS = 1e-12


def tokens(row):
    """row: fictional record. Return unique typed note/accord features."""
    return frozenset(['note:' + n for n in row['notes']] + ['accord:' + a for a in row['accords']])


class Recommender:
    def __init__(self, path=DATA):
        """path: explicit synthetic catalog, no fallbacks or recursive discovery."""
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
        if not rows or len({r['id'] for r in rows}) != len(rows):
            raise ValueError('Synthetic catalog must be nonempty with unique IDs')
        required = {'id', 'brand', 'name', 'notes', 'accords', 'description', 'family', 'top_notes', 'middle_notes', 'base_notes'}
        if any(not required <= r.keys() or not r['id'].startswith('DEMO-') or not r['notes'] for r in rows):
            raise ValueError('Invalid synthetic catalog fields')
        self.rows = {r['id']: r for r in rows}
        self.features = {i: tokens(r) for i, r in self.rows.items()}
        df = Counter(t for ts in self.features.values() for t in ts)
        self.idf = {t: math.log((1 + len(rows)) / (1 + count)) + 1 for t, count in sorted(df.items())}
        self.vectors = {}
        for item, features in self.features.items():
            norm = math.sqrt(sum(self.idf[t] ** 2 for t in sorted(features)))
            self.vectors[item] = {t: self.idf[t] / norm for t in sorted(features)}

    def search(self, query, mode='name'):
        """query: name/brand/ID text or note text; mode: name or notes. AND tokens."""
        terms = query.casefold().strip().split()
        hits = []
        for item, row in sorted(self.rows.items()):
            haystack = ' '.join(row['notes'] + row['accords']) if mode == 'notes' else ' '.join([item, row['brand'], row['name']])
            if all(t in haystack.casefold() for t in terms):
                hits.append(row)
        return {'results': hits[:10], 'suggestions': [], 'query': query,
                'search_mode': mode, 'hint': 'Fictional catalog only; real brands and brand aliases are not included.'}

    def recommend(self, ratings, required_scent='none', required_scents=()):
        """ratings: validated objects (perfume_id, numeric 0..10).

        required_scent: compatible single rule; required_scents: extra AND rules.
        Return computed Top-5; neutral/cancelled profiles yield explicit zero ties.
        """
        seen = {r.perfume_id for r in ratings}
        if any(i not in self.rows for i in seen):
            raise ValueError('Unknown demo perfume ID')
        rules = sorted(set(required_scents) | ({required_scent} if required_scent != 'none' else set()))
        if any(r not in RULES for r in rules):
            raise ValueError('Unsupported scent rule')
        profile = {t: 0.0 for t in self.idf}
        # Sorted summation makes request permutation deterministic as well as reruns.
        for r in sorted(ratings, key=lambda r: r.perfume_id):
            weight = (float(r.rating) - 5.0) / 5.0
            for t, value in self.vectors[r.perfume_id].items():
                profile[t] += weight * value
        norm = math.sqrt(sum(v * v for v in profile.values()))
        pool = sorted(set(self.rows) - seen)
        eligible = [i for i in pool if all(RULES[r] in self.features[i] for r in rules)]
        scores = {i: max(-1.0, min(1.0, sum(profile[t] * v for t, v in self.vectors[i].items()) / norm))
                  if norm > EPS else 0.0 for i in eligible}
        if any(not math.isfinite(s) for s in scores.values()):
            raise ArithmeticError('Nonfinite demo score')
        ranked = sorted(eligible, key=lambda i: (-scores[i], i))[:5]
        support_tokens = set().union(*(self.features[i] for i in seen))
        results = [{**self.rows[i], 'rank': rank, 'score': scores[i],
                    'shared_tokens': sorted(support_tokens & self.features[i]),
                    'required_satisfied': True} for rank, i in enumerate(ranked, 1)]
        notices = ['Synthetic data; content-based algorithm only. Scores are signed cosine similarities, not probabilities.']
        if norm <= EPS:
            notices.append('Neutral or cancelling profile: no preference direction; scores are zero and IDs break ties.')
        if len(eligible) < 5:
            notices.append(f'Only {len(eligible)} unseen perfumes satisfy all filters; returning available results.')
        return {'mode': 'demo', 'data_origin': 'synthetic', 'engine': 'content_tfidf_cosine',
                'results': results, 'top_k': 5, 'required_scent': required_scent, 'required_scents': rules,
                'candidate_count': len(self.rows), 'unseen_count': len(pool), 'eligible_count': len(eligible),
                'profile_norm': norm, 'notice': ' '.join(notices)}
