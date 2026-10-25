"""Bounded development-validation search. Never reads test or external source files."""
import hashlib
import json
import platform
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from perfume.data import read_json,write_json,write_csv,fragrantica,counts
from perfume.models import Baseline,hybrid
from perfume.improvements import ProfileContent,make_mf
from perfume.evaluation import evaluate,rating_errors

OUT=Path('outputs/improvement')


def ranked(pool,values):
    """Finite-score ranking with deterministic item-ID tie breaking."""
    return [pool[n] for n in sorted(range(len(pool)),key=lambda n:(-float(values[n]) if np.isfinite(values[n]) else float('inf'),pool[n])) if np.isfinite(values[n])]


def prepare(train,users,candidates,catalog,modes,relevance):
    """Cache support-only content and baseline scores, separately for each train arm."""
    histories=defaultdict(list)
    for u,i,r in train:histories[u].append((i,r))
    content={m:ProfileContent(m,relevance).fit(catalog,{i for _,i,_ in train}) for m in modes}
    baseline=Baseline().fit(train)
    cache={}
    for u in users:
        support=histories[u];seen={i for i,_ in support}
        pool=[i for i in candidates if i not in seen]
        cache[u]={'pool':pool,'baseline':baseline.score(pool),
                  'content':{m:model.score(support,pool) for m,model in content.items()}}
    return cache,baseline


def predictions(cache,mf,alpha_grid,profiles,with_hybrid=True):
    """Scoring boundary accepts no labels; return full rankings for each validation user."""
    output={}
    for u,row in cache.items():
        pool=row['pool'];m=mf.score(u,pool)
        scores={'mf':m,'popularity':row['baseline']}
        for mode in profiles:
            c=row['content'][mode];scores['content_'+mode]=c
            if with_hybrid:
                for alpha in alpha_grid:
                    scores[f'hybrid_{mode}_{alpha:g}']=hybrid(c,m,alpha,row['baseline'])
        output[u]={name:ranked(pool,values) for name,values in scores.items()}
    return output


def main():
    config=read_json('configs/improvement.json')
    validation=read_json(OUT/'validation.json');candidates=read_json(OUT/'candidates.json')
    users=sorted({u for u,_,_ in validation})
    catalog,_=fragrantica('Term-project-datasets/fra_cleaned.csv')
    metrics,per_users,losses,errors,diagnostics=[],[],{},{},[]
    arms={};models={};eligible={}
    for threshold in config['thresholds']:
        train=read_json(f'outputs/validation/train_exclude_{threshold}.json')
        cache,baseline=prepare(train,users,candidates,catalog,config['profile_modes'],config['relevance'])
        arms[threshold]=(train,cache,baseline)
        scores=[]
        for grid,parameters in enumerate(config['mf_grid']):
            mf=make_mf(parameters,config['seed']).fit(train)
            models[threshold,grid]=mf
            pred=predictions(cache,mf,[],[],False)
            summary,_=evaluate(pred,validation,config['k'],config['relevance'])
            cf=next(r for r in summary if r['method']=='mf');scores.append(cf['ndcg'])
            metrics.extend({'stage':'mf_search','threshold':threshold,'grid':grid,**r} for r in summary)
            losses[f'{threshold}_{grid}']=mf.losses
            errors[f'{threshold}_{grid}']=rating_errors(validation,mf,baseline)
            print(f'fit threshold={threshold} grid={grid} kind={parameters["kind"]} MF_NDCG={cf["ndcg"]:.8f}',flush=True)
        best=min(range(len(scores)),key=lambda n:(-scores[n],n))
        chosen=best if scores[best]>scores[0]+1e-12 else 0
        # The unchanged CF stays a hybrid candidate even when pure CF improves.
        eligible[threshold]=sorted({0,chosen})
        for grid in eligible[threshold]:
            mf=models[threshold,grid]
            pred=predictions(cache,mf,config['alphas'],config['profile_modes'])
            summary,per=evaluate(pred,validation,config['k'],config['relevance'])
            metrics.extend({'stage':'hybrid_search','threshold':threshold,'grid':grid,**r} for r in summary)
            per_users.extend({'threshold':threshold,'grid':grid,**r} for r in per)
        for grid in sorted({0,chosen}):
            mf=models[threshold,grid];ucount=__import__('collections').Counter(u for u,_,_ in train)
            icount=__import__('collections').Counter(i for _,i,_ in train)
            valerrors=[];baseerrors=[];supportcounts=[];itemcounts=[]
            for u,i,r in validation:
                pred=mf.score(u,[i])[0]
                if np.isfinite(pred):valerrors.append(pred-r);baseerrors.append(baseline.mean-r)
                supportcounts.append(ucount[u]);itemcounts.append(icount[i])
            allscores=np.concatenate([mf.score(u,row['pool']) for u,row in cache.items()])
            finite=allscores[np.isfinite(allscores)]
            diagnostics.append({'threshold':threshold,'grid':grid,**counts(train),
               'mean_train_ratings_per_eval_user':float(np.mean(supportcounts)),
               'median_train_item_ratings':float(np.median(list(icount.values()))),
               'validation_items_untrained':sum(n==0 for n in itemcounts),
               'validation_items_with_le2_train':sum(n<=2 for n in itemcounts),
               'train_rating_mean':baseline.mean,'train_rating_sd':float(np.std([r for _,_,r in train])),
               'observed_prediction_n':len(valerrors),'mf_rmse_same_rows':float(np.sqrt(np.mean(np.square(valerrors)))),
               'mean_rmse_same_rows':float(np.sqrt(np.mean(np.square(baseerrors)))),
               'ranking_score_sd':float(np.std(finite)),'clipped_to_1_fraction':float(np.mean(finite==1)),
               'clipped_to_0_fraction':float(np.mean(finite==0))})
    hybrid_rows=[r for r in metrics if r['stage']=='hybrid_search' and r['method'].startswith('hybrid_')]
    winner=min(hybrid_rows,key=lambda r:(-r['ndcg'],r['threshold'],r['grid'],r['method']))
    # Existing best baseline pipeline is included exactly, so no downgrade can be selected.
    legacy=next(r for r in hybrid_rows if r['threshold']==5 and r['grid']==0 and r['method']=='hybrid_rating_0.25')
    if winner['ndcg']<=legacy['ndcg']+1e-12:winner=legacy
    _,mode,alpha=winner['method'].split('_')
    selected={'zero_policy':'exclude_as_analysis_assumption','zero_semantics':'UNRESOLVED',
              'threshold':winner['threshold'],'mf':config['mf_grid'][winner['grid']],
              'profile_mode':mode,'alpha':float(alpha),'seed':config['seed'],'k':config['k'],'relevance':config['relevance'],
              'validation_result':winner,'previous_pipeline_result':legacy,
              'changed':winner['ndcg']>legacy['ndcg']+1e-12,
              'pure_mf_selected_grid_by_threshold':{str(t):eligible[t][-1] for t in eligible},
              'external_protocol':config['external_protocol']}
    write_csv(OUT/'validation_metrics.csv',metrics)
    write_csv(OUT/'validation_per_user.csv',per_users)
    write_csv(OUT/'mf_diagnostics.csv',diagnostics)
    write_json(OUT/'training_loss.json',losses)
    write_json(OUT/'validation_rating_errors.json',errors)
    write_json(OUT/'selection.json',selected)
    # Sensitivity: use selected model/configuration on included-zero training only; do not reselect.
    train=read_json(f'outputs/validation/train_include_{selected["threshold"]}.json')
    cache,base=prepare(train,users,candidates,catalog,[mode],config['relevance'])
    sensitivity=make_mf(selected['mf'],config['seed']).fit(train)
    summary,per=evaluate(predictions(cache,sensitivity,[selected['alpha']],[mode]),validation,config['k'],config['relevance'])
    write_csv(OUT/'zero_included_frozen_sensitivity.csv',summary)
    write_json(OUT/'run_metadata.json',{'config':config,'python':platform.python_version(),'numpy':np.__version__,
      'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('configs/improvement.json'),OUT/'validation.json',OUT/'candidates.json']},
      'test_and_external_data_used':False})
    print('SELECTED',json.dumps(selected,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
