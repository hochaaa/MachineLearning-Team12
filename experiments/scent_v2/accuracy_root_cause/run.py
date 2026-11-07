"""Evaluate preregistered diagnoses-driven policies, no additional MF fitting."""
import json,csv,hashlib
import numpy as np
from perfume.data import fragrantica
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from experiments.scent_v2.final_validation.analysis import stability
from experiments.scent_v2.background_data_recovery.core import load_model
from .diagnostic import ROOT,OUT,CONFIG,developer_data,folds,component_arrays,train_reference,pack_state,save_states
from .model import Structured,predict,score
from .access import guard


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def refs(z,n):return {key:z[f'fold{n}_calib_{key}'].copy() for key in ['raw_reference','content_reference']}


def load_selected(path,fold=1):
    """Compatible item bank plus structural matrix/Train calibrator; no raw data."""
    c,m,b,meta=load_model(path,fold)
    with np.load(path,allow_pickle=False) as z:
        struct=Structured.__new__(Structured);struct.ids=list(map(str,z[f'fold{fold}_struct_ids']));struct.items={i:n for n,i in enumerate(struct.ids)};struct.matrix=z[f'fold{fold}_struct_matrix'].copy();struct.matrix.flags.writeable=False
        reference=refs(z,fold);gate=bool(z[f'fold{fold}_gate'])
    return c,m,b,struct,reference,gate,meta


def main():
    if (OUT/'evaluation_results.json').exists():raise FileExistsError('Existing evaluation; no overwrite')
    guard();diag=json.loads((OUT/'diagnostics.json').read_text());assert diag['MF_actual_new_fits']==5 and not diag['MF_ID_bug_found'] and not diag['MF_Foldin_bug_found']
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());bg,cohort,reserved,source=developer_data(ROOT/'outputs/validation/train_exclude_3.json',candidates);assert source==diag['source'];parts=folds(cohort);catalog,raw_rows=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');policies=['baseline','structured']+(['train_cdf'] if diag['calibration_eligible'] else [])
    records={p:[] for p in policies};summaries={p:[] for p in policies};table=[];banks=[];extra={};struct_info=[];replay=[]
    with np.load(OUT/'diagnostic_fold_models.npz',allow_pickle=False) as z:
        for f in parts:
            n=f['fold'];c,m,b,meta=load_model(OUT/'diagnostic_fold_models.npz',n);reference=refs(z,n);gate=diag['folds'][n-1]['component_scores']['calibration_gate'];structured=Structured(raw_rows,{i for u,i,r in f['train']},candidates);struct_info.append(dict(fold=n,coverage=structured.coverage,vocabulary_sizes={k:len(v) for k,v in structured.vocab.items()},train_CDF_gate=gate));fr={p:[] for p in policies}
            for row in f['evaluation']:
                support=row['support'];x=component_arrays(support,candidates,c,m,b);preds={p:score(p,support,x,structured,reference,gate)[0] for p in policies}
                for p,top in preds.items():
                    assert len(top)==len(set(top))==5 and not set(top)&{i for i,r in support} and set(top)<=set(candidates)
                    fr[p].append(dict(top=top,answers=row['answers'],accuracy=user_metrics(top,row['answers'])))
            for p,recs in fr.items():
                s=summarize(recs,candidates);summaries[p].append(s);records[p].extend(recs);table.append(dict(scope='without_background',model=p,fold=n,train_users=40,train_ratings=len(f['train']),ndcg_at5=s['ndcg'],recall_at5=s['recall'],hit_rate_at5=s['hit_rate']))
            banks.append(pack_state(c,m,b,candidates));extra.update({f'fold{n}_calib_{k}':value for k,value in reference.items()});extra[f'fold{n}_gate']=np.asarray(gate);extra[f'fold{n}_struct_matrix']=structured.matrix;extra[f'fold{n}_struct_ids']=np.asarray(structured.ids)
            synthetic=list(zip(sorted(candidates)[:5],[.9,.1,.7,.3,.5]));replay.append({p:predict(p,synthetic,candidates,c,m,b,structured,reference,gate) for p in policies})
    results={p:dict(mean_ndcg=float(np.mean([s['ndcg'] for s in ss])),mean_recall=float(np.mean([s['recall'] for s in ss])),mean_hit_rate=float(np.mean([s['hit_rate'] for s in ss])),fold_ndcg=[s['ndcg'] for s in ss],pooled=summarize(records[p],candidates)) for p,ss in summaries.items()}
    assert abs(results['baseline']['mean_ndcg']-.040963057685131546)<1e-12
    for p in policies:
        pairs=[]
        for n,(a,b) in enumerate(zip(records['baseline'],records[p])):
            aa,bb=a['accuracy'],b['accuracy'];pairs.append(dict(fold=n//10+1,baseline_ndcg=aa['ndcg'] if aa else None,selected_ndcg=bb['ndcg'] if bb else None,delta=bb['ndcg']-aa['ndcg'] if aa else None,baseline_hit=aa['hit_rate'] if aa else None,selected_hit=bb['hit_rate'] if bb else None))
        results[p]['stability']=stability(pairs,CONFIG['bootstrap_seed'],CONFIG['bootstrap_draws']);results[p]['folds_improved']=sum(a>b+1e-12 for a,b in zip(results[p]['fold_ndcg'],results['baseline']['fold_ndcg']));results[p]['folds_worse']=sum(a<b-1e-12 for a,b in zip(results[p]['fold_ndcg'],results['baseline']['fold_ndcg']))
        print(f'{p}: {results[p]["mean_ndcg"]:.12f}, folds improved{results[p]["folds_improved"]}',flush=True)
    key=lambda p:(round(results[p]['mean_ndcg'],12),round(results[p]['mean_recall'],12),round(results[p]['mean_hit_rate'],12),p=='baseline');eligible=[p for p in policies if results[p]['mean_ndcg']>results['baseline']['mean_ndcg']+1e-12];selected=max(eligible,key=key) if eligible else 'baseline'
    write('selection.json',dict(selected=selected,policy_fixed_before_background_check=True,rule='NDCG then Recall then HitRate; strict baseline improvement',no_independent_claim=True));save_states(OUT/'best_model.npz',banks,extra,selected)
    for n in range(1,6):
        c,m,b,struct,ref,gate,meta=load_selected(OUT/'best_model.npz',n)
        for p in policies:assert predict(p,synthetic,candidates,c,m,b,struct,ref,gate)==replay[n-1][p]
    background_result={'status':'NOT_RUN_NO_PROMISING_NEW_POLICY'}
    if selected!='baseline':
        bg_records={'baseline':[],'selected':[]};bg_stats={'baseline':[],'selected':[]};roundtrip_bg=[]
        for f in parts:
            n=f['fold'];c,m,b,meta=load_model(ROOT/'outputs/scent_v2/background_data_recovery/best_model.npz',n);train=bg+f['train'];structured=Structured(raw_rows,{i for u,i,r in train},candidates)
            reference,train_diag=train_reference(train,candidates,c,m,b);gate=train_diag['calibration_gate'];fr={p:[] for p in bg_records}
            for row in f['evaluation']:
                support=row['support'];x=component_arrays(support,candidates,c,m,b)
                for name,p in [('baseline','baseline'),('selected',selected)]:
                    top,sc=score(p,support,x,structured,reference,gate);fr[name].append(dict(top=top,answers=row['answers'],accuracy=user_metrics(top,row['answers'])))
            for name,recs in fr.items():
                ss=summarize(recs,candidates);bg_stats[name].append(ss);bg_records[name].extend(recs);table.append(dict(scope='with_background',model='baseline' if name=='baseline' else selected,fold=n,train_users=295,train_ratings=len(train),ndcg_at5=ss['ndcg'],recall_at5=ss['recall'],hit_rate_at5=ss['hit_rate']))
        background_result=dict(status='EVALUATED_FIXED_SELECTED_POLICY_ONLY',selected=selected,new_MF_fits=0,models={p:dict(mean_ndcg=float(np.mean([s['ndcg'] for s in ss])),mean_recall=float(np.mean([s['recall'] for s in ss])),mean_hit_rate=float(np.mean([s['hit_rate'] for s in ss])),fold_ndcg=[s['ndcg'] for s in ss],pooled=summarize(bg_records[p],candidates)) for p,ss in bg_stats.items()},used_for_primary_selection=False)
        assert abs(background_result['models']['baseline']['mean_ndcg']-.024877491337577405)<1e-12
    diag['structured_feature_audit']=struct_info;diag['calibration_per_fold_gates']=[d['component_scores']['calibration_gate'] for d in diag['folds']]
    # Add only new feature audit to this experiment's own diagnostic output.
    (OUT/'diagnostics.json').write_text(json.dumps(diag,indent=2,ensure_ascii=False,allow_nan=False))
    write('evaluation_results.json',dict(status='COMPLETED_REUSED_DEVELOPMENT_CV',primary_without_background=results,selected=selected,relative_improvement_percent=100*(results[selected]['mean_ndcg']/results['baseline']['mean_ndcg']-1),background_check=background_result,actual_new_MF_fits=5,background_MF_fits=0,Content_fit_count=5,all5fold_policy_roundtrip_scores_and_IDs_exact=True,source=source,reserved_labels_decoded=0,final25_evaluations=0,V24_V31_final_result_reads=0,independent_generalization_claim=False,inner_CV='Not run: fixed minimal policies/weights before diagnosis and answers; same reused5fold selection bias disclosed',service_changed=False))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(selected=selected,baseline=results['baseline']['mean_ndcg'],selected_ndcg=results[selected]['mean_ndcg'],background=background_result,MF_new_fits=5)),flush=True)

if __name__=='__main__':main()
