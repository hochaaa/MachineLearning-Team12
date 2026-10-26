"""STEP6 fixed-setting diagnostic reconstruction: no tuning, no legacy validation/Test access.

All algorithms imported unchanged. New outputs only in hybrid_failure_step6.
"""
import sys,os,json,csv,time,hashlib,subprocess
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE))
from data import ROOT,OUT,guard,sha,bundle,histories,known_folds,newuser_folds
from config import MF_GRID,CONTENT_GRID
from content_v2 import ContentV2
from mf_v2 import train_mf
from foldin_v2 import fold_in,score_vector
from evaluate_v2 import component_scores,evaluate_arrays
from hybrid_v2 import combine,ranked,rank_scores
from perfume.evaluation import evaluate,ranking_metrics
DOUT=OUT/'diagnostics/hybrid_failure_step6'
READS=Counter()

def save(name,value):
    """New diagnostic directory only; never overwrite any prior result."""
    p=DOUT/name
    if p.exists():raise RuntimeError('Refuse overwrite: '+name)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2))

def table(name,rows):
    p=DOUT/name
    if p.exists():raise RuntimeError('Refuse overwrite: '+name)
    if rows:
        with p.open('w',newline='') as f:
            keys=sorted(set().union(*(r.keys() for r in rows)));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def load(rel):return json.loads((ROOT/rel).read_text())

def deny_legacy(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
    p=Path(os.fsdecode(args[0])).resolve()
    if p==ROOT/'outputs/improvement/validation.json':raise PermissionError('STEP6: no legacy validation answers')
    if ROOT/'outputs/final' in p.parents and p.name not in {'freeze.json','model.json','model.npz','content.json'}:raise PermissionError('STEP6: no legacy final answers/results')
    if ROOT/'outputs/validation' in p.parents and p.name!='train_exclude_3.json':raise PermissionError('STEP6: no legacy split/answer files')
    if p.parent==ROOT/'Term-project-datasets' and p.name!='fra_cleaned.csv':raise PermissionError('STEP6: no raw user/external records')
    if p.parent==ROOT/'outputs/improvement' and p.name not in {'candidates.json','selection.json'}:raise PermissionError('STEP6: only train source/candidate metadata')
    if ROOT/'outputs' in p.parents and DOUT not in p.parents:READS[str(p.relative_to(ROOT))]+=1

def snapshot():
    """Hash V1 protected/source and all old V2 files; stat-only forbidden data/results."""
    tracked=[s.decode() for s in subprocess.check_output(['git','ls-files','-z']).split(b'\0') if s]
    f=load('outputs/final/freeze.json');paths=set(tracked)|set(f['protected_sha256'])|{'outputs/final/freeze.json'}
    for folder in [BASE,OUT]:
        for p in folder.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or BASE/'diagnostics' in p.parents or DOUT in p.parents:continue
            paths.add(str(p.relative_to(ROOT)))
    stats={}
    for folder in [ROOT/'Term-project-datasets',ROOT/'outputs/final',ROOT/'outputs/validation',ROOT/'web']:
        for p in folder.rglob('*'):
            if p.is_file() and not set(p.parts)&{'.venv','node_modules','dist','__pycache__','.state','logs'}:
                st=p.stat();stats[str(p.relative_to(ROOT))]={'size':st.st_size,'mtime_ns':st.st_mtime_ns}
    return {'sha256':{p:sha(ROOT/p) for p in sorted(paths)},'stat_only':stats}

def avg_rank(values):
    """Average ties for Spearman; differs intentionally from production ID-ordered ranks."""
    v=np.asarray(values);order=np.argsort(v,kind='stable');r=np.empty(len(v),dtype=float);start=0
    while start<len(v):
        end=start+1
        while end<len(v) and v[order[end]]==v[order[start]]:end+=1
        r[order[start:end]]=(start+end-1)/2+1;start=end
    return r

def spearman(c,m):
    valid=np.isfinite(c)&np.isfinite(m)
    if valid.sum()<2:return None
    a,b=avg_rank(c[valid]),avg_rank(m[valid])
    return float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else None

def jaccard(a,b):return len(set(a)&set(b))/len(set(a)|set(b)) if a or b else None

def score_stats(v):
    x=np.asarray(v);x=x[np.isfinite(x)]
    if not len(x):return {'finite':0}
    _,counts=np.unique(x,return_counts=True)
    return {'finite':len(x),'mean':float(x.mean()),'sd':float(x.std()),'min':float(x.min()),'max':float(x.max()),'clip_boundary_fraction':float(np.mean((x==0)|(x==1))),'duplicate_score_fraction':1-len(counts)/len(x),'largest_tie_fraction':float(counts.max()/len(x))}

def coverage(pred,pool,catalog):
    """All scored-user Top10 exposures; Gini/entropy include zero-frequency eligible items."""
    counts=Counter(i for r in pred.values() for i in r[:10]);x=np.array([counts[i] for i in pool],dtype=float);total=x.sum();prob=x[x>0]/total if total else np.array([]);sortedx=np.sort(x);n=len(x)
    gin=float(np.sum((2*np.arange(1,n+1)-n-1)*sortedx)/(n*total)) if total and n else None
    divers=[]
    for ranking in pred.values():
        top=ranking[:10];pairs=[]
        for i,a in enumerate(top):
            for b in top[i+1:]:
                aa,bb=set(catalog[a]['tokens']),set(catalog[b]['tokens']);pairs.append(1-len(aa&bb)/len(aa|bb) if aa|bb else 0.)
        if pairs:divers.append(float(np.mean(pairs)))
    return {'users':len(pred),'candidate_pool':len(pool),'unique_top5':len({i for r in pred.values() for i in r[:5]}),'unique_top10':len(counts),'catalog_coverage':len(counts)/len(pool),'mean_user_unique_top10':float(np.mean([len(set(r[:10])) for r in pred.values()])),'max_item_slot_share':float(x.max()/total) if total else None,'max_item_request_incidence':float(x.max()/len(pred)) if pred else None,'top10_item_slot_share':sum(v for _,v in counts.most_common(10))/total if total else None,'gini':gin,'entropy_bits':float(-np.sum(prob*np.log2(prob))) if total else None,'mean_intralist_token_diversity':float(np.mean(divers)) if divers else None},counts

def cluster_bootstrap(differences,users,folds=3,seed=12,draws=3000):
    """Resample users jointly across folds; reproduce primary unweighted fold-macro delta."""
    users=sorted(users);matrix=np.full((len(users),folds),np.nan)
    for n,u in enumerate(users):
        for f,v in differences.get(u,{}).items():matrix[n,f]=v
    rng=np.random.default_rng(seed);boots=[]
    for _ in range(draws):
        m=matrix[rng.integers(len(users),size=len(users))];means=np.nanmean(m,axis=0);boots.append(float(np.mean(means)))
    usermeans=np.array([np.nanmean(v) for v in matrix if np.isfinite(v).any()]);primary=float(np.mean(np.nanmean(matrix,axis=0)))
    return {'cluster_users_including_no_positive':len(users),'users_with_positive':len(usermeans),'fold_macro_delta':primary,'interval_low':float(np.quantile(boots,.025)),'interval_high':float(np.quantile(boots,.975)),'draws':draws,'user_mean_delta_quantiles':list(map(float,np.quantile(usermeans,[0,.25,.5,.75,1]))),'user_positive_delta_fraction':float(np.mean(usermeans>0)),'user_negative_delta_fraction':float(np.mean(usermeans<0)),'method':'paired user cluster bootstrap; missing no-positive fold cells excluded as original metric; descriptive post-selection only'}

def metric_parity():
    """Synthetic reference formula/aggregator equivalence; no historical labels."""
    pred={'a':{'x':['b','a']},'z':{'x':['a','b']}};answers=[('a','a',.8),('z','a',.2)]
    s,_=evaluate(pred,answers,k=10,relevance=.7);v,_=evaluate_arrays({u:m['x'] for u,m in pred.items()},answers)
    for key in ['precision','recall','ndcg','positive_users','no_positive_users','evaluation_users']:assert np.isclose(s[0][key],v[key])
    assert np.isclose(v['ndcg'],1/np.log2(3));assert v['positive_users']==1
    assert np.isclose(rank_scores([.5,.5],['a','b'])[0],1.)
    assert rank_scores([.5,.5],['a','b'])[0]>rank_scores([.5,.5],['a','b'])[1]
    return {'synthetic_metric_parity':True,'manual_ndcg':float(1/np.log2(3)),'positive_denominator':1,'rank_tie_rule':'canonical ID; production RRF ordinal ranks, diagnostic Spearman average ties'}

def main():
    guard()
    if (DOUT/'started.json').exists():raise RuntimeError('STEP6 diagnostic already attempted; do not overwrite')
    save('started.json',{'scope':'fixed-setting diagnostics only','tuning':False,'legacy_validation_access':False,'legacy_test_access':False})
    before=snapshot();save('before_integrity.json',before);sys.addaudithook(deny_legacy);start=time.perf_counter()
    original=load('outputs/development_v2/metrics/final_comparison.json');sel=load('outputs/development_v2/models/model.json')['config'];loss=load('outputs/development_v2/diagnostics/loss_curves.json')
    name=sel['selected_recipe']['name'];cfgc=sel['content_config'];cfgm=sel['mf_config'];ridge=sel['foldin_regularization'];v1c=CONTENT_GRID[0];v1m=MF_GRID[0]
    save('metric_parity.json',metric_parity())
    train,pool,catalog,raw=bundle();protocols=[]
    for f,fit,answer in known_folds(train):
        supports={u:histories(fit)[u] for u,_,_ in answer};protocols.append(('known',f,fit,pool,supports,answer,{}))
    for f,fit,p,sp,a,excluded,held in newuser_folds(train,pool):protocols.append(('newuser',f,fit,p,sp,a,excluded))
    summaries=[];relations=[];distributions=[];bias_stats=[];frequency=[];metric_rows=[];replay=[];diffs=defaultdict(lambda:defaultdict(dict));clusters=defaultdict(set);replaymodel=[]
    for protocol,fold,fit,p,supports,answers,excluded in protocols:
        # Fixed original models. Known fold epochs recovered from STEP5 saved curves.
        if protocol=='known':
            epochs=next(r['epochs'] for r in loss if r['fold']==fold and r['name']==cfgm['name']);fixed=dict(cfgm,epochs=epochs,early=False)
        else:
            # Fold models were not saved in STEP5; deterministic exact replay of original
            # nested-stop procedure is reconstruction, not a new grid/settings search.
            fixed=dict(cfgm)
        models=[train_mf(fit,v1m,12),train_mf(fit,fixed,12)]
        contents=[ContentV2(c).fit(catalog,raw,{i for _,i,_ in fit}) for c in [v1c,cfgc]]
        caches=[]
        for version,(model,content) in enumerate(zip(models,contents),1):
            reg=None if protocol=='known' else (.01 if version==1 else ridge)
            cache,_=component_scores(model,content,fit,p,supports,reg);caches.append(cache)
        replaymodel.append({'protocol':protocol,'fold':fold,'v1_epochs':models[0].best_epoch,'v2_epochs':models[1].best_epoch,'v2_reg':models[1].config['regularization'],'foldin_reg':None if protocol=='known' else ridge,'nested_stop_replay':protocol=='newuser','support_users':len(supports),'excluded':excluded})
        predictions={label:{} for label in ['V1C','V1M','V1H','V1RRF_counterfactual','V2C','V2M','V2H','V2Linear_counterfactual']};fallback=Counter()
        for u in sorted(supports):
            assert caches[0][u][0]==caches[1][u][0]
            p0,c1,m1,b,n=caches[0][u];_,c2,m2,_,_=caches[1][u]
            variants=[('V1C',c1),('V1M',m1),('V2C',c2),('V2M',m2)]
            for label,c,m,method in [('V1H',c1,m1,'linear'),('V1RRF_counterfactual',c1,m1,'rrf'),('V2H',c2,m2,'rrf'),('V2Linear_counterfactual',c2,m2,'linear')]:
                values,fb=combine(c,m,b,p0,{'method':method,'alpha':.25},n);variants.append((label,values));fallback[label]+=fb['popularity_fallback']
            for label,values in variants:predictions[label][u]=ranked(p0,values)
            for version,c,m in [(1,c1,m1),(2,c2,m2)]:
                ctop=ranked(p0,c);mtop=ranked(p0,m);rrftop=predictions['V1RRF_counterfactual' if version==1 else 'V2H'][u];lineartop=predictions['V1H' if version==1 else 'V2Linear_counterfactual'][u]
                relations.append({'protocol':protocol,'fold':fold,'version':version,'spearman':spearman(c,m),'component_top10_overlap_fraction':len(set(ctop)&set(mtop))/10,'linear_rrf_top10_jaccard':jaccard(lineartop,rrftop),'mf_top10_displaced_by_rrf':1-len(set(mtop)&set(rrftop))/10,'content_top10_displaced_by_rrf':1-len(set(ctop)&set(rrftop))/10,'unseen_candidates':len(p0)})
                for component,v in [('C',c),('M',m)]:distributions.append({'protocol':protocol,'fold':fold,'version':version,'component':component,**score_stats(v)})
            model=models[1];indices=np.array([model.items[i] for i in p0 if i in model.items])
            if protocol=='known':z=np.r_[model.P[model.users[u]],model.bu[model.users[u]]]
            else:z=fold_in(model,supports[u],ridge)
            if z is not None:
                latent=model.Q[indices]@z[:-1];itembias=model.bi[indices];rawpred=model.mean+z[-1]+itembias+latent
                bias_stats.append({'protocol':protocol,'fold':fold,'support_mean':float(np.mean([r for _,r in supports[u]])),'support_std':float(np.std([r for _,r in supports[u]])),'latent_sd':float(np.std(latent)),'item_bias_sd':float(np.std(itembias)),'latent_to_itembias_sd':float(np.std(latent)/np.std(itembias)) if np.std(itembias)>0 else None,'mf_itembias_spearman':spearman(rawpred,itembias),'user_bias':float(z[-1]),'clip_boundary_fraction':float(np.mean((rawpred<=0)|(rawpred>=1)))})
        per={}
        for label,pred in predictions.items():
            s,per[label]=evaluate_arrays(pred,answers);metric_rows.append({'protocol':protocol,'fold':fold,'model':label,**s})
            cv,counts=coverage(pred,p,catalog);summaries.append({'protocol':protocol,'fold':fold,'model':label,'popularity_fallback_slots':fallback[label],**cv})
            for item,count in counts.most_common(15):frequency.append({'protocol':protocol,'fold':fold,'model':label,'brand':catalog[item]['brand'],'name':catalog[item]['name'],'top10_exposures':count,'request_incidence':count/len(pred),'slot_share':count/sum(counts.values())})
        clusters[protocol].update(supports)
        assert set(per['V1H'])==set(per['V2H'])
        for u in per['V1H']:diffs[protocol][u][fold]=per['V2H'][u]-per['V1H'][u]
        # Check baseline/chosen metrics reproduced to numerical precision before any inference.
        oldfile='outputs/development_v2/metrics/hybrid_cv.csv' if protocol=='known' else 'outputs/development_v2/metrics/newuser_cv.csv'
        with (ROOT/oldfile).open() as stream:old=list(csv.DictReader(stream))
        for label,oldname in [('V1H','v1_hybrid'),('V2H',name)]:
            target=next(r for r in old if int(r['fold'])==fold and r['name']==oldname and (protocol=='known' or float(r['ridge'])==(.01 if label=='V1H' else ridge)))
            value=next(r['ndcg'] for r in metric_rows if r['protocol']==protocol and r['fold']==fold and r['model']==label)
            assert abs(value-float(target['ndcg']))<1e-12,(protocol,fold,label,value,target['ndcg'])
            replay.append({'protocol':protocol,'fold':fold,'model':label,'stored_ndcg':float(target['ndcg']),'reconstructed_ndcg':value,'absolute_difference':abs(value-float(target['ndcg']))})
        print('Reconstruction matches STEP5',protocol,fold,flush=True)
    table('metrics.csv',metric_rows);table('coverage.csv',summaries);table('rank_conflicts_anonymous.csv',relations);table('score_distributions_anonymous.csv',distributions);table('bias_decomposition_anonymous.csv',bias_stats);table('public_product_frequency.csv',frequency)
    save('replay_checks.json',replay);save('reconstructed_model_receipts.json',replaymodel)
    save('paired_cluster_bootstrap.json',{p:cluster_bootstrap(diffs[p],clusters[p]) for p in diffs})
    aggregate=[]
    for protocol in ['known','newuser']:
        for label in predictions:
            rr=[r for r in summaries if r['protocol']==protocol and r['model']==label];mm=[r for r in metric_rows if r['protocol']==protocol and r['model']==label]
            row={'protocol':protocol,'model':label,'ndcg':float(np.mean([r['ndcg'] for r in mm]))}
            for k in ['unique_top10','catalog_coverage','max_item_request_incidence','top10_item_slot_share','gini','entropy_bits','mean_intralist_token_diversity']:row[k]=float(np.mean([r[k] for r in rr]))
            aggregate.append(row)
    table('aggregate_metrics.csv',aggregate)
    ranking_summary=[]
    for protocol in ['known','newuser']:
        for version in [1,2]:
            rr=[r for r in relations if r['protocol']==protocol and r['version']==version];row={'protocol':protocol,'version':version,'user_fold_rows':len(rr),'spearman_defined_rows':sum(r['spearman'] is not None for r in rr)}
            for key in ['spearman','component_top10_overlap_fraction','linear_rrf_top10_jaccard','mf_top10_displaced_by_rrf','content_top10_displaced_by_rrf']:row[key]=float(np.mean([r[key] for r in rr if r[key] is not None]))
            ranking_summary.append(row)
    table('rank_summary.csv',ranking_summary)
    after=snapshot();changed=[p for p,h in before['sha256'].items() if after['sha256'].get(p)!=h];stat=[p for p,s in before['stat_only'].items() if after['stat_only'].get(p)!=s]
    assert not changed,changed;assert not stat,stat;guard()
    save('integrity.json',{'old_v1_v2_sha_changed':changed,'old_data_results_web_stat_changed':stat,'protected19_match':True,'manifest_sha256':sha(ROOT/'outputs/final/freeze.json'),'original_model_and_config_replaced':False})
    save('complete.json',{'seconds':time.perf_counter()-start,'read_receipts':dict(READS),'legacy_validation_or_test_read':False,'new_tuning_or_selection':False,'same_component_linear_vs_rrf':'fixed alpha.25 diagnostic counterfactual only; not recommended/reselected model','source_sha256':sha(Path(__file__))})
    print('STEP6 COMPLETE',flush=True)
if __name__=='__main__':main()
