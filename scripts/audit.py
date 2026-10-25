"""Read-only raw audit. Does not train or score external held-out answers."""
import argparse
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from perfume.data import (fragrantica, matcher, match, atrafshan, aligned, counts,
                          laure_catalog, read_json, write_json, write_csv)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', default='Term-project-datasets')
    parser.add_argument('--output', default='outputs/audit')
    args = parser.parse_args()
    raw, out = Path(args.raw), Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.iterdir()) if p.is_file()}
    write_json(out / 'input_sha256.json', hashes)
    catalog, metadata = fragrantica(raw / 'fra_cleaned.csv')
    index = matcher(catalog)
    products, _, _ = atrafshan(raw / 'atrafshan_data.json', 'include')
    mapping, matches = {}, []
    for item, row in sorted(products.items()):
        target, status = match(index, row['brand'], row['name'])
        if target:
            mapping[item] = target
        matches.append({'source': 'atrafshan', 'source_item': item, 'brand': row['brand'],
                        'name': row['name'], 'target_item': target or '', 'status': status})
    write_csv(out / 'atrafshan_matching.csv', matches)
    scenarios, thresholds = {}, []
    for policy in ('include', 'exclude'):
        _, ratings, stats = atrafshan(raw / 'atrafshan_data.json', policy)
        links = aligned(ratings, mapping)
        activity = Counter(u for u, _, _ in links)
        scenarios[policy] = {'raw': stats, 'matched': counts(links)}
        for threshold in (3, 4, 5):
            before = Counter(u for u, _, _ in ratings)
            filtered = [r for r in links if activity[r[0]] >= threshold]
            thresholds.append({'zero_scenario': policy, 'threshold': threshold,
                               'pre_alignment_users': sum(n >= threshold for n in before.values()),
                               **counts(filtered)})
    external, fk = laure_catalog(raw)
    external_mapping, match_rows = {}, []
    for item, row in sorted(external.items()):
        target, status = match(index, row['brand'], row['name'])
        if target:
            external_mapping[item] = target
        match_rows.append({'source_item': item, 'target_item': target or '', 'status': status})
    # Feasibility uses identities and counts only, not external rating values or preferences.
    review_ids = [(str(r['fields']['user']), str(r['fields']['perfume'])) for r in read_json(raw / 'reviews.json')]
    unique = set(review_ids)
    source_factor_upper_bound = set(mapping.values())
    external_summary = {'catalog_items': len(external), 'raw_reviews': len(review_ids),
                        'unique_user_item_pairs': len(unique), 'rated_items': len({i for _, i in unique}),
                        'users': len({u for u, _ in unique}), 'broken_fks': fk}
    for label, allowed in [('content', set(catalog)), ('pretrain_mf_upper_bound', source_factor_upper_bound)]:
        surviving = [(u, external_mapping[i]) for u, i in unique
                     if i in external_mapping and external_mapping[i] in allowed]
        activity = Counter(u for u, _ in set(surviving))
        external_summary[label] = {'matched_source_rated_items': len({i for _, i in unique if i in external_mapping and external_mapping[i] in allowed}),
                                   'surviving_unique_interactions': len(set(surviving)),
                                   'users_with_2plus': sum(n >= 2 for n in activity.values()),
                                   'users_with_5plus': sum(n >= 5 for n in activity.values())}
    write_csv(out / 'external_matching.csv', match_rows)
    write_csv(out / 'threshold_counts.csv', thresholds)
    summary = {'fragrantica_rows': len(metadata), 'fragrantica_missing_fraction':
               {key: sum(r[key] in ('', 'unknown', 'NA') for r in metadata) / len(metadata) for key in metadata[0]},
               'atrafshan_catalog_items': len(products), 'atrafshan_match_status': dict(Counter(r['status'] for r in matches)),
               'atrafshan_unique_matched_targets': len(set(mapping.values())), 'scenarios': scenarios,
               'external': external_summary,
               'warning': 'Zero semantics unresolved. User confirmed local classroom usage on 2026-10-22; redistribution not authorized. MF counts are upper bounds BEFORE training/splits, not learned factors.'}
    write_json(out / 'summary.json', summary)
    print(__import__('json').dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
