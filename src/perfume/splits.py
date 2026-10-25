"""Deterministic label partitioning independent of rating values."""
import hashlib
from collections import Counter, defaultdict


def partition(rows, seed=12):
    """Hold one validation and one test per >=5 user; retain >=3 train ratings.

    rows: unique normalized (user,item,rating) edges. seed: stable hash salt.
    Lower-activity users are train-only. Hashing item identity avoids RNG/order drift.
    """
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[0]].append(tuple(row))
    if len({(u, i) for u, i, _ in rows}) != len(rows):
        raise ValueError('Split requires unique user/item pairs')
    train, validation, test = [], [], []
    for user, history in sorted(grouped.items()):
        history.sort(key=lambda r: hashlib.sha256(f'{seed}:{user}:{r[1]}'.encode()).hexdigest())
        if len(history) >= 5:
            validation.append(history[0])
            test.append(history[1])
            train.extend(history[2:])
        else:
            train.extend(history)
    assert_disjoint(train, validation, test)
    return train, validation, test


def assert_disjoint(*parts):
    """Raise on any shared (user,item) keys across partitions."""
    seen = set()
    for rows in parts:
        pairs = {(u, i) for u, i, _ in rows}
        if seen & pairs:
            raise ValueError('Label leakage between partitions')
        seen.update(pairs)


def threshold_arms(rows, seed=12):
    """Return threshold->(train,validation,test) with identical >=5 evaluation labels."""
    activity = Counter(u for u, _, _ in rows)
    train, validation, test = partition(rows, seed)
    return {threshold: ([r for r in train if activity[r[0]] >= threshold], validation, test)
            for threshold in (3, 4, 5)}
