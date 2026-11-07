"""Train only new independent pairwise models; Inner-only locked selection.

Mechanics adapted from local signed_content/run.py, baseline Q/IDF never changed.
"""
import os,sys,json,hashlib,subprocess,math,platform
from collections import Counter,defaultdict
from datetime import datetime,timezone
from types import SimpleNamespace
from pathlib import Path
from .config import ROOT,HEAD,TRAIN,CANDIDATES,CATALOG,BASE,TUNING,OUT,POLICY
from experiments.scent_v2.run import write_json,write_csv


def main():
    """Max15 real-data fits (12 Inner, <=3 selected Outer); no final full fit."""
    os.chdir(ROOT)
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=HEAD:raise RuntimeError('HEAD mismatch')
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='development-v2':raise RuntimeError('Branch mismatch')
    if OUT.exists():raise RuntimeError('Existing output: STOP, no overwrite')
    protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for d in (ROOT/'experiments/scent_v2',ROOT/'outputs/scent_v2',ROOT/'docs/presentation')for p in d.rglob('*')if p.is_file()}
    state={'outer':False,'integrity':False};allowed={TRAIN.resolve(),CANDIDATES.resolve(),CATALOG.resolve()}
    def guard(event,args):
        if event=='open'and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();writing=(isinstance(args[1],str)and any(c in args[1]for c in 'wax+'))or(isinstance(args[2],int)and args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise RuntimeError('Protected file write')
            if not writing and p.is_relative_to(ROOT)and p.suffix in ('.json','.csv','.npz','.npy'):
                inner=p.is_relative_to(TUNING)and(p.name in ('fit_ledger.json','inner_results.private.json')or'inner'in p.name)
                outer=state['outer']and p.is_relative_to(BASE)
                integrity=state['integrity']and str(p.relative_to(ROOT))in protected
                if p not in allowed and not inner and not outer and not integrity and not p.is_relative_to(OUT):raise RuntimeError('Forbidden old artifact/answer access')
        if event in ('os.remove','os.rmdir','os.rename','os.link','os.symlink','os.truncate','subprocess.Popen'):raise RuntimeError('Forbidden action')
        if event=='os.mkdir'and not Path(args[0]).resolve().is_relative_to(OUT):raise RuntimeError('Unexpected mkdir')
    sys.addaudithook(guard)
    import numpy as np
    from perfume.models import Content,Baseline
    from perfume.data import fragrantica
    from experiments.scent_v2.splits import build,validate
    from experiments.scent_v2.recommend import fold_in as ridge
    from .training import fit
    from .evaluation import evaluate_context,aggregate,comparisons,select_inner,compatibility
    fit_events=[]
    OUT.mkdir();write_json(OUT/'policy.json',POLICY);policyhash=hashlib.sha256((OUT/'policy.json').read_bytes()).hexdigest()
    def countfit(frame,event,arg):
        if event=='call'and frame.f_code is fit.__code__:
            fit_events.append(dict(number=len(fit_events)+1,phase='outer'if state['outer']else 'inner',variant=frame.f_locals['variant'],train_sha256=hashlib.sha256(json.dumps(frame.f_locals['rows']).encode()).hexdigest()))
            if len(fit_events)>15:raise RuntimeError('Real fit budget exceeded')
            write_json(OUT/f'fit{len(fit_events):02d}_started.json',fit_events[-1])
        if event=='call'and frame.f_code.co_name=='fit'and 'perfume'in frame.f_code.co_filename:raise RuntimeError('Original models cannot be fitted')
    sys.setprofile(countfit)
    rows=json.loads(TRAIN.read_text());candidates=json.loads(CANDIDATES.read_text());outers=build(rows,candidates);catalog,_=fragrantica(CATALOG)
    led=json.loads((TUNING/'fit_ledger.json').read_text())['fits'];old=json.loads((TUNING/'inner_results.private.json').read_text())
    refs={(r['outer'],r['inner'],r['track'],r['user'],r['method']):r for r in old['accuracy']if r['lambda']==.01 and r['method']in ('mf','hybrid')}
    refrob={(r['outer'],r['inner'],r['track'],r['user'],r['method'],r['amplitude']):r for r in old['robustness']if r['lambda']==.01 and r['method']in ('mf','hybrid')}
    training=[];reuses=[];all_a=[];all_r=[];all_i=[];choices=[];parity=0;maxdiff=0.
    def load(directory,stem,fold,evidence,excluded):
        validate(fold,candidates);assert not({u for u,i,y in fold['train']}&set(excluded));assert hashlib.sha256(json.dumps(fold['train']).encode()).hexdigest()==evidence['train_sha256']
        md=json.loads((directory/(stem+'_model.private.json')).read_text())
        with np.load(directory/(stem+('_Q.npz'if directory==TUNING else '_factors.npz')))as a:q=a['Q'].copy()
        q.flags.writeable=False;assert hashlib.sha256(q.tobytes()).hexdigest()==evidence['q_sha256'];assert set(md['items'])=={i for u,i,y in fold['train']}
        mf=SimpleNamespace(Q=q,items=md['items'],factors=4,reg=.01,variant='baseline')
        c=Content();c.idf=md['content_idf'];c.vectors={}
        for item,row in catalog.items():
            v={t:c.idf[t]for t in set(row['tokens'])if t in c.idf};norm=math.sqrt(sum(x*x for x in v.values()));c.vectors[item]={t:x/norm for t,x in v.items()}if norm else {}
        pop=Baseline();pop.counts=Counter(i for u,i,y in fold['train']);pop.maximum=max(pop.counts.values())
        reuses.append(dict(stem=stem,q_sha256=evidence['q_sha256'],mapping_verified=True,train_boundary_verified=True))
        return c,mf,pop
    def ridge_rmse(model,train):
        by=defaultdict(list)
        for u,i,y in train:by[u].append((i,y))
        errors=[]
        for support in by.values():
            p=ridge(model,support)
            if p is not None:errors.extend((float(np.einsum('i,i->',p,model.Q[model.items[i]]))-y)**2 for i,y in support if i in model.items)
        return float(np.sqrt(np.mean(errors)))if errors else None
    def train_new(fold,excluded,variant,stem,baseline):
        model,diagnostic=fit(fold['train'],excluded,variant)
        diagnostic.update(stem=stem,train_sha256=hashlib.sha256(json.dumps(fold['train']).encode()).hexdigest(),q_sha256=hashlib.sha256(model.Q.tobytes()).hexdigest(),train_ridge_rmse=ridge_rmse(model,fold['train']),baseline_train_ridge_rmse=ridge_rmse(baseline,fold['train']),baseline_Q_norm=float(np.linalg.norm(baseline.Q)),factor_items=len(model.items))
        np.savez(OUT/(stem+'_factors.private.npz'),Q=model.Q,P=model.P)
        write_json(OUT/(stem+'_mapping.private.json'),dict(items=model.items,users=model.users));training.append(diagnostic)
        return model,diagnostic
    for outer in outers:
        o=outer['fold'];folds=json.loads((TUNING/f'outer{o}_inner_splits.private.json').read_text());aa=[];rr=[];ii=[];tt=[]
        for f in folds:
            n=f['fold'];ev=next(e for e in led if e['outer']==o and e['inner']==n);excluded=set(outer['users'])|set(f['users']);c,base,pop=load(TUNING,f'outer{o}_inner{n}',f,ev,excluded);models={'baseline':base}
            for p in ('variant_a','variant_b'):
                models[p],d=train_new(f,excluded,p,f'outer{o}_inner{n}_{p}',base);tt.append(d)
            a,r,i=evaluate_context(f,o,'inner',c,models,pop,candidates)
            for x in a:
                if x['policy']!='baseline'or x['method']=='content':continue
                old=refs[o,n,x['track'],x['user'],x['method']];assert x['top']==old['top']and x['accuracy']==old['accuracy'];diff=max(abs(a-b)for a,b in zip(x['top_scores'],old['top_scores']));assert diff<=1e-12;maxdiff=max(maxdiff,diff);parity+=1
            for x in r:
                if x['policy']=='baseline'and x['method']!='content':
                    old=refrob[o,n,x['track'],x['user'],x['method'],x['amplitude']];assert all(x[k]==old[k]for k in ('replacement','first','set_same','order_same','jaccard','rank_move'))
            aa+=a;rr+=r;ii+=i;print(f'Outer{o}/Inner{n}: A/B fitted and baseline parity passed; real fits={len(fit_events)}',flush=True)
        comp=compatibility(aa,tt);choice=dict(outer=o,**select_inner(aa,rr,comp),selected_at_utc=datetime.now(timezone.utc).isoformat());choices.append(choice);all_a+=aa;all_r+=rr;all_i+=ii
        print(f'Outer{o}: Inner choice locked = {choice["selected_policy"]}',flush=True)
    assert len(fit_events)==12
    write_json(OUT/'selection_locked.json',dict(policy_sha256=policyhash,outer_results_seen=False,choices=choices));lockhash=hashlib.sha256((OUT/'selection_locked.json').read_bytes()).hexdigest()
    write_json(OUT/'inner_results.private.json',dict(accuracy=all_a,robustness=all_r,impact=all_i))
    a,r=aggregate(all_a,all_r);write_csv(OUT/'inner_results.csv',a);write_json(OUT/'inner_robustness.json',r);inner_ci=comparisons(all_a,all_r)
    state['outer']=True
    saved=json.loads((BASE/'user_results.private.json').read_text());outerledger=json.loads((BASE/'fit_ledger.json').read_text())['fits'];outer_a=[];outer_r=[];outer_i=[]
    for f,choice in zip(outers,choices):
        o=f['fold'];c,base,pop=load(BASE,f'fold{o}',f,outerledger[o-1],f['users']);models={'baseline':base};selected=choice['selected_policy']
        if selected!='baseline':models[selected],_=train_new(f,f['users'],selected,f'outer{o}_{selected}',base)
        a,r,i=evaluate_context(f,o,'outer',c,models,pop,candidates)
        for x in a:
            if x['policy']!='baseline':continue
            ref=next(y for y in saved['accuracy']if y['fold']==o and y['track']==x['track']and y['user']==x['user']and y['method']==x['method']);assert x['top']==ref['top']and x['accuracy']==ref['accuracy'];d=max(abs(a-b)for a,b in zip(x['top_scores'],ref['top_scores']));assert d<=1e-12;maxdiff=max(maxdiff,d);parity+=1
        for label,p in [('baseline','baseline'),('selected',selected)]:
            outer_a.extend(dict(x,policy=label,actual_policy=p)for x in a if x['policy']==p and(x['method']!='content'or label=='baseline'))
            outer_r.extend(dict(x,policy=label,actual_policy=p)for x in r if x['policy']==p and(x['method']!='content'or label=='baseline'))
            outer_i.extend(dict(x,policy=label,actual_policy=p)for x in i if x['policy']==p and(x['method']!='content'or label=='baseline'))
        print(f'Outer{o}: baseline + locked selection evaluated only ({selected})',flush=True)
    oa=[];orr=[]
    for label in ('baseline','selected'):
        a,r=aggregate([dict(x,policy='baseline')for x in outer_a if x['policy']==label],[dict(x,policy='baseline')for x in outer_r if x['policy']==label])
        for x in a+r:x['policy']=label
        oa+=a;orr+=r
    write_csv(OUT/'outer_results.csv',oa);write_json(OUT/'outer_results.private.json',dict(accuracy=outer_a,robustness=outer_r,impact=outer_i))
    write_json(OUT/'bootstrap_ci.json',dict(inner=inner_ci,outer=comparisons(outer_a,outer_r,('selected',))))
    write_json(OUT/'robustness.json',dict(inner=r if False else json.loads((OUT/'inner_robustness.json').read_text()),outer=orr))
    write_json(OUT/'training_diagnostics.json',dict(real_data_fit_calls=len(fit_events),fits=training))
    write_json(OUT/'fit_ledger.json',dict(actual_real_data_fit_calls=len(fit_events),fit_events=fit_events,synthetic_test_fit_calls_before_run=6,no_fit_cache=True))
    foldin=[{k:x[k]for k in ('phase','outer','inner','user','policy','track','method','foldin','clipping_frequency','factor_candidates','score_distribution','mf_raw_distribution','mf_mapped_distribution')}for x in all_a+outer_a if x['method']=='mf']
    write_json(OUT/'foldin_diagnostics.private.json',foldin)
    summary=dict(status='PASS',new_real_data_fits=len(fit_events),baseline_Q_context_reuses=len(reuses),choices=[dict(outer=x['outer'],selected=x['selected_policy'])for x in choices],A_hybrid_diagnostic_only=True,service_model_unchanged=True)
    write_json(OUT/'summary.json',summary)
    sys.setprofile(None);state['integrity']=True
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in protected.items());assert hashlib.sha256((OUT/'policy.json').read_bytes()).hexdigest()==policyhash;assert hashlib.sha256((OUT/'selection_locked.json').read_bytes()).hexdigest()==lockhash
    write_json(OUT/'verification.json',dict(status='PASS',actual_real_data_fits=len(fit_events),baseline_Q_reuses=reuses,baseline_comparisons=parity,maximum_baseline_top5_score_difference=maxdiff,baseline_metrics_and_robustness_exact=True,selection_locked_before_outer=True,selection_sha256=lockhash,policy_sha256=policyhash,original_validation_internal_external_answers_read=False,unselected_outer_models_not_fitted_or_evaluated=True,python=platform.python_version(),numpy=np.__version__,code_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path(__file__).parent.rglob('*.py')}))
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
