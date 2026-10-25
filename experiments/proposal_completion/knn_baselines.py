"""Exploratory memory-CF; training only similarities, validation only evaluation.

No MF fitting, no fold-in, no internal/external answers opened. Original implementation.
"""
from common import *
from perfume.evaluation import evaluate
class KNN:
    """Overlap-only cosine with n/(n+shrinkage); no missing-as-zero interpretation."""
    def __init__(self,mode,k=10,min_common=2,shrinkage=5):
        """mode user/item; k maximum contributing neighbors per candidate; min_common overlap; shrinkage confidence damping."""
        if mode not in ('user','item') or k<1 or min_common<1 or shrinkage<0:raise ValueError('Invalid KNN parameters')
        self.mode,self.k,self.min_common,self.shrinkage=mode,k,min_common,shrinkage
    def fit(self,train):
        """Store observed edges only; similarities have no validation input."""
        self.users=defaultdict(dict);self.items=defaultdict(dict)
        for u,i,r in train:self.users[u][i]=r;self.items[i][u]=r
        self.counts=Counter(i for _,i,_ in train);self.maximum=max(self.counts.values(),default=1)
        entities=self.users if self.mode=='user' else self.items
        self.similarities=defaultdict(dict);self.overlaps=[]
        ids=sorted(entities)
        for n,a in enumerate(ids):
            for b in ids[n+1:]:
                keys=entities[a].keys()&entities[b].keys();self.overlaps.append(len(keys))
                s=self.similarity(entities[a],entities[b])
                if s>0:self.similarities[a][b]=s;self.similarities[b][a]=s
        return self
    def similarity(self,a,b):
        """Cosine on co-observed coordinates only; undefined/insufficient overlap→0."""
        keys=sorted(a.keys()&b.keys())
        if len(keys)<self.min_common:return 0.
        x=np.array([a[i] for i in keys]);y=np.array([b[i] for i in keys]);den=np.linalg.norm(x)*np.linalg.norm(y)
        return float(x@y/den*len(keys)/(len(keys)+self.shrinkage)) if den else 0.
    def predict(self,user,pool,support=None):
        """Existing-user inference; optional new support compares to train only. Fallback is train log-popularity."""
        history=self.users.get(user,{}) if support is None else dict(support)
        if self.mode=='user':
            sims=self.similarities.get(user,{}) if support is None else {u:self.similarity(history,h) for u,h in self.users.items() if u!=user}
        scores=[];fallback=0;effective=[]
        for item in pool:
            if self.mode=='user':neighbors=[(s,u,self.items[item][u]) for u,s in sims.items() if s>0 and u!=user and u in self.items.get(item,{})]
            else:neighbors=[(self.similarities.get(item,{}).get(i,0),i,r) for i,r in history.items() if i!=item and self.similarities.get(item,{}).get(i,0)>0]
            neighbors=sorted(neighbors,key=lambda x:(-x[0],x[1]))[:self.k]
            effective.append(len(neighbors))
            if neighbors:scores.append(sum(s*r for s,_,r in neighbors)/sum(s for s,_,_ in neighbors))
            else:
                fallback+=1;scores.append(float(np.log1p(self.counts[item])/np.log1p(self.maximum)))
        return scores,fallback,effective

def main():
    train=load('outputs/validation/train_exclude_3.json');val=load('outputs/improvement/validation.json');pool=load('outputs/improvement/candidates.json')
    users=sorted({u for u,_,_ in val});out=[];sparse={}
    for mode in ['user','item']:
        model=KNN(mode).fit(train)
        entities=model.users if mode=='user' else model.items
        ov=np.asarray(model.overlaps)
        sparse[mode]={'entity_count':len(entities),'pairs':len(ov),'common_count_distribution':dict(sorted(Counter(model.overlaps).items())),'pairs_with_no_overlap_fraction':float(np.mean(ov==0)),'entities_without_valid_neighbors':sum(not model.similarities[e] for e in entities),'mean_observations_per_entity':float(np.mean([len(h) for h in entities.values()]))}
        for k in [5,10,20]:
            model.k=k;predictions={};fallback=0;total=0;allfallbackusers=0;effective=[]
            for u in users:
                candidates=[i for i in pool if i not in model.users[u]]
                scores,fb,eff=model.predict(u,candidates)
                fallback+=fb;total+=len(candidates);allfallbackusers+=fb==len(candidates);effective.extend(eff)
                ranked=[candidates[n] for n in sorted(range(len(candidates)),key=lambda n:(-scores[n],candidates[n]))][:10]
                assert len(ranked)==10 and len(set(ranked))==10
                assert set(ranked)<=set(pool) and not set(ranked)&set(model.users[u])
                predictions[u]={f'{mode}_knn':ranked}
            summaries,_=evaluate(predictions,val,k=10,relevance=.7)
            assert summaries[0]['evaluation_users']==168 and summaries[0]['positive_users']==137
            row={'mode':mode,'neighbors':k,'min_common':2,'shrinkage':5,**summaries[0],'fallback_candidate_fraction':fallback/total,'all_candidate_fallback_users':allfallbackusers,'candidate_scores':total,'mean_used_neighbors':float(np.mean(effective))}
            out.append(row);print(mode,k,row['ndcg'],row['fallback_candidate_fraction'],flush=True)
    table('knn_validation.csv',out);save('knn_sparsity.json',sparse)
    selected={m:max((r for r in out if r['mode']==m),key=lambda r:(r['ndcg'],-r['neighbors'])) for m in ['user','item']}
    save('knn_selection.json',{'scope':'post-freeze exploratory validation only; final model unchanged','selected':selected,'cohort_users':len(users),'positive_users':137,'candidates':len(pool),'relevance':.7,'k_ranking':10,'ranking_checks':'all6 configurations: 168 users, Top10 unique, within479, no train-seen, positive denominator137', 'new_user_evaluation':'N/A; optional support inference implemented but no new-user score claimed'})
    bar('knn_validation.svg','Supplementary kNN validation NDCG@10',[f"{r['mode']} k={r['neighbors']}" for r in out],[r['ndcg'] for r in out],'Train min3; 479 common pool; 137 positive users; min_common=2; shrinkage=5; no test evaluation')
if __name__=='__main__':main_run(main,'knn_baselines')
