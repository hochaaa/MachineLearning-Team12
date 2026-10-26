"""Live Frozen V1 smoke/parity check. No training or evaluation labels.

reference: optional local JSON list of anonymous synthetic support requests and
previous inference results. Never commit reference/output files containing assets.
"""
import argparse
import json
import math
from urllib.request import Request, urlopen


def verify(base, frontend, reference=None):
    """Compare real API rankings to optional reference; only own loopback URLs."""
    if not base.startswith('http://127.0.0.1:') or not frontend.startswith('http://127.0.0.1:'):
        raise ValueError('Use loopback URLs only')
    def request(path,body=None):
        payload=json.dumps(body).encode() if body is not None else None
        with urlopen(Request(base+path,data=payload,headers={'Content-Type':'application/json'}),timeout=15) as response:
            return json.load(response)
    health=request('/api/health')
    assert health['model_loaded'] and health['recommendation_ready'] and health['candidate_count']==479
    if reference:
        with open(reference,encoding='utf-8') as f:cases=json.load(f)
    else:
        found=request('/api/perfumes?q=Tom%20Ford&mode=name')['results']
        assert len(found)>=3
        cases=[{'body':{'ratings':[{'perfume_id':r['id'],'rating':v} for r,v in zip(found[:3],[9,7,2])],'required_scent':s,'top_k':5}} for s in ('none','woody','floral','rose')]
    maximum=0.0;results=[]
    for case in cases:
        body=case['body'];answer=request('/api/recommend',body)
        assert answer['alpha']==.25 and answer['candidate_count']==479
        rows=answer['results'];assert len(rows)==5
        ids=[r['id'] for r in rows];assert len(set(ids))==5
        assert not set(ids)&{r['perfume_id'] for r in body['ratings']}
        assert all(math.isfinite(r['score']) and r['required_satisfied'] for r in rows)
        slim=[{k:r[k] for k in ('id','rank','score')} for r in rows]
        if 'results' in case:
            old=case['results'];assert [r['id'] for r in old]==ids
            assert [r['rank'] for r in old]==[r['rank'] for r in rows]
            for x,y in zip(old,rows):
                maximum=max(maximum,abs(x['score']-y['score']))
                assert math.isclose(x['score'],y['score'],abs_tol=1e-12,rel_tol=1e-10)
        results.append({'body':body,'results':slim})
    with urlopen(frontend,timeout=5) as r:assert 'SCENT MATCH' in r.read().decode()
    return {'status':'PASS','health':health,'comparisons':len(cases),'reference_compared':bool(reference),
            'ids_and_ranks_equal':True if reference else None,'max_absolute_score_difference':maximum if reference else None,
            'atol':1e-12,'rtol':1e-10,'training_calls':0,'evaluation_labels_read':False,'responses':results}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://127.0.0.1:8004');p.add_argument('--frontend',default='http://127.0.0.1:5177');p.add_argument('--reference')
    a=p.parse_args();print(json.dumps(verify(a.base,a.frontend,a.reference),ensure_ascii=False,indent=2))
