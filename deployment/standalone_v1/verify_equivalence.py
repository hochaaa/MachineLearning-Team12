"""Synthetic API parity; no training or evaluation labels. Writes only fresh STEP12 receipts."""
import json,sys,contextlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
from fastapi.testclient import TestClient
from web.backend.app import app as original_app
from web.backend.adapter import FrozenService,SCENTS
from .app import create_app
from .runtime_loader import ROOT,sha256
from .runtime_config import asset_directory
from perfume.models import MatrixFactorization,Content,Baseline
OUT=ROOT/'outputs/step12_runtime'
ACTIVE=False;READS=set();DENIED=[]
def audit(event,args):
    """While standalone is active, deny every legacy outputs/dataset read; track new assets."""
    if not ACTIVE or event!='open' or not isinstance(args[0],(str,bytes)):return
    p=Path(args[0].decode() if isinstance(args[0],bytes) else args[0]).resolve();assets=asset_directory()
    if assets in p.parents:READS.add(str(p.relative_to(assets)));return
    if ROOT/'outputs' in p.parents or ROOT/'Term-project-datasets' in p.parents:
        DENIED.append('legacy_private_access');raise PermissionError('Standalone cannot read legacy private asset')
@contextlib.contextmanager
def standalone_only():
    """Enable the read guard for standalone load or request, then restore guard mode."""
    global ACTIVE
    ACTIVE=True
    try:yield
    finally:ACTIVE=False

def main():
    sys.addaudithook(audit);guards=[patch.object(c,'fit',side_effect=AssertionError('No model fit permitted')) for c in [MatrixFactorization,Content,Baseline]]
    for g in guards:g.start()
    try:
        with TestClient(original_app) as old:
            oldservice=original_app.state.service;ids=list(oldservice.candidates);q_before=sha256(ROOT/'outputs/final/model.npz')
            with standalone_only():newclient=TestClient(create_app());new=newclient.__enter__()
            try:
                patterns={'high':[9,9,9],'low':[1,1,1],'mixed':[9,1,6],'equal':[5,5,5],'zeros':[0,0,0],'float_ten':[.5,10,0]};comparisons=0;maxdiff=0.;queries=0
                def parity(body):
                    nonlocal comparisons,maxdiff
                    a=old.post('/api/recommend',json=body)
                    with standalone_only():b=new.post('/api/recommend',json=body)
                    assert a.status_code==b.status_code==200
                    a,b=a.json(),b.json();ar,br=a['results'],b['results'];assert len(ar)==len(br)==5
                    assert [r['id'] for r in ar]==[r['id'] for r in br] and [r['rank'] for r in ar]==[r['rank'] for r in br]
                    assert not {r['id'] for r in br}&{r['perfume_id'] for r in body['ratings']}
                    for x,y in zip(ar,br):
                        maxdiff=max(maxdiff,abs(x['score']-y['score']));np.testing.assert_allclose(x['score'],y['score'],atol=1e-12,rtol=1e-10)
                        assert {k:v for k,v in x.items() if k!='score'}=={k:v for k,v in y.items() if k!='score'}
                    assert {k:v for k,v in a.items() if k!='results'}=={k:v for k,v in b.items() if k!='results'};comparisons+=1
                for pattern,values in patterns.items():
                    for count in [1,2,3,4,50]:
                        ratings=[{'perfume_id':i,'rating':values[n%len(values)]} for n,i in enumerate(ids[:count])]
                        for scent in SCENTS:parity({'ratings':ratings,'required_scent':scent,'top_k':5})
                    reverse=[{'perfume_id':i,'rating':values[n]} for n,i in enumerate(ids[:3])][::-1]
                    for scent in SCENTS:parity({'ratings':reverse,'required_scent':scent,'top_k':5})
                for mode,texts in [('name',['Tom Ford','TomFord','톰포','톰 포','톰포 Black Orchid','톰포두','입생로 Libre','Dior Sauvage Elixir','','zzzzzznonexistent']),('notes',['바닐','vanill','바니라','베르가','bergam','florel','vanila'])]:
                    for q in texts:
                        a=old.get('/api/perfumes',params={'q':q,'mode':mode})
                        with standalone_only():b=new.get('/api/perfumes',params={'q':q,'mode':mode})
                        assert a.status_code==b.status_code and a.json()==b.json();queries+=1
                errors=[{}, {'ratings':[]},{'ratings':[{'perfume_id':ids[0]}]}, {'ratings':[{'perfume_id':ids[0],'rating':'9'}]}, {'ratings':[{'perfume_id':ids[0],'rating':True}]}, {'ratings':[{'perfume_id':ids[0],'rating':11}]}, {'ratings':[{'perfume_id':ids[0],'rating':-1}]}, {'ratings':[{'perfume_id':'synthetic-unknown','rating':5}]}, {'ratings':[{'perfume_id':ids[0],'rating':5}]*2}, {'ratings':[{'perfume_id':i,'rating':5} for i in ids[:51]]}, {'ratings':[{'perfume_id':ids[0],'rating':5}],'top_k':10}, {'ratings':[{'perfume_id':ids[0],'rating':5}],'required_scent':'price'}]
                for body in errors:
                    a=old.post('/api/recommend',json=body)
                    with standalone_only():b=new.post('/api/recommend',json=body)
                    assert a.status_code==b.status_code==422 and a.json()==b.json()
                for raw in ['{','{"ratings":[{"perfume_id":"x","rating":NaN}]}','{"ratings":[{"perfume_id":"x","rating":Infinity}]}']:
                    a=old.post('/api/recommend',content=raw,headers={'Content-Type':'application/json'})
                    with standalone_only():b=new.post('/api/recommend',content=raw,headers={'Content-Type':'application/json'})
                    assert a.status_code==b.status_code==422 and a.json()==b.json()
                for origin in ['http://127.0.0.1:5173','https://unknown.invalid']:
                    headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type'};a=old.options('/api/recommend',headers=headers)
                    with standalone_only():b=new.options('/api/recommend',headers=headers)
                    assert a.status_code==b.status_code and a.headers.get('access-control-allow-origin')==b.headers.get('access-control-allow-origin')
                assert old.get('/api/health').json()==new.get('/api/health').json()
                assert new.get('/api/health').headers['cache-control']=='no-store'
                assert q_before==sha256(ROOT/'outputs/final/model.npz');assert not DENIED
                result={'status':'PASS','synthetic_support_profiles':36,'valid_recommendation_comparisons':comparisons,'filters':list(SCENTS),'ids_and_order_exact':True,'maximum_absolute_score_difference':maxdiff,'atol':1e-12,'rtol':1e-10,'search_response_comparisons':queries,'invalid_request_comparisons':len(errors)+3,'cors_cases':2,'api_schema_behavior_and_metadata_equal':True,'legacy_private_read_attempts_by_standalone':len(DENIED),'standalone_asset_reads':sorted(READS),'no_old_train_or_user_mapping_needed':True,'original_model_file_unchanged':True,'fit_calls':0,'original_service_source_connected_to_standalone':False}
                with (OUT/'equivalence.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
                print(json.dumps(result,ensure_ascii=False,indent=2))
            finally:
                with standalone_only():newclient.__exit__(None,None,None)
    finally:
        for g in guards:g.stop()
if __name__=='__main__':main()
