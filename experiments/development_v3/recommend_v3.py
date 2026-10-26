"""Independent V3-selection CLI. Never changes or connects to the existing website."""
import json,argparse,time
from pathlib import Path
import numpy as np
from v3_data import ROOT,OUT,load_train,guard,sha
from mf_v3 import MFV3
from perfume.models import MatrixFactorization
from content_v2 import ContentV2
from foldin_v2 import validate_support
from foldin_v3 import fold,score,normalize_support
from hybrid_v2 import combine,ranked
from perfume.models import Baseline

class ServiceV3:
    def __init__(self):
        guard();start=time.perf_counter();path=OUT/'models/final'
        if not (path/'metadata.json').exists():raise RuntimeError('V3 final training has not completed')
        meta=json.loads((path/'metadata.json').read_text());self.policy=meta['policy'];cfg=meta['training_config'];self.seed=meta['seed']
        self.model=MatrixFactorization(**{k:cfg[k] for k in ['factors','epochs','learning_rate','regularization']},seed=self.seed) if self.policy['id']=='V1' else MFV3(cfg,self.seed)
        self.model.users,self.model.items=meta['users'],meta['items'];self.model.config=cfg
        if meta['mean'] is not None:self.model.mean=meta['mean']
        with np.load(path/'weights.npz',allow_pickle=False) as archive:
            for key in archive.files:
                a=archive[key].copy();a.flags.writeable=False;setattr(self.model,key,a)
        recipe=json.loads((path/'input_recipe.json').read_text())
        for key,p in [('train_sha256','outputs/validation/train_exclude_3.json'),('candidate_sha256','outputs/improvement/candidates.json'),('catalog_sha256','Term-project-datasets/fra_cleaned.csv')]:
            if sha(ROOT/p)!=recipe[key]:raise ValueError('V3 permitted source input changed')
        train,self.pool,self.catalog,raw=load_train();c={'kind':'v1','mode':'rating'} if self.policy['content']=='v1' else {'kind':'split','mode':'neutral','accord_weight':.5}
        self.content=ContentV2(c).fit(self.catalog,raw,{i for _,i,_ in train});self.baseline=Baseline().fit(train);self.load_seconds=time.perf_counter()-start
    def recommend(self,support,condition='none',rating_scale=10,k=5):
        if k not in (5,10):raise ValueError('k must be5 or10')
        support=normalize_support(support,rating_scale);support=validate_support(support,self.catalog,3)
        if any(i not in self.pool for i,_ in support):raise ValueError('Input must belong to479 pool')
        rules={'none':None,'woody':'accord:woody','floral':'accord:floral','rose':'note:rose'}
        if condition not in rules:raise ValueError('Unknown filter')
        seen={i for i,_ in support};pool=[i for i in self.pool if i not in seen];start=time.perf_counter();z=fold(self.model,support,self.policy);fold_seconds=time.perf_counter()-start
        c=self.content.score(support,pool);m=score(self.model,z,pool);s,fb=combine(c,m,self.baseline.score(pool),pool,{'method':self.policy['fusion'],'alpha':self.policy['alpha']},3)
        available=[(i,float(v)) for i,v in zip(pool,s) if rules[condition] is None or rules[condition] in self.catalog[i]['tokens']];ids=ranked([i for i,v in available],[v for i,v in available],k);values=dict(available)
        return {'model_version':'Development V3 selection (independent, not website)','policy':self.policy['id'],'retained_v1_equations':self.policy['id']=='V1','condition':condition,'k':k,'results':[{'perfume_id':i,'brand':self.catalog[i]['brand'],'name':self.catalog[i]['name'],'score':values[i],'condition_satisfied':rules[condition] is None or rules[condition] in self.catalog[i]['tokens']} for i in ids],'fallback':fb,'foldin_seconds':fold_seconds}

def synthetic_support(service,scenario='mixed'):
    values={'high':[9,9,9],'low':[1,1,1],'mixed':[9,1,6],'equal':[5,5,5],'zeros':[0,0,0],'tens':[10,10,10]}
    return list(zip(service.pool[:3],values[scenario]))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--support',type=Path);p.add_argument('--rating-scale',type=int,choices=[1,10],default=10);p.add_argument('--demo',choices=['high','low','mixed','equal','zeros','tens'],default='mixed');p.add_argument('--condition',choices=['none','woody','floral','rose'],default='none');p.add_argument('--k',type=int,choices=[5,10],default=5);a=p.parse_args();service=ServiceV3()
    if a.support:
        path=a.support.resolve()
        if any(folder in path.parents for folder in [ROOT/'outputs/final',ROOT/'outputs/validation',ROOT/'outputs/improvement',ROOT/'Term-project-datasets']):p.error('Legacy data/answer files cannot be request inputs')
        support=json.loads(path.read_text())
    else:
        if a.rating_scale!=10:p.error('Demo ratings use explicit raw0..10 scale')
        support=synthetic_support(service,a.demo)
    try:result=service.recommend(support,a.condition,a.rating_scale,a.k)
    except ValueError as exc:p.error(str(exc))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
