"""Frozen model bundles and score-only inference; no held-out loader or fit calls."""
from pathlib import Path
import hashlib
import json
from collections import defaultdict
import numpy as np
from .data import read_json
from .improvements import make_mf,ProfileContent
from .models import Baseline,hybrid


def sha256(path):
    """Hash bytes from path for immutable freeze integrity checks."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frozen(directory):
    """Verify frozen files and restore fixed arrays/statistics, without training anything."""
    directory=Path(directory)
    freeze=read_json(directory/'freeze.json')
    for path,expected in freeze['protected_sha256'].items():
        if sha256(path)!=expected:
            raise ValueError(f'Frozen input changed: {path}')
    metadata=read_json(directory/'model.json')
    selected=freeze['selected']
    mf=make_mf(selected['mf'],selected['seed'])
    with np.load(directory/'model.npz') as archive:
        for name in archive.files:
            value=archive[name].copy();value.flags.writeable=False
            setattr(mf,name,value)
    mf.users,mf.items=metadata['users'],metadata['items']
    if 'mean' in metadata:mf.mean=metadata['mean']
    content=ProfileContent(selected['profile_mode'],selected['relevance'])
    representation=read_json(directory/'content.json')
    content.idf,content.vectors=representation['idf'],representation['vectors']
    baseline=Baseline()
    baseline.counts=defaultdict(int,metadata['popularity_counts'])
    baseline.mean,baseline.maximum=metadata['global_mean'],metadata['popularity_maximum']
    return freeze,mf,content,baseline


def score_frozen(support,candidates,mf,content,baseline,alpha,k=10,user=None):
    """Return pure component/baseline/hybrid rankings, using ONLY known support or train user.

    support: item/rating list, candidates: frozen development catalog pool independent of answers.
    user: existing internal user ID; None means new user and fixed-factor ridge fold-in.
    No input or output contains answer labels. Missing pure component scores remain unscorable.
    """
    seen={i for i,_ in support}
    pool=[i for i in candidates if i not in seen]
    if user is None:
        vector=mf.fold_in(support)
        m=mf.score_vector(vector,pool) if vector is not None else np.full(len(pool),np.nan)
    else:m=mf.score(user,pool)
    c,b=content.score(support,pool),baseline.score(pool)
    values={'popularity':b,'content':c,'mf':m,'hybrid':hybrid(c,m,alpha,b)}
    rankings={name:[pool[n] for n in sorted(range(len(pool)),key=lambda n:
                       (-float(scores[n]) if np.isfinite(scores[n]) else float('inf'),pool[n]))
                   if np.isfinite(scores[n])][:k] for name,scores in values.items()}
    return rankings
