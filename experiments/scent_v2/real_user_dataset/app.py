"""Loopback-only independent standard-library collection server; no model loading."""
import argparse,json,os,secrets,time,tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs
from .config import DATA,CONSENT_VERSION
from .catalog import load_catalog,search
from .storage import Store,FileRLock
from .validation import ValidationError

STATIC=Path(__file__).parent/'static'
MAX_BODY=512000


def strict_json(raw):
 def pairs(items):
  out={}
  for k,v in items:
   if k in out:raise ValueError('Duplicate JSON key')
   out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in()).throw(ValueError('Nonfinite JSON')))


class CollectorServer(ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,port,store):
  super().__init__(('127.0.0.1',port),Handler);self.store=store;self.origin=f'http://127.0.0.1:{self.server_port}';self.admin_sessions={}


class Handler(BaseHTTPRequestHandler):
 server_version='ScentLocal/1'
 def log_message(self,*args):pass # No IP addresses, search queries, tokens or ratings in request logs.
 def headers_common(self,mime):
  self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
 def respond(self,data,status=200,cookie=None):
  body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode();self.send_response(status);self.headers_common('application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)))
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(body)
 def cookie(self,name):
  try:
   name=f'{name}_{self.server.server_port}';c=SimpleCookie(self.headers.get('Cookie',''));return c[name].value if name in c else ''
  except Exception:return ''
 def gate(self,write=False):
  if self.client_address[0]!='127.0.0.1'or self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':raise PermissionError('로컬 주소로만 접속할 수 있습니다.')
  if write and(self.headers.get('Origin')!=self.server.origin or self.headers.get('X-Scent-Request')!='1'):raise PermissionError('같은 로컬 화면에서 전송한 요청만 허용합니다.')
 def admin(self):
  tok=self.cookie('sc_admin');expires=self.server.admin_sessions.get(tok,0)
  if expires<time.monotonic():raise PermissionError('관리자 로그인이 필요합니다.')
 def read_body(self):
  if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValidationError('JSON 요청이 필요합니다.')
  try:n=int(self.headers.get('Content-Length','-1'))
  except ValueError:raise ValidationError('요청 크기가 올바르지 않습니다.')
  if not 0<=n<=MAX_BODY:raise ValidationError('요청 크기 제한을 초과했습니다.')
  try:return strict_json(self.rfile.read(n).decode('utf-8'))
  except(ValueError,UnicodeError):raise ValidationError('올바른 JSON이 필요합니다.')
 def do_GET(self):self.route('GET')
 def do_POST(self):self.route('POST')
 def do_DELETE(self):self.route('DELETE')
 def route(self,method):
  try:
   self.gate(method!='GET');url=urlsplit(self.path);path=url.path;s=self.server.store
   if method=='GET'and path in('/','/admin','/style.css','/main.js','/admin.js'):
    name={'/':'index.html','/admin':'admin.html','/style.css':'style.css','/main.js':'main.js','/admin.js':'admin.js'}[path];body=(STATIC/name).read_bytes();mime='text/html'if name.endswith('.html')else'text/css'if name.endswith('.css')else'application/javascript';self.send_response(200);self.headers_common(mime+'; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
   if method=='GET'and path=='/api/info':return self.respond(dict(candidate_count=len(s.catalog),consent_version=CONSENT_VERSION,test_mode=s.kind=='test_fixture',local_only=True))
   if method=='GET'and path=='/api/session':
    try:session=s.session(self.cookie('sc_collect'));session['registered']=True
    except PermissionError:session=dict(registered=False)
    return self.respond(session)
   if method=='GET'and path=='/api/search':return self.respond(dict(results=search(s.catalog,parse_qs(url.query).get('q',[''])[0])))
   if method=='POST'and path=='/api/register':
    body=self.read_body()
    if not isinstance(body,dict)or set(body)!={'consent','consent_version'}:raise ValidationError('동의 정보가 필요합니다.')
    try:existing=s.session(self.cookie('sc_collect'));return self.respond(dict(registered=True,**existing))
    except PermissionError:pass
    new=s.register(body['consent'],body['consent_version']);return self.respond(dict(registered=True,user_id=new['user_id'],csrf=new['csrf'],csv_sync_pending=new['csv_sync_pending']),201,f"sc_collect_{self.server.server_port}={new['token']}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000")
   if method=='GET'and path=='/api/me':
    rows=s.own_ratings(self.cookie('sc_collect'));return self.respond(dict(ratings=[dict(r,**s.catalog[r['perfume_id']])for r in rows]))
   if method=='POST'and path=='/api/ratings':return self.respond(s.submit(self.cookie('sc_collect'),self.headers.get('X-CSRF-Token',''),self.read_body()))
   if method=='DELETE'and path=='/api/me':return self.respond(s.withdraw(self.cookie('sc_collect'),self.headers.get('X-CSRF-Token','')),200,f'sc_collect_{self.server.server_port}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
   if method=='POST'and path=='/api/admin/login':
    body=self.read_body();token=body.get('token','')if isinstance(body,dict)else''
    if not isinstance(token,str)or not secrets.compare_digest(token,s.admin_token):raise PermissionError('관리자 코드가 올바르지 않습니다.')
    session=secrets.token_urlsafe(32);self.server.admin_sessions[session]=time.monotonic()+3600;return self.respond(dict(authenticated=True),200,f'sc_admin_{self.server.server_port}={session}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600')
   if method=='GET'and path=='/api/admin/summary':self.admin();return self.respond(s.aggregate())
   if method=='POST'and path=='/api/admin/logout':
    self.admin();self.server.admin_sessions.pop(self.cookie('sc_admin'),None);return self.respond(dict(logged_out=True),200,f'sc_admin_{self.server.server_port}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
   return self.respond(dict(error='찾을 수 없는 경로입니다.'),404)
  except (PermissionError,)as e:self.respond(dict(error=str(e)),403)
  except (ValidationError,ValueError)as e:self.respond(dict(error=str(e)),400)
  except (OSError,Exception):
   # Do not echo file paths/SQL/user data. SQLite rollback protects authority.
   self.respond(dict(error='저장소 처리 오류입니다. 응답을 보관하고 재시도해 주세요. 운영자는 로컬 저장 공간과 권한을 확인해 주세요.'),503)


def main():
 parser=argparse.ArgumentParser(description='SCENT MATCH local collection, no public hosting');parser.add_argument('command',choices=['start','init','recover','admin-code'],nargs='?',default='start');parser.add_argument('--port',type=int,default=8014);parser.add_argument('--test-mode',action='store_true');parser.add_argument('--data-root',type=Path);args=parser.parse_args()
 root=args.data_root.resolve()if args.data_root else DATA.resolve()
 if args.test_mode:
  if not args.data_root or root==DATA.resolve()or not(root.is_relative_to(Path(tempfile.gettempdir()).resolve())or root.is_relative_to(Path('/private/tmp'))):parser.error('Test data must be an explicit temporary directory, never production data')
 elif root!=DATA.resolve():parser.error('Real collection root is fixed to the new experiment data directory')
 catalog=load_catalog();store=Store(root,catalog,dataset_kind='test_fixture'if args.test_mode else'real_user_collection')
 if args.command=='admin-code':print(store.admin_token);return
 if args.command in('init','recover'):print(json.dumps(dict(status='PASS',candidates=len(catalog),dataset_kind=store.kind,summary=store.aggregate()),ensure_ascii=False));return
 if not 1024<=args.port<=65535:parser.error('Use an unprivileged local port1024..65535')
 server=CollectorServer(args.port,store);print(f'Local collector: {server.origin} | admin: {server.origin}/admin | mode={store.kind}',flush=True);print('Admin code is stored in data/.admin_token (0600); never upload it. Ctrl+C stops this process.',flush=True)
 try:server.serve_forever(poll_interval=.3)
 except KeyboardInterrupt:pass
 finally:server.server_close();store.lock.close();print('Collector stopped',flush=True)

if __name__=='__main__':main()
