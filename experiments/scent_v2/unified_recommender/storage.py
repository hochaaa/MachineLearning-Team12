"""V2-21 storage reuse; new DB only, one immutable session per participant AND mode."""
import hashlib,json,random,sqlite3,uuid
from pathlib import Path
from experiments.scent_v2.real_user_evaluation.storage import EvaluationStore as BaseStore,now,ValidationError
from .engine import MODES

class Store(BaseStore):
    def __init__(self,root,engine,policy,fixture=False):
        root=Path(root);root.mkdir(parents=True,exist_ok=True,mode=0o700)
        # New isolated schema before inherited CREATE IF NOT EXISTS. No old DB migration.
        with sqlite3.connect(root/'participants.sqlite3') as c:
            c.execute('''CREATE TABLE IF NOT EXISTS v21_sessions(session_id TEXT PRIMARY KEY,user_id TEXT,model_version TEXT,catalog_version TEXT,support_json TEXT,recommendations_json TEXT,created_at TEXT,mode TEXT,candidate_count INTEGER,excluded_json TEXT,UNIQUE(user_id,model_version))''')
        super().__init__(root,engine,policy,fixture)
    def session_view(self,c,s):
        result=super().session_view(c,s);result.update(mode=s['mode'],candidate_count=s['candidate_count']);return result
    def state(self,token):
        result=super().state(token)
        with self.lock,self.connection() as c:
            p=self.identity(c,token);sessions=c.execute('SELECT * FROM v21_sessions WHERE user_id=? ORDER BY created_at,mode',(p['user_id'],)).fetchall()
            result['sessions']=[self.session_view(c,s) for s in sessions]
        return result
    def recommend_mode(self,token,csrf,mode):
        if mode not in MODES:raise ValidationError('UNSUPPORTED_MODEL_MODE')
        version=self.engine.version(mode)
        with self.lock,self.connection() as c:
            p=self.identity(c,token,csrf);c.execute('BEGIN IMMEDIATE')
            try:
                existing=c.execute('SELECT * FROM v21_sessions WHERE user_id=? AND model_version=?',(p['user_id'],version)).fetchone()
                if existing:c.rollback();return self.session_view(c,existing)
                rows=[dict(r) for r in c.execute("SELECT * FROM v21_ratings WHERE user_id=? AND source='pre_recommendation_rating'",(p['user_id'],))]
                allowed=self.engine.old if mode==MODES[0] else set(self.catalog)
                matched=[r for r in rows if r['product_id'] in allowed]
                if len(matched)<5:raise ValidationError('INSUFFICIENT_MATCHED_SUPPORT: 선택한 모드에 정확히 연결된 사전평점5개가 필요합니다.')
                chosen=sorted(matched,key=lambda r:hashlib.sha256(('12:v221:support:'+p['user_id']+':'+r['product_id']).encode()).hexdigest())[:5]
                support=[dict(product_id=r['product_id'],rating=r['rating']) for r in chosen];seen={r['product_id'] for r in chosen}
                excluded={r[0] for r in c.execute('SELECT product_id FROM v21_ratings WHERE user_id=?',(p['user_id'],))}
                excluded.update(r[0] for r in c.execute("SELECT f.product_id FROM v21_feedback f JOIN v21_sessions s USING(session_id) WHERE s.user_id=? AND f.experience='EXPERIENCED' AND f.rating IS NOT NULL",(p['user_id'],)))
                excluded.update(r[0] for r in c.execute("SELECT f.product_id FROM v21_comparisons f JOIN v21_sessions s USING(session_id) WHERE s.user_id=? AND f.experience='EXPERIENCED' AND f.rating IS NOT NULL",(p['user_id'],)))
                results=self.engine.recommend(support,mode,excluded)
                if any(r['id'] in excluded for r in results):raise RuntimeError('Assessed item leaked into recommendations')
                count=479 if mode==MODES[0] else 497;sid=uuid.uuid4().hex
                c.execute('INSERT INTO v21_sessions VALUES (?,?,?,?,?,?,?,?,?,?)',(sid,p['user_id'],version,self.engine.frozen.catalog_version if count==479 else self.engine.catalog_version,json.dumps(sorted(seen)),json.dumps(results),now(),mode,count,json.dumps(sorted(excluded))))
                pool=sorted(allowed-excluded-{r['id'] for r in results});k=min(5,len(pool));rng=random.Random(int(hashlib.sha256(('12:v222:comparison:'+sid).encode()).hexdigest(),16))
                for i in rng.sample(pool,k):c.execute('INSERT INTO v21_comparisons VALUES (?,?,?,?,?,?,?)',(sid,i,'V222 Uniform SRSWOR; exclude ALL assessed+Top5; conditional probability',k/len(pool),None,None,now()))
                c.commit();return self.session_view(c,c.execute('SELECT * FROM v21_sessions WHERE session_id=?',(sid,)).fetchone())
            except BaseException:c.rollback();raise
    def save_rating(self,token,csrf,row):
        # Do not allow a recommendation from ANY mode to become a post-hoc pre label.
        with self.lock,self.connection() as c:
            p=self.identity(c,token,csrf)
            for s in c.execute('SELECT * FROM v21_sessions WHERE user_id=?',(p['user_id'],)):
                excluded=set(json.loads(s['support_json']))|{r['id'] for r in json.loads(s['recommendations_json'])}
                if row.get('product_id') in excluded:raise ValidationError('이미 입력/추천된 제품입니다. 해당 모델 피드백 화면을 사용하세요.')
        return super().save_rating(token,csrf,row)

    def analyses(self):
        """Retain feedback analysis but never count three model sessions as three people."""
        result=super().analyses()
        with self.lock,self.connection() as c:
            result['feedback']['participants_with_session']=c.execute('SELECT COUNT(DISTINCT user_id) FROM v21_sessions').fetchone()[0]
            result['feedback']['mode_groups']=[dict(r) for r in c.execute('SELECT mode,COUNT(DISTINCT user_id) AS participants,COUNT(*) AS sessions FROM v21_sessions GROUP BY mode')]
        return result
