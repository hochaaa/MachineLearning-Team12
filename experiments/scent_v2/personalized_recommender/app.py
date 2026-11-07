"""V2-22 HTTP reuse; override new UI, mode metadata and personalized recommendation."""
import argparse,json,tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from experiments.scent_v2.unified_recommender.app import Handler as BaseHandler
from experiments.scent_v2.real_user_evaluation.storage import VERSION,policy_ready
from .engine import Engine,ROOT,OUT,MODES
from .storage import Store
STATIC=Path(__file__).parent/'static'

class Handler(BaseHandler):
    def route(self,method):
        path=urlsplit(self.path).path;s=self.server.store
        try:
            self.gate(method!='GET');s.purge_expired()
            if method=='GET' and path in ('/','/main.js'):
                body=(STATIC/('index.html' if path=='/' else 'main.js')).read_bytes();self.send_response(200);self.headers_common(('text/html' if path=='/' else 'application/javascript')+'; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
            if method=='GET' and path=='/api/info':return self.respond(dict(candidate_count=497,modes=MODES,default_mode=MODES[0],old_ids=sorted(s.engine.old),consent_version=VERSION,operating_policy=s.policy if policy_ready(s.policy,s.fixture) else None,collection_enabled=policy_ready(s.policy,s.fixture),test_fixture=s.fixture))
            if method=='POST' and path=='/api/recommend':return self.respond(s.recommend_mode(self.cookie('sc_eval'),self.headers.get('X-CSRF-Token',''),self.read_body().get('mode')))
            return super().route(method)
        except PermissionError as e:self.respond(dict(error=str(e)),403)
        except (ValueError,TypeError) as e:self.respond(dict(error=str(e)),400)
        except Exception:self.respond(dict(error='MODEL_UNAVAILABLE · 입력 또는 로컬 저장소를 확인하세요.'),503)

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,port,store):
        super().__init__(('127.0.0.1',port),Handler);self.store=store;self.origin=f'http://127.0.0.1:{self.server_port}'


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8025);p.add_argument('--fixture',action='store_true');a=p.parse_args()
    policy=json.loads((ROOT/'outputs/scent_v2/real_user_evaluation/operating_policy.json').read_text());tmp=tempfile.TemporaryDirectory(prefix='v223-fixture-') if a.fixture else None
    engine=Engine();store=Store(Path(tmp.name)/'data' if tmp else OUT/'data',engine,policy,a.fixture);store.purge_expired();server=Server(a.port,store)
    print(f'V2-23 http://127.0.0.1:{server.server_port} fixture={a.fixture}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();store.lock.close();tmp.cleanup() if tmp else None

if __name__=='__main__':main()
