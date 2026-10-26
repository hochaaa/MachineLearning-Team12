"""Clean-clone-only smoke test. Requires minimal assets; old runtime files must be absent.

--assets local new asset path; --output fresh receipt. No original data or labels.
"""
import argparse,json,os,sys,platform,socket,subprocess,time,urllib.request,urllib.parse
from pathlib import Path
from unittest.mock import patch

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    from .runtime_config import ROOT
    legacy=['Term-project-datasets/fra_cleaned.csv','outputs/validation/train_exclude_3.json','outputs/final/model.json','outputs/final/model.npz','outputs/final/content.json','outputs/final/freeze.json','outputs/improvement/selection.json','outputs/improvement/candidates.json']
    assert all(not (ROOT/n).exists() for n in legacy),'Use clean copy, never delete original assets'
    attempted=[]
    def deny(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        name=Path(args[0].decode() if isinstance(args[0],bytes) else args[0]).resolve()
        if name==a.assets.resolve() or a.assets.resolve() in name.parents:return
        if ROOT/'outputs' in name.parents or ROOT/'Term-project-datasets' in name.parents:attempted.append('legacy_private_open');raise PermissionError('No legacy private assets in clean runtime')
    sys.addaudithook(deny)
    from .app import create_app
    from .runtime_loader import StandaloneService
    from fastapi.testclient import TestClient
    from perfume.models import MatrixFactorization,Content,Baseline
    import numpy as np
    guards=[patch.object(c,'fit',side_effect=AssertionError('No training')) for c in [MatrixFactorization,Content,Baseline]]
    for g in guards:g.start()
    try:
        service=StandaloneService(a.assets);assert not hasattr(service.mf,'users') and not hasattr(service.mf,'P')
        assert ROOT in Path(sys.modules['web.backend.adapter'].__file__).resolve().parents
        with TestClient(create_app(a.assets)) as client:
            assert client.get('/api/health').json()['recommendation_ready'];items=[]
            for q in ['Dior Sauvage Elixir','Bleu de Chanel Parfum','Tom Ford Black Orchid']:
                found=client.get('/api/perfumes',params={'q':q}).json()['results'];assert found;items.append(found[0]['id'])
            body={'ratings':[{'perfume_id':i,'rating':r} for i,r in zip(items,[9,8,2])],'top_k':5}
            for scent in ['none','woody','floral','rose']:
                response=client.post('/api/recommend',json={**body,'required_scent':scent});assert response.status_code==200 and len(response.json()['results'])==5
            assert client.post('/api/recommend',json={}).status_code==422
        with TestClient(create_app(a.assets/'missing')) as missing:
            assert not missing.get('/api/health').json()['recommendation_ready'];assert missing.get('/api/perfumes',params={'q':'Dior'}).status_code==503
        assert not attempted
        # Independently start and stop ONLY this temporary standalone ASGI process.
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',18112))==0:raise RuntimeError('Probe port occupied; leave existing processes alone')
        env={**os.environ,'SCENT_MATCH_STANDALONE_ASSETS':str(a.assets.resolve()),'PYTHONDONTWRITEBYTECODE':'1'}
        log=(a.output.parent/'standalone-server.log').open('x');proc=subprocess.Popen([sys.executable,'-B','-m','uvicorn','deployment.standalone_v1.app:create_app','--factory','--host','127.0.0.1','--port','18112','--no-access-log'],cwd=ROOT,env=env,stdout=log,stderr=log)
        def http(route,data=None):
            req=urllib.request.Request('http://127.0.0.1:18112'+route,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=10) as r:return json.load(r)
        try:
            for _ in range(150):
                try:
                    if http('/api/health')['recommendation_ready']:break
                except OSError:pass
                if proc.poll() is not None:raise RuntimeError('Owned standalone process failed')
                time.sleep(.05)
            else:raise RuntimeError('Owned standalone startup timeout')
            assert len(http('/api/recommend',body)['results'])==5
        finally:
            if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
            log.close()
        result={'status':'PASS','python':platform.python_version(),'machine':platform.machine(),'fresh_venv':sys.prefix!=sys.base_prefix,'numpy_in_fresh_venv':Path(np.__file__).is_relative_to(Path(sys.prefix)),'legacy_runtime_files_absent':len(legacy),'minimal_files':5,'users_mapping_absent':True,'user_factors_absent':True,'searches':3,'filters':4,'top5':True,'bad_input_422':True,'missing_assets_health_false_api503':True,'legacy_read_attempts':len(attempted),'owned_standalone_http_server_top5':True,'existing_servers_modified':False,'training_calls':0,'windows':'NOT TESTED'}
        with a.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        for g in guards:g.stop()
if __name__=='__main__':main()
