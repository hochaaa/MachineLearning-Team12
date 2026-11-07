"""Train-only reference: old fitted P unavailable, so identify inferred P explicitly."""
import json,csv
from types import SimpleNamespace
import numpy as np
from .config import OUT,TUNING
from .pairwise_data import build_pairs
from experiments.scent_v2.recommend import fold_in
from collections import defaultdict


def main():
    """Old Q + all known Train observations per user, no heldout/inference evaluation.

    This measures Train pair accuracy after Ridge re-inference, NOT the unavailable
    original SGD-fitted P. No new fit is called and no accuracy label is tuned on.
    """
    dest=OUT/'baseline_train_pair_reference.csv'
    if dest.exists():raise RuntimeError('Existing reference audit')
    rows=[]
    for o in (1,2,3):
        for f in json.loads((TUNING/f'outer{o}_inner_splits.private.json').read_text()):
            n=f['fold'];stem=f'outer{o}_inner{n}';md=json.loads((TUNING/(stem+'_model.private.json')).read_text())
            with np.load(TUNING/(stem+'_Q.npz'))as a:q=a['Q'].copy()
            mf=SimpleNamespace(Q=q,items=md['items'],reg=.01,factors=4);by=defaultdict(list)
            for u,i,y in f['train']:by[u].append((i,y))
            p={u:fold_in(mf,support)for u,support in by.items()};pairs,_=build_pairs(f['train']);correct=sum(float(np.einsum('i,i->',p[u],q[mf.items[i]]-q[mf.items[j]]))>0 for u,i,j in pairs)
            rows.append(dict(stem=stem,pairs=len(pairs),train_pair_accuracy_ridge_inferred_P=correct/len(pairs),original_fitted_P_pair_accuracy='N/A_not_saved'))
    with dest.open('x',newline='')as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('PASS: Train-only baseline reference, no model fits/new evaluation')

if __name__=='__main__':main()
