"""Transactional SQLite authority, physically separated role databases and CSV views.

SQLite multi-file transactions use disk main DB + DELETE journal/synchronous FULL.
CSV is a replace-atomic derived snapshot; DB remains authoritative after export I/O
failure, and a last-published checksummed manifest makes partial exports detectable.
"""
import os,sqlite3,secrets,hashlib,json,csv,io,tempfile,threading,uuid
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
from .config import CONSENT_VERSION
from .validation import validate_batch,csv_safe,ValidationError
from .split_manager import assign_role

RATING_FIELDS=['user_id','perfume_id','rating','experience_type','confidence','preference_reason','created_at','updated_at','source']
PARTICIPANT_FIELDS=['user_id','role','consent_version','consented_at','created_at']
ALIASES={'development':'dev','independent':'holdout'}


def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def digest(s):return hashlib.sha256(s.encode()).hexdigest()


def atomic_write(path,payload):
 """New0600 temp in same directory, fsync, replace; old target survives pre-replace error."""
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);fd,tmp=tempfile.mkstemp(prefix='.snapshot-',dir=path.parent)
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,'wb')as f:f.write(payload);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 except BaseException:
  try:os.unlink(tmp)
  except FileNotFoundError:pass
  raise


def csv_bytes(fields,rows):
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields);w.writeheader()
 for r in rows:w.writerow({k:csv_safe(r.get(k,''))for k in fields})
 return s.getvalue().encode('utf-8')


class FileRLock:
 """Reentrant thread + cross-process file lock; serialize mutation and CSV publication."""
 def __init__(self,path):
  self.fd=os.open(path,os.O_RDWR|os.O_CREAT,0o600);self.thread=threading.RLock();self.depth=0
  if os.fstat(self.fd).st_size==0:os.write(self.fd,b'0')
 def __enter__(self):
  self.thread.acquire()
  try:
   if self.depth==0:
    if os.name=='nt':
     import msvcrt
     os.lseek(self.fd,0,0);msvcrt.locking(self.fd,msvcrt.LK_LOCK,1)
    else:
     import fcntl
     fcntl.flock(self.fd,fcntl.LOCK_EX)
   self.depth+=1;return self
  except BaseException:self.thread.release();raise
 def __exit__(self,*args):
  self.depth-=1
  if self.depth==0:
   if os.name=='nt':
    import msvcrt
    os.lseek(self.fd,0,0);msvcrt.locking(self.fd,msvcrt.LK_UNLCK,1)
   else:
    import fcntl
    fcntl.flock(self.fd,fcntl.LOCK_UN)
  self.thread.release()
 def close(self):
  if getattr(self,'fd',None) is not None:os.close(self.fd);self.fd=None
 def __del__(self):self.close()


class Store:
 """Collection-only store. Dataset builders must use development export only.

 `dataset_kind=test_fixture` has different IDs/source and may never merge with real
 data. Tests only use temporary roots. This OS user's file access is not a security
 sandbox; independent data protection is an application boundary plus0700/0600.
 """
 def __init__(self,root,catalog,legacy_ids=(),dataset_kind='real_user_collection'):
  if dataset_kind not in('real_user_collection','test_fixture'):raise ValueError('Dataset kind')
  self.root=Path(root).resolve();self.catalog=catalog;self.legacy_ids=set(legacy_ids);self.kind=dataset_kind;self.root.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(self.root,0o700);self.lock=FileRLock(self.root/'.store.lock')
  for role in ALIASES:(self.root/role).mkdir(exist_ok=True,mode=0o700);os.chmod(self.root/role,0o700)
  self.master=self.root/'participants.sqlite3'
  with self.lock,self.connection()as c:
   c.executescript('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS participants(user_id TEXT PRIMARY KEY,auth_hash TEXT UNIQUE NOT NULL,csrf TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN (\'development\',\'independent\')),consent_version TEXT NOT NULL,consented_at TEXT NOT NULL,created_at TEXT NOT NULL);')
   for alias in ALIASES.values():
    c.executescript(f'CREATE TABLE IF NOT EXISTS {alias}.ratings(user_id TEXT NOT NULL,perfume_id TEXT NOT NULL,rating REAL NOT NULL CHECK(rating>=0 AND rating<=10),experience_type TEXT NOT NULL CHECK(experience_type IN (\'used\',\'sampled\')),confidence TEXT NOT NULL,preference_reason TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,source TEXT NOT NULL,PRIMARY KEY(user_id,perfume_id)); CREATE TABLE IF NOT EXISTS {alias}.receipts(user_id TEXT NOT NULL,request_id TEXT NOT NULL,body_hash TEXT NOT NULL,receipt TEXT NOT NULL,PRIMARY KEY(user_id,request_id));')
   for k,v in [('kind',self.kind),('revision','0'),('withdrawals','0')]:c.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)',(k,v))
   if c.execute("SELECT value FROM metadata WHERE key='kind'").fetchone()[0]!=self.kind:raise ValueError('Real/test namespace mismatch')
  for p in self.root.rglob('*.sqlite3'):os.chmod(p,0o600)
  tokenfile=self.root/'.admin_token'
  if not tokenfile.exists():atomic_write(tokenfile,secrets.token_urlsafe(32).encode())
  os.chmod(tokenfile,0o600);self.admin_token=tokenfile.read_text().strip();self.export()

 @contextmanager
 def connection(self):
  c=sqlite3.connect(self.master,timeout=10,isolation_level=None);c.row_factory=sqlite3.Row
  try:
   c.execute('PRAGMA journal_mode=DELETE');c.execute('PRAGMA synchronous=FULL');c.execute('PRAGMA secure_delete=ON')
   for role,alias in ALIASES.items():
    c.execute(f'ATTACH DATABASE ? AS {alias}',(str(self.root/role/'ratings.sqlite3'),));c.execute(f'PRAGMA {alias}.journal_mode=DELETE');c.execute(f'PRAGMA {alias}.synchronous=FULL');c.execute(f'PRAGMA {alias}.secure_delete=ON')
   yield c
  finally:c.close()

 @staticmethod
 def bump(c):c.execute("UPDATE metadata SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")

 def register(self,consent,version):
  if consent is not True or version!=CONSENT_VERSION:raise ValidationError('현재 동의 문구에 동의해야 시작할 수 있습니다.')
  with self.lock,self.connection()as c:
   c.execute('BEGIN IMMEDIATE')
   try:
    for attempt in range(10):
     uid=('realuser_'if self.kind=='real_user_collection'else'testuser_')+uuid.uuid4().hex
     if uid not in self.legacy_ids and not c.execute('SELECT 1 FROM participants WHERE user_id=?',(uid,)).fetchone():break
    else:raise RuntimeError('ID collision retry exhausted')
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32);stamp=now();role=assign_role(uid)
    c.execute('INSERT INTO participants VALUES (?,?,?,?,?,?,?)',(uid,digest(token),csrf,role,version,stamp,stamp));self.bump(c);c.commit()
   except BaseException:c.rollback();raise
   try:self.export();pending=False
   except OSError:pending=True
   return dict(user_id=uid,token=token,csrf=csrf,csv_sync_pending=pending)

 def participant(self,c,token):
  if not isinstance(token,str)or len(token)>200:raise PermissionError('참여 세션이 필요합니다.')
  r=c.execute('SELECT * FROM participants WHERE auth_hash=?',(digest(token),)).fetchone()
  if r is None:raise PermissionError('참여 세션이 만료되었거나 철회되었습니다.')
  return r

 def session(self,token):
  with self.lock,self.connection()as c:
   r=self.participant(c,token);return dict(user_id=r['user_id'],csrf=r['csrf'],consent_version=r['consent_version'])

 def own_ratings(self,token):
  with self.lock,self.connection()as c:
   p=self.participant(c,token);alias=ALIASES[p['role']]
   return [dict(r)for r in c.execute(f'SELECT * FROM {alias}.ratings WHERE user_id=? ORDER BY perfume_id',(p['user_id'],))]

 def submit(self,token,csrf,payload):
  rows,key=validate_batch(payload,self.catalog);bodyhash=digest(json.dumps(rows,sort_keys=True,ensure_ascii=False));receipt=None
  with self.lock,self.connection()as c:
   p=self.participant(c,token)
   if not isinstance(csrf,str)or not secrets.compare_digest(csrf,p['csrf']):raise PermissionError('요청 확인 토큰이 올바르지 않습니다.')
   alias=ALIASES[p['role']];c.execute('BEGIN IMMEDIATE')
   try:
    old=c.execute(f'SELECT * FROM {alias}.receipts WHERE user_id=? AND request_id=?',(p['user_id'],key)).fetchone()
    if old:
     if old['body_hash']!=bodyhash:raise ValidationError('같은 제출 ID로 다른 내용을 보낼 수 없습니다.')
     receipt=json.loads(old['receipt']);c.rollback()
    else:
     added=updated=0;stamp=now()
     for r in rows:
      prev=c.execute(f'SELECT created_at FROM {alias}.ratings WHERE user_id=? AND perfume_id=?',(p['user_id'],r['perfume_id'])).fetchone();added+=prev is None;updated+=prev is not None
      c.execute(f'INSERT INTO {alias}.ratings VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,perfume_id) DO UPDATE SET rating=excluded.rating,experience_type=excluded.experience_type,confidence=excluded.confidence,preference_reason=excluded.preference_reason,updated_at=excluded.updated_at',(p['user_id'],r['perfume_id'],r['rating'],r['experience_type'],r['confidence'],r['preference_reason'],prev['created_at']if prev else stamp,stamp,self.kind))
     count=c.execute(f'SELECT COUNT(*) FROM {alias}.ratings WHERE user_id=?',(p['user_id'],)).fetchone()[0]
     receipt=dict(saved=True,added=added,updated=updated,unique_ratings=count,request_id=key);c.execute(f'INSERT INTO {alias}.receipts VALUES (?,?,?,?)',(p['user_id'],key,bodyhash,json.dumps(receipt)));self.bump(c);c.commit()
   except BaseException:c.rollback();raise
   try:self.export();receipt['csv_sync_pending']=False
   except OSError:receipt['csv_sync_pending']=True
   return receipt

 def withdraw(self,token,csrf):
  with self.lock,self.connection()as c:
   p=self.participant(c,token)
   if not isinstance(csrf,str)or not secrets.compare_digest(csrf,p['csrf']):raise PermissionError('요청 확인 토큰이 올바르지 않습니다.')
   c.execute('BEGIN IMMEDIATE')
   try:
    for alias in ALIASES.values():
     c.execute(f'DELETE FROM {alias}.ratings WHERE user_id=?',(p['user_id'],));c.execute(f'DELETE FROM {alias}.receipts WHERE user_id=?',(p['user_id'],))
    c.execute('DELETE FROM participants WHERE user_id=?',(p['user_id'],));c.execute("UPDATE metadata SET value=CAST(value AS INTEGER)+1 WHERE key='withdrawals'");self.bump(c);c.commit()
   except BaseException:c.rollback();raise
   # Only collector-owned derived exports; never touch original datasets/models.
   for name in('merged_real_ratings.csv','training_ready_ratings.csv','merge_report.json'):
    (self.root/name).unlink(missing_ok=True)
   for name in('support.private.csv','heldout.private.csv','evaluation_manifest.private.json'):(self.root/'independent'/name).unlink(missing_ok=True)
   try:self.export();pending=False
   except OSError:pending=True
   return dict(withdrawn=True,csv_sync_pending=pending)

 def export(self):
  with self.lock,self.connection()as c:
   c.execute('BEGIN');participants=[dict(r)for r in c.execute('SELECT * FROM participants ORDER BY user_id')];meta=dict(c.execute('SELECT key,value FROM metadata').fetchall());role_rows={role:[dict(r)for r in c.execute(f'SELECT * FROM {alias}.ratings ORDER BY user_id,perfume_id')]for role,alias in ALIASES.items()};c.commit()
   files={'participants.csv':csv_bytes(PARTICIPANT_FIELDS,participants),'real_user_ratings.csv':csv_bytes(RATING_FIELDS,role_rows['development']),'development/real_user_ratings.csv':csv_bytes(RATING_FIELDS,role_rows['development']),'independent/real_user_ratings.csv':csv_bytes(RATING_FIELDS,role_rows['independent'])}
   # Last-published manifest certifies snapshots from a single authoritative revision.
   for name,payload in files.items():atomic_write(self.root/name,payload)
   metadata=dict(dataset_kind=self.kind,revision=int(meta['revision']),source=self.kind,consent_version=CONSENT_VERSION,split_seed=12,split_policy='sha256(12:realuser-split:ID) first64bits fraction<.60 development else independent; fixed at registration',root_real_user_ratings_csv_scope='DEVELOPMENT ONLY; independent labels excluded',actual_participants=len(participants),actual_ratings=sum(map(len,role_rows.values())),development_ratings=len(role_rows['development']),independent_ratings=len(role_rows['independent']),withdrawals=int(meta['withdrawals']),snapshot_sha256={name:hashlib.sha256(b).hexdigest()for name,b in files.items()},csv_text_formula_escaped=True,authoritative_storage='SQLite; CSV snapshots recoverable from committed DB')
   atomic_write(self.root/'collection_metadata.json',json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False).encode());return metadata

 def aggregate(self):
  """Counts for independent users only; no independent rating-value distribution."""
  with self.lock,self.connection()as c:
   participants=[dict(r)for r in c.execute('SELECT role FROM participants')];roles={'development':[dict(r)for r in c.execute('SELECT user_id,perfume_id,rating FROM dev.ratings')],'independent':[dict(r)for r in c.execute('SELECT user_id,perfume_id FROM holdout.ratings')]}
  from .quality_report import summarize
  return summarize(participants,roles,len(self.catalog),self.kind)
