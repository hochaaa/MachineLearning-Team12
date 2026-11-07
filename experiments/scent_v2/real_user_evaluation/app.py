"""V2-14 HTTP security/parser/styles reused; new loopback app, no existing API changes."""
import argparse,json
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from experiments.scent_v2.real_user_dataset.app import Handler as BaseHandler
from experiments.scent_v2.real_user_dataset.catalog import search
from experiments.scent_v2.real_user_dataset.validation import ValidationError
from .engine import Engine,concentration
from .storage import EvaluationStore,VERSION,policy_ready
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/scent_v2/real_user_evaluation';STATIC=Path(__file__).parent/'static'

class Handler(BaseHandler):
    """Reuse host/origin/CSRF/content-type/body limits and no-request-logging policy."""
    def route(self,method):
        try:
            self.gate(method!='GET');url=urlsplit(self.path);path=url.path;s=self.server.store;s.purge_expired();token=self.cookie('sc_eval');csrf=self.headers.get('X-CSRF-Token','')
            if method=='GET' and path in ('/','/main.js','/style.css'):
                if path=='/style.css':p=ROOT/'experiments/scent_v2/real_user_dataset/static/style.css'
                else:p=STATIC/('index.html' if path=='/' else 'main.js')
                body=p.read_bytes();self.send_response(200);self.headers_common(('text/html' if path=='/' else 'text/css' if path.endswith('css') else 'application/javascript')+'; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
            if method=='GET' and path=='/api/info':return self.respond(dict(candidate_count=len(s.catalog),model_status='READY' if s.engine else 'MODEL_UNAVAILABLE',model_mode='FROZEN_479_HYBRID',consent_version=VERSION,operating_policy=s.policy if policy_ready(s.policy,s.fixture) else None,collection_enabled=policy_ready(s.policy,s.fixture),test_fixture=s.fixture))
            if method=='GET' and path=='/api/state':
                try:return self.respond(s.state(token))
                except PermissionError:return self.respond(dict(registered=False))
            if method=='GET' and path=='/api/search':
                q=parse_qs(url.query).get('q',[''])[0];results=search(s.catalog,q) if q else [s.catalog[i] for i in sorted(s.catalog)[:10]]
                return self.respond(dict(results=[dict(r,concentration=concentration(r['name'])) for r in results]))
            if method=='POST' and path=='/api/register':
                body=self.read_body()
                try:return self.respond(s.state(token))
                except PermissionError:pass
                result=s.register_evaluation(body.get('consent'),body.get('version'));return self.respond(dict(registered=True,csrf=result['csrf'],deletion_code=result['deletion_code']),201,f"sc_eval_{self.server.server_port}={result['token']}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000")
            if method=='POST' and path=='/api/delete-code':return self.respond(s.delete_by_code(self.read_body().get('deletion_code')))
            if method=='POST' and path=='/api/ratings':return self.respond(s.save_rating(token,csrf,self.read_body()))
            if method=='POST' and path=='/api/recommend':
                body=self.read_body()
                if body.get('mode')!='FROZEN_479_HYBRID':raise ValidationError('UNSUPPORTED_MODEL_MODE: 497 Content는 이 평가 모델이 아닙니다.')
                return self.respond(s.recommend(token,csrf))
            if method=='POST' and path=='/api/feedback':
                b=self.read_body();return self.respond(s.feedback(token,csrf,b.get('session_id'),b.get('product_id'),b.get('experience'),b.get('rating'),b.get('comparison') is True))
            if method=='DELETE' and path=='/api/me':return self.respond(s.withdraw_evaluation(token,csrf),200,f'sc_eval_{self.server.server_port}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
            return self.respond(dict(error='찾을 수 없는 경로입니다.'),404)
        except PermissionError as e:self.respond(dict(error=str(e)),403)
        except (ValueError,TypeError) as e:self.respond(dict(error=str(e)),400)
        except Exception:self.respond(dict(error='MODEL_UNAVAILABLE 또는 저장 오류입니다. 로컬 운영자가 확인하세요.'),503)

class Server(ThreadingHTTPServer):
    """port loopback only; tests inject a separate Store and data root."""
    daemon_threads=True
    def __init__(self,port,store):
        super().__init__(('127.0.0.1',port),Handler);self.store=store;self.origin=f'http://127.0.0.1:{self.server_port}'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['start','init','export','audit','purge'],default='start',nargs='?');p.add_argument('--port',type=int,default=8021);p.add_argument('--policy',type=Path);a=p.parse_args()
    policy=json.loads(a.policy.read_text()) if a.policy else {}
    try:engine=Engine()
    except Exception:engine=None
    if engine is None and a.command!='purge':raise SystemExit('MODEL_UNAVAILABLE: inspect existing local Frozen assets; no substitute model')
    s=EvaluationStore(OUT/'data',engine,policy);purged=s.purge_expired()
    if a.command=='purge':print(json.dumps(dict(purged=purged)));return
    if a.command=='export':print(json.dumps(s.export_evaluation()));return
    if a.command=='audit':print(json.dumps(s.analyses(),ensure_ascii=False));return
    if a.command=='init':print(json.dumps(dict(initialized=True,candidates=len(s.catalog),collection_enabled=policy_ready(policy))));return
    server=Server(a.port,s);print(f'Local V2-21 http://127.0.0.1:{server.server_port}; collection_enabled={policy_ready(policy)}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();s.lock.close()

if __name__=='__main__':main()
