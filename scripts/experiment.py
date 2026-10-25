"""Provisional 0-included/excluded validation sensitivity. Never opens Basenotes files."""
import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from perfume.data import fragrantica, matcher, match, atrafshan, aligned, counts, write_json, write_csv, read_json
from perfume.splits import partition, assert_disjoint
from perfume.models import Content, MatrixFactorization, Baseline, knowledge, hybrid
from perfume.evaluation import score_users, evaluate, rating_errors
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', default='Term-project-datasets')
    parser.add_argument('--output', default='outputs/validation')
    parser.add_argument('--config', default='configs/experiment.json')
    args = parser.parse_args()
    raw, out = Path(args.raw), Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    config = read_json(args.config)
    catalog, _ = fragrantica(raw / 'fra_cleaned.csv')
    index = matcher(catalog)
    products, _, _ = atrafshan(raw / 'atrafshan_data.json', 'include')
    mapping = {i: target for i, r in products.items() if (target := match(index, r['brand'], r['name'])[0])}
    scenarios = {p: aligned(atrafshan(raw / 'atrafshan_data.json', p)[1], mapping) for p in ('include', 'exclude')}
    # Stronger control: SAME nonzero validation/test users and labels even across zero scenarios.
    common_train, validation, test = partition(scenarios['exclude'], config['seed'])
    held = {(u, i) for u, i, _ in validation+test}
    activity_nonzero = Counter(u for u, _, _ in scenarios['exclude'])
    common_train = [r for r in common_train if activity_nonzero[r[0]] >= 5]
    candidates = sorted({i for _, i, _ in common_train})
    users = sorted({u for u, _, _ in validation})
    write_json(out / 'split_manifest.json', {'seed': config['seed'], 'validation': validation, 'test': test,
               'candidates': candidates, 'warning': 'PRIVATE local manifest; test labels persisted, never evaluated or used for model selection'})
    results, per_users, scale_counts, error_log, losses, trains = [], [], [], {}, {}, {}
    for policy, rows in scenarios.items():
        activity = Counter(u for u, _, _ in rows)
        for threshold in (3, 4, 5):
            train = [r for r in rows if activity[r[0]] >= threshold and (r[0], r[1]) not in held]
            assert_disjoint(train, validation, test)
            label = f'{policy}_{threshold}'
            trains[label] = train
            write_json(out / f'train_{label}.json', train)
            scale_counts.append({'zero_scenario': policy, 'threshold': threshold, **counts(train),
                                 'validation_users': len(users), 'validation_labels': len(validation),
                                 'test_labels': len(test), 'candidates': len(candidates),
                                 'extra_train_only_users': len({u for u, _, _ in train}-set(users))})
            content = Content().fit(catalog, {i for _, i, _ in train})
            baseline = Baseline().fit(train)
            for grid_id, parameters in enumerate(config['mf_grid']):
                mf = MatrixFactorization(**parameters, seed=config['seed']).fit(train)
                predictions = score_users(train, users, candidates, content, mf, baseline, config['alphas'])
                summary, per_user = evaluate(predictions, validation, config['k'], config['relevance'])
                for row in summary:
                    results.append({'zero_scenario': policy, 'threshold': threshold, 'grid': grid_id, **row})
                per_users.extend({'zero_scenario': policy, 'threshold': threshold, 'grid': grid_id, **r} for r in per_user)
                losses[f'{label}_{grid_id}'] = mf.losses
                error_log[f'{label}_{grid_id}'] = rating_errors(validation, mf, baseline)
                print(f'completed {label} grid={grid_id}', flush=True)
    write_csv(out / 'metrics.csv', results)
    write_csv(out / 'per_user_metrics.csv', per_users)
    write_csv(out / 'training_counts.csv', scale_counts)
    write_json(out / 'validation_rating_errors.json', error_log)
    write_json(out / 'training_loss.json', losses)
    selections = {}
    external_factor_counts = {}
    for policy in scenarios:
        viable = [r for r in results if r['zero_scenario'] == policy and r['method'].startswith('hybrid_') and r['ndcg'] is not None]
        best = sorted(viable, key=lambda r: (-r['ndcg'], r['threshold'], r['grid'], r['method']))[0]
        selections[policy] = best
        train = trains[f'{policy}_{best["threshold"]}']
        mf = MatrixFactorization(**config['mf_grid'][best['grid']], seed=config['seed']).fit(train)
        np.savez(out / f'mf_{policy}.npz', P=mf.P, Q=mf.Q)
        write_json(out / f'model_{policy}.json', {'users': mf.users, 'items': mf.items,
                   'parameters': config['mf_grid'][best['grid']], 'alpha': float(best['method'].split('_')[1]),
                   'train_label': f'{policy}_{best["threshold"]}', 'status': 'PROVISIONAL zero-policy sensitivity'})
        external_factor_counts[policy] = len(mf.items)
    write_json(out / 'selection.json', {'status': 'PROVISIONAL; final zero policy BLOCKED; internal/external test NOT run',
               'scenario_selections': selections, 'learned_factor_items': external_factor_counts})
    write_json(out / 'run_metadata.json', {'python': platform.python_version(), 'numpy': np.__version__,
               'config': config, 'config_sha256': hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
               'inputs_sha256': {name: hashlib.sha256((raw/name).read_bytes()).hexdigest() for name in ('fra_cleaned.csv','atrafshan_data.json')},
               'common_split_sha256': hashlib.sha256((out/'split_manifest.json').read_bytes()).hexdigest()})


if __name__ == '__main__':
    main()
