"""All strict unequal observed rating pairs, never unobserved negatives."""
from collections import defaultdict,Counter
import numpy as np


def build_pairs(rows,excluded_users=()):
    """Unique normalized (user,item,rating) triples and evaluation users to reject.

    Each unordered pair yields exactly one directed high>low record, equal ratings
    excluded. No rating gap weights or popularity sampling. Returns pairs + counts.
    """
    if len({(u,i)for u,i,y in rows})!=len(rows):raise ValueError('Duplicate user/item')
    if {u for u,i,y in rows}&set(excluded_users):raise ValueError('Evaluation user in training')
    by=defaultdict(list)
    for u,i,y in rows:
        if not np.isfinite(y)or not 0<=y<=1:raise ValueError('Normalized rating required')
        by[u].append((i,float(y)))
    pairs=[];counts={};ties=0
    for u in sorted(by):
        history=sorted(by[u]);n=0
        for a,(i,yi)in enumerate(history):
            for j,yj in history[a+1:]:
                if yi==yj:ties+=1;continue
                pairs.append((u,i,j)if yi>yj else(u,j,i));n+=1
        counts[u]=n
    if len(set(pairs))!=len(pairs):raise ValueError('Duplicate pair')
    c=list(counts.values());q=np.quantile(c,[.25,.5,.75,.9,1])if c else [0]*5
    return pairs,dict(users=len(by),ratings=len(rows),pairs=len(pairs),users_without_pairs=sum(x==0 for x in c),users_with_pairs=sum(x>0 for x in c),equal_pairs_excluded=ties,pairs_min=min(c,default=0),pairs_p25=float(q[0]),pairs_median=float(q[1]),pairs_p75=float(q[2]),pairs_p90=float(q[3]),pairs_max=float(q[4]),pair_items=len({i for u,a,b in pairs for i in (a,b)}),user_pair_counts_private=counts)
