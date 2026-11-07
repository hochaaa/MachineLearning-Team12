"""Reuse V2-22 consent/data/feedback; new personalized variants get separate versions."""
import hashlib,json,random,uuid
from experiments.scent_v2.unified_recommender.storage import Store as BaseStore
from experiments.scent_v2.real_user_evaluation.storage import now,ValidationError
from .engine import PERSONAL,DIVERSE

class Store(BaseStore):
    def recommend_mode(self,token,csrf,mode):
        if mode not in (PERSONAL,DIVERSE):return super().recommend_mode(token,csrf,mode)
        version=self.engine.version(mode)
        with self.lock,self.connection() as c:
            p=self.identity(c,token,csrf);c.execute('BEGIN IMMEDIATE')
            try:
                existing=c.execute('SELECT * FROM v21_sessions WHERE user_id=? AND model_version=?',(p['user_id'],version)).fetchone()
                if existing:c.rollback();return self.session_view(c,existing)
                rows=[dict(r) for r in c.execute("SELECT * FROM v21_ratings WHERE user_id=? AND source='pre_recommendation_rating'",(p['user_id'],))]
                matched=[r for r in rows if r['product_id'] in self.catalog]
                if len(matched)<5:raise ValidationError('INSUFFICIENT_MATCHED_SUPPORT: 매칭된 사전 평점5개가 필요합니다.')
                chosen=sorted(matched,key=lambda r:hashlib.sha256(('12:v221:support:'+p['user_id']+':'+r['product_id']).encode()).hexdigest())[:5]
                support=[dict(product_id=r['product_id'],rating=r['rating']) for r in chosen];seen={r['product_id'] for r in support}
                excluded={r[0] for r in c.execute('SELECT product_id FROM v21_ratings WHERE user_id=?',(p['user_id'],))}
                for table in ('v21_feedback','v21_comparisons'):
                    excluded.update(r[0] for r in c.execute(f"SELECT f.product_id FROM {table} f JOIN v21_sessions s USING(session_id) WHERE s.user_id=? AND f.experience='EXPERIENCED' AND f.rating IS NOT NULL",(p['user_id'],)))
                result=self.engine.recommend(support,mode,excluded);sid=uuid.uuid4().hex
                if len(result)!=5 or len({r['id'] for r in result})!=5 or {r['id'] for r in result}&excluded:raise RuntimeError('Invalid Top5')
                c.execute('INSERT INTO v21_sessions VALUES (?,?,?,?,?,?,?,?,?,?)',(sid,p['user_id'],version,self.engine.catalog_version,json.dumps(sorted(seen)),json.dumps(result),now(),mode,497,json.dumps(sorted(excluded))))
                pool=sorted(set(self.catalog)-excluded-{r['id'] for r in result});k=min(5,len(pool));rng=random.Random(int(hashlib.sha256(('12:v223:comparison:'+sid).encode()).hexdigest(),16))
                for i in rng.sample(pool,k):c.execute('INSERT INTO v21_comparisons VALUES (?,?,?,?,?,?,?)',(sid,i,'V223 Uniform SRSWOR; known and Top5 excluded',k/len(pool),None,None,now()))
                c.commit();return self.session_view(c,c.execute('SELECT * FROM v21_sessions WHERE session_id=?',(sid,)).fetchone())
            except BaseException:c.rollback();raise
