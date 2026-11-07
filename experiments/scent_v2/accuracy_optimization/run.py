"""Accuracy-only limited MF search, developer freeze, and one-time sealed final test."""
import json,csv,hashlib,os,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .core import ROOT,OUT,CONFIG,Content,MatrixFactorization,Baseline,split,validate_train,evaluate,paired
from perfume.data import fragrantica


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,allow_nan=False,ensure_ascii=False)
    (OUT/name).chmod(0o600)


def guard():
    """Deny old model/answer reads and outside-output writes after imports."""
    allowed={ROOT/'outputs/validation/train_exclude_3.json',ROOT/'outputs/improvement/candidates.json',ROOT/'Term-project-datasets/fra_cleaned.csv'}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();m=args[1];flags=args[2]
            writing=(isinstance(m,str) and any(x in m for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('Write outside V24')
            if not writing and p.is_relative_to(ROOT) and p.suffix in ('.json','.csv','.npz','.npy') and p not in allowed and not p.is_relative_to(OUT):raise PermissionError('Old answer/model data denied')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded action denied')
    sys.addaudithook(audit)


def save_model(path,content,mf,pop,candidates,spec,mf_config):
    """Only learned item factors/IDF/item features/popularity; no P/user mapping/history."""
    tokens=sorted(content.idf);items=sorted(candidates);index={t:n for n,t in enumerate(tokens)};matrix=np.zeros((len(items),len(tokens)))
    for n,i in enumerate(items):
        for t,w in content.vectors[i].items():matrix[n,index[t]]=w
    with path.open('xb') as f:np.savez_compressed(f,Q=mf.Q,MF_items=np.asarray(sorted(mf.items,key=mf.items.get)),
        feature_items=np.asarray(items),tokens=np.asarray(tokens),idf=np.asarray([content.idf[t] for t in tokens]),features=matrix,
        popularity=np.asarray([pop.counts[i] for i in items]),popularity_maximum=np.asarray(pop.maximum),
        metadata=np.asarray(json.dumps(dict(spec=spec,mf_config=mf_config,scope='V24 developer-selected; final users excluded; common479'))))
    path.chmod(0o600)


def load_model(path):
    """No pickle, reconstruct frozen-in-memory scoring objects only."""
    with np.load(path,allow_pickle=False) as v:
        meta=json.loads(str(v['metadata']));mf=MatrixFactorization(**meta['mf_config']);mf.Q=v['Q'].copy();mf.Q.flags.writeable=False;mf.items={str(i):n for n,i in enumerate(v['MF_items'])}
        c=Content();c.idf=dict(zip(map(str,v['tokens']),map(float,v['idf'])));c.vectors={str(i):{str(v['tokens'][n]):float(w) for n,w in enumerate(row) if w} for i,row in zip(v['feature_items'],v['features'])}
        b=Baseline();from collections import defaultdict
        b.counts=defaultdict(int,zip(map(str,v['feature_items']),map(int,v['popularity'])));b.maximum=float(v['popularity_maximum'])
        return c,mf,b,meta


def open_final():
    """Fail closed unless selection AND final fitting are frozen; one allowed opening."""
    if not (OUT/'selection.json').is_file() or not (OUT/'final_fit_complete.json').is_file():raise RuntimeError('Final access before selection/final fits')
    with (OUT/'final_opened_once.json').open('x') as f:json.dump(dict(final_open_count=1,no_retuning=True),f)
    return json.loads((OUT/'sealed_final.private.json').read_text())


def main():
    if (OUT/'experiment_config.json').exists():raise FileExistsError('Existing run: no automatic fit/final retry')
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    raw=json.loads((ROOT/'outputs/validation/train_exclude_3.json').read_text());candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    train,dev,final=split(raw,candidates);final_users={r['user'] for r in final};dev_users={r['user'] for r in dev}
    assert not final_users&dev_users;assert split(raw,candidates)==(train,dev,final)
    write('sealed_final.private.json',final);final_count=len(final);del final,raw
    validate_train(train,final_users|dev_users)
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');content=Content().fit(catalog,{i for u,i,r in train});pop=Baseline().fit(train)
    write('split_summary.json',dict(train_users=len({u for u,i,r in train}),train_ratings=len(train),development_users=len(dev),development_support=len(dev)*5,
        development_answers=sum(len(r['answers']) for r in dev),final_users=final_count,final_answer_values_accessed_before_selection=False,
        split_seed=12,candidates=479,support_overlap=0,train_eval_user_overlap=0,
        population_limit='New user-disjoint V24 split of historically studied original Train. Not a new external/pristine dataset.'))
    fits=[];original_fit=MatrixFactorization.fit
    def counted(self,rows):
        if len(fits)>=5:raise RuntimeError('MF budget5 exceeded')
        validate_train(rows,final_users)
        fits.append(dict(number=len(fits)+1,ratings=len(rows),users=len({u for u,i,r in rows}),factors=self.factors,reg=self.reg))
        return original_fit(self,rows)
    comparisons=[];cache={};best=None;best_ndcg=-1.;baseline_mf_ndcg=None
    def measure(stage,name,spec,cohort,c,m,b,mf_index):
        stats,records=evaluate(spec,cohort,candidates,c,m,b)
        comparisons.append(dict(stage=stage,model=name,mf_config_index=mf_index,users=stats['users'],positive_users=stats['positive_users'],
            ndcg_at5=stats['ndcg'],recall_at5=stats['recall'],hit_rate_at5=stats['hit_rate'],coverage=stats['coverage_fraction'],positive_hits=stats['actual_positive_hits']))
        return stats,records
    with patch.object(MatrixFactorization,'fit',counted):
        for mi,mcfg in enumerate(CONFIG['MF_grid']):
            mf=MatrixFactorization(**mcfg).fit(train);del mf.P;mf.Q.flags.writeable=False;cache[mi]=mf
            print(f'Development MF fit{mi+1}/3 rows={len(train)} config={mi}',flush=True)
            mfstats,_=measure('development','pure_mf_diagnostic',dict(method='pure_mf'),dev,content,mf,pop,mi)
            if mi==0:
                baseline_mf_ndcg=mfstats['ndcg']
                for method in ('baseline','v22_unified','v23_personalized','v23_personalized_mmr'):
                    stats,_=measure('development',method,dict(method=method),dev,content,mf,pop,mi)
                    if method=='baseline' or stats['ndcg']>best_ndcg+1e-12:best=dict(spec=dict(method=method),mf_index=0);best_ndcg=stats['ndcg']
            elif mfstats['ndcg']<baseline_mf_ndcg:
                print(f'Prune MF config{mi}: pure MF developer NDCG below baseline',flush=True);continue
            for profile in CONFIG['profiles']:
                for alpha in CONFIG['rank_alphas']+(['adaptive'] if profile=='rating' else []):
                    spec=dict(method='rank_hybrid',profile=profile,alpha=alpha);name=f'rank_{profile}_{alpha}'
                    stats,_=measure('development',name,spec,dev,content,mf,pop,mi)
                    if stats['ndcg'] is not None and stats['ndcg']>best_ndcg+1e-12:best_ndcg=stats['ndcg'];best=dict(spec=spec,mf_index=mi)
        write('selection.json',dict(**best,development_ndcg=best_ndcg,rule=CONFIG['selection'],final_values_seen=False))
        # Freeze selection BEFORE learning from the development users for final assessment.
        final_train=list(train)+[(r['user'],i,y) for r in dev for i,y in r['support']+r['answers']]
        validate_train(final_train,final_users)
        final_content=Content().fit(catalog,{i for u,i,y in final_train});final_pop=Baseline().fit(final_train)
        final_base=MatrixFactorization(**CONFIG['MF_grid'][0]).fit(final_train);del final_base.P;final_base.Q.flags.writeable=False
        if best['mf_index']==0:final_selected=final_base
        else:
            final_selected=MatrixFactorization(**CONFIG['MF_grid'][best['mf_index']]).fit(final_train);del final_selected.P;final_selected.Q.flags.writeable=False
        save_model(OUT/'best_model.npz',final_content,final_selected,final_pop,candidates,best['spec'],CONFIG['MF_grid'][best['mf_index']])
        loaded_c,loaded_m,loaded_b,meta=load_model(OUT/'best_model.npz')
        assert np.array_equal(loaded_m.Q,final_selected.Q)
        write('final_fit_complete.json',dict(MF_fits=len(fits),Content_fits=2,final_users_excluded=True,final_train_users=len({u for u,i,y in final_train}),final_train_ratings=len(final_train),selected_model_sha256=hashlib.sha256((OUT/'best_model.npz').read_bytes()).hexdigest()))
        final=open_final() # The only final-label access, after frozen configuration and refits.
        final_stats={};final_records={}
        for method in ('baseline','v22_unified','v23_personalized','v23_personalized_mmr'):
            stats,records=measure('final',method,dict(method=method),final,final_content,final_base,final_pop,0);final_stats[method]=stats;final_records[method]=records
        stats,records=measure('final','selected',best['spec'],final,loaded_c,loaded_m,loaded_b,best['mf_index']);final_stats['selected']=stats;final_records['selected']=records
        uncertainty=paired(final_records['baseline'],final_records['selected'])
        delta=stats['ndcg']-final_stats['baseline']['ndcg']
        write('evaluation_results.json',dict(status='COMPLETED',split='User-disjoint one-time V24 final on previously studied source, not pristine external',
            selected=best,development_selected_ndcg=best_ndcg,final=final_stats,paired_ndcg=uncertainty,
            observed_final_improvement=delta>1e-12,final_ndcg_delta=delta,final_open_count=1,selection_uses_final=False,
            serving_model_modified=False,adoption='Developer-selected artifact only; keep deployed Frozen unchanged; no final-based retuning',
            MF_fit_count=len(fits),fits=fits,Content_fit_count=2,common_candidates=479,expanded497_accuracy=CONFIG['expanded497_accuracy']))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparisons[0]));w.writeheader();w.writerows(comparisons)
    print(json.dumps(dict(selected=best,development_ndcg=best_ndcg,final_baseline=final_stats['baseline']['ndcg'],final_selected=stats['ndcg'],delta=delta,MF_fits=len(fits)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
