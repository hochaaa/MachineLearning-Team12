"""Local HMAC pseudonyms remain potentially personal; never publish row outputs."""
import hashlib, hmac, re

def pseudonym(source, user_id, secret):
    """Namespace source and HMAC raw ID with private >=32-byte secret; do not persist it here."""
    if not re.fullmatch(r'[a-z0-9_]+', source) or not str(user_id) or len(secret) < 32:
        raise ValueError('Stable namespace, nonempty identity and private 32-byte key required')
    digest = hmac.new(secret, (source+'\0'+str(user_id)).encode(), hashlib.sha256).hexdigest()
    return 'external_'+source+'_'+digest
