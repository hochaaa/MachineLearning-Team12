"""Evidence gates are manual-review assertions, never an automatic legal opinion."""
import hashlib
from pathlib import Path
REQUIRED = ('download', 'academic_use', 'derivatives', 'privacy_review', 'upstream_terms')
PROTECTED = ('basenotes', 'laure', 'animalcrossingparty', 'atrafshan', 'synthetic', 'v2-14')

def require_permission(evidence):
    """Require version-bound documented approval of each necessary local use.

    Redistribution is recorded separately and is NEVER implied by local permission.
    A reviewer must supply evidence links and an actual review reference; this
    function checks completeness, not the authenticity or validity of legal claims.
    """
    source = evidence.get('source', '').casefold()
    if not source or any(p in source for p in PROTECTED):
        raise PermissionError('Protected, existing, synthetic, or unspecified source')
    if (evidence.get('status') != 'APPROVED_LOCAL' or
        not all(evidence.get(k) is True for k in REQUIRED) or
        not all(evidence.get(k) for k in ('version', 'evidence_urls', 'review_reference'))):
        raise PermissionError('HOLD_LICENSE_UNCLEAR or HOLD_PRIVACY_OR_TERMS')
    return True

def verified_file(path, evidence):
    """Gate before opening a local original; compare the approved SHA256/version."""
    require_permission(evidence)
    path = Path(path)
    # Never ingest the protected project's files via an external-file argument.
    if any(x in str(path).casefold() for x in ('real_user_dataset', 'outputs/final', 'outputs/validation', 'split_manifest')):
        raise PermissionError('Protected evaluation/collector path')
    if not evidence.get('sha256') or not path.is_file():
        raise ValueError('Original file and reviewed SHA256 required')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != evidence['sha256']:
        raise ValueError('Original SHA256 mismatch')
    return digest
