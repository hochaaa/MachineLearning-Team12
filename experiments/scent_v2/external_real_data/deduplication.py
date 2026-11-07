"""No arbitrary first/last-wins conflict resolution or cross-source identity merge."""
from collections import defaultdict

def deduplicate(rows):
    """Exact canonical duplicates collapse; conflicting user/item histories quarantine.

    No timestamp-based preference is assumed. Cross-source review versions cannot
    be detected from these minimal fields; report UNKNOWN rather than delete them.
    """
    groups = defaultdict(list)
    for r in rows: groups[(r['source'], r['user_id'], r['perfume_id'])].append(r)
    accepted, conflicts, exact = [], [], 0
    for key in sorted(groups):
        unique = []
        for r in groups[key]:
            if r in unique: exact += 1
            else: unique.append(r)
        if len(unique) == 1: accepted.append(unique[0])
        else: conflicts.extend(unique)
    return accepted, dict(exact_duplicates=exact, conflict_records=len(conflicts),
                         cross_source_person_or_review_overlap='UNKNOWN'), conflicts
