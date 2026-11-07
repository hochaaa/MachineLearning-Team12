"""Replay frozen40-user CV only, then observational labels/feature analysis."""
import json,csv,sys,os,hashlib
from pathlib import Path
from collections import Counter
from itertools import combinations
from unittest.mock import patch
import numpy as np
from perfume.models import Content,MatrixFactorization,hybrid
from perfume.data import fragrantica
from experiments.scent_v2.mf_cv_optimization.core import ROOT,developer_cohort,folds,validate_train
from experiments.scent_v2.accuracy_root_cause.run import load_selected
from experiments.scent_v2.accuracy_root_cause.model import structural_phrases,predict
from experiments.scent_v2.accuracy_root_cause.diagnostic import component_arrays
from experiments.scent_v2.similarity_reranking.core import rerank
from experiments.scent_v2.recommend import rank
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from .analysis import CONFIG,CHANNELS,preferences,pair_analysis,max_similarity,suspected,component_alignment,summarize_recommendations,label
OUT=ROOT/'outputs/scent_v2/preference_overgeneralization';OLD=ROOT/'outputs/scent_v2/accuracy_root_cause'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def write_csv(name,rows,fields=None):
    with (OUT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/p for p in ['outputs/validation/train_exclude_3.json','outputs/improvement/candidates.json','Term-project-datasets/fra_cleaned.csv','outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json','outputs/scent_v2/accuracy_root_cause/best_model.npz','outputs/scent_v2/accuracy_root_cause/evaluation_results.json','outputs/scent_v2/accuracy_root_cause/verification.json']}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2];writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V35 outputs only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.csv','.json','.npz','.npy')) and p not in allowed and not p.is_relative_to(OUT) and not p.is_relative_to(ROOT/'experiments'):raise PermissionError('Other model/final data denied, including V34 prepared305')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded action denied')
    sys.addaudithook(audit)


def main():
    OUT.chmod(0o700);write('analysis_config.json',CONFIG);guard()
    proof=json.loads((OLD/'verification.json').read_text());assert proof['status']=='PASS' and sha(OLD/'best_model.npz')==proof['model_sha256']
    for p,h in proof['source_sha256'].items():assert sha(ROOT/p)==h
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates);expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text());assert source['developer_split_sha256']==expected['developer_split_sha256'] and len(cohort)==50 and len(reserved)==25
    parts=folds(cohort);catalog,raw=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');features={r['url']:structural_phrases(r) for r in raw};contexts={};aliases={};counter=0
    def deny_fit(*a,**k):raise RuntimeError('No training permitted for observational V35')
    with patch.object(MatrixFactorization,'fit',deny_fit),patch.object(Content,'fit',deny_fit):
        # PHASE1: every recommendation/score/rank is complete before answer analysis.
        for f in parts:
            n=f['fold'];validate_train(f['train'],reserved|{r['user'] for r in f['evaluation']});assert len({u for u,i,r in f['train']})==40
            c,m,b,structure,ref,gate,meta=load_selected(OLD/'best_model.npz',n);assert meta['folds']==5 and meta['policy']=='structured';qpin=hashlib.sha256(m.Q.tobytes()).hexdigest();matrixpin=hashlib.sha256(structure.matrix.tobytes()).hexdigest()
            for row in f['evaluation']:
                u=row['user'];counter+=1;alias=f'U{counter:02}';aliases[u]=alias;support=row['support'];x=component_arrays(support,candidates,c,m,b);pool=x['pool'];pos=[i for i,r in support if label(r)=='POSITIVE'];neg=[i for i,r in support if label(r)=='NEGATIVE'];sp=max_similarity(structure.matrix,structure.items,pos,pool);sn=max_similarity(structure.matrix,structure.items,neg,pool);horder=rank(pool,x['hybrid']);hs={i:k+1 for k,i in enumerate(horder)}
                cache=dict(pool=pool,hybrid=x['hybrid'],signals={'max':sp},baseline_order=horder);sorder,sscores=rerank(dict(signal='max',mode='top50',**{'lambda':.2}),cache,k=len(pool));sr={i:k+1 for k,i in enumerate(sorder)};sv=dict(zip(sorder,sscores));xlookup={i:k for k,i in enumerate(pool)}
                mvalues=hybrid(x['content'],x['mf'],0.,x['popularity']);cvalues=np.where(np.isfinite(x['content']),x['content'],x['popularity']);mr={i:k+1 for k,i in enumerate(rank(pool,mvalues))};cr={i:k+1 for k,i in enumerate(rank(pool,cvalues))}
                out={}
                for method,policy,order in [('Hybrid','baseline',horder),('Structured','structured',sorder)]:
                    top,sc=predict(policy,support,candidates,c,m,b,structure,ref,False);assert top==order[:5];expected_scores=[float(x['hybrid'][xlookup[i]]) if method=='Hybrid' else sv[i] for i in top];assert sc==expected_scores and len(top)==len(set(top))==5 and not set(top)&{i for i,r in support}
                    rows=[]
                    for number,i in enumerate(top,1):
                        k=xlookup[i];cf=float(x['content'][k]) if np.isfinite(x['content'][k]) else None;mf=float(x['mf'][k]) if np.isfinite(x['mf'][k]) else None;H=float(x['hybrid'][k]);active=method=='Structured' and hs[i]<=50 and np.isfinite(sp[k]) and sp[k]>=.05
                        wm=.75*mf if mf is not None and cf is not None else mf if mf is not None else 0.;wc=.25*cf if mf is not None and cf is not None else cf if cf is not None else 0.
                        rows.append(dict(user_alias=alias,fold=n,model=method,rank=number,perfume_id=i,brand=catalog[i]['brand'],perfume_name=catalog[i]['name'],final_score=expected_scores[number-1],Hybrid_score=H,MF_raw=float(x['raw'][k]) if np.isfinite(x['raw'][k]) else None,MF_score=mf,Content_score=cf,MF_weighted_contribution=wm,Content_weighted_contribution=wc,MF_share_of_H=wm/H if H>1e-12 else None,Content_share_of_H=wc/H if H>1e-12 else None,MF_component_rank=mr[i],Content_component_rank=cr[i],component_alignment=component_alignment(mr[i],cr[i],mf is not None,cf is not None),Hybrid_rank=hs[i],Structured_rank=sr[i],structured_rank_promotion=hs[i]-sr[i],structured_promoted=method=='Structured' and sr[i]<hs[i],entered_Top5_by_structure=method=='Structured' and hs[i]>5,structure_contribution=.2*float(sp[k]) if active else 0.,structural_similarity=float(sp[k]) if np.isfinite(sp[k]) else None,positive_support_similarity=float(sp[k]) if np.isfinite(sp[k]) else None,negative_support_similarity=float(sn[k]) if np.isfinite(sn[k]) else None,positive_Support_count=len(pos),negative_Support_count=len(neg),suspected_conflict=suspected(sp[k],sn[k]),Top=sorted(features[i]['Top']),Middle=sorted(features[i]['Middle']),Base=sorted(features[i]['Base']),Main_Accords=sorted(features[i]['accords'])))
                    out[method]=rows
                contexts[u]=dict(alias=alias,fold=n,support=support,recommendations=out,Hybrid_order=horder,Structured_order=sorder)
            assert hashlib.sha256(m.Q.tobytes()).hexdigest()==qpin and hashlib.sha256(structure.matrix.tobytes()).hexdigest()==matrixpin
            print(f'Fold{n}: frozen model replayed, no fit; 10 users x2 Top5 scored',flush=True)
    # PHASE2: held-out labels are now available ONLY for observational diagnostics.
    histories={row['user']:dict(row['support']+row['answers']) for row in cohort};answers={row['user']:dict(row['answers']) for row in cohort};support_hist={row['user']:dict(row['support']) for row in cohort};recommendations=[];profiles={};fold_metrics={method:[] for method in ['Hybrid','Structured']};metric_records={method:[] for method in fold_metrics}
    by_alias={contexts[u]['alias']:u for u in contexts}
    for u,ctx in contexts.items():
        profiles[ctx['alias']]=dict(fold=ctx['fold'],full_history_posthoc=preferences(histories[u],features),support_only=preferences(support_hist[u],features))
        for method,rows in ctx['recommendations'].items():
            for r in rows:
                r['heldout_rating_observed']=r['perfume_id'] in answers[u];r['heldout_class']=label(answers[u].get(r['perfume_id']));r['confirmed_inappropriate']=r['heldout_class']=='NEGATIVE';recommendations.append(r)
            top=[r['perfume_id'] for r in rows];metric_records[method].append((ctx['fold'],dict(top=top,answers=list(answers[u].items()),accuracy=user_metrics(top,list(answers[u].items())))))
    previous=json.loads((OLD/'evaluation_results.json').read_text());metrics={}
    for method,key in [('Hybrid','baseline'),('Structured','structured')]:
        ss=[summarize([r for n,r in metric_records[method] if n==f],candidates) for f in range(1,6)];metrics[method]={k:float(np.mean([s[k] for s in ss])) for k in ['ndcg','recall','hit_rate']}
        old=previous['primary_without_background'][key]
        for k,oldkey in [('ndcg','mean_ndcg'),('recall','mean_recall'),('hit_rate','mean_hit_rate')]:assert abs(metrics[method][k]-old[oldkey])<1e-12
    users=list(contexts);pairs=[];directional_links=[]
    for ua,ub in combinations(users,2):
        ca,cb=contexts[ua],contexts[ub];p=pair_analysis(ca['alias'],cb['alias'],histories[ua],histories[ub],features,ca['fold'],cb['fold']);pairs.append(p)
        if p['status']!='CONFIRMED_PRODUCT_PARTIAL_PREFERENCE_DIFFERENCE':continue
        for i in p['opposed_product_ids']:
            source_u,target=(ua,ub) if label(histories[ua][i])=='POSITIVE' else (ub,ua);ctx=contexts[target]
            inH=i in ctx['Hybrid_order'][:5];inS=i in ctx['Structured_order'][:5]
            if inH or inS:directional_links.append(dict(source_alias=contexts[source_u]['alias'],recipient_alias=ctx['alias'],source_in_recipient_train=contexts[source_u]['fold']!=ctx['fold'],mutual_positive_product_ids=p['common_positive_product_ids'],opposed_product_id=i,recipient_heldout_negative=i in answers[target] and label(answers[target][i])=='NEGATIVE',Hybrid_Top5=inH,Structured_Top5=inS,extra_accord_annotations=p['opposition_extra_accords'][i],causal_transfer_identified=False))
    summary={m:summarize_recommendations([r for r in recommendations if r['model']==m]) for m in ['Hybrid','Structured']};hist=Counter(p['common_rated_products'] for p in pairs);strict=[p for p in pairs if p['status']=='CONFIRMED_PRODUCT_PARTIAL_PREFERENCE_DIFFERENCE'];evaluable=[p for p in pairs if p['strict_evaluable']];qualified=[p for p in directional_links if p['source_in_recipient_train'] and p['recipient_heldout_negative'] and p['Hybrid_Top5']]
    negativeH=[r for r in recommendations if r['model']=='Hybrid' and r['heldout_class']=='NEGATIVE'];negativeS=[r for r in recommendations if r['model']=='Structured' and r['heldout_class']=='NEGATIVE']
    case1=dict(status='OBSERVED_LINKAGE_CAUSAL_TRANSFER_UNPROVEN',example=qualified[0]) if qualified else dict(status='INSUFFICIENT_EVIDENCE',reason='No exact same-product shared-positive/opposed-negative training-source to recipient Hybrid Top5 chain found',strict_product_partial_preference_pairs=len(strict),weaker_recommendation_links=directional_links[:3])
    removed=sorted((r for r in negativeH if r['Structured_rank']>5),key=lambda r:(-r['Structured_rank'],r['user_alias']));raised=sorted((r for r in negativeS if r['Structured_rank']<r['Hybrid_rank']),key=lambda r:(-(r['Hybrid_rank']-r['Structured_rank']),r['user_alias']))
    case2=dict(status='CONFIRMED_NEGATIVE_REMOVED_FROM_TOP5',example=removed[0],scope='A replacement may be unrated, so not a claim of known-positive replacement') if removed else dict(status='NOT_FOUND_IN_OBSERVED_LABELS',reason='No observed negative Hybrid Top5 removed by Structured')
    case3=dict(status='CONFIRMED_NEGATIVE_PROMOTED',example=raised[0]) if raised else dict(status='NOT_FOUND_IN_OBSERVED_LABELS',reason='No observed negative Top5 promoted by Structured')
    verdict='OVERGENERALIZATION_SUSPECTED' if qualified else 'INSUFFICIENT_EVIDENCE'
    per_feature={}
    for ch in CHANNELS:
        counts=Counter();either=Counter()
        for profile in profiles.values():
            x=profile['full_history_posthoc']['channels'][ch]
            if not x['both_polarities_evaluable']:continue
            counts.update(x['overlap_features']);either.update(set(x['positive_feature_union'])|set(x['negative_feature_union']))
        per_feature[ch]=[dict(feature=t,users_both_polarities=counts[t],users_either_polarity=either[t],overlap_fraction=counts[t]/either[t]) for t in sorted(either)]
    posneg_full=sum(p['full_history_posthoc']['positive_items']>0 and p['full_history_posthoc']['negative_items']>0 for p in profiles.values());posneg_support=sum(p['support_only']['positive_items']>0 and p['support_only']['negative_items']>0 for p in profiles.values())
    result=dict(status='OBSERVATIONAL_ANALYSIS_COMPLETE',hypothesis_verdict=verdict,evaluation_users=50,pair_count=len(pairs),compound_preference_users=sum(p['full_history_posthoc']['compound_mainaccord_product_proxy'] for p in profiles.values()),compound_proxy_denominator=50,full_history_both_polarities_users=posneg_full,support_both_polarities_users=posneg_support,Support_negative_ratings=sum(label(r)=='NEGATIVE' for ctx in contexts.values() for i,r in ctx['support']),Support_ratings=250,pair_summary=dict(common_product_count_histogram=dict(sorted(hist.items())),pairs_with_any_common_product=sum(p['common_rated_products']>0 for p in pairs),strict_evaluable_pairs=len(evaluable),strict_partial_preference_pairs=len(strict),opposed_products_with_extra_accord_pairs=sum(p['opposition_has_extra_accord_annotations'] for p in strict),insufficient_pairs=len(pairs)-len(evaluable),insufficient_fraction=(len(pairs)-len(evaluable))/len(pairs),feature_only_shared_accord_pairs=sum(bool(p['shared_positive_accord_annotations']) and not p['mutual_positive_products'] for p in pairs)),recommendation_metrics=summary,user_preferences=profiles,feature_overlap_per_channel=per_feature,directional_partial_preference_recommendation_links=directional_links,qualified_Hybrid_links=len(qualified),metric_reproduction=metrics,MF_new_fits=0,Content_new_fits=0,model_selection=False,hyperparameter_tuning=False,V34_prepared_model_reads=0,reserved_numeric_labels_decoded=0,reserved_evaluations=0,source=source,causal_claim=False,interpretation='Whole-product labels do not identify isolated note/family preference. Unknown recommendations not negatives. Sparse pair/negative data cannot establish CF transfer causality.')
    write('preference_analysis.json',result);write_csv('recommendation_error_analysis.csv',recommendations);write_csv('user_pair_analysis.csv',pairs);write('case_studies.json',dict(case1=case1,case2=case2,case3=case3,aliases='Temporary U01..U50, no raw/hash user mapping persisted',causal_claim=False))
    print(json.dumps(dict(verdict=verdict,compound_users=result['compound_preference_users'],strict_partial_pairs=len(strict),evaluable_pairs=len(evaluable),qualified_links=len(qualified),models=summary,MF_fits=0),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
