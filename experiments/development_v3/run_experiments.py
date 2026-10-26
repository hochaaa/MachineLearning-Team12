"""Approved <=61 actual MF fits. Inner locks precede outer/newseed/final fit."""
import sys,time,json,csv,subprocess,platform,copy
from pathlib import Path
from collections import Counter
import numpy as np
from v3_data import ROOT,OUT,load_train,save,guard,deny,snapshot,sha,histories,READS
from v3_config import POLICIES,V1,V2,SETTINGS,verify_source
from split import outer_specs,inner_specs,user_evaluation,known_split
from mf_v3 import MFV3
from mf_v2 import BiasMF
from data import inner_stop
from perfume.models import MatrixFactorization
from fit_budget import FitBudget
from evaluate_v3 import ScoringContext,assess,select_policy,paired_bootstrap


def table(name,rows):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    if rows:
        keys=sorted(set().union(*(r.keys() for r in rows)))
        with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def training_config(p):return {k:p[k] for k in ['factors','epochs','learning_rate','latent_l2','bias_l2']}


def train_model(fit,policy,seed,budget,phase,tag):
    if policy['id']=='V1':
        cfg={k:V1[k] for k in ['factors','epochs','learning_rate','regularization']};m=MatrixFactorization(**cfg,seed=seed);m.config=dict(V1);return budget.invoke(m,fit,phase,tag)
    if policy['id']=='V2':
        cfg={k:V2[k] for k in ['factors','epochs','learning_rate','regularization']};inner,stop=inner_stop(fit,seed);probe=budget.invoke(BiasMF(cfg,seed),inner,phase,tag+'/nested_stop',stop)
        cfg=dict(cfg,epochs=probe.best_epoch if stop else 40);return budget.invoke(BiasMF(cfg,seed),fit,phase,tag+'/refit')
    return budget.invoke(MFV3(training_config(policy),seed),fit,phase,tag)


def persist_model(model,path,policy,seed):
    arrays={'P':model.P,'Q':model.Q}
    if hasattr(model,'bu'):arrays.update(bu=model.bu,bi=model.bi)
    target=OUT/path;target.mkdir(parents=True,exist_ok=True);np.savez(target/'weights.npz',**arrays)
    (target/'metadata.json').write_text(json.dumps({'policy':policy,'seed':seed,'mean':getattr(model,'mean',None),'users':model.users,'items':model.items,'training_config':model.config,'actual_epochs':getattr(model,'best_epoch',getattr(model,'epochs',None))},ensure_ascii=False,indent=2))


def evaluate(context,model,policy,answers,stage,outer,inner=-1,seed=12,kinds=False):
    out=[];per={}
    for kind,label in [('hybrid',policy['id']+'H' if policy['id'] in ('V1','V2') else policy['id'])]+([('content',policy['id']+'C'),('mf',policy['id']+'M')] if kinds else []):
        pred,fb,diag,times=context.predict(model,policy,kind);row,pu=assess(pred,answers,context.pool,fb,diag,times);out.append({'stage':stage,'outer':outer,'inner':inner,'seed':seed,'policy':policy['id'] if stage=='inner' else label,'component':kind,**row});per[label]=pu
    return out,per


def main():
    guard();source=verify_source()
    if (OUT/'configs/run_started.json').exists():raise RuntimeError('Refuse rerun/overwrite; inspect original receipts')
    assert (OUT/'diagnostics/pretraining_tests_passed.json').exists(),'Synthetic tests must pass first'
    save('configs/execution.json',{'settings':SETTINGS,'policies':POLICIES,'baselines':[V1,V2],'source_validation':source,'all_phases_max':61,'test_fits':0,'final_procedure':'aggregate six inner folds before all outer evaluations; outer-specific choices from only its two inner folds'})
    save('configs/run_started.json',{'status':'started','source_hash':sha(Path(__file__))});before=snapshot();save('diagnostics/integrity_before.json',before);sys.addaudithook(deny)
    start=time.perf_counter();budget=FitBudget(SETTINGS['caps']);sys.setprofile(budget.profile)
    train,pool,catalog,raw=load_train();outer=outer_specs(train);inner_rows=[];receipts=[]
    # All inner choices and global final choice are locked before any outer labels/predictions.
    for o,ofit,oheld in outer:
        for j,fit,held in inner_specs(ofit,o):
            assert not oheld&{u for u,_,_ in fit};assert not oheld&held
            supports,answers,excluded=user_evaluation(ofit,fit,held,pool)
            positive=len({u for u,i,r in answers if r>=.7});assert positive>=SETTINGS['min_inner_positive']
            ctx=ScoringContext(fit,pool,catalog,raw,supports)
            receipts.append({'stage':'inner','outer':o,'inner':j,'fit_users':len({u for u,_,_ in fit}),'fit_ratings':len(fit),'fit_items':len({i for _,i,_ in fit}),'evaluation_users':len(supports),'positive_users':positive,'heldout_ratings':len(answers),'unknown_factor_answers':sum(i not in {ii for _,ii,_ in fit} for u,i,r in answers),'fixed_candidates':479,'excluded':excluded,'outer_user_overlap':0})
            for policy in [V1,V2,*POLICIES]:
                model=train_model(fit,policy,12,budget,'primary',f'outer{o}/inner{j}/{policy["id"]}')
                rows,_=evaluate(ctx,model,policy,answers,'inner',o,j);inner_rows.extend(rows)
            print('INNER COMPLETE',o,j,'fit_count',sum(budget.used.values()),flush=True)
            assert time.perf_counter()-start<SETTINGS['hard_seconds'],'Time budget reached'
    choices={};locks={}
    for o,_,_ in outer:choices[o],locks[str(o)]=select_policy([r for r in inner_rows if r['outer']==o],POLICIES,SETTINGS)
    final_policy,final_receipt=select_policy(inner_rows,POLICIES,SETTINGS)
    save('configs/selections_locked.json',{'per_outer':{str(o):p for o,p in choices.items()},'per_outer_receipts':locks,'full_train_policy':final_policy,'full_train_inner_only_receipt':final_receipt,'outer_results_used':False})
    table('metrics/inner.csv',inner_rows)
    outer_rows=[];known_rows=[];paired=[];outer_cache={}
    for o,fit,held in outer:
        supports,answers,excluded=user_evaluation(train,fit,held,pool);positive=len({u for u,i,r in answers if r>=.7});assert positive>=SETTINGS['min_outer_positive']
        receipts.append({'stage':'outer','outer':o,'fit_users':len({u for u,_,_ in fit}),'fit_ratings':len(fit),'fit_items':len({i for _,i,_ in fit}),'evaluation_users':len(supports),'positive_users':positive,'heldout_ratings':len(answers),'unknown_factor_answers':sum(i not in {ii for _,ii,_ in fit} for u,i,r in answers),'fixed_candidates':479,'excluded':excluded,'user_overlap':0})
        ctx=ScoringContext(fit,pool,catalog,raw,supports);outer_cache[o]=(supports,answers)
        for label,policy in [('V1',V1),('V2',V2),('Nested',choices[o])]:
            model=train_model(fit,policy,12,budget,'primary',f'outer{o}/{label}');persist_model(model,f'models/outer{o}/{label}',policy,12)
            rows,per=evaluate(ctx,model,policy,answers,'outer',o,kinds=label in ['V1','V2'])
            for row in rows:
                if label=='Nested':row['policy']='Nested';row['selected_policy']=policy['id']
                outer_rows.append(row)
            pu=per[policy['id']+'H' if policy['id'] in ('V1','V2') else policy['id']];paired.append((o,label+'H' if label in ('V1','V2') else label,pu))
        # Secondary known-user diagnostic, choices frozen; no V2 fit added.
        kfit,kanswers=known_split(fit,o);kh=histories(kfit);ksupport={u:kh[u] for u,i,r in kanswers};kctx=ScoringContext(kfit,pool,catalog,raw,ksupport)
        for label,policy in [('V1',V1),('Nested',choices[o])]:
            model=train_model(kfit,policy,12,budget,'primary',f'known{o}/{label}');pred,fb,d,t=kctx.predict(model,policy,known=True);s,_=assess(pred,kanswers,pool,fb,d,t);known_rows.append({'stage':'known_secondary','outer':o,'policy':label,'selected_policy':policy['id'],**s})
        print('OUTER COMPLETE',o,'selected',choices[o]['id'],'fit_count',sum(budget.used.values()),flush=True)
        assert time.perf_counter()-start<SETTINGS['hard_seconds'],'Time budget reached'
    assert budget.used['primary']<=54
    table('metrics/outer.csv',outer_rows);table('metrics/known_secondary.csv',known_rows);save('diagnostics/fold_receipts.json',receipts)
    save('diagnostics/paired_bootstrap.json',{'vs_V1':paired_bootstrap(paired),'vs_V2':paired_bootstrap(paired,reference='V2H')})
    seed_rows=[]
    for o,fit,held in outer:
        supports,answers=outer_cache[o];ctx=ScoringContext(fit,pool,catalog,raw,supports)
        for label,policy in [('V1',V1),('Nested',choices[o])]:
            model=train_model(fit,policy,29,budget,'seed',f'seed29/outer{o}/{label}');rows,_=evaluate(ctx,model,policy,answers,'seed',o,seed=29)
            for row in rows:row['policy']=label;row['selected_policy']=policy['id'];seed_rows.append(row)
        print('SEED29 COMPLETE',o,'fit_count',sum(budget.used.values()),flush=True)
    table('metrics/seed29.csv',seed_rows)
    # Policy locked from INNER results before any outer evaluation; exactly <=1 final fit.
    final=train_model(train,final_policy,12,budget,'final','fulltrain/final_locked_policy');persist_model(final,'models/final',final_policy,12)
    save('models/final/input_recipe.json',{'train_sha256':sha(ROOT/'outputs/validation/train_exclude_3.json'),'candidate_sha256':sha(ROOT/'outputs/improvement/candidates.json'),'catalog_sha256':sha(ROOT/'Term-project-datasets/fra_cleaned.csv'),'policy_lock_sha256':sha(OUT/'configs/selections_locked.json')})
    for key,model in budget.cache.items():
        # Baseline probes/refits also retained privately for fit/accounting reconstruction.
        policy={'id':'fit-cache','content':'neutral','training_only':True};persist_model(model,f'models/cache/{key}',policy,model.seed)
    after=snapshot();changed=[p for p,h in before['sha256'].items() if after['sha256'].get(p)!=h];stat=[p for p,s in before['stat_only'].items() if after['stat_only'].get(p)!=s];assert not changed,changed;assert not stat,stat;guard()
    save('diagnostics/integrity_after.json',{'old_sha_changed':changed,'old_data_results_web_stat_changed':stat,'protected19_match':True,'manifest_sha256':sha(ROOT/'outputs/final/freeze.json')})
    save('configs/run_complete.json',{'seconds':time.perf_counter()-start,'actual_mf_fits':sum(budget.used.values()),'phase_counts':budget.used,'cache_hits':len(budget.reuses),'caps':SETTINGS['caps'],'final_policy':final_policy['id'],'python':platform.python_version(),'numpy':np.__version__,'legacy_validation_test_not_opened':True,'permitted_legacy_reads':dict(READS),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in Path(__file__).parent.glob('*.py')}})
    print('COMPLETE actual_fits',sum(budget.used.values()),budget.used,'final',final_policy['id'],flush=True)
if __name__=='__main__':main()
