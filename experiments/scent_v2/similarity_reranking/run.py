"""V30 single-fit-per-fold, cached Support signals; no historical final data."""
import json,csv,os,sys,hashlib
from pathlib import Path
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline
from perfume.data import fragrantica
from experiments.scent_v2.mf_cv_optimization.core import developer_cohort,folds,validate_train
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from .core import ROOT,OUT,CONFIG,SimilarityIndex,cache_support,rerank,predict,save_model,load_model,specs


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/p for p in ['outputs/validation/train_exclude_3.json','outputs/improvement/candidates.json','Term-project-datasets/fra_cleaned.csv','outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json','outputs/scent_v2/content_accuracy/best_model.npz','outputs/scent_v2/content_accuracy/verification.json','outputs/scent_v2/content_accuracy/evaluation_results.json']}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2]
            writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V30 outputs only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.csv','.json','.npz','.npy')) and p not in allowed and not p.is_relative_to(OUT):raise PermissionError('Old final/result/model access denied')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded operation denied')
    sys.addaudithook(audit)


def paired_summary(recs,base):
    positive=[(a['accuracy'],b['accuracy']) for a,b in zip(recs,base) if b['accuracy'] is not None]
    return dict(users=len(positive),ndcg_better=sum(a['ndcg']>b['ndcg']+1e-12 for a,b in positive),ndcg_worse=sum(a['ndcg']<b['ndcg']-1e-12 for a,b in positive),ndcg_same=sum(abs(a['ndcg']-b['ndcg'])<=1e-12 for a,b in positive),hit_gained=sum(a['hit_rate']>b['hit_rate'] for a,b in positive),hit_lost=sum(a['hit_rate']<b['hit_rate'] for a,b in positive))


def main():
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates)
    expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text());assert len(cohort)==50 and source['developer_split_sha256']==expected['developer_split_sha256']
    parts=folds(cohort);catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');fits=[];contexts=[]
    for f in parts:
        excluded=reserved|{r['user'] for r in f['evaluation']};validate_train(f['train'],excluded)
        assert len({u for u,i,r in f['train']})==40 and len(f['evaluation'])==10 and len(fits)<CONFIG['max_actual_data_MF_fits']
        entry=dict(number=len(fits)+1,fold=f['fold'],train_users=40,train_ratings=len(f['train']));fits.append(entry)
        c=Content().fit(catalog,{i for u,i,r in f['train']});b=Baseline().fit(f['train']);m=MatrixFactorization(**CONFIG['mf']).fit(f['train']);entry.update(loss_first=m.losses[0],loss_last=m.losses[-1]);m.Q.flags.writeable=False;del m.P;del m.users
        index=SimilarityIndex(c,candidates);cached=[cache_support(row['support'],candidates,c,m,b,index) for row in f['evaluation']];contexts.append((f,cached))
        print(f'Fold{f["fold"]}: MF/TFIDF each fitted once, cosine479x479 and10 Support caches ready',flush=True)
    policies=specs();records={};summaries={};table=[]
    for name,spec in policies.items():
        recs=[];foldstats=[]
        for f,cache in contexts:
            fr=[]
            for row,x in zip(f['evaluation'],cache):
                top,sc=rerank(spec,x);assert len(top)==len(set(top))==5 and not set(top)&{i for i,r in row['support']} and set(top)<=set(candidates)
                if spec['mode']=='top50':assert set(top)<=set(x['baseline_order'][:50])
                # Held-out first enters here, after Support-only recommendation.
                fr.append(dict(top=top,answers=row['answers'],accuracy=user_metrics(top,row['answers'])))
            summary=summarize(fr,candidates);foldstats.append(summary);recs.extend(fr)
            table.append(dict(model=name,signal=spec['signal'],mode=spec['mode'],similarity_weight=spec['lambda'],fold=f['fold'],positive_users=summary['positive_users'],ndcg_at5=summary['ndcg'],recall_at5=summary['recall'],hit_rate_at5=summary['hit_rate']))
        records[name]=recs;summaries[name]=dict(mean_ndcg=float(np.mean([s['ndcg'] for s in foldstats])),mean_recall=float(np.mean([s['recall'] for s in foldstats])),mean_hit_rate=float(np.mean([s['hit_rate'] for s in foldstats])),fold_ndcg=[s['ndcg'] for s in foldstats],folds=foldstats,pooled_oof=summarize(recs,candidates))
        print(f'{name}: NDCG={summaries[name]["mean_ndcg"]:.12f}',flush=True)
    baseline=summaries['hybrid_baseline']['mean_ndcg'];assert abs(baseline-CONFIG['baseline_expected_ndcg'])<1e-12
    key=lambda n:(round(summaries[n]['mean_ndcg'],12),round(summaries[n]['mean_recall'],12),round(summaries[n]['mean_hit_rate'],12),-policies[n]['lambda'],int(policies[n]['mode']=='top50'),int(policies[n]['signal']=='max'))
    eligible=[n for n in policies if summaries[n]['mean_ndcg']>baseline+1e-12];selected=max(eligible,key=key) if eligible else 'hybrid_baseline'
    # Subgroups derived from baseline outputs/answers for diagnosis ONLY, never input.
    subgroup=[];only50=[]
    for f,cache in contexts:
        for row,x in zip(f['evaluation'],cache):
            pos={i for i,r in row['answers'] if r>=.7};subgroup.append(bool(pos&set(x['baseline_order'][:50])));only50.append(bool(pos&set(x['baseline_order'][:50])) and not bool(pos&set(x['baseline_order'][:5])))
    base_records=records['hybrid_baseline']
    for n,s in summaries.items():
        s['paired_users']=paired_summary(records[n],base_records);s['baseline_top50_positive_users']=paired_summary([r for r,yes in zip(records[n],subgroup) if yes],[r for r,yes in zip(base_records,subgroup) if yes]);s['baseline_top50_only_positive_users']=paired_summary([r for r,yes in zip(records[n],only50) if yes],[r for r,yes in zip(base_records,only50) if yes])
        s['fold_ndcg_delta']=[a-b for a,b in zip(s['fold_ndcg'],summaries['hybrid_baseline']['fold_ndcg'])];s['folds_improved']=sum(x>1e-12 for x in s['fold_ndcg_delta']);s['folds_worse']=sum(x< -1e-12 for x in s['fold_ndcg_delta'])
    best_by={}
    for field,values in [('signal',CONFIG['signals']),('mode',CONFIG['modes'])]:
        for value in values:best_by[value]=max((n for n in policies if policies[n][field]==value and n!='hybrid_baseline'),key=key)
    write('selection.json',dict(selected=selected,policy=policies[selected],best_by=best_by,strict_improvement_required=True))
    # Reuse pre-existing all50 developer model only AFTER selection. It is never
    # used for any fold inference/evaluation (would leak the evaluated users).
    previous=ROOT/'outputs/scent_v2/content_accuracy';proof=json.loads((previous/'verification.json').read_text());provenance=json.loads((previous/'evaluation_results.json').read_text())
    artifact_sha=hashlib.sha256((previous/'best_model.npz').read_bytes()).hexdigest()
    assert artifact_sha==proof['model_sha256'] and proof['status']=='PASS' and provenance['source']['developer_split_sha256']==source['developer_split_sha256'] and provenance['reserved_rating_tokens_decoded']==0 and provenance['fits'][-1]['train_users']==50
    c,m,b,meta=load_model(previous/'best_model.npz');assert meta['mf_config']==CONFIG['mf'] and set(c.vectors)==set(candidates)
    save_model(OUT/'best_model.npz',c,m,b,candidates,policies[selected]);lc,lm,lb,newmeta=load_model(OUT/'best_model.npz')
    support=list(zip(sorted(candidates)[:5],[.9,.1,.7,.3,.5]));index=SimilarityIndex(c,candidates);loaded_index=SimilarityIndex(lc,candidates)
    for spec in policies.values():
        assert predict(spec,support,candidates,c,m,b,index)==predict(spec,support,candidates,lc,lm,lb,loaded_index)
    write('evaluation_results.json',dict(status='COMPLETED_DEVELOPER_CV_ONLY',source=source,models=summaries,policies=policies,selected=selected,selected_policy=policies[selected],best_by=best_by,relative_improvement_percent=(summaries[selected]['mean_ndcg']/baseline-1)*100,actual_data_MF_fit_count=len(fits),fits=fits,Content_fit_count=5,similarity_matrices_CV=5,Support_cache_users=50,original_H_score_computations=50,each_similarity_signal_computations=50,all_policy_roundtrip_scores_and_ids_exact=True,reused_final_artifact=dict(path='outputs/scent_v2/content_accuracy/best_model.npz',sha256=artifact_sha,loaded_after_selection=True,used_for_CV=False,training_users=50),no_valid_positive_support_users=sum(x['diagnostic']['status']!='ok' for f,cache in contexts for x in cache),weak_signal_candidate_counts={kind:sum(int(np.sum(~np.isfinite(x['signals'][kind])|(x['signals'][kind]<CONFIG['signal_floor']))) for f,cache in contexts for x in cache) for kind in CONFIG['signals']},baseline_top50_positive_users=sum(subgroup),baseline_top50_only_positive_users=sum(only50),reserved_rating_tokens_decoded=0,V24_output_reads=0,independent_final='NOT_EVALUATED',generalization_claim=False,service_changed=False,PN='SKIPPED a priori: scarce negative Support, prioritize requested Max/Top2',no_answer_dependent_user_policy=True))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(selected=selected,baseline=baseline,selected_ndcg=summaries[selected]['mean_ndcg'],relative_percent=(summaries[selected]['mean_ndcg']/baseline-1)*100,best_by=best_by,actual_MF_fits=len(fits))),flush=True)

if __name__=='__main__':main()
