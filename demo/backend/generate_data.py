"""Generate 80 fictional records from constants and a fixed RNG; no input files.

Python random.Random is isolated from process-global randomness. General fragrance
words are ordinary domain vocabulary, not copied source records or brand aliases.
"""
import json
import random
from pathlib import Path

SEED = 1612
FAMILIES = {
    'citrus': ['bergamot', 'lemon', 'mandarin', 'grapefruit'],
    'floral': ['rose', 'iris', 'jasmine', 'violet'],
    'woody': ['cedar', 'sandalwood', 'vetiver', 'cypress'],
    'musk': ['soft musk', 'cotton musk', 'powder', 'ambrette'],
    'amber': ['amber', 'benzoin', 'labdanum', 'resin'],
    'aquatic': ['sea breeze', 'rain', 'mineral', 'water lily'],
    'green': ['green tea', 'leaf', 'fig leaf', 'grass'],
    'spicy': ['cardamom', 'ginger', 'pepper', 'cinnamon'],
    'gourmand': ['vanilla', 'cocoa', 'caramel', 'almond'],
    'aromatic': ['lavender', 'rosemary', 'sage', 'basil'],
}

def generate():
    """Return eight distinct note/accord combinations per family (80 total)."""
    rng = random.Random(SEED)
    families = list(FAMILIES)
    rows = []
    combinations = set()
    for fi, family in enumerate(families):
        for variant in range(8):
            while True:
                secondary = rng.choice([f for f in families if f != family])
                notes = rng.sample(FAMILIES[family], 2) + [rng.choice(FAMILIES[secondary])]
                extra = rng.choice([n for f in families for n in FAMILIES[f] if n not in notes])
                notes.append(extra)
                signature = (tuple(sorted(notes)), tuple(sorted([family, secondary])))
                if signature not in combinations:
                    combinations.add(signature)
                    break
            number = len(rows) + 1
            rows.append({
                'id': f'DEMO-{number:03d}',
                'brand': f'Imaginary Atelier {fi + 1:02d}',
                'name': f'Invented {family.title()} Study {variant + 1:02d}',
                'family': family,
                'top_notes': notes[:1], 'middle_notes': notes[1:3], 'base_notes': notes[3:],
                'notes': notes, 'accords': [family, secondary],
                'description': f'Fictional composition {number:03d}: an imagined {family} direction with a {secondary} contrast. Not a real product.',
            })
    return rows

if __name__ == '__main__':
    target = Path(__file__).parent / 'data' / 'synthetic_perfumes.json'
    # Explicit generation only; the server never creates or searches for assets.
    target.write_text(json.dumps(generate(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Generated {len(generate())} fictional records: {target.name}; seed={SEED}')
