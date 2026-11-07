"""Five developer-user folds share MF per fold; up to6fits incl selected all50 model."""
import json,csv,hashlib,os,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .core import ROOT,OUT,CONFIG,Content,MatrixFactorization,Baseline,developer_cohort,folds,validate_train,evaluate_fold,summarize
from perfume.data import fragrantica
from experiments.scent_v2.accuracy_optimization.run import load_model


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/'outputs/validation/train_exclude_3.json',ROOT/'outputs/improvement/candidates.json',ROOT/'Term-project-datasets/fra_cleaned.csv',ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json'}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();m=args[1];flags=args[2]
            writing=(isinstance(m,str) and any(x in m for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V26 new-output writes only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.json','.csv','.npz','.npy')) and p not in allowed and not p.is_relative_to(OUT):raise PermissionError('Old result/final/model data forbidden')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded action denied')
    sys.addaudithook(audit)


def save_model(path,content,mf,pop,candidates,spec):
    """All50 developer fit artifact, no evaluation of this fit on its train users."""
    tokens=sorted(content.idf);ids=sorted(candidates);features=np.asarray([[content.vectors[i].get(t,0) for t in tokens] for i in ids])
    meta=dict(spec=spec,mf_config=CONFIG['mf'],scope='V26 all50 developer-refit after userCV selection; not an independent final model evaluation')
    with path.open('xb') as f:np.savez_compressed(f,Q=mf.Q,MF_items=np.asarray(sorted(mf.items,key=mf.items.get)),feature_items=np.asarray(ids),tokens=np.asarray(tokens),idf=np.asarray([content.idf[t] for t in tokens]),features=features,
        popularity=np.asarray([pop.counts[i] for i in ids]),popularity_maximum=np.asarray(pop.maximum),metadata=np.asarray(json.dumps(meta)))


def main():
    if (OUT/'experiment_config.json').exists():raise FileExistsError('Run already exists; no automatic CV/refit overwrite')
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates)
    previous=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text())
    assert len(cohort)==50 and source['developer_split_sha256']==previous['developer_split_sha256'];parts=folds(cohort)
    assert [len(p['evaluation']) for p in parts]==[10]*5
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');fits=[];original_fit=MatrixFactorization.fit
    def counted(self,rows):
        if len(fits)>=CONFIG['fit_budget']:raise RuntimeError('MF fit budget6 exceeded')
        validate_train(rows,reserved);fits.append(dict(number=len(fits)+1,users=len({u for u,i,y in rows}),ratings=len(rows)))
        return original_fit(self,rows)
    cache=[];stats={};all_records={};table=[];specs={s['name']:s for s in CONFIG['baselines']+CONFIG['improvements']}
    def assess(spec):
        name=spec['name'];stats[name]=[];all_records[name]=[]
        for obj in cache:
            fold,c,m,b,shared=obj;summary,records=evaluate_fold(spec,fold,candidates,c,m,b,shared)
            stats[name].append(summary);all_records[name].extend(records)
            table.append(dict(model=name,fold=fold['fold'],alpha=spec['alpha'],ridge_scale=spec['ridge_scale'],center=spec['center'],users=summary['users'],positive_users=summary['positive_users'],
                ndcg_at5=summary['ndcg'],recall_at5=summary['recall'],hit_rate_at5=summary['hit_rate'],positive_hits=summary['actual_positive_hits'],coverage=summary['coverage_fraction']))
    with patch.object(MatrixFactorization,'fit',counted):
        for fold in parts:
            validate_train(fold['train'],reserved|{r['user'] for r in fold['evaluation']})
            assert len({u for u,i,y in fold['train']})==40
            c=Content().fit(catalog,{i for u,i,y in fold['train']});b=Baseline().fit(fold['train']);m=MatrixFactorization(**CONFIG['mf']).fit(fold['train']);del m.P;m.Q.flags.writeable=False
            shared={}
            for row in fold['evaluation']:
                pool=sorted(set(candidates)-{i for i,y in row['support']});cs=c.score(row['support'],pool);bs=b.score(pool);cs.flags.writeable=False;bs.flags.writeable=False;shared[row['user']]=(cs,bs)
            cache.append((fold,c,m,b,shared));print(f'CV MF fit {len(fits)}/5: train40 eval10 rows={len(fold["train"])}',flush=True)
        for spec in CONFIG['baselines']:assess(spec)
        print('Baseline mean fold NDCG: '+json.dumps({s['name']:float(np.mean([r['ndcg'] for r in stats[s['name']]])) for s in CONFIG['baselines']}),flush=True)
        for spec in CONFIG['improvements']:assess(spec)
        means=lambda name:float(np.mean([r['ndcg'] for r in stats[name]]))
        if means('support_centered')>=means('v25_alpha05'):
            for scale,label in ((.5,'centered_low'),(2.,'centered_high')):
                spec=dict(name=label,alpha=.05,ridge_scale=scale,center=True);specs[label]=spec;assess(spec)
        priority=['v25_alpha05','hybrid25','mf0','ridge_low','ridge_high','support_centered','centered_low','centered_high']
        selected=max(stats,key=lambda name:(round(means(name),12),-priority.index(name)))
        summaries={name:dict(mean_fold_ndcg=means(name),mean_fold_recall=float(np.mean([s['recall'] for s in st])),mean_fold_hit_rate=float(np.mean([s['hit_rate'] for s in st])),
            fold_ndcg=[s['ndcg'] for s in st],fold_std=float(np.std([s['ndcg'] for s in st])),
            wins_over_v25=sum(s['ndcg']>b['ndcg']+1e-12 for s,b in zip(st,stats['v25_alpha05'])),
            losses_to_v25=sum(s['ndcg']<b['ndcg']-1e-12 for s,b in zip(st,stats['v25_alpha05'])),
            pooled_positive_user=summarize(all_records[name],candidates)) for name,st in stats.items()}
        selection=dict(selected=selected,spec=specs[selected],reason=CONFIG['selection'],mean_ndcg=means(selected))
        write('selection.json',selection)
        full=[(r['user'],i,y) for r in cohort for i,y in r['support']+r['answers']];validate_train(full,reserved)
        assert len({u for u,i,y in full})==50
        c=Content().fit(catalog,{i for u,i,y in full});b=Baseline().fit(full);m=MatrixFactorization(**CONFIG['mf']).fit(full);del m.P;m.Q.flags.writeable=False
        save_model(OUT/'best_model.npz',c,m,b,candidates,specs[selected])
        lc,lm,lb,meta=load_model(OUT/'best_model.npz');assert np.array_equal(lm.Q,m.Q)
        # Synthetic support only for serialization, not an accuracy run on final-fit users.
        from .core import user_scores
        synthetic=[(i,.7) for i in sorted(candidates)[:5]]
        assert user_scores(specs[selected],synthetic,candidates,c,m,b)==user_scores(meta['spec'],synthetic,candidates,lc,lm,lb)
    write('evaluation_results.json',dict(status='COMPLETED_DEVELOPER_USER_CV_ONLY',source=source,user_folds=5,per_fold_train_users=40,per_fold_eval_users=10,
        selected=selection,models=summaries,relative_improvement_over_hybrid_percent=(means(selected)/means('hybrid25')-1)*100 if means('hybrid25') else None,
        relative_improvement_over_v25_percent=(means(selected)/means('v25_alpha05')-1)*100 if means('v25_alpha05') else None,
        MF_fit_count=len(fits),fits=fits,Content_fit_count=6,reserved_final_users_used=0,V24_output_reads=0,reserved_rating_tokens_decoded=0,background_user_training_rows=0,
        factor8='NOT_REPEATED_PRIOR_WEAK_RESULT',common_candidate_count=479,
        independent_final='NOT_EVALUATED',source_users_previously_selected=True,
        scope='Same50 developer users repeatedly used, non-nested selection on same5 folds. Mean fold metric, not the old895-row single split. Not independent generalization evidence.',
        saved_model_scope='Refit on all50 developers only after CV selection, no evaluation of that fit on its training users',roundtrip_inference_exact=True,serving_model_modified=False))
    with (OUT/'cv_model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(selected=selected,hybrid_mean=means('hybrid25'),v25_mean=means('v25_alpha05'),best_mean=means(selected),MF_fits=len(fits),all_means={n:means(n) for n in stats})),flush=True)

if __name__=='__main__':main()
