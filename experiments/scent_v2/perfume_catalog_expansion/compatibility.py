"""Read-only transformation with frozen IDF; no synonym inference or refitting."""
import math
from perfume.data import normalize


def feature_tokens(notes, accords):
    """notes/accords: literal verified labels, with distinct channel prefixes.

    Apply unmodified original normalize. Do not singularize musks, strip qualifiers,
    remove the word accord, substitute molecules or infer accords from note names.
    """
    output=set()
    for prefix, values in [('note:',notes),('accord:',accords)]:
        for value in values:
            value=normalize(value)
            if value not in ('','unknown','nan','na'):output.add(prefix+value)
    return output


def transform(tokens,idf):
    """Same binary-TF/IDF/L2 equation as src/perfume/models.py::Content.fit transform.

    idf is existing frozen dictionary; OOV tokens omitted. Returns an empty sparse
    mapping if all observed tokens are OOV, without creating vocabulary entries.
    Empty metadata must be distinguished from a measured zero vector by caller.
    """
    vector={t:float(idf[t]) for t in set(tokens) if t in idf}
    if any(not math.isfinite(v) or v<=0 for v in vector.values()):raise ValueError('Invalid frozen IDF')
    length=math.sqrt(sum(v*v for v in vector.values()))
    return {t:v/length for t,v in vector.items()} if length else {}


def coverage(tokens,vocabulary):
    """Unique labels by channel; None for an empty denominator, never fake0%."""
    result={}
    for channel in ('note:','accord:'):
        observed={t for t in tokens if t.startswith(channel)}
        known=observed & set(vocabulary)
        result[channel[:-1]]=dict(observed_unique=len(observed),known_unique=len(known),
            known_fraction=len(known)/len(observed) if observed else None,
            out_of_vocabulary=sorted(observed-known))
    return result
