"""Identity-only external partitioning; rating values deliberately absent from API."""
import hashlib
from collections import defaultdict


def external_partition(pairs, factor_items, min_history=3, seed=12):
    """pairs=(pseudonymous user,canonical item), fixed candidate-matched IDs only.

    Quarantine duplicates before calling; split identities using a seeded hash, not preference.
    First floor(n/2) support, remaining held-out. Require min_history and >=1 support factor.
    Return user->(support IDs,answer IDs) and structural exclusion counts, with no values.
    """
    grouped=defaultdict(set)
    for user,item in pairs:grouped[user].add(item)
    selected={};excluded={'insufficient_history':0,'no_support_factor':0}
    for user,items in sorted(grouped.items()):
        if len(items)<min_history:
            excluded['insufficient_history']+=1;continue
        ordered=sorted(items,key=lambda i:hashlib.sha256(f'{seed}:{user}:{i}'.encode()).hexdigest())
        n=len(ordered)//2
        support,answers=ordered[:n],ordered[n:]
        if not any(i in factor_items for i in support):
            excluded['no_support_factor']+=1;continue
        selected[user]=(support,answers)
    return selected,excluded
