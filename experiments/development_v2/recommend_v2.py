"""Standalone V2 CLI/service; never connects to or replaces the V1 website."""
import json,argparse,time
from pathlib import Path
import numpy as np
from data import ROOT,OUT,bundle,guard,sha
from content_v2 import ContentV2
from mf_v2 import BiasMF
from perfume.models import MatrixFactorization,Baseline
from foldin_v2 import validate_support,fold_in,score_vector
from hybrid_v2 import combine,ranked

class ServiceV2:
    """Load ignored V2 assets, rebuild fixed train-only content representation, no MF refit."""
    def __init__(self):
        guard();start=time.perf_counter();path=OUT/'models'
        meta=json.loads((path/'model.json').read_text());self.config=meta['config'];cfg=meta['mf_config']
        self.model=BiasMF(cfg,self.config['seed']) if meta['biased'] else MatrixFactorization(**{k:cfg[k] for k in ['factors','epochs','learning_rate','regularization']},seed=self.config['seed'])
        self.model.users,self.model.items=meta['users'],meta['items'];self.model.config=cfg
        if meta['biased']:self.model.mean=meta['mean']
        with np.load(path/'model.npz',allow_pickle=False) as archive:
            for key in archive.files:
                arr=archive[key].copy();arr.flags.writeable=False;setattr(self.model,key,arr)
        train,self.pool,self.catalog,raw=bundle()
        recipe=json.loads((path/'content_recipe.json').read_text())
        from data import INPUTS
        for kind,h in recipe['input_hashes'].items():
            if sha(ROOT/INPUTS[kind])!=h:raise ValueError('V2 source input changed')
        self.content=ContentV2(recipe['config']).fit(self.catalog,raw,{i for _,i,_ in train});self.baseline=Baseline().fit(train)
        self.load_seconds=time.perf_counter()-start
    def recommend(self,support,condition='none'):
        """Exactly3 normalized ratings; hard optional metadata filter, deterministic Top5."""
        support=validate_support(support,self.catalog,3)
        if any(i not in self.pool for i,_ in support):raise ValueError('Input must belong to fixed479 pool')
        required={'none':None,'woody':'accord:woody','floral':'accord:floral','rose':'note:rose'}
        if condition not in required:raise ValueError('Unknown condition')
        seen={i for i,_ in support};pool=[i for i in self.pool if i not in seen];start=time.perf_counter()
        z=fold_in(self.model,support,self.config['foldin_regularization']);fold_seconds=time.perf_counter()-start
        m=score_vector(self.model,z,pool);c=self.content.score(support,pool)
        s,fb=combine(c,m,self.baseline.score(pool),pool,self.config['selected_recipe']['fusion'],3)
        # Filter after fusion to preserve candidate-score calibration scope.
        lookup=dict(zip(pool,s));eligible=[i for i in pool if required[condition] is None or required[condition] in self.catalog[i]['tokens']]
        ids=ranked(eligible,[lookup[i] for i in eligible],5)
        return {'model_version':'Development V2 (experimental, not Frozen V1)','condition':condition,'results':[{'perfume_id':i,'name':self.catalog[i]['name'],'brand':self.catalog[i]['brand'],'score':float(lookup[i]),'filter_satisfied':required[condition] is None or required[condition] in self.catalog[i]['tokens']} for i in ids],'fallback':fb,'foldin_seconds':fold_seconds}

def demo_support(service,scenario='mixed'):
    """Synthetic values on deterministic public catalog IDs; never copied user ratings."""
    ratings={'high':[.9,.9,.9],'low':[.1,.1,.1],'mixed':[.9,.1,.6],'equal':[.5,.5,.5],'zeros':[0.,0.,0.]}
    return list(zip(service.pool[:3],ratings[scenario]))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--support',type=Path);parser.add_argument('--demo',choices=['high','low','mixed','equal','zeros'],default='mixed');parser.add_argument('--condition',choices=['none','woody','floral','rose'],default='none');args=parser.parse_args()
    service=ServiceV2()
    if args.support:
        path=args.support.resolve()
        if any(folder in path.parents for folder in [ROOT/'outputs/final',ROOT/'outputs/validation',ROOT/'outputs/improvement',ROOT/'Term-project-datasets']):raise ValueError('Legacy data/answers cannot be CLI support')
        support=json.loads(path.read_text())
    else:support=demo_support(service,args.demo)
    print(json.dumps(service.recommend(support,args.condition),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
