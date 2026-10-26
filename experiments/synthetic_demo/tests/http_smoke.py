"""HTTP integration receipt for an already-running demo. No original assets read."""
import argparse
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def run(base, frontend):
    """base: loopback API URL; frontend: loopback Vite URL, both user-owned."""
    if not base.startswith('http://127.0.0.1:') or not frontend.startswith('http://127.0.0.1:'):
        raise ValueError('Smoke checks must remain on loopback')
    def request(path, body=None):
        data=json.dumps(body).encode() if body is not None else None
        req=Request(base+path,data=data,headers={'Content-Type':'application/json'})
        try:
            with urlopen(req,timeout=5) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    h=request('/api/health');assert h[0]==200 and h[1]['mode']=='demo' and h[1]['candidate_count']==80
    assert request('/api/perfumes?q=rose&mode=notes')[1]['results']
    assert request('/api/perfumes/DEMO-001')[0]==200
    ids=['DEMO-001','DEMO-014','DEMO-038']
    body=lambda values:{'ratings':[{'perfume_id':i,'rating':r} for i,r in zip(ids,values)]}
    a=request('/api/recommend',body([9,7,2]))[1];b=request('/api/recommend',body([2,7,9]))[1]
    assert a['results']!=b['results'] and len(a['results'])==5
    filters={}
    for rules in [[],['woody'],['floral'],['rose'],['woody','floral','rose']]:
        data=body([9,7,2]);data['required_scents']=rules
        code,out=request('/api/recommend',data);assert code==200
        filters['+'.join(rules) or 'none']={'unseen':out['unseen_count'],'eligible':out['eligible_count'],'returned':len(out['results'])}
    errors={}
    for name,value in [('empty',{'ratings':[]}),('unknown',{'ratings':[{'perfume_id':'unknown','rating':7}]}),('range',{'ratings':[{'perfume_id':ids[0],'rating':11}]})]:
        code,_=request('/api/recommend',value);assert code==422;errors[name]=code
    with urlopen(frontend,timeout=5) as r:
        text=r.read().decode();assert 'Synthetic Demo' in text
    return {'result':'PASS','health':h[1],'sensitivity':{'ids':ids,'A':[{'id':r['id'],'score':r['score']} for r in a['results']],'B':[{'id':r['id'],'score':r['score']} for r in b['results']]},'filters':filters,'errors':errors,'frontend_http':200}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='http://127.0.0.1:8002');parser.add_argument('--frontend',default='http://127.0.0.1:5175')
    args=parser.parse_args();print(json.dumps(run(args.base,args.frontend),indent=2))
