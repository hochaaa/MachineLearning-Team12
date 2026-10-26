"""Run in a fresh source Clone only: refuse original data, audit file access.

No reconstruction or research evaluation. Receipt contains synthetic outputs only.
"""
import sys
import json
from pathlib import Path

ROOT=Path.cwd().resolve()
for name in ('outputs','Term-project-datasets'):
    if (ROOT/name).exists():
        raise SystemExit('Use a fresh source-only clone; never delete existing data to pass this check')
reads=[]
def audit(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes)):return
    path=Path(args[0]).resolve()
    try:relative=path.relative_to(ROOT)
    except ValueError:return
    if relative.parts[0] not in ('demo','.venv'):
        raise RuntimeError('Non-demo project read blocked')
    if relative.parts[0]=='demo':reads.append(str(relative))
sys.addaudithook(audit)
from fastapi.testclient import TestClient
from demo.backend.app import create_app
with TestClient(create_app()) as c:
    h=c.get('/api/health').json();assert h['recommendation_ready'] and h['candidate_count']==80
    assert c.get('/api/perfumes?q=rose&mode=notes').json()['results']
    b={'ratings':[{'perfume_id':i,'rating':r} for i,r in zip(('DEMO-001','DEMO-014','DEMO-038'),(9,7,2))]}
    out=c.post('/api/recommend',json=b).json();assert len(out['results'])==5
    b['required_scents']=['woody'];filtered=c.post('/api/recommend',json=b).json()
    assert all('woody' in r['accords'] for r in filtered['results'])
print(json.dumps({'result':'PASS','private_directories_absent':True,'non_demo_project_reads_blocked':True,
                  'demo_reads':sorted(set(reads)),'health':h,'top5_ids':[r['id'] for r in out['results']],
                  'woody_eligible':filtered['eligible_count']},indent=2))
