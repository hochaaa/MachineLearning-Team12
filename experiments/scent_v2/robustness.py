"""Same per-user perturbations for every method. No clamping or label access."""
import numpy as np
from .recommend import score


def variants(support, amplitude):
    """amplitude: UI units .5 or 1; support ratings are normalized [0,1]."""
    for n,(item,rating) in enumerate(support):
        for direction in (-1,1):
            value = rating*10 + direction*amplitude
            if 0 <= value <= 10:
                changed = list(support)
                changed[n] = (item,value/10)
                yield n,direction,changed


def compare(before, after):
    """Top-five metrics; common rank movement is undefined if intersection is empty."""
    a,b=before['top'],after['top'];common=set(a)&set(b);union=set(a)|set(b)
    return dict(replacement=1-len(common)/5,
                jaccard=len(common)/len(union) if union else 1.,
                first=float(bool(a) and bool(b) and a[0]==b[0]),
                set_same=float(set(a)==set(b)), order_same=float(a==b),
                rank_move=float(np.mean([abs(a.index(i)-b.index(i)) for i in common])) if common else None)


def measure(support,candidates,content,mf,popularity,baseline):
    """Return amplitude->method->USER means, with common-rank valid counts."""
    result=[]
    for amplitude in (.5,1.):
        by_method={m:[] for m in baseline['methods']}
        identities=[]
        for n,direction,changed in variants(support,amplitude):
            identities.append((n,direction))
            after=score(changed,candidates,content,mf,popularity)
            for method,base in baseline['methods'].items():
                by_method[method].append(compare(base,after['methods'][method]))
        for method,rows in by_method.items():
            row=dict(amplitude=amplitude,method=method,variants=len(identities),
                     rank_valid=sum(r['rank_move'] is not None for r in rows))
            for key in ('replacement','jaccard','first','set_same','order_same','rank_move'):
                values=[r[key] for r in rows if r[key] is not None]
                row[key]=float(np.mean(values)) if values else None
            result.append(row)
    return result


def aggregate(rows):
    """Equal user macro averages and user replacement P90; not perturbation micro means."""
    result=[]
    groups={}
    for r in rows:groups.setdefault((r['track'],r['method'],r['amplitude']),[]).append(r)
    for (track,method,amp),group in groups.items():
        row=dict(track=track,method=method,amplitude=amp,users=len(group),
                 variants=sum(r['variants'] for r in group),
                 replacement_p90=float(np.quantile([r['replacement'] for r in group],.9)))
        for key in ('replacement','jaccard','first','set_same','order_same','rank_move'):
            values=[r[key] for r in group if r[key] is not None]
            row[key]=float(np.mean(values)) if values else None
        result.append(row)
    return result
