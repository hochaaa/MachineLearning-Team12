"""Known-factor-only decomposition and exact fallback invariance audit.

Uses only newly saved V2-2 score arrays; does not fit or score any model. Kept
separate so completed diagnostic outputs/code are never overwritten for additions.
"""
import json,csv,hashlib
from collections import defaultdict
import numpy as np
from .config import OUT
from .analysis import mean_finite


def main():
    """Write new exclusive supplement artifacts; stop on any output collision."""
    paths=[OUT/'known_factor_contributions.csv',OUT/'fallback_invariance.json']
    if any(p.exists()for p in paths):raise RuntimeError('Supplement exists; no overwrite')
    with np.load(OUT/'candidate_scores.private.npz')as archive:a={k:archive[k]for k in archive.files}
    meta=json.loads((OUT/'candidate_metadata.private.json').read_text())
    contexts=json.loads((OUT/'context_results.private.json').read_text())['contexts']
    output=[];by_context=defaultdict(dict);maxdiff=0.
    for n,r in enumerate(meta):
        key=(r['outer'],r['inner'],r['user']);by_context[key][r['lambda']]=n
        known=a['factor_exists'][n]&~a['fallback'][n];h=a['hybrid'][n]
        c=a['nominal_content'][n,known];m=a['nominal_mf'][n,known]
        variance_c=float(np.var(c));variance_m=float(np.var(m));cov=float(np.mean((c-c.mean())*(m-m.mean())))
        assert abs(variance_c+variance_m+2*cov-float(np.var(h[known])))<1e-12
        top=np.argsort(-h,kind='stable')[:5];top_known=top[known[top]]
        output.append(dict(user=r['user'],**{'lambda':r['lambda']},content_variance=variance_c,
            mf_variance=variance_m,twice_covariance=2*cov,hybrid_variance=float(np.var(h[known])),
            known_top5_mf_score_fraction=float(np.sum(a['nominal_mf'][n,top_known])/np.sum(h[top_known]))if len(top_known)else None))
    for key,indices in by_context.items():
        baseline=indices[.01]
        for lam in (.1,1.):
            n=indices[lam];assert meta[n]['pool']==meta[baseline]['pool']
            np.testing.assert_array_equal(a['factor_exists'][n],a['factor_exists'][baseline])
            np.testing.assert_array_equal(a['fallback'][n],a['fallback'][baseline])
            np.testing.assert_array_equal(a['content'][n],a['content'][baseline])
            mask=a['fallback'][baseline]
            diff=float(np.max(abs(a['hybrid'][n,mask]-a['hybrid'][baseline,mask])))
            maxdiff=max(maxdiff,diff);assert diff==0
    grouped=defaultdict(list)
    for r in output:grouped[r['lambda'],r['user']].append(r)
    collapsed={}
    for lam in (.01,.1,1.):
        rs=[{k:mean_finite([r[k]for r in values])for k in values[0]if k not in ('user','lambda')}
            for (l,u),values in grouped.items()if l==lam]
        collapsed[lam]=dict(**{'lambda':lam},users=len(rs),**{k:mean_finite([r[k]for r in rs])for k in rs[0]})
    with paths[0].open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(collapsed[.01]));w.writeheader();w.writerows(collapsed.values())
    indexed={(r['outer'],r['inner'],r['user'],r['lambda']):r for r in contexts}
    monotonic={}
    for lam in (.1,1.):
        monotonic[lam]=dict(contexts=150,
            vector_norm_decreased=sum(indexed[*key,lam]['vector_norm']<indexed[*key,.01]['vector_norm']for key in by_context),
            raw_mean_decreased=sum(indexed[*key,lam]['mf_raw_mean']<indexed[*key,.01]['mf_raw_mean']for key in by_context))
    result=dict(status='PASS',contexts=150,unique_users=75,content_and_fallback_masks_exactly_same=True,
                maximum_fallback_score_change=maxdiff,monotonic_counts=monotonic,new_model_fits=0,
                supplement_source_sha256=hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest())
    with paths[1].open('x')as f:json.dump(result,f,indent=2)
    print(json.dumps(result));print(json.dumps(list(collapsed.values())))


if __name__=='__main__':main()
