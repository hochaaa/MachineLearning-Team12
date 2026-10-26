"""Synthetic-only STEP9 service audit. Never trains or reads evaluation answers.

Parameters: no CLI arguments. Uses fixed public demo products with invented scores.
Writes only new STEP9 aggregate evidence; mocks affect this process only.
"""
import sys,json,time,statistics,subprocess,resource,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from web.backend.app import app
from web.backend.adapter import FrozenService,SCENTS
from fastapi.testclient import TestClient
from perfume.models import MatrixFactorization,Content,Baseline
import numpy as np
OUT=ROOT/'outputs/step9_audit'
checks=[]
def check(name,ok,detail=''):
    checks.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':detail})
def live(path,body=None,port=8000):
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with op.open(req,timeout=20) as r:return json.load(r)
def summarize(values):return {'n':len(values),'mean_seconds':statistics.mean(values),'max_seconds':max(values),'median_seconds':statistics.median(values)}
def main():
    guards=[patch.object(c,'fit',side_effect=AssertionError('STEP9 training forbidden')) for c in [MatrixFactorization,Content,Baseline]]
    for g in guards:g.start()
    timings=[];loads=[];reference=None
    try:
        for _ in range(3):
            t=time.perf_counter();s=FrozenService();loads.append(time.perf_counter()-t)
        with TestClient(app) as client:
            s=app.state.service;ids=list(s.candidates)[:4]
            # Public perfume IDs paired with invented ratings; no real user histories.
            base={'ratings':[{'perfume_id':i,'rating':r} for i,r in zip(ids,[9,1,6])],'top_k':5,'required_scent':'none'}
            arrays={k:v.copy() for k,v in vars(s.mf).items() if isinstance(v,np.ndarray)}
            scenarios={'high':[9,9,9],'low':[1,1,1],'mixed':[9,1,6],'zero':[0,7,3],'ten':[10,8,2],'float':[8.5,1.5,6.5]}
            for name,ratings in scenarios.items():
                body={**base,'ratings':[{'perfume_id':i,'rating':v} for i,v in zip(ids,ratings)]}
                for scent,token in SCENTS.items():
                    body['required_scent']=scent;t=time.perf_counter();response=client.post('/api/recommend',json=body);timings.append(time.perf_counter()-t)
                    d=response.json();rows=d.get('results',[])
                    ok=response.status_code==200 and len(rows)==5 and len({r['id'] for r in rows})==5 and not {i for i in ids[:3]}&{r['id'] for r in rows}
                    ok=ok and all(r['id'] in s.allowed and np.isfinite(r['score']) and r['name']==s.catalog[r['id']]['name'] and r['brand']==s.catalog[r['id']]['brand'] for r in rows)
                    ok=ok and [r['rank'] for r in rows]==[1,2,3,4,5] and [(-r['score'],r['id']) for r in rows]==sorted((-r['score'],r['id']) for r in rows)
                    if token:ok=ok and all(token in s.catalog[r['id']]['tokens'] and r['required_satisfied'] for r in rows)
                    check('scenario/'+name+'/'+scent,ok)
            reference=client.post('/api/recommend',json=base).json()
            check('repeat20',all(client.post('/api/recommend',json=base).json()==reference for _ in range(20)))
            check('input_order',client.post('/api/recommend',json={**base,'ratings':list(reversed(base['ratings']))}).json()==reference)
            for n in [1,2,4]:
                body={**base,'ratings':[{'perfume_id':i,'rating':7} for i in ids[:n]]}
                check('contract/'+str(n)+'_perfumes',client.post('/api/recommend',json=body).status_code==200,'Existing API supports1..50; UI recommends>=3')
            invalid={
                'duplicate':{'ratings':[base['ratings'][0]]*2},'unknown':{'ratings':[{'perfume_id':'synthetic-unknown','rating':5}]},
                'negative':{'ratings':[{'perfume_id':ids[0],'rating':-1}]},'over10':{'ratings':[{'perfume_id':ids[0],'rating':11}]},
                'string':{'ratings':[{'perfume_id':ids[0],'rating':'7'}]},'missing_rating':{'ratings':[{'perfume_id':ids[0]}]},
                'empty':{},'empty_ratings':{'ratings':[]},'boolean':{'ratings':[{'perfume_id':ids[0],'rating':True}]}}
            for name,body in invalid.items():check('reject/'+name,client.post('/api/recommend',json=body).status_code==422)
            check('reject/malformed_json',client.post('/api/recommend',content='{',headers={'Content-Type':'application/json'}).status_code==422)
            with patch.object(app.state,'service',None):
                check('mock/model_unavailable_health',not client.get('/api/health').json()['recommendation_ready'])
                check('mock/model_unavailable_api',client.post('/api/recommend',json=base).status_code==503)
            with patch('web.backend.app.FrozenService',side_effect=FileNotFoundError('Synthetic missing asset')):
                with TestClient(app) as missing:check('mock/missing_model_startup',not missing.get('/api/health').json()['model_loaded'])
            app.state.service=s
            with patch.object(s,'recommend',side_effect=KeyError('Synthetic missing metadata')):
                check('mock/missing_metadata',client.post('/api/recommend',json=base).status_code==500)
            with patch('web.backend.adapter.knowledge',return_value=[]):
                check('mock/no_candidates',client.post('/api/recommend',json=base).json()['results']==[])
            for key,value in arrays.items():check('immutable/'+key,np.array_equal(value,getattr(s.mf,key)) and not getattr(s.mf,key).flags.writeable)
            check('live/backend_ready',live('/api/health')['recommendation_ready'])
            check('live/frontend_proxy',live('/api/health',port=5173)==live('/api/health'))
            live_times=[]
            for _ in range(20):
                t=time.perf_counter();result=live('/api/recommend',base);live_times.append(time.perf_counter()-t);assert result==reference
            check('live/repeat20_json_parity',True)
            golden=json.loads((ROOT/'web/evidence/brand-search/recommendations-before.json').read_text())
            support=json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())
            for scent in SCENTS:
                body={'ratings':[{'perfume_id':i,'rating':r*10} for i,r in support],'required_scent':scent,'top_k':5}
                check('original_golden/'+scent,live('/api/recommend',body)==golden[scent])
        # Isolated, owned cold-server probe; never stops an existing process.
        server_times=[]
        for n in range(2):
            with (OUT/f'owned_server_{n}.log').open('x') as log:
                t=time.perf_counter();proc=subprocess.Popen([sys.executable,'-B','-m','uvicorn','web.backend.app:app','--host','127.0.0.1','--port','18009','--no-access-log','--log-level','warning'],cwd=ROOT,stdout=log,stderr=log)
                try:
                    assert proc.poll() is None
                    for _ in range(200):
                        try:
                            ready=live('/api/health',port=18009)['recommendation_ready']
                            if ready:break
                        except (OSError,ValueError):pass
                        if proc.poll() is not None:raise RuntimeError('Owned probe did not start')
                        time.sleep(.05)
                    else:raise RuntimeError('Owned probe timeout')
                    server_times.append(time.perf_counter()-t)
                finally:
                    proc.terminate();proc.wait(timeout=10)
        result={'checks':checks,'status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL','model_load':summarize(loads),'testclient_top5':summarize(timings),'live_api_top5':summarize(live_times),'owned_backend_cold_start':summarize(server_times),'peak_audit_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'memory_scope':'macOS full audit process peak, not isolated model memory','mf_fits':0,'old_labels_read':False,'service_source_modified':False,'existing_server_stopped':False}
        with (OUT/'service_checks.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
        print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2));print('CHECKS',len(checks));assert result['status']=='PASS'
    finally:
        for g in guards:g.stop()
if __name__=='__main__':main()
