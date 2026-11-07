"""Support-only cosine profile, exact original weighting, immutable legacy features."""
import hashlib,json,math
from collections import defaultdict
from types import MappingProxyType
from perfume.data import normalize


def canonical_id(brand,name,concentration):
    """Concentration-preserving experiment ID; never replace source or legacy URL IDs."""
    key='\0'.join(normalize(x) for x in (brand,name,concentration))
    return 'v218:'+hashlib.sha256(key.encode()).hexdigest()[:24]


def project(tokens,idf):
    """Binary TF / frozen IDF / L2, no fit, no synonym or accord inference."""
    vector={t:float(idf[t]) for t in set(tokens) if t in idf}
    if any(not math.isfinite(v) or v<=0 for v in vector.values()):raise ValueError('Invalid frozen IDF')
    n=math.sqrt(sum(v*v for v in vector.values()))
    return {t:v/n for t,v in vector.items()} if n else {}


class ContentExperiment:
    """Read-only sparse vectors; scoring receives support and catalog candidates only."""
    def __init__(self,vectors):
        self.vectors=MappingProxyType({i:MappingProxyType(dict(v)) for i,v in vectors.items()})

    def score(self,support,candidates):
        """Exactly five unique finite [0,1] input ratings; never accepts answers.

        Same sum(max(0,r)*x)/norm and cosine as original Content.score. Seen input
        IDs excluded. All-zero/unavailable profile returns NO_USABLE_PROFILE.
        Unobserved candidates are ranked for retrieval, never labeled negatives.
        """
        if len(support)!=5 or len({i for i,r in support})!=5:raise ValueError('Exactly5 distinct support required')
        if any(isinstance(r,bool) or not isinstance(r,(int,float)) or not math.isfinite(r) or not 0<=r<=1 for i,r in support):raise ValueError('Support rating range')
        profile=defaultdict(float)
        for i,r in support:
            for t,v in self.vectors.get(i,{}).items():profile[t]+=max(0,r)*v
        norm=math.sqrt(sum(v*v for v in profile.values()));seen={i for i,r in support}
        pool=sorted(set(candidates)-seen)
        if not norm:return dict(status='NO_USABLE_PROFILE',top=[],scores=[],pool=len(pool),all_scores={})
        values={i:sum(profile[t]*v for t,v in self.vectors.get(i,{}).items())/norm for i in pool}
        # Nonnegative normalized vectors can differ from1 by floating-point error.
        if any(not math.isfinite(v) or v< -1e-12 or v>1+1e-12 for v in values.values()):raise ValueError('Invalid cosine')
        top=sorted(pool,key=lambda i:(-values[i],i))[:5]
        return dict(status='OK',top=top,scores=[values[i] for i in top],pool=len(pool),all_scores=values)


def permission_allows(entry):
    """Require a documented LOCAL_RESEARCH approval per source product before use.

    The caller/reviewer supplies evidence; this checks completeness, not legal
    truth. VERIFIED metadata alone or a generic user click is not a usage grant.
    No new metadata is approved by this source code itself.
    """
    return bool(entry and entry.get('scope')=='LOCAL_NONCOMMERCIAL_RECOMMENDATION_EXPERIMENT'
                and entry.get('reviewed') is True and entry.get('evidence_url') and entry.get('review_reference'))


def candidate_gate(row,vector,permission,existing_keys):
    """Identity+concentration+notes+nonzero+no duplicate+usage; PARTIAL not auto-excluded."""
    if row['identity_verified']!='True':return 'HOLD_IDENTITY'
    if not row['concentration'] or any(s in row['concentration'] for s in ('reference only','UNKNOWN','UNRESOLVED','NOT_CONFIRMED')):return 'HOLD_CONCENTRATION'
    key=tuple(normalize(row[k]) for k in ('official_brand','official_product_name','concentration'))
    if key in existing_keys:return 'HOLD_DUPLICATE'
    if not vector:return 'HOLD_ZERO_OR_NO_NOTES'
    if not permission_allows(permission):return 'HOLD_USAGE_SCOPE_UNVERIFIED'
    return 'APPROVED_FOR_LOCAL_EXPERIMENT_ONLY'
