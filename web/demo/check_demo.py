"""Local presentation smoke check. Synthetic-only inference, original golden+hashes.

No training, evaluation labels, installation, external URL, or server restart.
"""
import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
import urllib.parse

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from manager import ROOT, verify_frozen


class LoopbackClient:
    """port: local service TCP port. No proxy use or redirect following."""
    def __init__(self,port):
        self.base=f'http://127.0.0.1:{port}'
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,req,fp,code,msg,headers,newurl):return None
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())

    def request(self,path,body=None):
        """path: relative local path; optional body: synthetic JSON. Return parsed JSON."""
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
                                   headers={'Content-Type':'application/json'})
        with self.opener.open(req,timeout=10) as response:
            if response.status!=200:raise ValueError('HTTP status')
            data=response.read(2*1024*1024)
            return json.loads(data) if 'application/json' in response.headers.get('Content-Type','') else data

    def search(self,q,mode='name'):
        """q: synthetic search text; mode:name/notes. Never logs a user request body."""
        return self.request('/api/perfumes?'+urllib.parse.urlencode({'q':q,'mode':mode}))


def run(backend_port=8000,frontend_port=5173):
    """Return per-check statuses and synthetic response objects; no output file by default."""
    backend,front=LoopbackClient(backend_port),LoopbackClient(frontend_port)
    checks=[]; results={}; searches={}
    def check(name,fn):
        try:
            if fn() is not True:raise ValueError('assertion')
            checks.append({'check':name,'status':'PASS'})
        except Exception:
            checks.append({'check':name,'status':'FAIL','reason':'로컬 서버·후보·golden 또는 파일 무결성을 확인하세요.'})
    print('SCENT MATCH — DEMO READINESS CHECK')
    check('Backend health',lambda:backend.request('/api/health')['recommendation_ready'] is True)
    check('Frontend reachable',lambda:b'SCENT MATCH' in front.request('/'))
    check('Candidate pool: 479',lambda:backend.request('/api/health')['candidate_count']==479)
    check('Frontend API proxy',lambda:front.request('/api/health')==backend.request('/api/health'))
    def search_check():
        for q,mode in [('톰포','name'),('톰포 Black Orchid','name'),('톰포두','name'),
                       ('바닐','notes'),('vanill','notes'),('바니라','notes')]:
            searches[q]=backend.search(q,mode)
        return all(searches[q]['results'] and all(r['brand']=='tom-ford' for r in searches[q]['results'])
                   for q in ('톰포','톰포 Black Orchid'))
    check('Brand search',search_check)
    check('Note search',lambda:all(bool(searches[q]['results']) for q in ('바닐','vanill')))
    check('Typo suggestions',lambda:searches['톰포두']['suggestions'][0]['query']=='톰포드'
          and searches['바니라']['suggestions'][0]['query']=='바닐라')
    support=json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())
    golden=json.loads((ROOT/'web/evidence/brand-search/recommendations-before.json').read_text())
    check('Three demonstration perfumes',lambda:all(any(r['id']==i for r in backend.search(q)['results'])
          for (i,_),q in zip(support,['Dior Sauvage Elixir','Bleu de Chanel Parfum','Tom Ford Black Orchid'])))
    body={'ratings':[{'perfume_id':i,'rating':r*10} for i,r in support],'top_k':5}
    for scent,label,token in [('none','Hybrid recommendation',None),('woody','Woody filter','woody'),
                              ('floral','Floral filter','floral'),('rose','Rose filter','rose')]:
        def recommendation(scent=scent,token=token):
            result=backend.request('/api/recommend',{**body,'required_scent':scent});results[scent]=result
            rows=result['results']
            field='notes' if scent=='rose' else 'accords'
            return result==golden[scent] and len(rows)==5 and len({r['id'] for r in rows})==5 and all(
                token in r[field] for r in rows) if token else result==golden[scent] and len(rows)==5
        check(label,recommendation)
    check('Full recommendation JSON equals original golden',lambda:results==golden)
    check('Frozen model integrity (19 + manifest)',verify_frozen)
    for c in checks:print('['+c['status']+'] '+c['check'])
    ok=all(c['status']=='PASS' for c in checks)
    print('RESULT: '+('READY FOR LOCAL DEMO' if ok else 'NOT READY — 확인이 필요합니다'))
    return {'checks':checks,'result':'READY FOR LOCAL DEMO' if ok else 'NOT READY',
            'offline':'NOT VERIFIED (no system internet block)', 'recommendations':results,'searches':searches}


def main():
    """Optional --output saves synthetic-only evidence; ports support isolated lifecycle QA."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend-port',type=int,default=8000);p.add_argument('--frontend-port',type=int,default=5173)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    if not all(1024<=port<=65535 for port in (args.backend_port,args.frontend_port)):
        p.error('Invalid local ports')
    result=run(args.backend_port,args.frontend_port)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['result']=='READY FOR LOCAL DEMO' else 1


if __name__=='__main__':raise SystemExit(main())
