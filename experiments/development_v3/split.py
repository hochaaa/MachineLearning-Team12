"""Exact STEP7 blueprint: user outer3/inner2, common479, known3support."""
import hashlib
from v3_data import histories

def hkey(seed,*parts):return hashlib.sha256(':'.join(map(str,(seed,*parts))).encode()).hexdigest()

def outer_specs(train,seed=20261109):
    h=histories(train);eligible=sorted((u for u,v in h.items() if len(v)>=4),key=lambda u:hkey(seed,'v3outer',u))
    return [(k,[r for r in train if r[0] not in set(eligible[k::3])],set(eligible[k::3])) for k in range(3)]

def inner_specs(outer_train,outer_index,seed=20261109):
    h=histories(outer_train);eligible=sorted((u for u,v in h.items() if len(v)>=4),key=lambda u:hkey(seed,'v3inner',outer_index,u))
    return [(k,[r for r in outer_train if r[0] not in set(eligible[k::2])],set(eligible[k::2])) for k in range(2)]

def user_evaluation(source,fit,held,pool,seed=20261109):
    """Choose support by IDs only. Unknown-factor heldout retained as misses/fallback targets."""
    assert not held&{u for u,_,_ in fit};h=histories(source);known={i for _,i,_ in fit};poolset=set(pool);support={};answers=[];excluded={'fewer_than3_known_support':0,'no_heldout':0}
    for u in sorted(held):
        hist=[(i,r) for i,r in h[u] if i in poolset];available=sorted([(i,r) for i,r in hist if i in known],key=lambda r:hkey(seed,'v3support',u,r[0]))
        if len(available)<3:excluded['fewer_than3_known_support']+=1;continue
        if len(hist)<4:excluded['no_heldout']+=1;continue
        support[u]=available[:3];seen={i for i,_ in support[u]};answers.extend((u,i,r) for i,r in hist if i not in seen)
    assert not {(u,i) for u,v in support.items() for i,_ in v}&{(u,i) for u,i,_ in answers}
    return support,answers,excluded

def known_split(rows,outer_index,seed=20261109):
    h=histories(rows);held={(u,sorted(v,key=lambda r:hkey(seed,'v3known',outer_index,u,r[0]))[0][0]) for u,v in h.items() if len(v)>=4}
    return [r for r in rows if (r[0],r[1]) not in held],[r for r in rows if (r[0],r[1]) in held]
