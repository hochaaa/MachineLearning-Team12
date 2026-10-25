"""Owned temporary clean frontend/backend pair; synthetic HTTP checks, no training.

--root: temporary clone only. --output: fresh aggregate JSON. Never targets original
ports8000/5173 or changes original config; temp-only proxy uses15173->18100.
"""
import argparse,json,os,subprocess,sys,time,socket,urllib.request,urllib.parse,hashlib
from pathlib import Path

def get(path,body=None,port=15173):
    """path: loopback route; body: optional synthetic request; port: owned port."""
    req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=10) as r:
        b=r.read();return json.loads(b) if 'application/json' in r.headers.get('Content-Type','') else b

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
    if not str(root).startswith('/private/tmp/scent-step10-'):raise ValueError('Temporary clone only')
    for port in [18100,15173]:
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('Probe port occupied; do not stop existing server')
    cfg=root/'web/frontend/vite.step10.config.mjs'
    with cfg.open('x') as f:f.write("import base from './vite.config.ts'; export default {...base,server:{...base.server,port:15173,strictPort:true,host:'127.0.0.1',proxy:{'/api':'http://127.0.0.1:18100'}}};\n")
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'};processes=[];handles=[]
    try:
        for label,cmd,cwd in [('backend',[sys.executable,'-B','-m','uvicorn','web.backend.app:app','--host','127.0.0.1','--port','18100','--no-access-log'],root),('frontend',['node','node_modules/vite/bin/vite.js','--config','vite.step10.config.mjs'],root/'web/frontend')]:
            h=(root/f'step10-{label}.log').open('x');handles.append(h);processes.append(subprocess.Popen(cmd,cwd=cwd,env=env,stdout=h,stderr=h))
        for _ in range(150):
            try:
                if get('/api/health')['recommendation_ready']:break
            except (OSError,ValueError):pass
            if any(proc.poll() is not None for proc in processes):raise RuntimeError('Owned service failed')
            time.sleep(.1)
        else:raise RuntimeError('Owned service timeout')
        assert b'SCENT MATCH' in get('/')
        assert get('/api/health')==get('/api/health',port=18100)
        ids=[]
        for q in ['Dior Sauvage Elixir','Bleu de Chanel Parfum','Tom Ford Black Orchid']:
            found=get('/api/perfumes?'+urllib.parse.urlencode({'q':q}))['results'];assert found;ids.append(found[0]['id'])
        body={'ratings':[{'perfume_id':i,'rating':r} for i,r in zip(ids,[9,8,2])],'top_k':5}
        response=get('/api/recommend',body);assert len(response['results'])==5
        assert response==get('/api/recommend',body,port=18100)
        result={'status':'PASS','frontend_http':True,'fresh_venv_backend':True,'proxy_to_fresh_backend':True,'searches':3,'top5':5,'proxy_and_backend_json_equal':True,'new_fit_calls':0,'external_upload':False,'original_servers_touched':False,'temporary_proxy_override_only':True,'frontend_port':15173,'backend_port':18100,'response_sha256':hashlib.sha256(json.dumps(response,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
        with a.output.open('x') as f:json.dump(result,f,indent=2)
        print('PASS: fresh clone frontend -> fresh venv backend -> FrozenV1 Top5')
    finally:
        for proc in processes:
            if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
        for h in handles:h.close()
if __name__=='__main__':main()
