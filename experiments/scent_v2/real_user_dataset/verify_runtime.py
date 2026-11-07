"""Runtime checks without registering a real participant or submitting real ratings."""
import json,urllib.request,urllib.error,http.cookiejar
from .config import DATA,OUT
from .storage import atomic_write


def main():
 origin='http://127.0.0.1:8014';jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
 def request(path,payload=None):
  h={'Origin':origin,'X-Scent-Request':'1'}
  if payload is not None:h['Content-Type']='application/json'
  req=urllib.request.Request(origin+path,headers=h,data=json.dumps(payload).encode()if payload is not None else None)
  try:
   with client.open(req,timeout=5)as r:return r.status,r.headers,r.read()
  except urllib.error.HTTPError as r:
   with r:return r.code,r.headers,r.read()
 st,headers,body=request('/');assert st==200 and b'main.js'in body and'frame-ancestors' in headers['Content-Security-Policy']
 st,h,b=request('/api/info');assert st==200 and json.loads(b)['candidate_count']==479 and not json.loads(b)['test_mode']
 st,h,b=request('/api/session');assert not json.loads(b)['registered']
 assert request('/api/admin/summary')[0]==403
 # Local existing admin credential stays in process memory, never logs/results.
 token=(DATA/'.admin_token').read_text().strip();assert request('/api/admin/login',dict(token=token))[0]==200
 st,h,b=request('/api/admin/summary');q=json.loads(b);assert st==200 and q['actual_new_real_ratings']==q['participants']==0;assert 'rating_distribution'not in q['independent']
 assert request('/data/independent/real_user_ratings.csv')[0]==404
 result=dict(status='PASS',participant_page_http=200,original_candidates=479,production_mode=True,no_participant_created=True,actual_new_real_participants=0,actual_new_real_ratings=0,unauthenticated_admin_denied=403,authenticated_admin_aggregate_only=True,independent_label_distributions_exposed=False,private_files_http_status=404,loopback_origin=origin)
 atomic_write(OUT/'production_http_checks.json',json.dumps(result,ensure_ascii=False,indent=2).encode());print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
