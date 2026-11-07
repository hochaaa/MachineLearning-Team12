"""V29 same developer CV: diagnostics and cached Content experiments only."""
import os,sys,json,csv
from pathlib import Path
from collections import Counter
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline
from perfume.data import fragrantica
from experiments.scent_v2.mf_cv_optimization.core import developer_cohort,folds,validate_train
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from experiments.scent_v2.recommend import rank
from .core import ROOT,OUT,CONFIG,cache_support,score_cached,predict,save_model,load_model


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/'outputs/validation/train_exclude_3.json',ROOT/'outputs/improvement/candidates.json',ROOT/'Term-project-datasets/fra_cleaned.csv',ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json'}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2]
            writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V29 outputs only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.csv','.json','.npz','.npy')) and p not in allowed and not p.is_relative_to(OUT):raise PermissionError('Old results/models/final labels forbidden')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded action denied')
    sys.addaudithook(audit)


def experiment_specs():
    specs=dict(hybrid_baseline=dict(profile='original',alpha=.25),pure_mf_baseline=dict(profile='original',alpha=0.),pure_content=dict(profile='original',alpha=1.,pure='content'))
    for kind in CONFIG['profiles']:
        for a in CONFIG['alphas']:
            spec=dict(profile=kind,alpha=a)
            if a==1:spec['pure']='content'
            specs[f'{kind}_a{a:g}']=spec
    return specs


def main():
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates)
    expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text());assert len(cohort)==50 and source['developer_split_sha256']==expected['developer_split_sha256']
    parts=folds(cohort);catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');contexts=[];fits=[];diagnostics=[]
    def train(rows,excluded):
        validate_train(rows,excluded)
        if len(fits)>=CONFIG['max_actual_data_MF_fits']:raise RuntimeError('MF budget exceeded')
        entry=dict(number=len(fits)+1,train_users=len({u for u,i,y in rows}),ratings=len(rows));fits.append(entry)
        m=MatrixFactorization(**CONFIG['mf']).fit(rows);entry.update(loss_first=m.losses[0],loss_last=m.losses[-1]);m.Q.flags.writeable=False
        del m.P;del m.users
        return m
    for fold in parts:
        rows=fold['train'];excluded=reserved|{r['user'] for r in fold['evaluation']};assert len({u for u,i,y in rows})==40 and len(fold['evaluation'])==10
        c=Content().fit(catalog,{i for u,i,y in rows});b=Baseline().fit(rows);m=train(rows,excluded)
        # Scorers receive Support only. Cache every score before answer diagnostics.
        cached=[cache_support(row['support'],candidates,c,m,b) for row in fold['evaluation']]
        contexts.append((fold,c,m,b,cached))
        counts=Counter(i for u,i,y in rows);distribution=[counts[i] for i in sorted(candidates)];positive_sets=[{i for i,r in row['answers'] if r>=.7} for row in fold['evaluation']]
        allpos=[i for pos in positive_sets for i in pos];rankings=[rank(x['pool'],score_cached(dict(profile='original',alpha=.25),x)) for x in cached]
        rec={str(k):float(np.mean([len(set(top[:k])&pos)/len(pos) for top,pos in zip(rankings,positive_sets) if pos])) for k in CONFIG['recall_k']}
        categories=Counter();item_categories=Counter()
        for top,pos in zip(rankings,positive_sets):
            if not pos:continue
            categories['has_top5' if set(top[:5])&pos else 'has_top50_but_not_top5' if set(top[:50])&pos else 'none_in_top50']+=1
            for i in pos:item_categories['in_top5' if i in top[:5] else 'rank6_to50' if i in top[:50] else 'outside_top50']+=1
        supp=[i for row in fold['evaluation'] for i,r in row['support']];diag=dict(fold=fold['fold'],train_users=40,train_ratings=len(rows),training_items_all=len(counts),training_candidates=sum(counts[i]>0 for i in candidates),candidate_ratings=sum(distribution),ratings_per_candidate_quantiles=dict(zip(['min','p25','median','p75','p90','max'],map(float,np.quantile(distribution,[0,.25,.5,.75,.9,1])))),zero_rating_candidate_fraction=sum(n==0 for n in distribution)/479,positive_heldout_occurrences=len(allpos),positive_heldout_seen_train=sum(i in counts for i in allpos),positive_heldout_seen_train_fraction=sum(i in counts for i in allpos)/len(allpos),positive_heldout_in_candidates=sum(i in set(candidates) for i in allpos),positive_heldout_unique=len(set(allpos)),positive_heldout_unique_seen_train=sum(i in counts for i in set(allpos)),valid_support_vectors=sum(bool(c.vectors.get(i)) for i in supp),support_count=len(supp),support_content_valid_fraction=sum(bool(c.vectors.get(i)) for i in supp)/len(supp),baseline_recall=rec,positive_user_categories=dict(categories),positive_item_rank_categories=dict(item_categories),positive_users=sum(bool(p) for p in positive_sets))
        diagnostics.append(diag)
        print(f'Fold{fold["fold"]}: train40/{len(rows)}ratings, candidate coverage {diag["training_candidates"]}/479, Recall@5/50={rec["5"]:.6f}/{rec["50"]:.6f}',flush=True)
    specs=experiment_specs();records={};summaries={};table=[]
    for name,spec in specs.items():
        recs=[];fold_stats=[]
        for fold,c,m,b,cached in contexts:
            fr=[]
            for row,x in zip(fold['evaluation'],cached):
                top=rank(x['pool'],score_cached(spec,x))[:5]
                assert len(top)==len(set(top))==5 and not set(top)&{i for i,r in row['support']} and set(top)<=set(candidates)
                fr.append(dict(top=top,answers=row['answers'],accuracy=user_metrics(top,row['answers'])))
            summary=summarize(fr,candidates);fold_stats.append(summary);recs.extend(fr)
            table.append(dict(model=name,fold=fold['fold'],profile=spec['profile'],alpha=spec['alpha'],ndcg_at5=summary['ndcg'],recall_at5=summary['recall'],hit_rate_at5=summary['hit_rate'],positive_users=summary['positive_users']))
        records[name]=recs;summaries[name]=dict(mean_ndcg=float(np.mean([s['ndcg'] for s in fold_stats])),mean_recall=float(np.mean([s['recall'] for s in fold_stats])),mean_hit_rate=float(np.mean([s['hit_rate'] for s in fold_stats])),fold_ndcg=[s['ndcg'] for s in fold_stats],folds=fold_stats,pooled_oof=summarize(recs,candidates))
        print(f'{name}: NDCG={summaries[name]["mean_ndcg"]:.12f}',flush=True)
    baseline=summaries['hybrid_baseline']['mean_ndcg'];assert abs(baseline-CONFIG['baseline_expected_ndcg'])<1e-12
    key=lambda n:(round(summaries[n]['mean_ndcg'],12),round(summaries[n]['mean_recall'],12),round(summaries[n]['mean_hit_rate'],12),int(specs[n]['profile']=='original'),int(specs[n]['profile']=='rating_weighted'),-abs(specs[n]['alpha']-.25))
    eligible=[n for n in specs if n not in ('hybrid_baseline','pure_mf_baseline') and summaries[n]['mean_ndcg']>baseline+1e-12]
    selected=max(eligible,key=key) if eligible else 'hybrid_baseline';best_new=max((n for n in specs if specs[n]['profile']!='original'),key=key)
    for name,s in summaries.items():
        base=summaries['hybrid_baseline'];s['folds_better_than_baseline']=sum(a>b+1e-12 for a,b in zip(s['fold_ndcg'],base['fold_ndcg']));s['folds_worse_than_baseline']=sum(a<b-1e-12 for a,b in zip(s['fold_ndcg'],base['fold_ndcg']))
        paired=[(r['accuracy'],old['accuracy']) for r,old in zip(records[name],records['hybrid_baseline']) if old['accuracy'] is not None]
        s['paired_positive_users']=dict(count=len(paired),ndcg_better=sum(a['ndcg']>b['ndcg']+1e-12 for a,b in paired),ndcg_worse=sum(a['ndcg']<b['ndcg']-1e-12 for a,b in paired),ndcg_same=sum(abs(a['ndcg']-b['ndcg'])<=1e-12 for a,b in paired),hit_gained=sum(a['hit_rate']>b['hit_rate'] for a,b in paired),hit_lost=sum(a['hit_rate']<b['hit_rate'] for a,b in paired))
    write('selection.json',dict(selected=selected,spec=specs[selected],comparison_scope='Reused developer CV, not independent final',strict_improvement_required=True))
    full=[(r['user'],i,y) for r in cohort for i,y in r['support']+r['answers']];m=train(full,reserved);c=Content().fit(catalog,{i for u,i,y in full});b=Baseline().fit(full)
    save_model(OUT/'best_model.npz',c,m,b,candidates,specs[selected]);lc,lm,lb,meta=load_model(OUT/'best_model.npz')
    # Synthetic inference only, never an accuracy evaluation on refit users.
    support=[(i,r) for i,r in zip(sorted(candidates)[:5],[.9,.1,.7,.3,.5])]
    x=cache_support(support,candidates,c,m,b);y=cache_support(support,candidates,lc,lm,lb)
    assert np.array_equal(score_cached(specs[selected],x),score_cached(meta['spec'],y),equal_nan=True)
    assert predict(specs[selected],support,candidates,c,m,b)==predict(meta['spec'],support,candidates,lc,lm,lb)
    diag=dict(folds=diagnostics,baseline_recall_mean_fold={str(k):float(np.mean([d['baseline_recall'][str(k)] for d in diagnostics])) for k in CONFIG['recall_k']},positive_user_categories={cat:sum(d['positive_user_categories'].get(cat,0) for d in diagnostics) for cat in ['has_top5','has_top50_but_not_top5','none_in_top50']},positive_item_rank_categories={cat:sum(d['positive_item_rank_categories'].get(cat,0) for d in diagnostics) for cat in ['in_top5','rank6_to50','outside_top50']},positive_heldout_occurrences=sum(d['positive_heldout_occurrences'] for d in diagnostics),positive_heldout_seen_train=sum(d['positive_heldout_seen_train'] for d in diagnostics),positive_heldout_in_candidates=sum(d['positive_heldout_in_candidates'] for d in diagnostics),profile_diagnostics={kind:dict(fallback_users=sum(x['profile_diagnostics'][kind]['fallback'] is not None for fold,c,m,b,cache in contexts for x in cache),fallback_reasons=dict(Counter(x['profile_diagnostics'][kind]['fallback'] for fold,c,m,b,cache in contexts for x in cache if x['profile_diagnostics'][kind]['fallback'] is not None))) for kind in CONFIG['profiles']},candidate_ratings_distribution_scope='Fixed479 including zero counts; all other observed training items retained by original models',answer_access='Diagnosis/evaluation only, never scoring/calibration or per-user policy choice')
    support_values=[r for row in cohort for i,r in row['support']]
    negative_counts=[sum(r<=.3 for i,r in row['support']) for row in cohort]
    diag['support_rating_summary']=dict(users=50,ratings=len(support_values),negative_threshold=.3,positive_threshold=.7,negative_ratings=sum(r<=.3 for r in support_values),positive_ratings=sum(r>=.7 for r in support_values),users_with_negative=sum(n>0 for n in negative_counts),users_without_negative=sum(n==0 for n in negative_counts),reserved_rating_tokens_decoded=0)
    write('diagnostics.json',diag)
    write('evaluation_results.json',dict(status='COMPLETED_DEVELOPER_CV_ONLY',source=source,models=summaries,selected=selected,selected_spec=specs[selected],best_new=best_new,relative_improvement_percent=(summaries[selected]['mean_ndcg']/baseline-1)*100,actual_data_MF_fit_count=len(fits),fits=fits,Content_fit_count=6,score_cache_users=50,original_content_computations_CV=50,MF_score_computations_CV=50,profile_score_computations_CV=150,reserved_rating_tokens_decoded=0,background_rating_tokens_decoded=0,V24_output_reads=0,roundtrip_exact_scores_and_top5=True,independent_final='NOT_EVALUATED',generalization_claim=False,serving_model_changed=False,selection='Mean fold NDCG then Recall then HitRate; same reused developer set; all configs fixed before diagnostics'))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(selected=selected,baseline=baseline,best_new=best_new,selected_ndcg=summaries[selected]['mean_ndcg'],relative_percent=(summaries[selected]['mean_ndcg']/baseline-1)*100,actual_MF_fits=len(fits))),flush=True)

if __name__=='__main__':main()
