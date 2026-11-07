"""Answer-free three-mode engine; unchanged Frozen arithmetic, V2-18 feature reuse."""
import hashlib,json,math,re
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from experiments.scent_v2.real_user_evaluation.engine import Engine as FrozenEngine,concentration
from experiments.scent_v2.expanded_content.models import ContentExperiment,project
from experiments.scent_v2.recommend import rank
from perfume.models import hybrid
from web.backend.advanced_search import BRAND_ALIASES
from experiments.scent_v2.real_user_dataset.catalog import search,normalize
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/scent_v2/unified_recommender'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text());MODES=CONFIG['modes']
# UI query aliases only: these do not establish product identity or translate notes.
SEARCH_ALIASES={**BRAND_ALIASES,'byredo':['바이레도'],'diptyque':['딥티크'],'le labo':['르 라보','르라보'],'aesop':['이솝'],'jo malone london':['조 말론','조말론']}


def percentiles(scores):
    """scores ID→finite raw score. Deterministic tie midranks in [0,1], no fit."""
    ids=sorted(scores,key=lambda i:(-scores[i],i));n=len(ids);out={};start=0
    while start<n:
        end=start+1
        while end<n and scores[ids[end]]==scores[ids[start]]:end+=1
        value=1-(start+end-1)/2/(n-1) if n>1 else .5
        for i in ids[start:end]:out[i]=value
        start=end
    return out


class Engine:
    """Original479+accepted18 only; no new metadata/factors/IDF or scoring labels."""
    def __init__(self):
        self.frozen=FrozenEngine();self.old=set(self.frozen.catalog)
        source=ROOT/'outputs/scent_v2/expanded_content/expanded_feature_summary.json';self.expanded=json.loads(source.read_text())
        assert self.expanded['source']['license']=='CC-BY-4.0'
        self.new=set(self.expanded['new_items']);assert len(self.old)==479 and len(self.new)==18 and not self.old&self.new
        service=self.frozen.service;self.vectors={i:dict(v) for i,v in service.content.vectors.items()}
        self.catalog={i:dict(r) for i,r in self.frozen.catalog.items()}
        for i,r in self.expanded['new_items'].items():
            self.vectors[i]=project(r['tokens'],service.content.idf)
            self.catalog[i]=dict(id=i,brand=r['brand'],name=r['name']+' · '+r['concentration'])
            assert self.vectors[i]
        self.content=ContentExperiment(self.vectors);self.catalog_version=hashlib.sha256(json.dumps(sorted(self.catalog)).encode()).hexdigest()
        self.model_version='v222-1';assert len(self.catalog)==497
    def version(self,mode):
        if mode not in MODES:raise ValueError('UNSUPPORTED_MODEL_MODE')
        return mode+':'+(self.frozen.model_version if mode==MODES[0] else self.model_version)
    def recommend(self,support,mode=MODES[0],exclude=()):
        """support exactly5 raw ratings. exclude known IDs only, not held-out labels."""
        if mode not in MODES:raise ValueError('UNSUPPORTED_MODEL_MODE')
        if len(support)!=5 or len({r['product_id'] for r in support})!=5:raise ValueError('INSUFFICIENT_MATCHED_SUPPORT')
        if any(isinstance(r['rating'],bool) or not isinstance(r['rating'],(int,float)) or not math.isfinite(r['rating']) or not 0<=r['rating']<=10 or abs(r['rating']*2-round(r['rating']*2))>1e-9 for r in support):raise ValueError('INVALID_RATING')
        if any(r['product_id'] not in self.catalog for r in support):raise ValueError('UNSUPPORTED_PRODUCT')
        if mode==MODES[0] and any(r['product_id'] not in self.old for r in support):raise ValueError('INSUFFICIENT_MATCHED_SUPPORT: Frozen은 기존479 Support5가 필요합니다.')
        pairs=[(r['product_id'],r['rating']/10) for r in support];seen={i for i,r in pairs}|set(exclude);service=self.frozen.service
        oldpool=sorted(self.old-seen);allpool=sorted(set(self.catalog)-seen);known=[(i,r) for i,r in pairs if i in service.mf.items]
        def old_scores():
            vector=service.mf.fold_in(known);m=service.mf.score_vector(vector,oldpool) if vector is not None else np.full(len(oldpool),np.nan)
            values=hybrid(service.content.score(pairs,oldpool),m,.25,service.baseline.score(oldpool))
            return {i:float(v) for i,v in zip(oldpool,values) if np.isfinite(v)}
        if mode==MODES[0]:values=old_scores();count=479;kind='Frozen Hybrid'
        else:
            c=self.content.score(pairs,allpool)
            if c['status']!='OK':raise ValueError('NO_USABLE_PROFILE')
            if mode==MODES[1]:values=c['all_scores'];kind='Expanded Content';count=497
            else:
                p=percentiles(c['all_scores']);values=dict(p)
                if known:
                    h=percentiles(old_scores())
                    for i in h:values[i]=.5*p[i]+.5*h[i]
                kind='Unified Hybrid · Experimental'+(' · Content-only fallback' if not known else '');count=497
        top=sorted(values,key=lambda i:(-values[i],i))[:5]
        if len(top)!=5:raise ValueError('INSUFFICIENT_CANDIDATES')
        return [dict(**self.catalog[i],rank=n+1,score=values[i],mode=mode,model_type=kind,candidate_count=count,origin='new18' if i in self.new else 'old479',concentration=concentration(self.catalog[i]['name'])) for n,i in enumerate(top)]
    def search(self,query):
        """Reuse English token search; explicit Korean brand query aliases, no product merge."""
        if not isinstance(query,str) or len(query)>100:raise ValueError('검색어는100자이하입니다.')
        if not query.strip():return [dict(self.catalog[i],concentration=concentration(self.catalog[i]['name'])) for i in sorted(self.new)[:5]+sorted(self.old)[:5]]
        q=query
        # Match only configured brand aliases (including spaced input and prefixes>=2).
        for brand,aliases in SEARCH_ALIASES.items():
            for alias in sorted(aliases,key=len,reverse=True):
                compact=alias.replace(' ','');parts=q.split();leading=''
                for n,part in enumerate(parts):
                    if not re.fullmatch('[가-힣]+',part):break
                    leading+=part
                    if len(leading)>=2 and compact.startswith(leading):
                        q=brand+' '+' '.join(parts[n+1:]);break
                if q!=query:break
            if q!=query:break
        return [dict(r,concentration=concentration(r['name'])) for r in search(self.catalog,q)]
