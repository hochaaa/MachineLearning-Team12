"""V2-14 auth/SQLite/CSV reused in a NEW directory; immutable V2-21 stage records."""
import csv,hashlib,json,math,secrets,sqlite3,uuid,re
from datetime import date
from collections import Counter
from pathlib import Path
from experiments.scent_v2.real_user_dataset.storage import Store as LegacyStore,now,atomic_write,csv_bytes
from experiments.scent_v2.real_user_dataset.config import CONSENT_VERSION
from experiments.scent_v2.real_user_dataset.validation import validate_batch,ValidationError
from .engine import concentration

VERSION='v221-consent-1'
EXPERIENCE=('EXPERIENCED','NOT_EXPERIENCED','UNKNOWN_EXPERIENCE')


def policy_ready(policy,fixture=False):
    """Actual operator must provide retention/deletion/access; never invent approval."""
    ready=bool(isinstance(policy,dict) and all(isinstance(policy.get(k),str) and policy[k].strip() for k in ('retention_end','deletion_method','team_access','confirmed_by')) and policy.get('confirmed') is True and (fixture or not policy.get('test_only')))
    if not ready:return False
    if fixture:return True
    try:return date.fromisoformat(policy['retention_end'])>=date.today()
    except ValueError:return False


def preference(status,value):
    """Non-experience MUST have null, not zero. Real experienced zero is valid."""
    if status not in EXPERIENCE:raise ValidationError('경험 여부를 선택하세요.')
    if status!='EXPERIENCED':
        if value is not None:raise ValidationError('미경험·기억 불명에는 평점을 저장할 수 없습니다.')
        return None
    if value is None:return None # Experienced person may decline rating.
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=10 or abs(value*2-round(value*2))>1e-9:raise ValidationError('0~10점, 0.5점 단위만 허용합니다.')
    return float(value)


class EvaluationStore(LegacyStore):
    """root NEW data path; engine Frozen-only; policy actual operator settings or pending."""
    def __init__(self,root,engine,policy=None,fixture=False):
        self.engine=engine;self.policy=policy or {};self.fixture=fixture
        super().__init__(root,engine.catalog if engine else {},dataset_kind='test_fixture' if fixture else 'real_user_collection')
        with self.lock,self.connection() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS v21_consents(user_id TEXT PRIMARY KEY,version TEXT,policy_json TEXT,created_at TEXT,deletion_hash TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS v21_ratings(user_id TEXT,product_id TEXT,original_name TEXT,concentration TEXT,rating REAL,experience TEXT,source TEXT,created_at TEXT,PRIMARY KEY(user_id,product_id,source));
CREATE TABLE IF NOT EXISTS v21_sessions(session_id TEXT PRIMARY KEY,user_id TEXT UNIQUE,model_version TEXT,catalog_version TEXT,support_json TEXT,recommendations_json TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS v21_feedback(session_id TEXT,product_id TEXT,rank INTEGER,experience TEXT,rating REAL,created_at TEXT,PRIMARY KEY(session_id,product_id));
CREATE TABLE IF NOT EXISTS v21_comparisons(session_id TEXT,product_id TEXT,selection_policy TEXT,selection_probability REAL,experience TEXT,rating REAL,created_at TEXT,PRIMARY KEY(session_id,product_id));''')
    def register_evaluation(self,consent,version):
        """Participant consent plus exact operator-policy snapshot; does not claim rights."""
        if not policy_ready(self.policy,self.fixture):raise ValidationError('OPERATION_POLICY_PENDING')
        if version!=VERSION or consent is not True:raise ValidationError('현재 안내에 동의해야 합니다.')
        result=super().register(True,CONSENT_VERSION)
        code=secrets.token_urlsafe(32)
        with self.lock,self.connection() as c:c.execute('INSERT INTO v21_consents VALUES (?,?,?,?,?)',(result['user_id'],VERSION,json.dumps(self.policy,ensure_ascii=False),now(),hashlib.sha256(code.encode()).hexdigest()))
        result['deletion_code']=code # returned once only; never persisted or logged
        return result
    def identity(self,c,token,csrf=None):
        """Authenticate inherited opaque cookie; no direct-identifying fields collected."""
        p=self.participant(c,token)
        if csrf is not None and (not isinstance(csrf,str) or not secrets.compare_digest(csrf,p['csrf'])):raise PermissionError('요청 토큰 오류')
        if not c.execute('SELECT 1 FROM v21_consents WHERE user_id=?',(p['user_id'],)).fetchone():raise PermissionError('V2-21 동의가 필요합니다.')
        return p
    def state(self,token):
        with self.lock,self.connection() as c:
            p=self.identity(c,token);rows=[dict(r) for r in c.execute('SELECT * FROM v21_ratings WHERE user_id=? ORDER BY created_at,product_id',(p['user_id'],))]
            session=c.execute('SELECT * FROM v21_sessions WHERE user_id=?',(p['user_id'],)).fetchone()
            feedback=[dict(r) for r in c.execute('SELECT f.* FROM v21_feedback f JOIN v21_sessions s USING(session_id) WHERE s.user_id=?',(p['user_id'],))]
            return dict(registered=True,csrf=p['csrf'],ratings=[{k:v for k,v in r.items() if k!='user_id'} for r in rows],session=self.session_view(c,session) if session else None,feedback=feedback)
    def save_rating(self,token,csrf,row):
        """Exact product identity validation; before/after-source is server-derived, immutable."""
        if not isinstance(row,dict):raise ValidationError('평점 형식 오류')
        pid=row.get('product_id');y=row.get('rating');form=row.get('concentration');matched=pid in self.catalog
        if row.get('experience')!='EXPERIENCED':raise ValidationError('실제 경험한 향수만 사전·추가 평점에 입력하세요.')
        preference('EXPERIENCED',y)
        if y is None:raise ValidationError('경험 평점이 필요합니다.')
        if matched:
            original=self.catalog[pid]['name'];expected=concentration(original)
            if row.get('identity_confirmed') is not True or form!=expected:raise ValidationError('농도·제품 식별 확인이 필요합니다. 다른 판본을 연결하지 마세요.')
            # Reuse V2-14 authoritative range/experience/duplicate validation.
            validate_batch(dict(request_id='v221-rating',ratings=[dict(perfume_id=pid,rating=y,experience_type='sampled')]),self.catalog)
        else:
            # No fuzzy mapping; retain a review-only custom product. No free-form contact field.
            if not isinstance(row.get('original_name'),str) or not 1<=len(row['original_name'])<=150:raise ValidationError('미등록 제품명(150자 이하)을 입력하세요.')
            original=row['original_name']
            if re.search(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|0?1[016789][ -]?\d{3,4}[ -]?\d{4}',original):raise ValidationError('제품명에 연락처를 입력하지 마세요.')
            form='UNKNOWN';pid='custom:'+hashlib.sha256(original.encode()).hexdigest()
        with self.lock,self.connection() as c:
            p=self.identity(c,token,csrf);c.execute('BEGIN IMMEDIATE')
            try:
                exposed=c.execute('SELECT * FROM v21_sessions WHERE user_id=?',(p['user_id'],)).fetchone()
                source='post_recommendation_feedback' if exposed else 'pre_recommendation_rating'
                if exposed:
                    excluded=set(json.loads(exposed['support_json']))|{r['id'] for r in json.loads(exposed['recommendations_json'])}
                    if pid in excluded:raise ValidationError('Support 재평가 또는 추천 피드백 화면을 사용하세요. 추가 비교평가 대상이 아닙니다.')
                if c.execute('SELECT 1 FROM v21_ratings WHERE user_id=? AND product_id=? AND source=?',(p['user_id'],pid,source)).fetchone():raise ValidationError('이미 저장한 제품입니다. 자동으로 덮어쓰지 않습니다.')
                c.execute('INSERT INTO v21_ratings VALUES (?,?,?,?,?,?,?,?)',(p['user_id'],pid,original,form,y,'EXPERIENCED',source,now()));c.commit()
            except BaseException:c.rollback();raise
        return dict(saved=True,source=source,matched=matched,status='MATCHED_EXACT_CANONICAL_ID' if matched else 'UNSUPPORTED_PRODUCT')
    def session_view(self,c,s):
        """Own exposure only; support IDs but never held-out values sent to client scorer."""
        return dict(session_id=s['session_id'],model_version=s['model_version'],catalog_version=s['catalog_version'],support_product_ids=json.loads(s['support_json']),
            results=json.loads(s['recommendations_json']),comparisons=[dict(r,**self.catalog[r['product_id']]) for r in c.execute('SELECT * FROM v21_comparisons WHERE session_id=? ORDER BY product_id',(s['session_id'],))])
    def recommend(self,token,csrf):
        """First immutable session per participant; label-blind5 support, score API only5."""
        with self.lock,self.connection() as c:
            p=self.identity(c,token,csrf);c.execute('BEGIN IMMEDIATE')
            try:
                existing=c.execute('SELECT * FROM v21_sessions WHERE user_id=?',(p['user_id'],)).fetchone()
                if existing:c.rollback();return self.session_view(c,existing)
                if self.engine is None:raise ValidationError('MODEL_UNAVAILABLE')
                rows=[dict(r) for r in c.execute("SELECT * FROM v21_ratings WHERE user_id=? AND source='pre_recommendation_rating'",(p['user_id'],))]
                matched=[r for r in rows if r['product_id'] in self.catalog]
                if len(matched)<5:raise ValidationError('INSUFFICIENT_MATCHED_SUPPORT')
                selected=sorted(matched,key=lambda r:hashlib.sha256(('12:v221:support:'+p['user_id']+':'+r['product_id']).encode()).hexdigest())[:5]
                inputs=[dict(product_id=r['product_id'],rating=r['rating']) for r in selected]
                results=self.engine.recommend(inputs) # No remaining pre/held-out records passed.
                seen={r['product_id'] for r in selected}
                if len(results)!=5 or len({r['id'] for r in results})!=5 or seen&{r['id'] for r in results} or any(r['id'] not in self.catalog or not math.isfinite(r['score']) for r in results):raise ValidationError('MODEL_UNAVAILABLE')
                sid=uuid.uuid4().hex;c.execute('INSERT INTO v21_sessions VALUES (?,?,?,?,?,?,?)',(sid,p['user_id'],self.engine.model_version,self.engine.catalog_version,json.dumps(sorted(seen)),json.dumps(results),now()))
                # Uniform SRSWOR: no model scores, ratings or held-out IDs used.
                pool=sorted(set(self.catalog)-seen-{r['id'] for r in results});k=min(5,len(pool))
                chosen=__import__('random').Random(int(hashlib.sha256(('12:v221:comparison:'+sid).encode()).hexdigest(),16)).sample(pool,k)
                for pid in chosen:c.execute('INSERT INTO v21_comparisons VALUES (?,?,?,?,?,?,?)',(sid,pid,'Uniform SRSWOR; seed12+sessionID; exclude Support+Top5 only',k/len(pool),None,None,now()))
                c.commit();s=c.execute('SELECT * FROM v21_sessions WHERE session_id=?',(sid,)).fetchone();return self.session_view(c,s)
            except BaseException:c.rollback();raise
    def feedback(self,token,csrf,sid,pid,status,rating,comparison=False):
        """Store post-exposure response; null unknown/never-experienced, never offline labels."""
        rating=preference(status,rating)
        with self.lock,self.connection() as c:
            p=self.identity(c,token,csrf);s=c.execute('SELECT * FROM v21_sessions WHERE session_id=? AND user_id=?',(sid,p['user_id'])).fetchone()
            if s is None:raise PermissionError('본인 세션만 평가할 수 있습니다.')
            if comparison:
                if not c.execute('SELECT 1 FROM v21_comparisons WHERE session_id=? AND product_id=?',(sid,pid)).fetchone():raise ValidationError('비교 노출에 없는 제품')
                c.execute('UPDATE v21_comparisons SET experience=?,rating=?,created_at=? WHERE session_id=? AND product_id=?',(status,rating,now(),sid,pid))
            else:
                items={r['id']:r['rank'] for r in json.loads(s['recommendations_json'])}
                if pid not in items:raise ValidationError('추천 목록에 없는 제품')
                c.execute('INSERT INTO v21_feedback VALUES (?,?,?,?,?,?) ON CONFLICT(session_id,product_id) DO UPDATE SET experience=excluded.experience,rating=excluded.rating,created_at=excluded.created_at',(sid,pid,items[pid],status,rating,now()))
        return dict(saved=True,rating=rating,source='post_recommendation_feedback')
    def _delete_user(self,uid):
        """Delete participant-linked raw rows transactionally; rebuild only NEW exports."""
        with self.lock,self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            try:
                ids=[r[0] for r in c.execute('SELECT session_id FROM v21_sessions WHERE user_id=?',(uid,))]
                for sid in ids:
                    c.execute('DELETE FROM v21_feedback WHERE session_id=?',(sid,));c.execute('DELETE FROM v21_comparisons WHERE session_id=?',(sid,))
                for table in ('v21_sessions','v21_ratings','v21_consents'):c.execute(f'DELETE FROM {table} WHERE user_id=?',(uid,))
                for alias in ('dev','holdout'):
                    c.execute(f'DELETE FROM {alias}.ratings WHERE user_id=?',(uid,));c.execute(f'DELETE FROM {alias}.receipts WHERE user_id=?',(uid,))
                c.execute('DELETE FROM participants WHERE user_id=?',(uid,));self.bump(c);c.commit()
            except BaseException:c.rollback();raise
            # Invalidate raw V2-21 snapshots before returning; inherited exports rebuilt.
            for path in self.root.glob('v21_*.csv'):path.unlink()
            super().export()
        return dict(withdrawn=True)
    def withdraw_evaluation(self,token,csrf):
        """Same-browser withdrawal is also supported; delete code survives cookie loss."""
        with self.lock,self.connection() as c:uid=self.identity(c,token,csrf)['user_id']
        return self._delete_user(uid)
    def delete_by_code(self,code):
        """A 256-bit random bearer code authorizes deletion; hash-only lookup, no identity."""
        if not isinstance(code,str) or not 30<=len(code)<=100:raise ValidationError('삭제 코드를 확인하세요.')
        value=hashlib.sha256(code.encode()).hexdigest()
        with self.lock,self.connection() as c:
            row=c.execute('SELECT user_id FROM v21_consents WHERE deletion_hash=?',(value,)).fetchone()
        if row is None:raise ValidationError('삭제 코드를 확인하세요. 분실 시 개별 확인이 불가능합니다.')
        return self._delete_user(row[0])
    def purge_expired(self,today=None):
        """At startup/each request: erase raw rows after their consent retention end."""
        today=today or date.today()
        with self.lock,self.connection() as c:rows=c.execute('SELECT user_id,policy_json FROM v21_consents').fetchall()
        expired=[]
        for row in rows:
            try:
                end=date.fromisoformat(json.loads(row['policy_json'])['retention_end'])
                if today>end:expired.append(row['user_id'])
            except (ValueError,KeyError):continue # Only fixture policy may lack actual date.
        for uid in expired:self._delete_user(uid)
        return len(expired)
    def export_evaluation(self):
        """CLI-only private CSV snapshots; no HTTP download, no auth secrets exported."""
        with self.lock,self.connection() as c:
            for table in ('v21_ratings','v21_sessions','v21_feedback','v21_comparisons'):
                rows=[dict(r) for r in c.execute(f'SELECT * FROM {table}')];fields=[r[1] for r in c.execute(f'PRAGMA table_info({table})')]
                atomic_write(self.root/(table+'.csv'),csv_bytes(fields,rows))
        return dict(exported=True,scope='LOCAL_PRIVATE_NO_UPLOAD')
    def analyses(self):
        """Counts only for Offline pending; feedback denominators explicit and no trained claim."""
        with self.lock,self.connection() as c:
            users=c.execute('SELECT COUNT(*) FROM v21_consents').fetchone()[0];ratings=[dict(r) for r in c.execute('SELECT * FROM v21_ratings')];sessions=[dict(r) for r in c.execute('SELECT * FROM v21_sessions')];feedback=[dict(r) for r in c.execute('SELECT * FROM v21_feedback')]
        pre=[r for r in ratings if r['source']=='pre_recommendation_rating'];counts=Counter(r['user_id'] for r in pre if r['product_id'] in self.catalog)
        eligible=sum(n>=6 for n in counts.values());exp=[r for r in feedback if r['experience']=='EXPERIENCED'];rated=[r for r in exp if r['rating'] is not None];observed=len(feedback);slots=5*len(sessions)
        return dict(collection=dict(dataset_kind=self.kind,actual_new_participants=users,ratings=len(ratings),pre_ratings=len(pre),post_ratings=len(ratings)-len(pre),average_ratings_per_participant=len(ratings)/users if users else None,sessions=len(sessions),offline_count_eligible=eligible,goals=dict(initial_users=10,recommended_users=20,ratings_per_user='8–10; not statistical sufficiency'),person_dedup='One cookie participant per model/session; cleared cookies/devices may duplicate real people'),
            offline=dict(status='NOT_EVALUATED_NO_NEW_DATA' if not users else 'BLOCKED_FROZEN_TRAIN_MEMBERSHIP_UNVERIFIED',count_eligible=eligible,minimum_matched=6,minimum_reporting_users=10,metrics='NOT_EVALUATED',training_exclusion_verified=False,post_feedback_excluded=True,reason='Frozen user identity overlap unknown; no training/fake attestation performed'),
            feedback=dict(status='NOT_EVALUATED_NO_NEW_DATA' if not users else 'EXPOSURE_BASED_ONLY',participants_with_session=len(sessions),responses=observed,exposed_slots=slots,response_rate=observed/slots if slots else None,
                experienced_among_responded=len(exp)/observed if observed else None,experienced_among_exposed=len(exp)/slots if slots else None,mean_experienced_rating=sum(r['rating'] for r in rated)/len(rated) if rated else None,
                positive_among_rated=sum(r['rating']>=7 for r in rated)/len(rated) if rated else None,positive_among_exposed=sum(r['rating']>=7 for r in rated)/slots if slots else None,
                unexperienced_not_negative=True,independent_offline_accuracy=False,model_versions=dict(Counter(s['model_version'] for s in sessions))),
            quality=dict(duplicate_rating_keys=len(ratings)-len({(r['user_id'],r['product_id'],r['source']) for r in ratings}),database_unique_constraints=True,invalid_preference_rows=sum(not (isinstance(r['rating'],(int,float)) and math.isfinite(r['rating']) and 0<=r['rating']<=10 and abs(r['rating']*2-round(r['rating']*2))<1e-9) for r in ratings),unknown_experience_with_rating=sum(r['rating'] is not None and r['experience']!='EXPERIENCED' for r in feedback),catalog_concentration_mismatches=sum(r['concentration']!=concentration(self.catalog[r['product_id']]['name']) for r in ratings if r['product_id'] in self.catalog),matched_pre=sum(r['product_id'] in self.catalog for r in pre),unmatched_pre=sum(r['product_id'] not in self.catalog for r in pre),matching_rate=sum(r['product_id'] in self.catalog for r in pre)/len(pre) if pre else None,
                real_identity_overlap='UNVERIFIED',concentration='Literal catalog fields only; CATALOG_UNSPECIFIED is not an EDP/EDT assertion',actual_accuracy_improvement='NOT_EVALUATED'))
