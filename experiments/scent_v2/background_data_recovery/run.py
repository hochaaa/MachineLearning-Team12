"""Background restoration only: two fixed algorithms, five shared real MF fits."""
import json,csv,hashlib,os,sys
from collections import Counter
from pathlib import Path
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline
from perfume.data import fragrantica
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from experiments.scent_v2.final_validation.analysis import stability
from experiments.scent_v2.similarity_reranking.core import CONFIG as V30_CONFIG
from .core import ROOT,OUT,CONFIG,developer_data,digest,validate_data,SimilarityIndex,cache_support,rerank,predict,pack_state,save_bank,load_model


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/p for p in ['outputs/validation/train_exclude_3.json','outputs/improvement/candidates.json','Term-project-datasets/fra_cleaned.csv','outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json','outputs/scent_v2/similarity_reranking/evaluation_results.json','outputs/scent_v2/similarity_reranking/verification.json']}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2];writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V32 outputs only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.csv','.json','.npz','.npy')) and p not in allowed and not p.is_relative_to(OUT) and not p.is_relative_to(ROOT/'experiments'):raise PermissionError('Other old results/final labels/models denied')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded operation denied')
    sys.addaudithook(audit)


def counts_coverage(rows,candidates,positive_items):
    count=Counter(i for u,i,r in rows);values=[count[i] for i in candidates]
    return dict(users=len({u for u,i,r in rows}),ratings=len(rows),items_all=len(count),candidate_items_with_ratings=sum(v>0 for v in values),candidate_zero_rating_fraction=sum(v==0 for v in values)/len(candidates),candidate_rating_quantiles=dict(zip(['min','p25','median','p75','p90','max'],map(float,np.quantile(values,[0,.25,.5,.75,.9,1])))),positive_heldout_occurrences=len(positive_items),positive_heldout_seen_train=sum(i in count for i in positive_items),positive_heldout_seen_train_fraction=sum(i in count for i in positive_items)/len(positive_items) if positive_items else None)


def main():
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    assert CONFIG['mf']==V30_CONFIG['mf'] and CONFIG['model_A']==dict(signal='none',mode='full',**{'lambda':0.}) and CONFIG['model_B']==dict(signal='max',mode='top50',**{'lambda':.2})
    old=json.loads((ROOT/'outputs/scent_v2/similarity_reranking/evaluation_results.json').read_text());proof=json.loads((ROOT/'outputs/scent_v2/similarity_reranking/verification.json').read_text())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in proof['source_sha256'].items())
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    background,cohort,reserved,source=developer_data(ROOT/'outputs/validation/train_exclude_3.json',candidates);expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text())
    assert source==expected and len(cohort)==50 and len(reserved)==25
    assert source['developer_split_sha256']==old['source']['developer_split_sha256']
    parts=validate_data(background,cohort,reserved,candidates);catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
    retained=[(row['user'],i,r) for row in cohort for i,r in row['support']+row['answers']]+background
    assert {i for u,i,r in retained}<=set(catalog) and set(candidates)<=set(catalog)
    integrity=dict(status='PASS',source=source,background_users=len({u for u,i,r in background}),background_ratings=len(background),development_users=len(cohort),development_ratings=sum(len(r['support'])+len(r['answers']) for r in cohort),reserved_users_excluded=len(reserved),reserved_rating_tokens_decoded=0,reserved_rating_rows_skipped=source['reserved_rows_skipped'],background_development_user_overlap=0,background_reserved_user_overlap=0,training_evaluation_user_overlap_all_folds=0,duplicate_train_user_item_pairs=0,original_V25_background_checksum_matches=source['original_train_sha256']==expected['original_train_sha256'],same_developer_split_checksum=True,background_origin='Original outputs/validation/train_exclude_3.json, exactly original V25 training-role rows; no validation/test files merged',normalization='Existing finite normalized [0,1] scent ratings, unchanged; original exclude-zero source; no rescaling',ID_mapping='Original canonical string user/item IDs retained; sorted MF internal row indices rebuilt per Train, never transfer old Q indices',catalog_item_IDs_validated=True,fold_training=[dict(fold=f['fold'],users=len({u for u,i,r in f['train']}),ratings=len(f['train']),developer_train_users=len({u for u,i,r in f['developer_train']}),evaluation_users=len(f['evaluation'])) for f in parts])
    write('data_integrity.json',integrity)
    print(f'PASS original background: {integrity["background_users"]}users/{len(background)}ratings; developer50/{integrity["development_ratings"]}; reserved25 decoded0',flush=True)
    records={'A':[],'B':[]};foldstats={'A':[],'B':[]};pairs=[];table=[];coverage=[];states=[];roundtrip_inputs=[];fits=[]
    for f in parts:
        if len(fits)>=CONFIG['max_actual_MF_fits']:raise RuntimeError('MF budget5 exceeded')
        c=Content().fit(catalog,{i for u,i,r in f['train']});b=Baseline().fit(f['train']);entry=dict(number=len(fits)+1,fold=f['fold'],users=len({u for u,i,r in f['train']}),ratings=len(f['train']));fits.append(entry)
        m=MatrixFactorization(**CONFIG['mf']).fit(f['train']);entry.update(loss_first=m.losses[0],loss_last=m.losses[-1]);m.Q.flags.writeable=False;del m.P;del m.users;index=SimilarityIndex(c,candidates)
        fr={'A':[],'B':[]};recalls={'A':{k:[] for k in CONFIG['recall_k']},'B':{k:[] for k in CONFIG['recall_k']}};positive_items=[]
        for row in f['evaluation']:
            x=cache_support(row['support'],candidates,c,m,b,index)
            predictions={name:rerank(CONFIG['model_'+name],x,k=100)[0] for name in ['A','B']}
            # Only after BOTH rankings are complete do answers enter metrics.
            positives={i for i,r in row['answers'] if r>=.7};positive_items.extend(positives)
            for name,ordered in predictions.items():
                top=ordered[:5];assert len(top)==len(set(top))==5 and not set(top)&{i for i,r in row['support']} and set(top)<=set(candidates)
                if name=='B':assert set(top)<=set(x['baseline_order'][:50])
                fr[name].append(dict(top=top,answers=row['answers'],accuracy=user_metrics(top,row['answers'])))
                if positives:
                    for k in recalls[name]:recalls[name][k].append(len(set(ordered[:k])&positives)/len(positives))
            a,z=fr['A'][-1]['accuracy'],fr['B'][-1]['accuracy'];pairs.append(dict(fold=f['fold'],baseline_ndcg=a['ndcg'] if a else None,selected_ndcg=z['ndcg'] if z else None,delta=z['ndcg']-a['ndcg'] if a else None,baseline_hit=a['hit_rate'] if a else None,selected_hit=z['hit_rate'] if z else None))
        for name in ['A','B']:
            stats=summarize(fr[name],candidates);stats['recall_at_k']={str(k):float(np.mean(values)) for k,values in recalls[name].items()};foldstats[name].append(stats);records[name].extend(fr[name])
            table.append(dict(model=name,fold=f['fold'],train_users=entry['users'],train_ratings=entry['ratings'],positive_users=stats['positive_users'],ndcg_at5=stats['ndcg'],recall_at5=stats['recall'],hit_rate_at5=stats['hit_rate'],recall_at20=stats['recall_at_k']['20'],recall_at50=stats['recall_at_k']['50'],recall_at100=stats['recall_at_k']['100'],hit_users=sum(bool(r['accuracy'] and r['accuracy']['hit_rate']) for r in fr[name])))
        coverage.append(dict(fold=f['fold'],without_background=counts_coverage(f['developer_train'],candidates,positive_items),with_background=counts_coverage(f['train'],candidates,positive_items),valid_support_features=sum(bool(c.vectors.get(i)) for r in f['evaluation'] for i,y in r['support']),Support_items=50))
        states.append(pack_state(c,m,b,candidates));synthetic=list(zip(sorted(candidates)[:5],[.9,.1,.7,.3,.5]));roundtrip_inputs.append({name:predict(CONFIG['model_'+name],synthetic,candidates,c,m,b,index) for name in ['A','B']})
        print(f'Fold{f["fold"]}: {entry["users"]}users/{entry["ratings"]}ratings, A={foldstats["A"][-1]["ndcg"]:.12f}, B={foldstats["B"][-1]["ndcg"]:.12f}',flush=True)
    summary={name:dict(mean_ndcg=float(np.mean([s['ndcg'] for s in fs])),mean_recall=float(np.mean([s['recall'] for s in fs])),mean_hit_rate=float(np.mean([s['hit_rate'] for s in fs])),fold_ndcg=[s['ndcg'] for s in fs],folds=fs,recall_at_k={str(k):float(np.mean([s['recall_at_k'][str(k)] for s in fs])) for k in CONFIG['recall_k']},hit_users=sum(bool(r['accuracy'] and r['accuracy']['hit_rate']) for r in records[name]),pooled_oof=summarize(records[name],candidates)) for name,fs in foldstats.items()}
    delta=summary['B']['mean_ndcg']-summary['A']['mean_ndcg'];selected='B' if delta>1e-12 else 'A';selected_policy=CONFIG['model_'+selected];relative=100*delta/summary['A']['mean_ndcg'] if summary['A']['mean_ndcg'] else None
    analysis=stability(pairs,CONFIG['bootstrap_seed'],CONFIG['bootstrap_draws']);analysis['delta_definition']='B minus A (not historical40-user baseline)';analysis['improved_folds']=sum(z>a+1e-12 for a,z in zip(summary['A']['fold_ndcg'],summary['B']['fold_ndcg']));analysis['worsened_folds']=sum(z<a-1e-12 for a,z in zip(summary['A']['fold_ndcg'],summary['B']['fold_ndcg']))
    save_bank(OUT/'best_model.npz',states,selected_policy)
    for n in range(1,6):
        lc,lm,lb,meta=load_model(OUT/'best_model.npz',fold=n);idx=SimilarityIndex(lc,candidates)
        for name in ['A','B']:assert predict(CONFIG['model_'+name],synthetic,candidates,lc,lm,lb,idx)==roundtrip_inputs[n-1][name]
    reference=old['models']['hybrid_baseline'];oldselected=old['models'][old['selected']]
    write('coverage_diagnostics.json',dict(folds=coverage,positive_heldout_occurrences=sum(d['with_background']['positive_heldout_occurrences'] for d in coverage),before_positive_seen=sum(d['without_background']['positive_heldout_seen_train'] for d in coverage),after_positive_seen=sum(d['with_background']['positive_heldout_seen_train'] for d in coverage),before_candidate_zero_fraction_mean=float(np.mean([d['without_background']['candidate_zero_rating_fraction'] for d in coverage])),after_candidate_zero_fraction_mean=float(np.mean([d['with_background']['candidate_zero_rating_fraction'] for d in coverage])),scope='Occurrence-weighted positive seen ratios, candidate479 includes zero counts; labels diagnostic only'))
    write('evaluation_results.json',dict(status='COMPLETED_REUSED_DEVELOPMENT_CV',models=summary,selected=selected,selected_policy=selected_policy,B_minus_A_ndcg=delta,B_vs_A_relative_percent=relative,selected_improves_A=selected=='B',stability=analysis,reference_without_background=dict(scope='Historical40-user Train, not same-training model comparison',hybrid_mean_ndcg=reference['mean_ndcg'],hybrid_mean_recall=reference['mean_recall'],hybrid_mean_hit_rate=reference['mean_hit_rate'],V30_mean_ndcg=oldselected['mean_ndcg']),background_observed_A_ndcg_change=summary['A']['mean_ndcg']-reference['mean_ndcg'],background_observed_A_relative_percent=100*(summary['A']['mean_ndcg']/reference['mean_ndcg']-1),actual_MF_fit_count=len(fits),fits=fits,Content_fit_count=5,cosine_matrix_count=5,Support_cache_count=50,MF_shared_between_A_B=True,roundtrip_all5folds_ids_order_scores_exact=True,model_artifact='Five individual fold states + globally selected policy; default_fold1 predeclared, not best fold, not ensemble, not all305-user refit',source=source,reserved_rating_tokens_decoded=0,final25_evaluations=0,V24_V31_final_results_read=False,independent_generalization_claim=False,service_changed=False,parameter_search=False))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(selected=selected,A=summary['A']['mean_ndcg'],B=summary['B']['mean_ndcg'],relative_percent=relative,MF_fits=len(fits),original_background_restored=True)),flush=True)

if __name__=='__main__':main()
