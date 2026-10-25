"""Clean-copy service smoke checks only; never runs old evidence-writing tests.

--root clone directory, --phase missing|ready, --output fresh JSON path.
Independent interpreter imports only the target copy and its installed packages.
"""
import argparse,json,sys,os,hashlib,platform
from pathlib import Path
from unittest.mock import patch

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--phase',choices=['missing','ready'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root.resolve();os.chdir(root);sys.path.insert(0,str(root))
    from web.backend.app import app
    from fastapi.testclient import TestClient
    from perfume.models import MatrixFactorization,Content,Baseline
    import numpy as np
    guards=[patch.object(c,'fit',side_effect=AssertionError('No fitting in setup checks')) for c in [MatrixFactorization,Content,Baseline]]
    for g in guards:g.start()
    try:
        with TestClient(app) as client:
            health=client.get('/api/health').json()
            if a.phase=='missing':
                assert not health['recommendation_ready'];assert client.get('/api/perfumes',params={'q':'Dior'}).status_code==503;result={'status':'EXPECTED_BLOCKED_PRIVATE_ASSETS_MISSING','candidate_count':health['candidate_count']}
            else:
                assert health['recommendation_ready'] and health['candidate_count']==479
                service=app.state.service;records=[]
                for q in ['Dior Sauvage Elixir','Bleu de Chanel Parfum','Tom Ford Black Orchid']:
                    found=client.get('/api/perfumes',params={'q':q}).json()['results'];assert found;records.append(found[0]['id'])
                body={'ratings':[{'perfume_id':i,'rating':r} for i,r in zip(records,[9,8,2])],'top_k':5}
                rankings={}
                for condition in ['none','woody','floral','rose']:
                    response=client.post('/api/recommend',json={**body,'required_scent':condition});assert response.status_code==200;d=response.json();rows=d['results'];assert len(rows)==5 and len({r['id'] for r in rows})==5
                    assert not set(records)&{r['id'] for r in rows};assert all(np.isfinite(r['score']) for r in rows)
                    assert all(r['id'] in service.allowed and r['required_satisfied'] for r in rows)
                    rankings[condition]=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                assert client.post('/api/recommend',json=body).json()==client.post('/api/recommend',json=body).json()
                result={'status':'PASS','candidate_count':479,'searches':3,'top5_conditions':4,'repeat_deterministic':True,'synthetic_response_sha256':rankings}
            result.update({'python':platform.python_version(),'machine':platform.machine(),'isolated_venv':sys.prefix!=sys.base_prefix,'system_site_packages':False,'numpy_location_in_independent_venv':Path(np.__file__).is_relative_to(Path(sys.prefix)),'mf_fits':0,'legacy_answers_read':False})
        with a.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
        print(result['status'])
    finally:
        for g in guards:g.stop()
if __name__=='__main__':main()
