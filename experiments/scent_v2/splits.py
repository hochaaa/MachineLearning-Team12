"""Identity-only five-support splits, shared across every method and track."""
import hashlib
from collections import defaultdict


def digest(text):
    """SHA256 text order; independent of Python's randomized hash()."""
    return hashlib.sha256(text.encode()).hexdigest()


def build(rows, candidates, seed=12):
    """rows: unique normalized triples; candidates: public inference catalog IDs.

    Eligibility uses IDs/counts only. Return train and per-user support/answers
    for each fold. This private structure belongs only to the evaluation harness.
    """
    if len({(u, i) for u, i, _ in rows}) != len(rows):
        raise ValueError('Duplicate user/item pairs')
    histories = defaultdict(list)
    for u, i, r in rows:
        if not 0 <= r <= 1:
            raise ValueError('Expected normalized ratings')
        histories[u].append((i, float(r)))
    pool = set(candidates)
    users = [u for u, h in histories.items()
             if len(h) >= 6 and sum(i in pool for i, _ in h) >= 5]
    users.sort(key=lambda u: digest(f'{seed}:user:{u}'))
    folds = []
    for n in range(3):
        evaluation = users[n::3]
        excluded = set(evaluation)
        train = [tuple(r) for r in rows if r[0] not in excluded]
        support, answers = {}, {}
        for u in evaluation:
            ordered = sorted((i for i, _ in histories[u] if i in pool),
                             key=lambda i: digest(f'{seed}:support:{u}:{i}'))
            seen = set(ordered[:5])
            support[u] = sorted((i, r) for i, r in histories[u] if i in seen)
            answers[u] = sorted((i, r) for i, r in histories[u] if i not in seen)
        fold = dict(fold=n+1, train=train, users=evaluation,
                    support=support, answers=answers)
        validate(fold, candidates)
        folds.append(fold)
    return folds


def validate(fold, candidates):
    """Fail closed on user leakage, support/answer overlap or incorrect support size."""
    train_users = {u for u, _, _ in fold['train']}
    if train_users & set(fold['users']):
        raise ValueError('Evaluation user in training')
    for u in fold['users']:
        s, a = fold['support'][u], fold['answers'][u]
        if len(s) != 5 or len({i for i, _ in s}) != 5 or not a:
            raise ValueError('Need exactly five unique support and nonempty answers')
        if not {i for i, _ in s} <= set(candidates):
            raise ValueError('Support outside service catalog')
        if {i for i, _ in s} & {i for i, _ in a}:
            raise ValueError('Support/answer overlap')
