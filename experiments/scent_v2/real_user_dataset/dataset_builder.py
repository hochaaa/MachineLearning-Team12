"""Development-only provenance-aware merge; never opens independent rating files."""
import csv,json,sqlite3,math,hashlib
from pathlib import Path
from .config import DATA,LEGACY,OUT
from .storage import FileRLock,atomic_write,csv_bytes
FIELDS=['user_id','perfume_id','rating','normalized_rating','source','zero_policy','in_service_candidates']


def merge_rows(legacy,new,candidates,development_ids):
 """OriginalTrain normalized triples + validated actual DEV CSV rows only.

 Legacy outside479 is retained in merged with a flag, excluded only from explicit
 training_ready view, and counts reported. Real0 stays0. Synthetic/test sources
 and role collisions raise, not silently discarded. No prior synthetic files read.
 """
 allowed=set(candidates);oldids={u for u,i,y in legacy};seen=set();merged=[]
 for row in legacy:
  if len(row)!=3:raise ValueError('Legacy triples required')
  u,i,y=row
  if not isinstance(u,str)or u.startswith(('synthetic_','testuser_','realuser_')):raise ValueError('Unexpected legacy source/user namespace')
  if isinstance(y,bool)or not isinstance(y,(int,float))or not math.isfinite(y)or not 0<y<=1 or abs(y*20-round(y*20))>1e-9:raise ValueError('Legacy zero-excluded analytical contract mismatch')
  if (u,i)in seen:raise ValueError('Duplicate legacy user/item')
  seen.add((u,i));merged.append(dict(user_id=u,perfume_id=i,rating=y*10,normalized_rating=y,source='legacy_atrafshan_train',zero_policy='legacy_zero_excluded_analysis_assumption',in_service_candidates=i in allowed))
 for r in new:
  u=r['user_id'];i=r['perfume_id'];y=float(r['rating'])
  if u in oldids:raise ValueError('Legacy/new user ID collision')
  if not u.startswith('realuser_')or r.get('source')!='real_user_collection':raise ValueError('Synthetic/test/non-real input forbidden')
  if u not in development_ids:raise ValueError('Independent/unknown participant cannot enter development merge')
  if i not in allowed:raise ValueError('New item outside frozen479')
  if not math.isfinite(y)or not 0<=y<=10 or y*2!=round(y*2)or r.get('experience_type')not in('used','sampled'):raise ValueError('New rating/experience invalid')
  if(u,i)in seen:raise ValueError('Duplicate user/item in new rows')
  seen.add((u,i));merged.append(dict(user_id=u,perfume_id=i,rating=y,normalized_rating=y/10,source='real_user_collection',zero_policy='explicit_experienced_zero_valid',in_service_candidates=True))
 return merged


def build(root=DATA,legacy_path=LEGACY,candidates=()):
 """Verified DEV snapshot only; no independent data file is opened or concatenated."""
 root=Path(root).resolve();lock=FileRLock(root/'.store.lock')
 with lock:
  meta=json.loads((root/'collection_metadata.json').read_text())
  if meta['dataset_kind']!='real_user_collection':raise ValueError('Test fixtures cannot become a real dataset')
  dev=root/'real_user_ratings.csv'
  if hashlib.sha256(dev.read_bytes()).hexdigest()!=meta['snapshot_sha256']['real_user_ratings.csv']:raise ValueError('Snapshot incomplete/corrupt; run recovery export')
  c=sqlite3.connect((root/'participants.sqlite3').as_uri()+'?mode=ro',uri=True)
  try:
   rev=int(c.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]);ids={r[0]for r in c.execute("SELECT user_id FROM participants WHERE role='development'")}
  finally:c.close()
  if rev!=meta['revision']:raise ValueError('Stale CSV snapshot; recover before training export')
  with dev.open(encoding='utf-8',newline='')as f:new=list(csv.DictReader(f))
  legacy=json.loads(Path(legacy_path).read_text());merged=merge_rows(legacy,new,candidates,ids);ready=[r for r in merged if r['in_service_candidates']]
  atomic_write(root/'merged_real_ratings.csv',csv_bytes(FIELDS,merged));atomic_write(root/'training_ready_ratings.csv',csv_bytes(FIELDS,ready))
  result=dict(status='PASS',legacy_rows=len(legacy),new_development_rows=len(new),merged_rows=len(merged),training_ready_candidate_rows=len(ready),legacy_outside479_preserved_flagged=len(merged)-len(ready),legacy_outside479_unique_items=len({r['perfume_id']for r in merged if not r['in_service_candidates']}),independent_ratings_read_or_merged=0,synthetic_ratings_read_or_merged=0,explicit_new_zero_rows=sum(float(r['rating'])==0 for r in new),zero_compatibility='Normalized0 retained; src/perfume/models.py accepts0. Do NOT re-run legacy atrafshan(zero_policy=exclude) on collection CSV.',source_revision=rev,dev_snapshot_sha256=meta['snapshot_sha256']['real_user_ratings.csv'],legacy_sha256=hashlib.sha256(Path(legacy_path).read_bytes()).hexdigest(),training_ready_sha256=hashlib.sha256((root/'training_ready_ratings.csv').read_bytes()).hexdigest())
  atomic_write(root/'merge_report.json',json.dumps(result,ensure_ascii=False,indent=2).encode());return result


def load_training_rows(root=DATA):
 """Future experiments must verify generation before loading this DEV-only view."""
 root=Path(root);meta=json.loads((root/'collection_metadata.json').read_text());m=json.loads((root/'merge_report.json').read_text());c=sqlite3.connect((root/'participants.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
 try:revision=int(c.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0])
 finally:c.close()
 if meta['dataset_kind']!='real_user_collection'or revision!=m['source_revision']or hashlib.sha256((root/'training_ready_ratings.csv').read_bytes()).hexdigest()!=m['training_ready_sha256']:raise ValueError('Stale/unverified development dataset; rebuild before training')
 with(root/'training_ready_ratings.csv').open(encoding='utf-8',newline='')as f:return [(r['user_id'],r['perfume_id'],float(r['normalized_rating']))for r in csv.DictReader(f)]


def main():
 from .catalog import load_catalog
 print(json.dumps(build(candidates=load_catalog()),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
