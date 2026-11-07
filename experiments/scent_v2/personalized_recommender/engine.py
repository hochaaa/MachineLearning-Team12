"""Signed Content as a SEPARATE mode, not an extra adjustment to old rating weights."""
import json,math
from pathlib import Path
from experiments.scent_v2.unified_recommender.engine import Engine as BaseEngine,MODES as OLD_MODES,ROOT
from experiments.scent_v2.real_user_evaluation.engine import concentration
OUT=ROOT/'outputs/scent_v2/personalized_recommender'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())
PERSONAL='PERSONALIZED_497';DIVERSE='PERSONALIZED_497_MMR';MODES=[*OLD_MODES,PERSONAL,DIVERSE]


def cosine(a,b):
    """a,b: existing unit sparse feature dictionaries; empty vectors contribute0."""
    return sum(w*b.get(t,0) for t,w in a.items())


def preferences(vectors,support,candidates):
    """Exactly5 raw-score records; signed mean similarity, not baseline score+correction."""
    if len(support)!=5 or len({r['product_id'] for r in support})!=5:raise ValueError('INSUFFICIENT_MATCHED_SUPPORT')
    if any(isinstance(r['rating'],bool) or not isinstance(r['rating'],(int,float)) or not math.isfinite(r['rating']) or not 0<=r['rating']<=10 or abs(r['rating']*2-round(r['rating']*2))>1e-9 for r in support):raise ValueError('INVALID_RATING')
    if any(r['product_id'] not in vectors for r in support):raise ValueError('UNSUPPORTED_PRODUCT')
    pos=[(r['product_id'],(r['rating']-6)/4) for r in support if r['rating']>=CONFIG['positive_min_raw']]
    neg=[(r['product_id'],(4-r['rating'])/4) for r in support if r['rating']<=CONFIG['negative_max_raw']]
    values={};parts={}
    for i in candidates:
        p=sum(w*cosine(vectors[j],vectors[i]) for j,w in pos)/len(pos) if pos else 0
        n=sum(w*cosine(vectors[j],vectors[i]) for j,w in neg)/len(neg) if neg else 0
        values[i]=max(0.,min(1.,.5+.5*(p-n)));parts[i]=dict(positive_similarity=p,negative_similarity=n,positive_anchors=[j for j,w in pos],negative_anchors=[j for j,w in neg])
    return values,parts


def rerank(values,vectors,k=5,diversity=True):
    """Greedy λ*relevance−(1−λ)*maxcos; top30, per-pick loss bounded by.05."""
    if len(values)<k:raise ValueError('INSUFFICIENT_CANDIDATES')
    remaining=sorted(values,key=lambda i:(-values[i],i))[:max(k,CONFIG['mmr_shortlist'])];chosen=[];trace={}
    while len(chosen)<k:
        best=max(values[i] for i in remaining)
        allowed=[i for i in remaining if not diversity or values[i]>=best-CONFIG['maximum_relevance_drop_per_pick']]
        def detail(i):
            sim=max((cosine(vectors[i],vectors[j]) for j in chosen),default=0)
            return (CONFIG['mmr_lambda']*values[i]-(1-CONFIG['mmr_lambda'])*sim if diversity else values[i],sim)
        i=min(allowed,key=lambda i:(-detail(i)[0],i));score,sim=detail(i)
        trace[i]=dict(mmr_score=score,diversity_penalty=(1-CONFIG['mmr_lambda'])*sim if diversity else 0,best_remaining_relevance=best)
        chosen.append(i);remaining.remove(i)
    return chosen,trace


class Engine(BaseEngine):
    def version(self,mode):
        return mode+':'+CONFIG['version'] if mode in (PERSONAL,DIVERSE) else super().version(mode)
    def explain(self,item,support,parts=None,trace=None):
        """Only overlap tokens and computed similarity; no invented notes or LLM calls."""
        high=[r for r in support if r['rating']>=7];evidence=[];reasons=[]
        if high:
            closest=max(high,key=lambda r:cosine(self.vectors[item],self.vectors[r['product_id']]))
            anchor=closest['product_id'];shared=sorted(set(self.vectors[item])&set(self.vectors[anchor]));similarity=cosine(self.vectors[item],self.vectors[anchor])
            if shared and similarity>0:
                evidence=shared[:4];labels=', '.join(t.split(':',1)[1] for t in evidence)
                reasons.append(f"높게 평가한 {self.catalog[anchor]['name']}와 공통 특성({labels})이 있습니다. 콘텐츠 유사도 {similarity:.3f}.")
        if parts:
            if parts['negative_anchors']:reasons.append(f"평점 강도를 반영한 비선호 콘텐츠 유사도 {parts['negative_similarity']:.3f}를 비선호 신호로 반영했습니다.")
            if not parts['positive_anchors'] and not parts['negative_anchors']:reasons.append('중립 평점만 입력되어 뚜렷한 선호·비선호를 추정하지 않았습니다.')
        if trace and trace['diversity_penalty']>0:reasons.append(f"앞선 추천과의 중복 유사도를 줄이는 재정렬을 적용했습니다. 다양성 감점 {trace['diversity_penalty']:.3f}.")
        if not reasons:reasons.append('선택한 모델의 계산 점수에 따라 추천했습니다. 높은 평점과의 공통 향 특성은 확인되지 않았습니다.')
        return dict(reasons=reasons,evidence_tokens=evidence)
    def recommend(self,support,mode=OLD_MODES[0],exclude=()):
        if mode not in (PERSONAL,DIVERSE):
            rows=super().recommend(support,mode,exclude)
            # Explanatory metadata only: old mode scores/IDs/order stay identical.
            return [dict(r,**self.explain(r['id'],support)) for r in rows]
        seen={r['product_id'] for r in support}|set(exclude);pool=sorted(set(self.catalog)-seen)
        values,parts=preferences(self.vectors,support,pool);top,trace=rerank(values,self.vectors,diversity=mode==DIVERSE)
        return [dict(**self.catalog[i],rank=n+1,score=values[i],relevance_score=values[i],mode=mode,
            model_type='Personalized Content'+(' + MMR' if mode==DIVERSE else ''),candidate_count=497,
            origin='new18' if i in self.new else 'old479',concentration=concentration(self.catalog[i]['name']),
            preference_components=parts[i],reranking=trace[i],**self.explain(i,support,parts[i],trace[i] if mode==DIVERSE else None)) for n,i in enumerate(top)]
