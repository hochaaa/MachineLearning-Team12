"""Loopback-only HTTP smoke check; synthetic input, no upload or evaluation labels."""
import json
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:8001'


def request(path, body=None, headers=None, method=None, raw=None):
    """path: API path; body: JSON object; raw: malformed test bytes; no external URL."""
    data = raw if raw is not None else None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE+path, data=data, headers={'Content-Type':'application/json', **(headers or {})}, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        payload = response.read()
        parsed = json.loads(payload) if 'application/json' in response.headers.get('Content-Type','') else payload.decode()
        return response.code, parsed, response.headers


def main():
    """Check fresh local production server, write aggregate observations without ratings."""
    rows=[]
    code,data,_=request('/api/health')
    assert code==200 and data['candidate_count']==479
    rows.append({'check':'health','status':code,'pass':True})
    for q,mode in [('톰포','name'),('톰포두 Black Orchid','name'),('Savage Elixir','name'),
                   ('바닐','notes'),('바니라','notes'),('florel','notes')]:
        code,data,_=request('/api/perfumes?'+urllib.parse.urlencode({'q':q,'mode':mode}))
        assert code==200
        rows.append({'check':q,'status':code,'result_count':len(data['results']),
                     'suggestions':[s['query'] for s in data['suggestions']],'pass':True})
    support=json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())
    ratings=[{'perfume_id':i,'rating':r*10} for i,r in support]
    golden=json.loads((ROOT/'web/evidence/brand-search/recommendations-before.json').read_text())
    for scent,expected in golden.items():
        code,data,_=request('/api/recommend',{'ratings':ratings,'required_scent':scent})
        assert code==200 and data==expected
        rows.append({'check':'recommend_'+scent,'status':code,'full_json_identical':True,'pass':True})
    for origin,allowed in [('http://127.0.0.1:4173',True),('https://evil.invalid',False)]:
        code,_,headers=request('/api/recommend',headers={'Origin':origin,
                'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type'},method='OPTIONS')
        assert ('access-control-allow-origin' in headers)==allowed
        rows.append({'check':'cors_'+str(allowed),'status':code,'pass':True})
    code,data,_=request('/api/recommend',raw=b'{INVALID')
    assert code==422 and 'INVALID' not in json.dumps(data)
    rows.append({'check':'malformed_json','status':code,'pass':True})
    code,_,_=request('/api/recommend',raw=b'x'*65537)
    assert code==413
    rows.append({'check':'body_limit','status':code,'pass':True})
    code,_,_=request('/outputs/final/model.npz')
    assert code==404
    rows.append({'check':'private_file_not_served','status':code,'pass':True})
    out=ROOT/'web/evidence/safe-deployment/live-http.json'
    out.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    print('Local production HTTP checks:',len(rows),'PASS')


if __name__=='__main__':main()
