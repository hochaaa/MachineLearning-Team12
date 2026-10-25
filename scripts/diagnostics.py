"""Real-data diagnostics; external identities/counts only, never external preference scores."""
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from perfume.data import read_json, write_json, write_csv


def main():
    raw = Path('Term-project-datasets')
    out = Path('outputs/audit')
    groups = defaultdict(Counter)
    for row in read_json(raw/'atrafshan_data.json'):
        votes = row.get('user_vote_on_perfume',{}).get('votes',{})
        if not votes:
            continue
        group = 'scent_zero' if votes['رایحه']=='0' else 'scent_nonzero'
        groups[group]['total'] += 1
        groups[group]['all_four_zero'] += all(v=='0' for v in votes.values())
        groups[group]['other_any_nonzero'] += any(v!='0' for k,v in votes.items() if k!='رایحه')
        for key,value in votes.items():
            groups[group][key+'='+value] += 1
    write_json(out/'zero_joint_distribution.json', groups)
    # Pseudonymous training manifests only. Item factor coverage differs from catalog matching.
    ext_mapping = {r['source_item']:r['target_item'] for r in __import__('csv').DictReader((out/'external_matching.csv').open()) if r['status']=='accepted'}
    review_ids = {(str(r['fields']['user']),str(r['fields']['perfume'])) for r in read_json(raw/'reviews.json')}
    records = []
    for policy in ('include','exclude'):
        metadata = read_json(f'outputs/validation/model_{policy}.json')
        factors = set(metadata['items'])
        links = {(u,ext_mapping[i]) for u,i in review_ids if i in ext_mapping and ext_mapping[i] in factors}
        activity = Counter(u for u,_ in links)
        records.append({'scenario':policy,'learned_factor_items':len(factors),
                        'external_matched_factor_items':len({i for _,i in links}),
                        'surviving_unique_interactions':len(links),
                        'users_with_2plus':sum(v>=2 for v in activity.values()),
                        'users_with_5plus':sum(v>=5 for v in activity.values())})
    write_csv(out/'external_trained_factor_feasibility.csv',records)
    selection = read_json('outputs/validation/selection.json')
    catalog,_ = __import__('perfume.data',fromlist=['fragrantica']).fragrantica(raw/'fra_cleaned.csv')
    selected=selection['scenario_selections']['exclude']
    train=read_json(f'outputs/validation/train_exclude_{selected["threshold"]}.json')
    from perfume.models import Content,MatrixFactorization,Baseline,knowledge,hybrid
    import numpy as np
    config=read_json('configs/experiment.json')
    mf=MatrixFactorization(**config['mf_grid'][selected['grid']], seed=config['seed']).fit(train)
    content=Content().fit(catalog,mf.items)
    baseline=Baseline().fit(train)
    histories=defaultdict(list)
    for u,i,r in train: histories[u].append((i,r))
    candidates=read_json('outputs/validation/split_manifest.json')['candidates']
    rules=[]
    for token in ['accord:woody','accord:floral','note:rose']:
        returned=success=empty=0
        for user,support in histories.items():
            pool=[i for i in candidates if i not in {x for x,_ in support}]
            c,m=content.score(support,pool),mf.score(user,pool)
            score=hybrid(c,m,.25,baseline.score(pool))
            result=knowledge(catalog,pool,score,required=[token])[:10]
            empty+=not bool(result)
            for item,_,_ in result:
                returned+=1
                success+=token in catalog[item]['tokens']
        rules.append({'required':token,'users':len(histories),'returned':returned,'satisfied':success,
                      'constraint_satisfaction_rate':success/returned if returned else None,'empty_users':empty,
                      'note':'Constraint verification only; no claim of personalized ranking accuracy'})
    write_csv('outputs/validation/knowledge_rules.csv',rules)
    # Demo input comes only from development train, no answer item IDs.
    first=sorted(histories)[0]
    write_json('data/demo_support.json',histories[first][:3])
    # Raw vs aligned user-history histograms, with no real user IDs exported.
    from perfume.data import atrafshan,aligned,fragrantica,matcher,match
    index=matcher(catalog)
    products,_,_=atrafshan(raw/'atrafshan_data.json','include')
    mapping={i:target for i,r in products.items() if (target:=match(index,r['brand'],r['name'])[0])}
    distribution=[]
    for policy in ('include','exclude'):
        rows=atrafshan(raw/'atrafshan_data.json',policy)[1]
        for stage,edges in [('raw',rows),('aligned',aligned(rows,mapping))]:
            hist=Counter(Counter(u for u,_,_ in edges).values())
            distribution.extend({'scenario':policy,'stage':stage,'interactions_per_user':n,'users':v} for n,v in sorted(hist.items()))
    write_csv(out/'user_history_distribution.csv',distribution)


if __name__=='__main__': main()
