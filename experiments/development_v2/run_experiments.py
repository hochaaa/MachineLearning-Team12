"""Training-internal CV search; locks shortlist BEFORE one-shot legacy validation."""
import sys,time,json,csv,platform,subprocess,copy,os
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from data import ROOT,OUT,INPUTS,read_input,write,guard,sha,bundle,histories,known_folds,newuser_folds
from config import *
from content_v2 import ContentV2
from mf_v2 import train_mf
from evaluate_v2 import component_scores,predictions,evaluate_arrays,paired_interval

READS=Counter()
def access_policy(event,args):
    """Block old answer/results files even if accidentally requested by a future code path."""
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
    path=Path(os.fsdecode(args[0])).resolve()
    final=ROOT/'outputs/final'
    if final in path.parents and path.name not in {'freeze.json','model.npz','model.json','content.json'}:raise PermissionError('V2 cannot open legacy final answers/results')
    if path.parent==ROOT/'Term-project-datasets' and path.name!='fra_cleaned.csv':raise PermissionError('V2 train only: no raw interaction/external files')
    legacy=ROOT/'outputs/validation'
    if legacy in path.parents and path.name!='train_exclude_3.json':raise PermissionError('V2 cannot read legacy splits/answers/results')
    if path.parent==ROOT/'outputs/improvement' and path.name not in {'candidates.json','validation.json','selection.json'}:raise PermissionError('V2 cannot read legacy improvement artifacts')
    if str(path).startswith(str(ROOT/'outputs')) and OUT not in path.parents:READS[str(path.relative_to(ROOT))]+=1

def table(path,rows):
    target=OUT/path;target.parent.mkdir(parents=True,exist_ok=True)
    if rows:
        keys=sorted(set().union(*(r.keys() for r in rows)))
        with target.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def aggregate(rows):
    """Mean fold score, explicit sum positive denominators; not pooled independent users."""
    valid=[r['ndcg'] for r in rows if r.get('ndcg') is not None]
    return float(np.mean(valid)) if valid else -1.

def top_names(rows,limit=2,exclude=()):
    names=sorted({r['name'] for r in rows}-set(exclude));return sorted(names,key=lambda name:(-aggregate([r for r in rows if r['name']==name]),name))[:limit]

def snapshot():
    """Hash tracked V1 code and protected19; stat forbidden data/results without opening them."""
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0');files=[p.decode() for p in tracked if p]
    protected=json.loads((ROOT/'outputs/final/freeze.json').read_text())['protected_sha256']
    hashed={p:sha(ROOT/p) for p in sorted(set(files)|set(protected)|{'outputs/final/freeze.json'})}
    stats={}
    for folder in [ROOT/'Term-project-datasets',ROOT/'outputs/final',ROOT/'outputs/validation',ROOT/'web']:
        for p in folder.rglob('*'):
            if p.is_file() and not set(p.parts)&{'.venv','node_modules','__pycache__','dist','.state','logs'}:
                st=p.stat();stats[str(p.relative_to(ROOT))]={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
    return {'sha256':hashed,'stat_only':stats}

def record_row(stage,fold,name,cache,answers,kind='hybrid',fusion=None,**more):
    pred,fb=predictions(cache,kind,fusion);s,per=evaluate_arrays(pred,answers)
    return {'stage':stage,'fold':fold,'name':name,**more,**s,**fb},per

def save_model(model,content,config):
    """Private V2 model bundle; all output stays ignored and cannot replace V1."""
    biased=hasattr(model,'bu')
    arrays={'P':model.P,'Q':model.Q}
    if biased:arrays.update(bu=model.bu,bi=model.bi)
    np.savez(OUT/'models/model.npz',**arrays)
    write('models/model.json',{'users':model.users,'items':model.items,'mean':getattr(model,'mean',None),'biased':biased,'mf_config':model.config,'config':config})
    # Content is rebuilt deterministically from allowed train metadata on load; never pickle.
    write('models/content_recipe.json',{'config':content.config,'train_only_idf':True,'input_hashes':{k:sha(ROOT/INPUTS[k]) for k in ['train','catalog','candidates']}})

def main():
    guard()
    if (OUT/'experiments/run_started.json').exists():raise RuntimeError('Refuse overwrite/re-tune completed or attempted V2 run; inspect existing receipts')
    write('experiments/run_started.json',{'seed':SEED,'content_grid':CONTENT_GRID,'mf_grid':MF_GRID,'hybrid_grid':HYBRID_GRID,'foldin_reg':FOLDIN_REG,'selection_policy':'known-user3fold NDCG selects components and shortlist; new-user user-CV selects ridge; legacy validation does not select/retune','legacy_test_access':'DENIED'})
    before=snapshot();write('audit/integrity_before.json',before)
    sys.addaudithook(access_policy)
    start=time.perf_counter();train,pool,catalog,raw=bundle();h=histories(train)
    write('audit/input_contract.json',{'train_rows':len(train),'users':len(h),'items':len({i for _,i,_ in train}),'candidates':len(pool),'support3_eligible':sum(len(v)>=4 for v in h.values()),'input_sha256':{k:sha(ROOT/INPUTS[k]) for k in ['train','catalog','candidates']},'python':platform.python_version(),'numpy':np.__version__,'git_base':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()})
    folds=list(known_folds(train,FOLDS,SEED));fold_receipts=[];content_rows=[];mf_rows=[];content_cache={};mf_cache={};losses=[]
    for fold,fit,answers in folds:
        supports={u:histories(fit)[u] for u,_,_ in answers};fititems={i for _,i,_ in fit}
        fold_receipts.append({'protocol':'known-user','fold':fold,'train_users':len({u for u,_,_ in fit}),'train_items':len(fititems),'train_ratings':len(fit),'evaluation_users':len(supports),'heldout_ratings':len(answers),'positive_users':len({u for u,_,r in answers if r>=.7}),'candidates':len(pool),'trained_candidate_items':len(set(pool)&fititems),'min_eval_train':min(len(v) for v in supports.values()),'excluded_low_history_users':len(h)-len(supports),'outside_candidate_positive':sum(r>=.7 and i not in pool for _,i,r in answers)})
        for cfg in CONTENT_GRID:
            c=ContentV2(cfg).fit(catalog,raw,fititems);cache,_=component_scores(None,c,fit,pool,supports)
            content_cache[fold,cfg['name']]=cache
            row,_=record_row('content_cv',fold,cfg['name'],cache,answers,'content');content_rows.append(row)
        for cfg in MF_GRID:
            m=train_mf(fit,cfg,SEED);cache,_=component_scores(m,None,fit,pool,supports);mf_cache[fold,cfg['name']]=cache
            row,_=record_row('mf_cv',fold,cfg['name'],cache,answers,'mf',epochs=m.best_epoch);mf_rows.append(row)
            losses.append({'fold':fold,'name':cfg['name'],'epochs':m.best_epoch,'nested_stop':getattr(m,'stop_curve',[]),'fit_curve':getattr(m,'curve',[]),'factor_norm':float(np.linalg.norm(m.Q)),'finite':bool(np.isfinite(m.Q).all())})
            print('CV',fold,cfg['name'],m.best_epoch,row['ndcg'],flush=True)
    table('metrics/content_cv.csv',content_rows);table('metrics/mf_cv.csv',mf_rows);write('diagnostics/loss_curves.json',losses)
    selected_c=top_names(content_rows,2,exclude=['v1_content']);selected_m=top_names(mf_rows,2,exclude=['v1_mf'])
    # Only top2 components from train-CV enter fusion (plus explicit V1 baseline).
    hybrid_rows=[];hybrid_per=defaultdict(lambda:defaultdict(list));diagnostics=[]
    recipes=[{'name':'v1_hybrid','content':'v1_content','mf':'v1_mf','fusion':{'method':'linear','alpha':.25}}]
    recipes += [{'name':f'{c}__{m}__{f["name"]}','content':c,'mf':m,'fusion':f} for c in selected_c for m in selected_m for f in HYBRID_GRID]
    for fold,fit,answers in folds:
        for recipe in recipes:
            cc=content_cache[fold,recipe['content']];mm=mf_cache[fold,recipe['mf']]
            cache={u:(cc[u][0],cc[u][1],mm[u][2],cc[u][3],cc[u][4]) for u in cc}
            row,per=record_row('hybrid_cv',fold,recipe['name'],cache,answers,fusion=recipe['fusion']);hybrid_rows.append(row)
            for u,x in per.items():hybrid_per[recipe['name']][u].append(x)
            if recipe['name']=='v1_hybrid':
                for u,(ids,c,m,b,n) in cache.items():diagnostics.append({'fold':fold,'content_sd':float(np.nanstd(c)),'mf_sd':float(np.nanstd(m)),'content_weighted_sd':float(.25*np.nanstd(c)),'mf_weighted_sd':float(.75*np.nanstd(m)),'mf_clipped_fraction':float(np.mean((m==0)|(m==1)))})
    table('metrics/hybrid_cv.csv',hybrid_rows);table('diagnostics/v1_score_distributions.csv',diagnostics)
    top=top_names(hybrid_rows,2,exclude=['v1_hybrid']);recipe_lookup={r['name']:r for r in recipes};shortlist=[recipe_lookup[n] for n in top];chosen=shortlist[0]
    c_lookup={c['name']:c for c in CONTENT_GRID};m_lookup={m['name']:m for m in MF_GRID}
    # Entire-user holdout, actual3 support; compare baseline + the fixed two hybrid candidates.
    nu_rows=[];nu_recipes=[recipes[0],*shortlist]
    for fold,fit,nupool,supports,answers,excluded,held_users in newuser_folds(train,pool,FOLDS,SEED):
        fold_receipts.append({'protocol':'new-user-support3','fold':fold,'train_users':len({u for u,_,_ in fit}),'train_items':len({i for _,i,_ in fit}),'train_ratings':len(fit),'held_users_before_item_coverage':held_users,'evaluation_users':len(supports),'heldout_ratings':len(answers),'positive_users':len({u for u,_,r in answers if r>=.7}),'candidates':len(nupool),'excluded':excluded,'support_per_user':3,'training_user_overlap':0})
        models={};contents={}
        for recipe in nu_recipes:
            mn=recipe['mf'];cn=recipe['content']
            if mn not in models:models[mn]=train_mf(fit,m_lookup[mn],SEED)
            if cn not in contents:contents[cn]=ContentV2(c_lookup[cn]).fit(catalog,raw,{i for _,i,_ in fit})
            for reg in ([.01] if recipe['name']=='v1_hybrid' else FOLDIN_REG):
                model=models[mn];q=model.Q.copy();cache,_=component_scores(model,contents[cn],fit,nupool,supports,reg);assert np.array_equal(q,model.Q)
                row,_=record_row('newuser_cv',fold,recipe['name'],cache,answers,fusion=recipe['fusion'],ridge=reg);nu_rows.append(row)
                if True:
                    for kind in (['content','mf'] if reg==.01 else ['mf']):
                        label=('v1_' if recipe['name']=='v1_hybrid' else recipe['name']+'__')+kind
                        r,_=record_row('newuser_cv',fold,label,cache,answers,kind,ridge=reg);nu_rows.append(r)
        print('New-user fold',fold,'evaluated',len(supports),'excluded',excluded,flush=True)
    table('metrics/newuser_cv.csv',nu_rows);write('audit/fold_receipts.json',fold_receipts)
    ridge_by_recipe={}
    for r in shortlist:
        ridge_by_recipe[r['name']]=max(FOLDIN_REG,key=lambda reg:(aggregate([v for v in nu_rows if v['name']==r['name'] and v['ridge']==reg]),-reg))
    # Primary recipe fixed by known-user CV, ridge fixed by user-group CV. No validation-driven choice.
    selection={'selected_recipe':chosen,'shortlist':shortlist,'ridge_by_recipe':ridge_by_recipe,'content_config':c_lookup[chosen['content']],'mf_config':m_lookup[chosen['mf']],'seed':SEED,'selection':'primary recipe known-user CV only; ridge user-heldoutCV only; no legacy validation selection','test_access':'not used'}
    write('experiments/selection_locked.json',selection)
    cv_users={name:{u:float(np.mean(v)) for u,v in users.items()} for name,users in hybrid_per.items()}
    write('diagnostics/cv_paired_bootstrap.json',paired_interval(cv_users['v1_hybrid'],cv_users[chosen['name']]))
    # Seed stability is diagnostic with chosen recipe fixed, never a new parameter search.
    stability=[]
    for seed in STABILITY_SEEDS:
        for fold,fit,answers in folds:
            supports={u:histories(fit)[u] for u,_,_ in answers}
            for recipe in [recipes[0],chosen]:
                model=train_mf(fit,m_lookup[recipe['mf']],seed);content=ContentV2(c_lookup[recipe['content']]).fit(catalog,raw,{i for _,i,_ in fit})
                cache,_=component_scores(model,content,fit,pool,supports);r,_=record_row('seed_stability',fold,recipe['name'],cache,answers,fusion=recipe['fusion'],seed=seed);stability.append(r)
        print('Stability seed complete',seed,flush=True)
    table('metrics/seed_stability.csv',stability)
    # Legacy validation opened exactly after selection receipt; a one-shot ledger prevents repeated tuning.
    with (OUT/'experiments/legacy_validation_started.json').open('x') as f:json.dump({'selection_sha256':sha(OUT/'experiments/selection_locked.json')},f)
    answers=[tuple(r) for r in read_input('validation')];supports={u:h[u] for u,_,_ in answers};rows=[];val_per={};full_models={};full_contents={}
    for recipe in [recipes[0],*shortlist]:
        mn,cn=recipe['mf'],recipe['content']
        if mn not in full_models:full_models[mn]=train_mf(train,m_lookup[mn],SEED)
        if cn not in full_contents:full_contents[cn]=ContentV2(c_lookup[cn]).fit(catalog,raw,{i for _,i,_ in train})
        cache,_=component_scores(full_models[mn],full_contents[cn],train,pool,supports)
        r,per=record_row('legacy_validation',-1,recipe['name'],cache,answers,fusion=recipe['fusion']);rows.append(r);val_per[recipe['name']]=per
        for kind in ['content','mf']:
            r,_=record_row('legacy_validation',-1,recipe['content'] if kind=='content' else recipe['mf'],cache,answers,kind);rows.append(r)
        if recipe['name']=='v1_hybrid':r,_=record_row('legacy_validation',-1,'popularity',cache,answers,'popularity');rows.append(r)
    table('metrics/legacy_validation.csv',rows);write('diagnostics/validation_paired_bootstrap.json',paired_interval(val_per['v1_hybrid'],val_per[chosen['name']]))
    model=full_models[chosen['mf']];content=full_contents[chosen['content']];selection['final_epochs']=model.best_epoch;selection['foldin_regularization']=ridge_by_recipe[chosen['name']]
    save_model(model,content,selection)
    table('metrics/summary.csv',[{'model':'V1 Hybrid','known_cv_ndcg':aggregate([r for r in hybrid_rows if r['name']=='v1_hybrid']),'newuser_cv_ndcg':aggregate([r for r in nu_rows if r['name']=='v1_hybrid']),'legacy_validation_ndcg':next(r['ndcg'] for r in rows if r['name']=='v1_hybrid')},{'model':'V2 Hybrid','known_cv_ndcg':aggregate([r for r in hybrid_rows if r['name']==chosen['name']]),'newuser_cv_ndcg':aggregate([r for r in nu_rows if r['name']==chosen['name'] and r['ridge']==selection['foldin_regularization']]),'legacy_validation_ndcg':next(r['ndcg'] for r in rows if r['name']==chosen['name'])}])
    after=snapshot();write('audit/integrity_after.json',{'protected_and_tracked_unchanged':before['sha256']==after['sha256'],'changed_sha_paths':[p for p,h in before['sha256'].items() if after['sha256'].get(p)!=h],'stat_changed_paths':[p for p,v in before['stat_only'].items() if after['stat_only'].get(p)!=v],'test_files_content_read':False})
    guard();write('experiments/run_complete.json',{'seconds':time.perf_counter()-start,'permitted_legacy_output_reads':dict(READS),'config_hash':sha(Path(__file__).parent/'config.py'),'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in Path(__file__).parent.glob('*.py')},'validation_selection_locked_before_read':True,'internal_external_tests_not_opened':True})
    print('COMPLETE',selection,flush=True)
if __name__=='__main__':main()
