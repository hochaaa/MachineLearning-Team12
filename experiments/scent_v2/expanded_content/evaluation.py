"""Answer harness separated from scoring; no fit, tuning or synthetic ground truth."""
import math,hashlib
from collections import Counter
from statistics import mean,pstdev
from perfume.evaluation import ranking_metrics


def user_metrics(top,answers):
    """Same binary positive>=.7; P denominator5; R/IDCG use all observed positives."""
    positives={i for i,r in answers if r>=.7}
    result=ranking_metrics(top,positives,5)
    if result is not None:result['hit_rate']=float(bool(set(top)&positives))
    return result


def summarize(records,universe,new_ids=()):
    """Positive-user conditional accuracy, ALL-user exposure/coverage/concentration."""
    if not records:return dict(status='NOT_EVALUATED',users=0)
    positive=[r for r in records if r['accuracy'] is not None]
    count=Counter(i for r in records for i in r['top']);slots=sum(count.values());newslots=sum(n for i,n in count.items() if i in new_ids)
    result=dict(status='MEASURED',users=len(records),positive_users=len(positive),no_positive_users=len(records)-len(positive),
        coverage_items=len(count),coverage_fraction=len(count)/len(universe),
        top1_slot_concentration=max(count.values(),default=0)/slots if slots else None,
        top5_slot_concentration=sum(n for i,n in count.most_common(5))/slots if slots else None,
        new_slot_fraction=newslots/slots if slots else None,old_slot_fraction=(slots-newslots)/slots if slots else None,
        actual_positive_hits=sum(len(set(r['top'])&{i for i,y in r['answers'] if y>=.7}) for r in records),
        ndcg_user_std=pstdev([r['accuracy']['ndcg'] for r in positive]) if positive else None)
    for metric in ('ndcg','precision','recall','hit_rate'):result[metric]=mean(r['accuracy'][metric] for r in positive) if positive else None
    return result


def label_blind_split(history,user,seed=12):
    """Require>=6 unique available items; split by ID hashes, not labels/scores."""
    if len(history)<6 or len({i for i,y in history})!=len(history):raise ValueError('Need5support+heldout')
    ordered=sorted(history,key=lambda p:hashlib.sha256(f'{seed}:v218:support:{user}:{p[0]}'.encode()).hexdigest())
    return ordered[:5],ordered[5:]
