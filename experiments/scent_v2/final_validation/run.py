"""Validate exactly two frozen algorithms, then one historical25-user assessment."""
import json,hashlib,os,sys,csv
from pathlib import Path
from collections import defaultdict
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline
from perfume.data import fragrantica
from experiments.scent_v2.mf_cv_optimization.core import developer_cohort,folds,validate_train
from experiments.scent_v2.mf_accuracy_optimization.core import read_identities,digest
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from experiments.scent_v2.similarity_reranking.core import ROOT,SimilarityIndex,cache_support,rerank,load_model,CONFIG as V30_CONFIG
from .analysis import stability,paired_counts,final_uncertainty
OUT=ROOT/'outputs/scent_v2/final_validation';V30=ROOT/'outputs/scent_v2/similarity_reranking'
BASE=dict(signal='none',mode='full',**{'lambda':0.});SELECTED=dict(signal='max',mode='top50',**{'lambda':.2})
POLICY=dict(baseline=BASE,selected=SELECTED,support=5,candidates=479,relevance=.7,k=5,seed=12,bootstrap=20000,final_training_scope='Reuse frozen V30 artifact:50 developers/659 ratings only; exclude25 reserved and255 background, zero final fits',independence='Reused historical user-disjoint holdout, NOT pristine independent; V24 already opened; indirect historical influence unverifiable',final_runs=1,max_CV_reconstruction_MF_fits=5,no_retuning=True)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/p for p in ['outputs/validation/train_exclude_3.json','outputs/improvement/candidates.json','Term-project-datasets/fra_cleaned.csv','outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json','outputs/scent_v2/content_accuracy/evaluation_results.json','outputs/scent_v2/content_accuracy/best_model.npz','outputs/scent_v2/content_accuracy/verification.json','outputs/scent_v2/accuracy_optimization/final_opened_once.json','outputs/scent_v2/accuracy_optimization/split_summary.json','outputs/scent_v2/accuracy_optimization/final_fit_complete.json']}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2];writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V31 outputs only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.csv','.json','.npz','.npy')) and p not in allowed and not p.is_relative_to(V30) and not p.is_relative_to(OUT) and not p.is_relative_to(ROOT/'experiments'):raise PermissionError('Other result/private final/model reads forbidden')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded operation denied')
    sys.addaudithook(audit)


def check_lock(lock):
    assert sha(V30/'best_model.npz')==lock['model_sha256']
    for p,h in lock['source_sha256'].items():assert sha(ROOT/p)==h
    assert V30_CONFIG==lock['config'] and lock['selected']==SELECTED


def metric_record(top,answers):return dict(top=top,answers=answers,accuracy=user_metrics(top,answers))


def pair_metrics(a,b,fold):
    ma,mb=a['accuracy'],b['accuracy'];assert (ma is None)==(mb is None)
    return dict(fold=fold,baseline_ndcg=ma['ndcg'] if ma else None,selected_ndcg=mb['ndcg'] if mb else None,delta=mb['ndcg']-ma['ndcg'] if ma else None,baseline_hit=ma['hit_rate'] if ma else None,selected_hit=mb['hit_rate'] if mb else None)


def reserved_tokens(path,candidates,reserved):
    """ID-only reconstruction: no numeric labels decoded until final open gate."""
    raw=read_identities(path);counts=defaultdict(list)
    for u,i,t in raw:
        if u in reserved:counts[u].append((i,t))
    result=[]
    for u in sorted(reserved,key=lambda u:digest('12:v224:role:'+u)):
        history=counts[u];ids=sorted((i for i,t in history if i in set(candidates)),key=lambda i:digest('12:v224:support:'+u+':'+i));seen=set(ids[:5]);support=sorted((i,t) for i,t in history if i in seen);answers=sorted((i,t) for i,t in history if i not in seen)
        if len(support)!=5 or not answers or seen&{i for i,t in answers}:raise ValueError('Invalid reserved split')
        result.append(dict(user=u,support_tokens=support,answer_tokens=answers))
    return result


def decode(tokens):
    result=[]
    for i,t in tokens:
        r=json.loads(t)
        if isinstance(r,bool) or not isinstance(r,(int,float)) or not np.isfinite(r) or not 0<=r<=1:raise ValueError('Invalid normalized rating')
        result.append((i,float(r)))
    return result


def open_gate(lock):
    """Fail closed, one exclusive marker BEFORE any reserved Support/answer decoding."""
    check_lock(lock)
    if not (OUT/'development_stability.json').exists() or not (OUT/'independence_audit.json').exists():raise RuntimeError('Preflight incomplete')
    write('final_opened_once.json',dict(final_open_count_V31=1,historical_V24_open_count=1,policy_locked=True,no_retuning=True))


def main():
    OUT.chmod(0o700);guard()
    old=json.loads((V30/'evaluation_results.json').read_text());proof=json.loads((V30/'verification.json').read_text());config=json.loads((ROOT/'experiments/scent_v2/similarity_reranking/config.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in proof['source_sha256'].items())
    assert old['selected_policy']==SELECTED and proof['status']=='PASS' and sha(V30/'best_model.npz')==proof['model_sha256'] and config==V30_CONFIG
    source_paths=['experiments/scent_v2/similarity_reranking/core.py','experiments/scent_v2/similarity_reranking/config.json','experiments/scent_v2/content_accuracy/core.py','experiments/scent_v2/mf_cv_optimization/core.py','src/perfume/models.py','experiments/scent_v2/recommend.py']
    lock=dict(policy=POLICY,selected=SELECTED,config=config,model_sha256=proof['model_sha256'],source_sha256={p:sha(ROOT/p) for p in source_paths});write('locked_protocol.json',lock)
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates)
    assert len(candidates)==len(set(candidates))==479 and len(cohort)==50 and len(reserved)==25 and source==old['source']
    full=[(r['user'],i,y) for r in cohort for i,y in r['support']+r['answers']];validate_train(full,reserved);assert len({u for u,i,r in full})==50 and len(full)==659
    v24=json.loads((ROOT/'outputs/scent_v2/accuracy_optimization/final_opened_once.json').read_text());v24split=json.loads((ROOT/'outputs/scent_v2/accuracy_optimization/split_summary.json').read_text());assert v24['final_open_count']==1 and v24split['final_users']==25 and v24split['development_users']==50
    write('independence_audit.json',dict(classification=POLICY['independence'],pristine_independent=False,technical_user_disjoint=True,V30_reserved_labels_decoded=old['reserved_rating_tokens_decoded'],V30_V24_result_reads=old['V24_output_reads'],V24_already_evaluated=True,V24_outcome_values_read_in_V31=False,V24_raw_private_manifest_read=False,indirect_human_or_historical_influence='UNVERIFIABLE, cannot assert absent',background_users=v24split['train_users'],background_used_in_V31=False,final_training_users=50,final_training_ratings=659,training_reserved_overlap=0,final_support=5,heldout_access='Only after all fixed-model predictions',candidate_policy='Existing479, historically studied catalog; no claim of pristine candidate selection',evidence=['experiments/scent_v2/accuracy_optimization/run.py:open_final/main','outputs/scent_v2/accuracy_optimization/final_opened_once.json','outputs/scent_v2/accuracy_optimization/split_summary.json','experiments/scent_v2/similarity_reranking/run.py:guard/main']))
    # Saved V30 synthetic inference replay uses its exact original item-only state.
    c,m,b,meta=load_model(V30/'best_model.npz');assert meta['spec']==SELECTED and meta['mf_config']==config['mf'] and set(c.vectors)==set(candidates)
    recorded=json.loads((V30/'inference_check.json').read_text());support=list(zip(sorted(candidates)[:5],[.9,.1,.7,.3,.5]));index=SimilarityIndex(c,candidates);x=cache_support(support,candidates,c,m,b,index);top,sc=rerank(SELECTED,x)
    assert top==recorded['Top5'] and sc==recorded['scores']
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');records={'baseline':[],'selected':[]};foldstats=[];pairs=[];fits=[]
    # V30 stores aggregates but no per-user outputs/fold artifacts. Reconstruct
    # exactly5 old folds to recover paired concentration, no alternative policy.
    for f in folds(cohort):
        validate_train(f['train'],reserved|{r['user'] for r in f['evaluation']});assert len(fits)<5
        fc=Content().fit(catalog,{i for u,i,r in f['train']});fm=MatrixFactorization(**config['mf']).fit(f['train']);fb=Baseline().fit(f['train']);fm.Q.flags.writeable=False;del fm.P;del fm.users;idx=SimilarityIndex(fc,candidates)
        fits.append(dict(fold=f['fold'],users=len({u for u,i,r in f['train']}),ratings=len(f['train'])));fr={'baseline':[],'selected':[]}
        for row in f['evaluation']:
            cached=cache_support(row['support'],candidates,fc,fm,fb,idx)
            for name,spec in [('baseline',BASE),('selected',SELECTED)]:
                top,s=rerank(spec,cached);assert len(top)==len(set(top))==5 and not set(top)&{i for i,r in row['support']}
                if name=='selected':assert set(top)<=set(cached['baseline_order'][:50])
                fr[name].append(metric_record(top,row['answers']))
            pairs.append(pair_metrics(fr['baseline'][-1],fr['selected'][-1],f['fold']))
        summaries={name:summarize(r,candidates) for name,r in fr.items()}
        for name,oldname in [('baseline','hybrid_baseline'),('selected',old['selected'])]:
            saved=old['models'][oldname]['folds'][f['fold']-1]
            for key in ['ndcg','recall','hit_rate']:assert abs(summaries[name][key]-saved[key])<1e-12
            records[name].extend(fr[name])
        foldstats.append(dict(fold=f['fold'],baseline=summaries['baseline']['ndcg'],selected=summaries['selected']['ndcg'],delta=summaries['selected']['ndcg']-summaries['baseline']['ndcg'],metrics=summaries))
        print(f'Reproduced fold{f["fold"]}: {foldstats[-1]["baseline"]:.12f} -> {foldstats[-1]["selected"]:.12f}',flush=True)
    dev=stability(pairs,POLICY['seed'],POLICY['bootstrap']);dev.update(reproduced_metrics={name:{metric:float(np.mean([f['metrics'][name][metric] for f in foldstats])) for metric in ['ndcg','recall','hit_rate']} for name in ['baseline','selected']},folds=foldstats,improved_folds=sum(f['delta']>1e-12 for f in foldstats),worsened_folds=sum(f['delta']< -1e-12 for f in foldstats),reproduced_saved_aggregate_metrics=True,reproduced_saved_artifact_ids_scores=True,actual_CV_reconstruction_MF_fits=len(fits),fits=fits,why_reconstructed='V30 persists only aggregate CV results, not user-level predictions or per-fold trained artifacts',source=source,accuracy_condition='Positive-answer users only; equal mean5folds',no_personal_ids_or_raw_ratings_exported=True)
    write('development_stability.json',dev);check_lock(lock)
    # One newly authorized V31 historical assessment, without changing V24 marker.
    opaque=reserved_tokens(ROOT/'outputs/validation/train_exclude_3.json',candidates,reserved);assert len(opaque)==25 and not {r['user'] for r in opaque}&{u for u,i,r in full}
    open_gate(lock);predictions=[];support_count=0
    for row in opaque:
        support=decode(row['support_tokens']);support_count+=len(support);cache=cache_support(support,candidates,c,m,b,index);result={}
        for name,spec in [('baseline',BASE),('selected',SELECTED)]:
            top,score=rerank(spec,cache);assert len(top)==len(set(top))==5 and not set(top)&{i for i,r in support} and set(top)<=set(candidates)
            if name=='selected':assert set(top)<=set(cache['baseline_order'][:50])
            result[name]=top
        predictions.append(result)
    write('final_predictions_complete.json',dict(users=25,models=2,support_ratings_decoded=support_count,heldout_ratings_decoded=0,policy_hash=sha(OUT/'locked_protocol.json')))
    final={'baseline':[],'selected':[]};fpairs=[];answer_count=0
    for row,pred in zip(opaque,predictions):
        answers=decode(row['answer_tokens']);answer_count+=len(answers)
        for name in final:final[name].append(metric_record(pred[name],answers))
        fpairs.append(pair_metrics(final['baseline'][-1],final['selected'][-1],1))
    stats={name:summarize(r,candidates) for name,r in final.items()};uncertainty=final_uncertainty(fpairs,POLICY['seed'],POLICY['bootstrap']);delta=stats['selected']['ndcg']-stats['baseline']['ndcg'];relative=100*delta/stats['baseline']['ndcg'] if stats['baseline']['ndcg'] else None;check_lock(lock)
    write('final_evaluation.json',dict(status='COMPLETED_HISTORICAL_USER_DISJOINT_REVALIDATION',independence=POLICY['independence'],pristine_independent=False,policy_fixed=SELECTED,models=stats,ndcg_delta=delta,relative_improvement_percent=relative,observed_improvement=delta>1e-12,independent_generalization_improvement_confirmed=False,paired=paired_counts(fpairs),paired_bootstrap=uncertainty,users=25,support_ratings=support_count,heldout_ratings=answer_count,final_runs_V31=1,V24_prior_final_runs=1,training_users=50,training_ratings=659,background_users_used=0,evaluation_train_overlap=0,new_final_MF_fits=0,model_sha256=lock['model_sha256'],predictions_complete_before_heldout_decoding=True,old_V24_final_metric_values_read=False,no_retuning=True,service_changed=False,conclusion='Fixed candidate improves on this historical holdout, not pristine independent proof' if delta>1e-12 else 'Generalization improvement not confirmed; retain original Hybrid'))
    with (OUT/'final_model_comparison.csv').open('x',newline='') as f:
        cols=['model','users','positive_users','ndcg_at5','recall_at5','hit_rate_at5','hit_users'];w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for name,s in stats.items():w.writerow(dict(model=name,users=s['users'],positive_users=s['positive_users'],ndcg_at5=s['ndcg'],recall_at5=s['recall'],hit_rate_at5=s['hit_rate'],hit_users=sum(bool(r['accuracy'] and r['accuracy']['hit_rate']) for r in final[name])))
    print(json.dumps(dict(final_baseline=stats['baseline']['ndcg'],final_selected=stats['selected']['ndcg'],relative_percent=relative,confidence95=[uncertainty['low95'],uncertainty['high95']],classification='Historical reused holdout, NOT pristine independent',MF_fits=len(fits)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
