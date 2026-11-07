"""Descriptive data quality only; no model fitting or accuracy assessment."""
from collections import Counter, defaultdict
from statistics import mean, median, pstdev

def summarize(rows, candidates, previous_counts=None):
    """Canonical rows use 0..10 normalized_rating; 7+ positive, <5 low descriptive assumptions."""
    if not rows: return dict(status='NOT_MEASURED_NO_ACQUIRED_DATA')
    users, items = Counter(), Counter(); values=[]; graph=defaultdict(set); raw_values=defaultdict(list)
    for r in rows:
        u,i=r['user_id'],r['perfume_id']
        if i not in candidates: raise ValueError('Quality rows must stay within fixed candidates')
        users[u]+=1;items[i]+=1;values.append(r['normalized_rating'])
        if r.get('raw_rating') is not None:raw_values[str(r.get('raw_scale','UNKNOWN'))].append(float(r['raw_rating']))
        graph[('u',u)].add(('i',i));graph[('i',i)].add(('u',u))
    seen=set(); sizes=[]
    for start in graph:
        if start in seen: continue
        todo=[start];seen.add(start);size=0
        while todo:
            current=todo.pop();size+=1
            for nxt in graph[current]-seen:seen.add(nxt);todo.append(nxt)
        sizes.append(size)
    common=Counter()
    for node,adj in graph.items():
        if node[0]=='i':
            uu=sorted(n[1] for n in adj)
            for a in range(len(uu)):
                for b in range(a+1,len(uu)): common[(uu[a],uu[b])]+=1
    n=len(values); previous_counts=previous_counts or {}
    raw=Counter(str(r.get('raw_scale','legacy')) for r in rows)
    return dict(status='MEASURED', users=len(users), perfumes=len(items), ratings=n,
        mean_per_user=n/len(users),mean_per_observed_item=n/len(items), mean=mean(values),median=median(values),std=pstdev(values),
        positive_fraction=sum(v>=7 for v in values)/n, low_fraction=sum(v<5 for v in values)/n,
        user_activity_histogram=dict(Counter(users.values())), users_at_least_2=sum(v>=2 for v in users.values()),
        users_at_least_3=sum(v>=3 for v in users.values()),users_at_least_5=sum(v>=5 for v in users.values()),
        observed_candidates=sum(items[i]>0 for i in candidates),unobserved_candidates=sum(items[i]==0 for i in candidates),
        observed_1_to_2=sum(1<=items[i]<=2 for i in candidates),observed_at_most_2=sum(items[i]<=2 for i in candidates),
        newly_observed=sum(items[i]>0 and previous_counts.get(i,0)==0 for i in candidates) if previous_counts else 'UNKNOWN_NO_BASELINE',
        density=len({(r['user_id'],r['perfume_id']) for r in rows})/(len(users)*len(candidates)),
        components=len(sizes),component_node_sizes=sorted(sizes,reverse=True),user_pairs_with_shared_item=len(common),
        shared_items_per_connected_user_pair=dict(Counter(common.values())),raw_scale_counts=dict(raw),normalized_rating_histogram=dict(Counter(values)),
        raw_scale_distributions={k:dict(count=len(v),mean=mean(v),median=median(v),std=pstdev(v),histogram=dict(Counter(v))) for k,v in raw_values.items()},
        model_accuracy='NOT_EVALUATED',mf_eligibility='Activity alone does not prove sufficient MF connectivity')
