"""Local provisional CLI: user ratings and explicit note/accord rules -> explained Top-K."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from perfume.data import fragrantica, read_json
from perfume.models import MatrixFactorization, Content, Baseline, hybrid, knowledge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['include', 'exclude'], required=True, help='Unresolved zero sensitivity model; not a final policy')
    parser.add_argument('--support', required=True, help='Local JSON list [[Fragrantica URL,rating 0..1], ...]')
    parser.add_argument('--required', action='append', default=[], help='Exact token, e.g. accord:woody; repeat for AND')
    parser.add_argument('--forbidden', action='append', default=[])
    parser.add_argument('--preferred', action='append', default=[])
    parser.add_argument('--k', type=int, default=10)
    parser.add_argument('--raw', default='Term-project-datasets')
    parser.add_argument('--model-dir', default='outputs/validation')
    args = parser.parse_args()
    model_dir = Path(args.model_dir)
    catalog, _ = fragrantica(Path(args.raw)/'fra_cleaned.csv')
    metadata = read_json(model_dir/f'model_{args.scenario}.json')
    train = read_json(model_dir/f'train_{metadata["train_label"]}.json')
    mf = MatrixFactorization(**metadata['parameters'])
    arrays = np.load(model_dir/f'mf_{args.scenario}.npz')
    mf.P, mf.Q = arrays['P'], arrays['Q']
    mf.users, mf.items = metadata['users'], metadata['items']
    content = Content().fit(catalog, {i for _, i, _ in train})
    baseline = Baseline().fit(train)
    support = read_json(args.support)
    for item, rating in support:
        if item not in catalog or not isinstance(rating, (int,float)) or not 0 <= rating <= 1:
            raise ValueError('Support requires known catalog URLs and finite ratings in [0,1]')
    seen = {i for i, _ in support}
    pool = sorted(set(catalog)-seen)
    vector = mf.fold_in(support)
    c = content.score(support, pool)
    m = mf.score_vector(vector, pool) if vector is not None else np.full(len(pool), np.nan)
    scores = hybrid(c, m, metadata['alpha'], baseline.score(pool))
    results = knowledge(catalog, pool, scores, args.required, args.forbidden, args.preferred)
    print(json.dumps({'status': metadata['status'], 'results': [
        {'item': item, 'name': catalog[item]['name'], 'brand': catalog[item]['brand'], 'score': score,
         'explanation': {**explanation, 'method': 'content + frozen MF fold-in where factors available; otherwise explicit fallback',
                         'support_shared_tokens': sorted(set(catalog[item]['tokens']) & {t for i,_ in support for t in catalog[i]['tokens']})}}
        for item, score, explanation in results[:args.k]]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
