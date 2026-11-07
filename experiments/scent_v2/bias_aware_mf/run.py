"""Same V26 developer folds; train real bias-aware models, no old final data access."""
import json,csv,hashlib,os,sys,math
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .core import ROOT,OUT,CONFIG,Content,MatrixFactorization,Baseline,developer_cohort,folds,validate_train,evaluate,predict,summarize
from .model import BiasAwareMF,freeze_user_state
from perfume.data import fragrantica


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/'outputs/validation/train_exclude_3.json',ROOT/'outputs/improvement/candidates.json',ROOT/'Term-project-datasets/fra_cleaned.csv',ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json'}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();m=args[1];flags=args[2]
            writing=(isinstance(m,str) and any(c in m for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('New V27 output only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.json','.csv','.npy','.npz')) and p not in allowed and not p.is_relative_to(OUT):raise PermissionError('Old result/model/final data forbidden')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded action denied')
    sys.addaudithook(audit)


def save_model(path,content,mf,pop,candidates,spec,cfg):
    """Save item state and policy, not training user biases/P/maps/history."""
    tokens=sorted(content.idf);ids=sorted(candidates);matrix=np.asarray([[content.vectors[i].get(t,0) for t in tokens] for i in ids])
    values=dict(Q=mf.Q,MF_items=np.asarray(sorted(mf.items,key=mf.items.get)),feature_items=np.asarray(ids),tokens=np.asarray(tokens),idf=np.asarray([content.idf[t] for t in tokens]),features=matrix,
        popularity=np.asarray([pop.counts[i] for i in ids]),popularity_maximum=np.asarray(pop.maximum),metadata=np.asarray(json.dumps(dict(spec=spec,mf_config=cfg,scope='V27 all50 developer refit, not independent validation'))))
    if spec['family']=='bias':values.update(mean=np.asarray(mf.mean),item_bias=mf.item_bias)
    with path.open('xb') as f:np.savez_compressed(f,**values)


def load_model(path):
    with np.load(path,allow_pickle=False) as v:
        meta=json.loads(str(v['metadata']));m=(BiasAwareMF if meta['spec']['family']=='bias' else MatrixFactorization)(**meta['mf_config']);m.Q=v['Q'].copy();m.items={str(i):n for n,i in enumerate(v['MF_items'])};m.Q.flags.writeable=False
        if meta['spec']['family']=='bias':m.mean=float(v['mean']);m.item_bias=v['item_bias'].copy();m.item_bias.flags.writeable=False
        c=Content();c.idf=dict(zip(map(str,v['tokens']),map(float,v['idf'])));c.vectors={str(i):{str(v['tokens'][n]):float(w) for n,w in enumerate(row) if w} for i,row in zip(v['feature_items'],v['features'])}
        from collections import defaultdict
        b=Baseline();b.counts=defaultdict(int,zip(map(str,v['feature_items']),map(int,v['popularity'])));b.maximum=float(v['popularity_maximum'])
        return c,m,b,meta


def main():
    if (OUT/'experiment_config.json').exists():raise FileExistsError('Existing run; no automatic retry/overwrite')
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates);parts=folds(cohort)
    expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text())
    assert len(cohort)==50 and source['developer_split_sha256']==expected['developer_split_sha256']
    assert [len(f['evaluation']) for f in parts]==[10]*5
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');base_cfg=CONFIG['base_mf'];fits=[]
    old_fit=MatrixFactorization.fit;bias_fit=BiasAwareMF.fit
    def counted(self,rows,family,fn):
        if len(fits)>=CONFIG['max_actual_data_MF_fits']:raise RuntimeError('Actual data fit budget26 exceeded')
        validate_train(rows,self._excluded)
        entry=dict(number=len(fits)+1,family=family,factors=self.factors,factor_L2=self.reg,bias_L2=getattr(self,'bias_reg',None),users=len({u for u,i,r in rows}),ratings=len(rows));fits.append(entry)
        result=fn(self,rows);entry.update(loss_first=self.losses[0],loss_last=self.losses[-1])
        if family=='bias':entry.update(train_mean=self.mean,user_bias_norm=float(np.linalg.norm(self.user_bias)),item_bias_norm=float(np.linalg.norm(self.item_bias)))
        return result
    def fit(cls,cfg,rows,excluded):
        model=cls(**cfg);model._excluded=set(excluded);model.fit(rows);del model._excluded;return freeze_user_state(model)
    table=[];stats={};records={};specs={};family_cfg={};contexts=[];model_cache={}
    def assess(spec,models):
        name=spec['name'];stats[name]=[];records[name]=[];specs[name]=spec
        for n,(fold,c,b,shared) in enumerate(contexts):
            m=models[n];summary,recs=evaluate(spec,fold,candidates,c,m,b,shared);stats[name].append(summary);records[name].extend(recs)
            table.append(dict(model=name,family=spec['family'],fold=fold['fold'],factors=m.factors,bias_L2=getattr(m,'bias_reg','N/A'),bias_shrinkage=spec.get('bias_shrinkage','N/A'),alpha=spec['alpha'],
                users=summary['users'],positive_users=summary['positive_users'],ndcg_at5=summary['ndcg'],recall_at5=summary['recall'],hit_rate_at5=summary['hit_rate'],positive_hits=summary['actual_positive_hits']))
    means=lambda name:float(np.mean([s['ndcg'] for s in stats[name]]))
    bias_configurations=[]
    def train_bias(cfg_index,cfg):
        models=[]
        for fold,c,b,shared in contexts:models.append(fit(BiasAwareMF,cfg,fold['train'],reserved|{r['user'] for r in fold['evaluation']}))
        model_cache[cfg_index]=models;family_cfg[cfg_index]=cfg;bias_configurations.append(cfg_index)
        for shrink in CONFIG['bias_shrinkage']:
            for alpha in CONFIG['alphas']:
                spec=dict(name=f'bias{cfg_index}_s{shrink:g}_a{alpha:g}',family='bias',config_index=cfg_index,bias_shrinkage=shrink,alpha=alpha);assess(spec,models)
        print(json.dumps(dict(bias_configuration=cfg,best_mean=max(means(name) for name in stats if specs[name].get('config_index')==cfg_index),actual_fits=len(fits))),flush=True)
    with patch.object(MatrixFactorization,'fit',lambda self,rows:counted(self,rows,'legacy',old_fit)),patch.object(BiasAwareMF,'fit',lambda self,rows:counted(self,rows,'bias',bias_fit)):
        legacy=[]
        for fold in parts:
            excluded=reserved|{r['user'] for r in fold['evaluation']};validate_train(fold['train'],excluded)
            c=Content().fit(catalog,{i for u,i,y in fold['train']});b=Baseline().fit(fold['train']);m=fit(MatrixFactorization,base_cfg,fold['train'],excluded);legacy.append(m)
            shared={}
            for row in fold['evaluation']:
                pool=sorted(set(candidates)-{i for i,y in row['support']});cs=c.score(row['support'],pool);bs=b.score(pool);cs.flags.writeable=False;bs.flags.writeable=False;shared[row['user']]=(cs,bs)
            contexts.append((fold,c,b,shared))
        for name,alpha in [('hybrid_baseline',.25),('pure_mf_baseline',0.)]:assess(dict(name=name,family='legacy',alpha=alpha),legacy)
        baseline=means('hybrid_baseline');assert abs(baseline-CONFIG['baseline_expected_ndcg'])<1e-12
        print(f'Baseline Hybrid mean reproduced {baseline:.12f}; initial4factor bias training',flush=True)
        train_bias(0,dict(**base_cfg,bias_regularization=.01))
        initial_best=max(means(n) for n in stats if specs[n]['family']=='bias');gate=initial_best>baseline+1e-12
        if gate:
            train_bias(1,dict(**base_cfg,bias_regularization=.001));train_bias(2,dict(**base_cfg,bias_regularization=.1))
            best4=max((n for n in stats if specs[n]['family']=='bias'),key=lambda n:means(n));cfg8=dict(family_cfg[specs[best4]['config_index']],factors=8);train_bias(3,cfg8)
        else:print('Initial bias-aware below original Hybrid: prune extra bias training and8factors',flush=True)
        def key(name):
            st=stats[name];spec=specs[name];cfg=family_cfg[spec['config_index']] if spec['family']=='bias' else base_cfg
            return (round(means(name),12),round(float(np.mean([s['recall'] for s in st])),12),round(float(np.mean([s['hit_rate'] for s in st])),12),-cfg['factors'],-abs(math.log(cfg.get('bias_regularization',.01)/.01)),-abs(math.log(spec.get('bias_shrinkage',1))),-abs(spec['alpha']-.25))
        eligible=[n for n in stats if specs[n]['family']=='bias' and means(n)>baseline+1e-12]
        selected=max(eligible,key=key) if eligible else 'hybrid_baseline';selected_spec=specs[selected];selected_cfg=family_cfg[selected_spec['config_index']] if selected_spec['family']=='bias' else base_cfg
        write('selection.json',dict(name=selected,spec=selected_spec,mf_config=selected_cfg,strict_improvement_required=True))
        summaries={n:dict(mean_ndcg=means(n),mean_recall=float(np.mean([s['recall'] for s in st])),mean_hit_rate=float(np.mean([s['hit_rate'] for s in st])),fold_ndcg=[s['ndcg'] for s in st],fold_std=float(np.std([s['ndcg'] for s in st])),
            folds_better_than_baseline=sum(s['ndcg']>b['ndcg']+1e-12 for s,b in zip(st,stats['hybrid_baseline'])),folds_worse_than_baseline=sum(s['ndcg']<b['ndcg']-1e-12 for s,b in zip(st,stats['hybrid_baseline'])),
            pooled_oof=summarize(records[n],candidates)) for n,st in stats.items()}
        full=[(r['user'],i,y) for r in cohort for i,y in r['support']+r['answers']];validate_train(full,reserved)
        c=Content().fit(catalog,{i for u,i,y in full});b=Baseline().fit(full);m=fit(BiasAwareMF if selected_spec['family']=='bias' else MatrixFactorization,selected_cfg,full,reserved)
        save_model(OUT/'best_model.npz',c,m,b,candidates,selected_spec,selected_cfg);lc,lm,lb,meta=load_model(OUT/'best_model.npz')
        synthetic=[(i,.7) for i in sorted(candidates)[:5]];assert predict(selected_spec,synthetic,candidates,c,m,b)==predict(meta['spec'],synthetic,candidates,lc,lm,lb)
        assert np.array_equal(m.Q,lm.Q)
        if selected_spec['family']=='bias':assert np.array_equal(m.item_bias,lm.item_bias) and m.mean==lm.mean
    best_bias=max((n for n in stats if specs[n]['family']=='bias'),key=key)
    write('evaluation_results.json',dict(status='COMPLETED_DEVELOPER_CV_ONLY',source=source,models=summaries,selected=selected,selected_spec=selected_spec,selected_mf_config=selected_cfg,best_bias_candidate=best_bias,
        relative_improvement_percent=(means(selected)/baseline-1)*100,observed_developer_CV_improvement=selected!='hybrid_baseline',adoption='Experimental artifact only; existing serving model unchanged',
        actual_data_MF_fit_count=len(fits),fits=fits,Content_fit_count=6,additional_gate_passed=gate,bias_training_configurations=[family_cfg[i] for i in bias_configurations],
        CV_user_count=50,folds=5,train_per_fold=40,test_per_fold=10,candidates=479,reserved_rating_tokens_decoded=0,background_rating_tokens_decoded=0,V24_output_reads=0,
        independent_final='NOT_EVALUATED',generalization_claim=False,score_clipping='[0,1] unchanged',score_normalization='NONE',component_fallback_unchanged=True,
        selection='Mean of5 positive-user fold NDCGs then Recall/HR; same developer folds used for selection, not nested or independent final',
        saved_model='Refit all50 only, not reevaluated on those training users; Q/item_bias/mean fixed at inference, no training-user P or bu saved',roundtrip_exact=True))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(baseline=baseline,best_bias=means(best_bias),selected=selected,selected_ndcg=means(selected),relative_percent=(means(selected)/baseline-1)*100,actual_data_MF_fits=len(fits))),flush=True)

if __name__=='__main__':main()
