"""Pure preparation functions; never train, evaluate, publish or read V2-14 storage."""
from .license_audit import require_permission
from .schema_inspection import validate
from .rating_normalization import normalize_rating
from .user_id_mapping import pseudonym
from .perfume_matching import match
from .deduplication import deduplicate
from datetime import datetime

def prepare(rows, evidence, scale, catalog, secret):
    """Rights gate precedes iteration; return minimal matched rows, aggregate audit.

    Input is already canonically mapped explicit real records. No raw user fields
    survive output. Possible same-person overlap is NOT cured by pseudonymization.
    """
    require_permission(evidence)
    results, statuses = [], {}
    for r in rows:
        validate(r)
        result = match(r, catalog); status = result['status']
        statuses[status] = statuses.get(status, 0)+1
        if result['item'] is None: continue
        rating = normalize_rating(r['rating'], scale)
        if rating is None: continue
        timestamp = r.get('rating_timestamp')
        if timestamp is not None:
            # Preserve supplied observation versions; never infer dates or latest-wins.
            if not isinstance(timestamp, str): raise ValueError('ISO timestamp required')
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        results.append(dict(user_id=pseudonym(evidence['source'], r['user_id'], secret),
                            perfume_id=result['item'], source=evidence['source'], rating_timestamp=timestamp, **rating))
    clean, duplicate_audit, conflicts = deduplicate(results)
    return clean, dict(match_status_records=statuses, **duplicate_audit), conflicts

def assemble(legacy_safe, external, candidates, excluded_users, *, overlap_verified=False):
    """Use ONLY previously filtered legacy train, never the full 1805-row archive.

    Caller supplies excluded evaluation identities before any rating access. All
    external records remain quarantined when cross-source overlap is unresolved.
    A reviewer assertion overlap_verified is not independent identity evidence.
    Full archive integration must be separately approved; this code does not read it.
    """
    output = []
    for u,i,y in legacy_safe:
        if u in excluded_users: raise ValueError('Evaluation history reached builder')
        if i in candidates: output.append(dict(user_id=u, perfume_id=i, normalized_rating=y*10, source='legacy_train'))
    for r in external:
        if r['perfume_id'] not in candidates or r['user_id'] in excluded_users:
            raise ValueError('Candidate or evaluation boundary violation')
    if external and not overlap_verified:
        return output, dict(external_quarantined=len(external), independence='NOT_ESTABLISHED')
    output.extend(external)
    return output, dict(external_quarantined=0, independence='REVIEWER_VERIFIED' if external else 'NO_EXTERNAL_ROWS')
