"""Preserve raw ratings; affine scale conversion is an assumption, not equivalence."""
import math

def normalize_rating(value, scale):
    """scale: minimum, maximum, zero meaning(valid/missing/unknown), evidence URL.

    Returns None for actual missing values/sentinels; unknown zero is quarantined.
    Output retains raw input/scale and the explicit affine conversion limitation.
    """
    lo, hi = scale['minimum'], scale['maximum']
    if not scale.get('evidence') or not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
        raise ValueError('Documented finite scale required')
    if value is None or value == '': return None
    if isinstance(value, bool): raise ValueError('Boolean is not an explicit rating')
    number = float(value)
    if not math.isfinite(number): raise ValueError('Non-finite rating')
    if number == 0:
        if scale.get('zero') == 'missing': return None
        if scale.get('zero') != 'valid': raise ValueError('Unresolved zero semantics')
    if not lo <= number <= hi: raise ValueError('Out-of-range rating')
    return dict(raw_rating=value, raw_scale=[lo, hi], normalized_rating=10*(number-lo)/(hi-lo),
                transformation='affine_to_0_10', limitation='Ordinal scales may not have equivalent preference meaning')
