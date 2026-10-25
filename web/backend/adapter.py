"""Web-only orchestration of unchanged frozen inference primitives; never fits models."""
from pathlib import Path
import os
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from perfume.data import fragrantica, read_json
from perfume.frozen import load_frozen
from perfume.models import hybrid, knowledge
from .advanced_search import AdvancedCatalogSearch

SCENTS = {'none': None, 'woody': 'accord:woody', 'floral': 'accord:floral', 'rose': 'note:rose'}


class FrozenService:
    """Load once from ROOT (required by original relative-path hash contract).

    No evaluation manifest/labels are read. Public records are catalog metadata only.
    Search and support are restricted to the original 479 candidates with MF factors.
    """
    def __init__(self):
        if Path.cwd().resolve() != ROOT:
            raise RuntimeError('Start backend from the project root')
        self.freeze, self.mf, self.content, self.baseline = load_frozen('outputs/final')
        self.catalog, _ = fragrantica('Term-project-datasets/fra_cleaned.csv')
        self.candidates = tuple(read_json(self.freeze['candidates_path']))
        if len(self.candidates) != 479 or not set(self.candidates) <= self.mf.items.keys():
            raise RuntimeError('Unexpected frozen candidate/factor contract')
        if self.freeze['selected']['alpha'] != .25:
            raise RuntimeError('Unexpected frozen alpha')
        self.allowed = frozenset(self.candidates)
        self.search_index = AdvancedCatalogSearch(self.candidates, self.catalog)

    def record(self, item):
        """Return catalog-only display fields; keep stable URL identity intact."""
        row = self.catalog[item]
        return {'id': item, 'name': row['name'], 'brand': row['brand'],
                'accords': [t[7:] for t in row['tokens'] if t.startswith('accord:')],
                'notes': [t[5:] for t in row['tokens'] if t.startswith('note:')]}

    def search(self, query):
        """Search the immutable candidate display index; preserve exact catalog records."""
        return [self.record(item) for item in self.search_index.lookup(query)['ids']]

    def search_response(self, query, mode='name'):
        """Return mode-specific metadata and explicit suggestions; no inference side effects."""
        found = self.search_index.lookup(query, mode)
        results = [{**self.record(i), **found['matches'].get(i, {})} for i in found['ids']]
        return {k:v for k,v in found.items() if k not in ('ids','matches')} | {'results': results}

    def recommend(self, ratings, scent):
        """Delegate arithmetic, fold-in, ordering and rules to existing core functions.

        ratings: validated web records, 0..10. scent: one SCENTS key.
        This adapts scripts/demo_frozen.py's orchestration, not its score formulas.
        """
        support = [(r.perfume_id, r.rating / 10) for r in ratings]
        seen = {i for i, _ in support}
        pool = [i for i in self.candidates if i not in seen]
        vector = self.mf.fold_in(support)
        m = self.mf.score_vector(vector, pool) if vector is not None else np.full(len(pool), np.nan)
        scores = hybrid(self.content.score(support, pool), m, self.freeze['selected']['alpha'],
                        self.baseline.score(pool))
        required = [SCENTS[scent]] if SCENTS[scent] else []
        ranked = knowledge(self.catalog, pool, scores, required=required)[:5]
        tokens = {t for i, _ in support for t in self.catalog[i]['tokens']}
        results = []
        for rank, (item, score, explanation) in enumerate(ranked, 1):
            if not np.isfinite(score):
                raise RuntimeError('Nonfinite frozen inference score')
            results.append({**self.record(item), 'rank': rank, 'score': score,
                            'shared_tokens': sorted(tokens & set(self.catalog[item]['tokens'])),
                            'required_satisfied': explanation['required_satisfied']})
        return {'results': results, 'alpha': .25, 'top_k': 5, 'required_scent': scent,
                'profile_mode': self.freeze['selected']['profile_mode'], 'candidate_count': len(self.candidates),
                'notice': '점수는 확률이 아닙니다. 공통 향 특성은 메타데이터의 교집합입니다.'}
