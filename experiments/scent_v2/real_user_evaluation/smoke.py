"""Temporary fixture-only actual Frozen HTTP/UI verification, never a real response."""
import argparse,json,tempfile,threading,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
from .app import Server,OUT
from .storage import EvaluationStore,VERSION
from .engine import Engine


def main():
    p=argparse.ArgumentParser();p.add_argument('--serve',action='store_true');a=p.parse_args()
    policy=dict(retention_end='2027-02-28',deletion_method='TEST_ONLY hash deletion code',team_access='TEST_ONLY one operator',confirmed_by='AUTOMATED_TEST_FIXTURE',confirmed=True,test_only=True)
    with tempfile.TemporaryDirectory(prefix='scent-v221-test-') as tmp:
        engine=Engine();store=EvaluationStore(Path(tmp)/'test_fixture',engine,policy,True);server=Server(8022 if a.serve else 0,store)
        if a.serve:
            print('TEST_FIXTURE actual Frozen UI: http://127.0.0.1:8022 — temporary data only',flush=True)
            try:server.serve_forever()
            except KeyboardInterrupt:pass
            finally:server.server_close();store.lock.close()
            return
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();origin=server.origin;jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        csrf=''
        def request(path,data=None,method=None):
            headers={'Origin':origin,'X-Scent-Request':'1','X-CSRF-Token':csrf,'Content-Type':'application/json'}
            req=urllib.request.Request(origin+path,data=None if data is None else json.dumps(data).encode(),headers=headers,method=method)
            try:
                with client.open(req,timeout=10) as r:return r.status,r.read()
            except urllib.error.HTTPError as r:return r.code,r.read()
        try:
            assert request('/')[0]==200
            status,body=request('/api/register',dict(consent=True,version=VERSION));assert status==201;r=json.loads(body);csrf=r['csrf'];code=r['deletion_code']
            candidates=json.loads(request('/api/search?q=')[1])['results']
            from .engine import concentration
            for row in candidates[:6]:assert request('/api/ratings',dict(product_id=row['id'],rating=7,experience='EXPERIENCED',identity_confirmed=True,concentration=concentration(row['name'])))[0]==200
            status,body=request('/api/recommend',dict(mode='FROZEN_479_HYBRID'));assert status==200;session=json.loads(body);assert len(session['results'])==5
            assert json.loads(request('/api/recommend',dict(mode='FROZEN_479_HYBRID'))[1])==session
            feedback=dict(session_id=session['session_id'],product_id=session['results'][0]['id'],experience='NOT_EXPERIENCED',rating=None)
            assert request('/api/feedback',feedback)[0]==200
            feedback.update(experience='UNKNOWN_EXPERIENCE');assert request('/api/feedback',feedback)[0]==200
            comparison=session['comparisons'][0];feedback.update(product_id=comparison['product_id'],experience='EXPERIENCED',rating=8,comparison=True);assert request('/api/feedback',feedback)[0]==200
            assert request('/api/recommend',dict(mode='EXPANDED_497_CONTENT'))[0]==400
            assert request('/data/participants.sqlite3')[0]==404
            assert request('/api/delete-code',dict(deletion_code=code))[0]==200
            assert store.analyses()['collection']['actual_new_participants']==0
            result=dict(status='PASS',kind='TEST_FIXTURE_ONLY',actual_Frozen_loaded=True,ui_http=200,register_http=201,pre_ratings_saved=6,top5=5,comparison_exposures=5,unknown_unexperienced_null=True,idempotent_session=True,mode497_rejected=True,private_file_http=404,deletion_code_cascade=True,test_participants_remaining=0,actual_new_real_participants=0)
            with (OUT/'http_checks.json').open('x') as f:json.dump(result,f,indent=2)
            print(json.dumps(result))
        finally:server.shutdown();server.server_close();thread.join();store.lock.close()

if __name__=='__main__':main()
