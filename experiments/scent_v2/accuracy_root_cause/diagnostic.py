"""Training-only MF and component diagnostics, no new recommender or tuning."""
from pathlib import Path
import json,hashlib
from collections import Counter
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline,hybrid
from perfume.data import fragrantica
from experiments.scent_v2.mf_accuracy_optimization.core import developer_data,digest
from experiments.scent_v2.mf_cv_optimization.core import ROOT,folds,ridge,validate_train
from experiments.scent_v2.background_data_recovery.core import pack_state,load_model as load_background
OUT=ROOT/'outputs/scent_v2/accuracy_root_cause';CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def stats(values):
    a=np.asarray(values,float);a=a[np.isfinite(a)]
    return dict(n=len(a),mean=float(a.mean()) if len(a) else None,std=float(a.std()) if len(a) else None,quantiles=list(map(float,np.quantile(a,[0,.05,.5,.95,1]))) if len(a) else None)


def group_stats(rows):
    users=sorted({u for u,i,r in rows});counts=Counter(u for u,i,r in rows);items=Counter(i for u,i,r in rows);ys=[r for u,i,r in rows]
    means=[np.mean([r for a,i,r in rows if a==u]) for u in users];variances=[np.var([r for a,i,r in rows if a==u]) for u in users]
    return dict(users=len(users),ratings=len(rows),rating=stats(ys),user_rating_counts=stats(list(counts.values())),user_rating_means=stats(means),user_rating_variances=stats(variances),positive_rating_fraction=float(np.mean(np.asarray(ys)>=.7)),item_rating_counts=stats(list(items.values())),unique_items=len(items),top5_item_rating_fraction=sum(n for i,n in items.most_common(5))/len(rows))


def component_arrays(support,candidates,c,m,b):
    pool=sorted(set(candidates)-{i for i,r in support});p,_=ridge(m,support)
    raw=np.asarray([np.einsum('i,i->',p,m.Q[m.items[i]]) if p is not None and i in m.items else np.nan for i in pool]);cs=c.score(support,pool);ms=np.clip(raw,0,1);bs=b.score(pool)
    return dict(pool=pool,content=cs,raw=raw,mf=ms,popularity=bs,hybrid=hybrid(cs,ms,.25,bs))


def train_reference(rows,candidates,c,m,b):
    """Predict from deterministic TRAIN users' pseudoSupport only; no eval data."""
    histories={u:[] for u,i,r in rows}
    for u,i,r in rows:
        if i in set(candidates):histories[u].append((i,r))
    eligible=sorted((u for u,h in histories.items() if len(h)>=5),key=lambda u:digest('12:v233:reference:'+u))[:CONFIG['calibration']['reference_users_max']];arrays=[];residuals=[]
    for u in eligible:
        support=sorted(histories[u],key=lambda p:digest('12:v233:support:'+u+':'+p[0]))[:5];x=component_arrays(support,candidates,c,m,b);arrays.append(x);p,_=ridge(m,support);known=[(i,r) for i,r in support if i in m.items]
        if known:
            q=np.asarray([m.Q[m.items[i]] for i,r in known]);y=np.asarray([r for i,r in known])
            G=np.einsum('ni,nj->ij',q,q)+len(known)*m.reg*np.eye(m.factors);rhs=np.einsum('ni,n->i',q,y);residuals.append(float(np.linalg.norm(np.einsum('ij,j->i',G,p)-rhs)))
    if not arrays:raise ValueError('No training-only calibration reference')
    raw=np.concatenate([x['raw'] for x in arrays]);cs=np.concatenate([x['content'] for x in arrays]);ms=np.clip(raw,0,1);h=np.concatenate([x['hybrid'] for x in arrays]);finite=np.isfinite(raw);valid=finite&np.isfinite(cs)
    norm=np.std(ms[valid])/np.std(cs[valid]) if np.std(cs[valid])>1e-12 else None;clipped=float(np.mean((raw[finite]<0)|(raw[finite]>1)));gate=clipped>.01 or norm is not None and (norm<.5 or norm>2)
    # Fallback probe uses an absent item identity and the unmodified hybrid.
    probe=hybrid(np.asarray([.2,np.nan,np.nan]),np.asarray([np.nan,.7,np.nan]),.25,np.asarray([.1,.1,.1]))
    assert np.array_equal(probe,[.2,.7,.1])
    return dict(raw_reference=np.sort(raw[finite]),content_reference=np.sort(cs[np.isfinite(cs)])),dict(reference_users=len(eligible),reference_pairs=len(raw),MF_raw=stats(raw),MF_clipped=stats(ms),Content=stats(cs),Hybrid=stats(h),raw_clipped_fraction=clipped,MF_to_Content_std_ratio=norm,weighted_MF_std=float(.75*np.std(ms[valid])),weighted_Content_std=float(.25*np.std(cs[valid])),weighted_covariance=float(np.cov(.25*cs[valid],.75*ms[valid],ddof=0)[0,1]),MF_top_tie_fraction=float(np.mean(ms[finite]==1)),ridge_normal_equation_residual_max=max(residuals,default=0),fallback_probe_pass=True,calibration_gate=bool(gate),uses='TRAIN pseudoSupport only; reference scores are not validation RMSE')


def save_states(path,states,extra=None,policy='baseline'):
    values={f'fold{n}_{key}':v for n,state in enumerate(states,1) for key,v in state.items()}
    if extra:values.update(extra)
    values['metadata']=np.asarray(json.dumps(dict(mf_config=CONFIG['mf'],folds=len(states),default_fold=1,policy=policy,config=CONFIG,artifact_type='Individual CV fold states; no ensemble or all-data final refit')))
    with path.open('xb') as f:np.savez_compressed(f,**values)


def main():
    if (OUT/'diagnostics.json').exists():raise FileExistsError('Diagnostics already completed')
    from .access import guard
    OUT.chmod(0o700)
    with (OUT/'experiment_config.json').open('x') as f:json.dump(CONFIG,f,indent=2)
    guard()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());bg,cohort,reserved,source=developer_data(ROOT/'outputs/validation/train_exclude_3.json',candidates);expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text());assert source==expected
    proof=json.loads((ROOT/'outputs/scent_v2/background_data_recovery/verification.json').read_text());old_bg=json.loads((ROOT/'outputs/scent_v2/background_data_recovery/evaluation_results.json').read_text())
    assert hashlib.sha256((ROOT/'outputs/scent_v2/background_data_recovery/best_model.npz').read_bytes()).hexdigest()==proof['model_sha256'] and old_bg['source']==source
    catalog,rows=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');parts=folds(cohort);states=[];fold_diag=[];extra={}
    for f in parts:
        validate_train(f['train'],reserved|{r['user'] for r in f['evaluation']});c=Content().fit(catalog,{i for u,i,r in f['train']});b=Baseline().fit(f['train']);m=MatrixFactorization(**CONFIG['mf']).fit(f['train'])
        assert len(m.items)==len(m.Q) and set(m.items.values())==set(range(len(m.Q))) and len(m.users)==len(m.P) and set(m.users.values())==set(range(len(m.P)))
        actual=np.asarray([r for u,i,r in f['train']]);pred=np.asarray([np.einsum('i,i->',m.P[m.users[u]],m.Q[m.items[i]]) for u,i,r in f['train']]);rmse=float(np.sqrt(np.mean((pred-actual)**2)));corr=float(np.corrcoef(pred,actual)[0,1]);m.Q.flags.writeable=False
        ref,diag=train_reference(f['train'],candidates,c,m,b);bc,bm,bb,meta=load_background(ROOT/'outputs/scent_v2/background_data_recovery/best_model.npz',f['fold']);_,bgdiag=train_reference(f['train'],candidates,bc,bm,bb)
        fold_diag.append(dict(fold=f['fold'],train40_ratings=len(f['train']),train_RMSE_raw=rmse,train_RMSE_clipped=float(np.sqrt(np.mean((np.clip(pred,0,1)-actual)**2))),train_prediction_rating_correlation=corr,loss_first=m.losses[0],loss_last=m.losses[-1],losses_finite=bool(np.isfinite(m.losses).all()),loss_increase_epochs=sum(b>a for a,b in zip(m.losses,m.losses[1:])),user_item_mapping_checks=True,train_user_counts=group_stats(f['train']),component_scores=diag,background_component_scores=bgdiag))
        states.append(pack_state(c,m,b,candidates));extra.update({f'fold{f["fold"]}_calib_{key}':value for key,value in ref.items()})
        print(f'Diagnostic fold{f["fold"]}: loss {m.losses[0]:.6f}->{m.losses[-1]:.6f}, Train RMSE {rmse:.6f}, clip {diag["raw_clipped_fraction"]:.3f}, CDF gate {diag["calibration_gate"]}',flush=True)
    save_states(OUT/'diagnostic_fold_models.npz',states,extra)
    valid_columns=all(k in rows[0] for k in ['Top','Middle','Base',*[f'mainaccord{i}' for i in range(1,6)]]);assert valid_columns
    report=dict(source=source,folds=fold_diag,background_distribution=group_stats(bg),developer_distribution_descriptive_only=group_stats([(r['user'],i,y) for r in cohort for i,y in r['support']+r['answers']]),MF_actual_new_fits=5,background_MF_fits=0,background_models_reused='V32 per-fold295-user archive, no new fits',rating_semantics='Existing normalized[0,1], original zero-excluded Train unchanged',MF_ID_bug_found=False,MF_Foldin_bug_found=False,MF_stabilization_model='NOT_IMPLEMENTED: no actual implementation bug established',validation_RMSE='NOT_EVALUATED: training-reference scores are in-sample, not a heldout RMSE',structured_columns_available=valid_columns,original_Content_representation='Binary TF-IDF of pooled note/accord phrases, NOT free-text descriptions; Top/Middle/Base roles are currently collapsed',calibration_eligible=any(f['component_scores']['calibration_gate'] for f in fold_diag),gate_does_not_read_Outer_answers=True,reserved_rating_tokens_decoded=0,V24_V31_final_results_read=False)
    with (OUT/'diagnostics.json').open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
    print('Diagnostics complete; new MF fits5, original MF retained',flush=True)

if __name__=='__main__':main()
