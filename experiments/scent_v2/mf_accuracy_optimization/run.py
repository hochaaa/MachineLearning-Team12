"""Five-fit limited MF search; development only; ALL V24 output reads forbidden."""
import csv,json,hashlib,os,sys
from unittest.mock import patch
from pathlib import Path
import numpy as np
from .core import ROOT,OUT,CONFIG,Content,MatrixFactorization,Baseline,developer_data,cache_scores,measure,tie_key,validate_train,hybrid
from perfume.data import fragrantica
from experiments.scent_v2.accuracy_optimization.core import paired
from experiments.scent_v2.accuracy_optimization.run import load_model


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,allow_nan=False,ensure_ascii=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/'outputs/validation/train_exclude_3.json',ROOT/'outputs/improvement/candidates.json',ROOT/'Term-project-datasets/fra_cleaned.csv'}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2]
            writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('Only V25 output writes allowed')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.json','.csv','.npy','.npz')) and p not in allowed and not p.is_relative_to(OUT):raise PermissionError('V24/final/old model data read forbidden')
        if event in ('socket.connect','subprocess.Popen','os.remove','os.rename','os.rmdir','os.symlink'):raise PermissionError('Unneeded action forbidden')
    sys.addaudithook(audit)


def save_model(content,mf,pop,candidates,selection):
    """Scoring artifact only; no P/user IDs/history/reserved values. Loader reused."""
    tokens=sorted(content.idf);items=sorted(candidates);matrix=np.asarray([[content.vectors[i].get(t,0) for t in tokens] for i in items])
    meta=dict(spec=dict(method='raw_alpha',alpha=selection['alpha']),mf_config=CONFIG['mf_grid'][selection['config_index']],scope='V25 development-trained; NOT independent final validation')
    with (OUT/'best_model.npz').open('xb') as f:np.savez_compressed(f,Q=mf.Q,MF_items=np.asarray(sorted(mf.items,key=mf.items.get)),feature_items=np.asarray(items),tokens=np.asarray(tokens),idf=np.asarray([content.idf[t] for t in tokens]),features=matrix,
        popularity=np.asarray([pop.counts[i] for i in items]),popularity_maximum=np.asarray(pop.maximum),metadata=np.asarray(json.dumps(meta)))


def main():
    if (OUT/'experiment_config.json').exists():raise FileExistsError('Existing experiment; no automatic refits/overwrite')
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    train,dev,reserved,split=developer_data(ROOT/'outputs/validation/train_exclude_3.json',candidates)
    assert split['train_ratings']==895 and split['development_users']==50 and split['reserved_users']==25
    write('development_split_summary.json',split)
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');content=Content().fit(catalog,{i for u,i,r in train});pop=Baseline().fit(train)
    fits=[];original_fit=MatrixFactorization.fit
    def counted(self,rows):
        if len(fits)>=CONFIG['MF_fit_budget']:raise RuntimeError('Fit budget5 exceeded')
        validate_train(rows,reserved|{r['user'] for r in dev});fits.append(dict(number=len(fits)+1,factors=self.factors,regularization=self.reg,ratings=len(rows)))
        return original_fit(self,rows)
    comparison=[];pruned=[];best=None;best_stats=None;best_records=None;best_mf=None;baseline_stats=None;baseline_records=None
    with patch.object(MatrixFactorization,'fit',counted):
        for index,cfg in enumerate(CONFIG['mf_grid']):
            mf=MatrixFactorization(**cfg).fit(train);del mf.P;mf.Q.flags.writeable=False
            qhash=hashlib.sha256(mf.Q.tobytes()).hexdigest();cache=cache_scores(dev,candidates,content,mf,pop);results={}
            def evaluate(alpha):
                nonlocal best,best_stats,best_records,best_mf
                if alpha in results:return results[alpha]
                stats,records=measure(alpha,cache,dev,candidates);results[alpha]=(stats,records)
                comparison.append(dict(config_index=index,factors=cfg['factors'],regularization=cfg['regularization'],learning_rate=cfg['learning_rate'],epochs=cfg['epochs'],alpha=alpha,
                    users=stats['users'],positive_users=stats['positive_users'],ndcg_at5=stats['ndcg'],recall_at5=stats['recall'],hit_rate_at5=stats['hit_rate'],coverage=stats['coverage_fraction'],positive_hits=stats['actual_positive_hits']))
                if best is None or stats['ndcg']>best_stats['ndcg']+1e-12 or (abs(stats['ndcg']-best_stats['ndcg'])<=1e-12 and tie_key(index,alpha)<tie_key(best['config_index'],best['alpha'])):
                    best=dict(config_index=index,alpha=alpha);best_stats=stats;best_records=records;best_mf=mf
                return stats,records
            if index==0:
                # First reproduce the old Hybrid exactly, before allowing search.
                baseline_stats,baseline_records=evaluate(.25)
                if abs(baseline_stats['ndcg']-CONFIG['baseline_expected_ndcg'])>1e-12:raise RuntimeError('V24 development baseline reproduction failed; stop')
                for alpha in CONFIG['alphas']:evaluate(alpha)
            else:
                left,_=evaluate(0.);right,_=evaluate(.25)
                if max(left['ndcg'],right['ndcg'])+1e-12>=baseline_stats['ndcg']:
                    for alpha in CONFIG['alphas']:evaluate(alpha)
                else:pruned.append(index)
            assert qhash==hashlib.sha256(mf.Q.tobytes()).hexdigest()
            print(json.dumps(dict(fit=len(fits),factors=cfg['factors'],reg=cfg['regularization'],alphas=list(results),best_development_ndcg=best_stats['ndcg'])),flush=True)
    save_model(content,best_mf,pop,candidates,best)
    c,m,b,meta=load_model(OUT/'best_model.npz');loaded_cache=cache_scores(dev,candidates,c,m,b)
    # Roundtrip inference equality, not another final/developer optimization pass.
    from experiments.scent_v2.recommend import rank
    for x,record in zip(loaded_cache,best_records):
        top=rank(x['pool'],hybrid(x['content'],x['mf'],best['alpha'],x['fallback']))[:5]
        if top!=record['top']:raise AssertionError('Saved model roundtrip changed ranking')
    improvement=(best_stats['ndcg']/baseline_stats['ndcg']-1)*100
    result=dict(status='COMPLETED_DEVELOPMENT_ONLY',baseline=baseline_stats,best=best_stats,selection=best,mf_config=CONFIG['mf_grid'][best['config_index']],
        development_relative_improvement_percent=improvement,development_absolute_improvement=best_stats['ndcg']-baseline_stats['ndcg'],
        paired_development_exploratory=paired(baseline_records,best_records),independent_final='NOT_EVALUATED',independent_improvement_claim=False,
        V24_output_files_read=0,V24_final_rating_tokens_decoded=0,reserved_users_used_for_training_or_tuning=False,
        source='Only original Train IDs/items plus retained train/developer labels',split=split,
        MF_fit_count=len(fits),fits=fits,Content_fit_count=1,actual_weight_comparisons=len(comparison),pruned_configs=pruned,
        same_C_MF_arrays_per_alpha=True,score_normalization=False,MF_clipping_unchanged=True,component_fallback_unchanged=True,
        alpha0_note='MF with existing content/popularity fallback for missing components; not strict pure-MF item exclusion',
        saved_model_roundtrip_top5_exact=True,model_path='outputs/scent_v2/mf_accuracy_optimization/best_model.npz',serving_model_modified=False)
    write('evaluation_results.json',result)
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    print(json.dumps(dict(best=best,MF_config=result['mf_config'],baseline=baseline_stats['ndcg'],best_ndcg=best_stats['ndcg'],relative_percent=improvement,fits=len(fits)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
