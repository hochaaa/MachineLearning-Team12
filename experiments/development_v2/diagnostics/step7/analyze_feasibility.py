"""STEP7: immutable-model/train-only feasibility, zero fitting or new model implementation."""
import sys,os,json,csv,subprocess,time
from pathlib import Path
from collections import Counter,defaultdict
from types import SimpleNamespace
import numpy as np
DIAG=Path(__file__).resolve().parents[1];BASE=DIAG.parent;sys.path.insert(0,str(DIAG));sys.path.insert(0,str(BASE))
from failure_diagnosis import guard,snapshot,sha,ROOT,OUT,avg_rank,spearman,ranked
from data import bundle,histories,hashed
from foldin_v2 import fold_in,score_vector
DEST=OUT/'diagnostics/step7'
READS=Counter();TRAIN_CALLS=0

def save(name,value):
    path=DEST/name
    if path.exists():raise RuntimeError('Refuse overwrite '+name)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2))

def table(name,rows):
    path=DEST/name
    if path.exists():raise RuntimeError('Refuse overwrite '+name)
    if rows:
        with path.open('w',newline='') as f:
            keys=sorted(set().union(*(r.keys() for r in rows)));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def describe(values):
    a=np.asarray(values,dtype=float)
    return {'n':len(a),'mean':float(a.mean()),'std':float(a.std()),'min':float(a.min()),'p25':float(np.quantile(a,.25)),'median':float(np.median(a)),'p75':float(np.quantile(a,.75)),'max':float(a.max())} if len(a) else {'n':0}

def histogram(values):return {str(k):v for k,v in sorted(Counter(values).items())}

def gini(values):
    x=np.sort(np.asarray(values,dtype=float));return float(np.sum((2*np.arange(1,len(x)+1)-len(x)-1)*x)/(len(x)*x.sum())) if x.sum() else None

def deny(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
    p=Path(os.fsdecode(args[0])).resolve()
    if p==ROOT/'outputs/improvement/validation.json':raise PermissionError('STEP7: validation answers forbidden')
    if ROOT/'outputs/final' in p.parents and p.name not in {'freeze.json','model.npz','model.json','content.json'}:raise PermissionError('STEP7: old test/results forbidden')
    if ROOT/'outputs/validation' in p.parents and p.name!='train_exclude_3.json':raise PermissionError('STEP7: old split/answer forbidden')
    if p.parent==ROOT/'Term-project-datasets' and p.name!='fra_cleaned.csv':raise PermissionError('STEP7: raw interaction/external data forbidden')
    if p.parent==ROOT/'outputs/improvement' and p.name not in {'candidates.json','selection.json'}:raise PermissionError('STEP7: no old tuning/results')
    if ROOT/'outputs' in p.parents and DEST not in p.parents:READS[str(p.relative_to(ROOT))]+=1

def prevent_training(frame,event,arg):
    """Abort any project fit/train_mf call; inference/linear solves are permitted."""
    if event=='call' and frame.f_code.co_name in {'fit','train_mf'}:
        path=Path(frame.f_code.co_filename).resolve()
        if ROOT in path.parents:raise RuntimeError('STEP7 forbids fit/train_mf')

def protected_snapshot():
    s=snapshot()
    # This stage's newly written logs/results are not pre-existing protected artifacts.
    prefix=str(DEST.relative_to(ROOT))+'/'
    s['sha256']={p:h for p,h in s['sha256'].items() if not p.startswith(prefix)}
    # Previous diagnostics are now protected too; exclude only this new STEP7 subtree.
    for p in DIAG.rglob('*'):
        if p.is_file() and Path(__file__).parent not in p.parents and '__pycache__' not in p.parts:s['sha256'][str(p.relative_to(ROOT))]=sha(p)
    return s

def data_analysis(train,catalog):
    h=histories(train);items=defaultdict(list)
    for u,i,r in train:items[i].append(r)
    ratings=[r for _,_,r in train];urows=[]
    for u,v in h.items():
        rr=np.array([r for _,r in v]);brands={catalog[i]['brand'] for i,_ in v};div=[]
        for n,(a,_) in enumerate(v):
            for b,_ in v[n+1:]:
                aa,bb=set(catalog[a]['tokens']),set(catalog[b]['tokens']);div.append(1-len(aa&bb)/len(aa|bb) if aa|bb else 0.)
        urows.append({'count':len(v),'mean':float(rr.mean()),'std':float(rr.std()),'high_fraction':float(np.mean(rr>=.7)),'low_fraction':float(np.mean(rr<=.3)),'same':bool(rr.std()<1e-12),'near_same':bool(rr.std()<=.05),'all_high':bool(np.all(rr>=.7)),'unique_brands':len(brands),'brand_ratio':len(brands)/len(v),'metadata_diversity':float(np.mean(div)) if div else None})
    irows=[{'count':len(v),'mean':float(np.mean(v)),'std':float(np.std(v))} for v in items.values()]
    # Bipartite connected components, with explicit node namespaces.
    parent={}
    def find(x):
        parent.setdefault(x,x)
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for u,i,r in train:parent[find(('u',u))]=find(('i',i))
    groups=defaultdict(lambda:[0,0])
    for x in parent:groups[find(x)][0 if x[0]=='u' else 1]+=1
    pair=Counter();differences=[];users=sorted(h);asdict={u:dict(v) for u,v in h.items()}
    for n,u in enumerate(users):
        for v in users[n+1:]:
            common=asdict[u].keys()&asdict[v].keys();pair[len(common)]+=1
            if len(common)>=2:differences.append(float(np.mean([abs(asdict[u][i]-asdict[v][i]) for i in common])))
    nratings=len(train);counts=sorted([len(v) for v in items.values()],reverse=True)
    result={'users':len(h),'items':len(items),'ratings':nratings,'matrix_shape':[len(h),len(items)],'density':nratings/(len(h)*len(items)),'sparsity':1-nratings/(len(h)*len(items)),'duplicate_pairs':nratings-len({(u,i) for u,i,_ in train}),'rating_distribution':describe(ratings),'rating_histogram':histogram(ratings),'high_ge_07_fraction':sum(r>=.7 for r in ratings)/nratings,'low_le_03_fraction':sum(r<=.3 for r in ratings)/nratings,'user_rating_counts':describe([r['count'] for r in urows]),'user_count_histogram':histogram(r['count'] for r in urows),'item_rating_counts':describe(counts),'item_count_histogram':histogram(counts),'user_mean_rating':describe([r['mean'] for r in urows]),'user_rating_std':describe([r['std'] for r in urows]),'user_high_fraction':describe([r['high_fraction'] for r in urows]),'user_low_fraction':describe([r['low_fraction'] for r in urows]),'users_same_rating':sum(r['same'] for r in urows),'users_near_same_std_le_005':sum(r['near_same'] for r in urows),'users_all_high':sum(r['all_high'] for r in urows),'user_unique_brands':describe([r['unique_brands'] for r in urows]),'user_brand_ratio':describe([r['brand_ratio'] for r in urows]),'user_metadata_diversity':describe([r['metadata_diversity'] for r in urows]),'item_mean_rating':describe([r['mean'] for r in irows]),'item_rating_std':describe([r['std'] for r in irows]),'singleton_items':sum(n==1 for n in counts),'longtail_count_le2':sum(n<=2 for n in counts),'longtail_count_le5':sum(n<=5 for n in counts),'interaction_count_gini':gini(counts),'top10_items_rating_share':sum(counts[:10])/nratings,'top20percent_items_rating_share':sum(counts[:int(np.ceil(.2*len(counts)))])/nratings,'graph_components':len(groups),'component_user_item_sizes':sorted(groups.values(),key=lambda z:-sum(z)),'coobserved_item_count_per_user_pair':dict(sorted(pair.items())),'user_pairs_with_ge2_overlap':sum(v for k,v in pair.items() if k>=2),'coobserved_ge2_mean_absolute_rating_difference':describe(differences),'note_coverage_train_items':sum(any(t.startswith('note:') for t in catalog[i]['tokens']) for i in items)/len(items),'accord_coverage_train_items':sum(any(t.startswith('accord:') for t in catalog[i]['tokens']) for i in items)/len(items)}
    return result,h,items

def load_fixed_model():
    path=OUT/'models';meta=json.loads((path/'model.json').read_text());arrays={}
    with np.load(path/'model.npz',allow_pickle=False) as z:
        for k in z.files:arrays[k]=z[k].copy();arrays[k].flags.writeable=False
    return SimpleNamespace(**arrays,users=meta['users'],items=meta['items'],mean=meta['mean'],config=meta['mf_config']),meta

def model_analysis(model,meta,train,pool,h,items):
    bi=model.bi;all_lat=[];all_abs_lat=[];per=[];biaspred={};fullpred={};changed=0;pairjac=[]
    for u,support in h.items():
        us=model.users[u];p=[i for i in pool if i not in dict(support)];idx=np.array([model.items[i] for i in p]);latent=model.Q[idx]@model.P[us];bias=model.bi[idx];raw=model.mean+model.bu[us]+bias+latent;clipped=np.clip(raw,0,1)
        ib=ranked(p,bias);full=ranked(p,clipped);biaspred[u]=set(ib);fullpred[u]=set(full);changed+=ib!=full
        per.append({'latent_mean':float(latent.mean()),'latent_sd':float(latent.std()),'bias_sd':float(bias.std()),'latent_bias_sd_ratio':float(latent.std()/bias.std()) if bias.std() else None,'rank_corr_raw_with_bias':spearman(raw,bias),'rank_corr_clipped_with_bias':spearman(clipped,bias),'top10_jaccard_bias_full':len(set(ib)&set(full))/len(set(ib)|set(full)),'top10_set_changed':set(ib)!=set(full),'top10_order_changed':ib!=full,'mean_abs_ordinal_rank_shift':float(np.mean(np.abs(avg_rank(raw)-avg_rank(bias))))})
        all_lat.extend(latent.tolist());all_abs_lat.extend(np.abs(latent).tolist())
    values=list(fullpred.values())
    for n,a in enumerate(values):
        for b in values[n+1:]:pairjac.append(len(a&b)/len(a|b))
    ids=list(model.items);degree=np.array([len(items[i]) for i in ids]);biasitems=np.array([model.bi[model.items[i]] for i in ids]);meanitems=np.array([np.mean(items[i]) for i in ids]);qnorm=np.array([np.linalg.norm(model.Q[model.items[i]]) for i in ids])
    bands=[]
    for label,mask in [('1',degree==1),('2',degree==2),('3-5',(degree>=3)&(degree<=5)),('6-10',(degree>=6)&(degree<=10)),('>10',degree>10)]:
        bands.append({'observations':label,'items':int(mask.sum()),'mean_abs_bias':float(np.mean(np.abs(biasitems[mask]))) if mask.any() else None,'mean_factor_norm':float(np.mean(qnorm[mask])) if mask.any() else None})
    # Snapshot gradient statistics only, not training or actual optimizer trajectory.
    gp=[];gq=[];gb=[];errors=[]
    reg=model.config['regularization']
    for u,i,r in train:
        a,b=model.users[u],model.items[i];p,q=model.P[a],model.Q[b];e=model.mean+model.bu[a]+model.bi[b]+p@q-r
        gp.append(float(np.sqrt(np.mean((e*q+reg*p)**2))));gq.append(float(np.sqrt(np.mean((e*p+reg*q)**2))));gb.append(abs(e+reg*model.bi[b]));errors.append(e)
    return {'scope':'stored FULL-TRAIN V2 known-user model, not user-heldout CV','mean':model.mean,'actual_epochs':meta['config']['final_epochs'],'factors':model.P.shape[1],'item_bias_signed':describe(bi),'item_bias_absolute':describe(np.abs(bi)),'latent_all_user_candidate_signed':describe(all_lat),'latent_all_user_candidate_absolute':describe(all_abs_lat),'per_user_latent_sd':describe([r['latent_sd'] for r in per]),'per_user_latent_bias_sd_ratio':describe([r['latent_bias_sd_ratio'] for r in per]),'mean_raw_rank_corr_with_bias':float(np.mean([r['rank_corr_raw_with_bias'] for r in per])),'mean_clipped_rank_corr_with_bias':float(np.mean([r['rank_corr_clipped_with_bias'] for r in per])),'top10_order_change_user_fraction':changed/len(h),'top10_set_change_user_fraction':sum(r['top10_set_changed'] for r in per)/len(h),'mean_bias_full_top10_jaccard':float(np.mean([r['top10_jaccard_bias_full'] for r in per])),'mean_ordinal_rank_shift':float(np.mean([r['mean_abs_ordinal_rank_shift'] for r in per])),'interuser_mf_top10_jaccard':describe(pairjac),'bias_vs_item_mean_spearman':spearman(biasitems,meanitems),'abs_bias_vs_degree_spearman':spearman(np.abs(biasitems),degree),'factor_norm_vs_degree_spearman':spearman(qnorm,degree),'degree_bands':bands,'P_row_norms':describe(np.linalg.norm(model.P,axis=1)),'Q_row_norms':describe(np.linalg.norm(model.Q,axis=1)),'user_bias':describe(model.bu),'snapshot_gradient_factor_coordinate_rms':describe(gp+gq),'snapshot_gradient_abs_itembias':describe(gb),'train_raw_rmse_snapshot':float(np.sqrt(np.mean(np.square(errors)))),'gradient_caveat':'final-state gradients only; no learning-speed/trajectory measured; parameters have different units/dimensions'}

def input_sensitivity(model,meta,pool):
    """Synthetic3-support prediction on current full-model ONLY, never a new-user quality CV."""
    ids=pool[:3];idx=[model.items[i] for i in ids];q=model.Q[idx];reg=meta['config']['foldin_regularization'];scenarios={'high':[.9,.9,.9],'low':[.1,.1,.1],'mixed':[.9,.1,.6],'equal':[.5,.5,.5],'zeros':[0.,0.,0.]};rows=[];tops={}
    candidates=[i for i in pool if i not in ids]
    for label,ratings in scenarios.items():
        support=list(zip(ids,ratings));z=fold_in(model,support,reg);scores=score_vector(model,z,candidates);tops[label]=set(ranked(candidates,scores));idxc=[model.items[i] for i in candidates];latent=model.Q[idxc]@z[:-1];bias=model.bi[idxc]
        rows.append({'scenario':label,'support_rating_mean':float(np.mean(ratings)),'support_rating_std':float(np.std(ratings)),'latent_vector_norm':float(np.linalg.norm(z[:-1])),'user_bias':float(z[-1]),'latent_score_sd':float(np.std(latent)),'item_bias_sd':float(np.std(bias)),'mf_bias_spearman':spearman(scores,bias)})
    return {'scope':'synthetic public-item inputs on existing fulltrain model; no heldout, no quality claim','support_count':3,'factors_plus_userbias_unknowns':model.P.shape[1]+1,'maximum_support_equation_rank':3,'support_Q_row_norms':describe(np.linalg.norm(q,axis=1)),'support_Q_singular_values':list(map(float,np.linalg.svd(q,compute_uv=False))),'requests':rows,'high_low_top10_jaccard':len(tops['high']&tops['low'])/len(tops['high']|tops['low']),'unique_top10_sets_among5_scenarios':len({tuple(sorted(v)) for v in tops.values()}),'foldin_regularization':reg}

def planned_split_counts(train,pool,seed=20261109):
    """Blueprint cohort availability only: no factor learning/prediction or model search."""
    h=histories(train);eligible=sorted([u for u,v in h.items() if len(v)>=4],key=lambda u:hashed(seed,'v3outer',u));result=[]
    def counts(fit,held,protocol,fold,inner=None):
        known={i for _,i,_ in fit};metrics=Counter();holdrows=0
        for u in held:
            available=sorted([(i,r) for i,r in h[u] if i in set(pool) and i in known],key=lambda r:hashed(seed,'v3support',u,r[0]))
            history=[(i,r) for i,r in h[u] if i in set(pool)]
            if len(available)<3:metrics['excluded_fewer_than3_known_support']+=1;continue
            if len(history)<4:metrics['excluded_no_heldout_after_support3']+=1;continue
            support={i for i,_ in available[:3]};answer=[(i,r) for i,r in history if i not in support]
            metrics['evaluation_users']+=1;metrics['positive_users']+=any(r>=.7 for _,r in answer);metrics['unknown_factor_heldout']+=sum(i not in known for i,r in answer);holdrows+=len(answer)
        return {'stage':protocol,'outer_fold':fold,'inner_fold':inner,'train_users':len({u for u,_,_ in fit}),'train_ratings':len(fit),'trained_items_assuming_observed_item_factor':len(known),'fixed_candidates':len(pool),'held_users_before_coverage':len(held),'heldout_ratings':holdrows,**dict(metrics)}
    for outer in range(3):
        held=set(eligible[outer::3]);fit=[r for r in train if r[0] not in held];result.append(counts(fit,held,'proposed_outer_confirmation',outer))
        remaining=sorted([u for u in eligible if u not in held],key=lambda u:hashed(seed,'v3inner',outer,u))
        for inner in range(2):
            ih=set(remaining[inner::2]);innerfit=[r for r in fit if r[0] not in ih];result.append(counts(innerfit,ih,'proposed_inner_selection',outer,inner))
    return result

def main():
    guard()
    if (DEST/'started.json').exists():raise RuntimeError('STEP7 already attempted; do not overwrite')
    save('started.json',{'purpose':'feasibility + V3 design only','training_forbidden':True,'new_hyperparameter_search':False})
    before=protected_snapshot();save('integrity_before.json',before);sys.addaudithook(deny);sys.setprofile(prevent_training);start=time.perf_counter()
    train,pool,catalog,raw=bundle();data,h,items=data_analysis(train,catalog);save('train_distribution.json',data)
    model,meta=load_fixed_model();save('fixed_fullmodel_personalization.json',model_analysis(model,meta,train,pool,h,items));save('fixed_fullmodel_synthetic_support3.json',input_sensitivity(model,meta,pool))
    # Historical honest new-user CV evidence only: no missing fold model reconstruction.
    previous=OUT/'diagnostics/hybrid_failure_step6'
    with (previous/'bias_decomposition_anonymous.csv').open() as f:old=list(csv.DictReader(f))
    old=[r for r in old if r['protocol']=='newuser'];ridge=json.loads((previous/'ridge_stability.json').read_text());requests=ridge['per_request_anonymous']
    save('stored_newuser_cv_evidence.json',{'scope':'existing STEP6 held-user fold diagnostics; no retraining/re-evaluation','users':len(old),'latent_bias_sd_ratio_mean':float(np.mean([float(r['latent_to_itembias_sd']) for r in old])),'ratio_definition':'unweighted mean over142 users of SD_candidate(pq)/SD_candidate(bi), not percentage contribution to score/ranking','support_mean':describe([float(r['support_mean']) for r in old]),'support_std':describe([float(r['support_std']) for r in old]),'user_vector_norm':describe([r['user_vector_norm'] for r in requests]),'ridge_user_bias':describe([float(r['user_bias']) for r in old]),'max_condition_number':ridge['max_condition_number'],'fold_support_Q_distribution':'N/A: fold Q arrays not saved; retraining forbidden in STEP7','new_fixed_fold_predictions':'N/A: same reason; only previously saved fold diagnostics reused'})
    plan=planned_split_counts(train,pool);table('proposed_v3_split_feasibility.csv',plan)
    after=protected_snapshot();changed=[p for p,h in before['sha256'].items() if after['sha256'].get(p)!=h];stat=[p for p,v in before['stat_only'].items() if after['stat_only'].get(p)!=v]
    assert not changed,changed;assert not stat,stat;guard()
    save('completion.json',{'seconds':time.perf_counter()-start,'existing_sha_changed':changed,'old_forbidden_data_and_web_stat_changed':stat,'protected19_match':True,'manifest_sha256':sha(ROOT/'outputs/final/freeze.json'),'fit_train_calls':0,'new_hyperparameter_search':False,'read_receipts':dict(READS),'forbidden_validation_test_read':False,'source_sha256':sha(Path(__file__))})
    print('STEP7 analysis complete; ZERO model fitting. Data',data['users'],data['items'],data['ratings'])
if __name__=='__main__':main()
