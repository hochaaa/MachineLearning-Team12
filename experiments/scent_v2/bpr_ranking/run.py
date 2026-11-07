"""Same V26 folds; bounded real BPR training, no V24 outputs read."""
import csv,hashlib,json,os,sys
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline,hybrid
from perfume.data import fragrantica
from experiments.scent_v2.mf_cv_optimization.core import ROOT,developer_cohort,folds,validate_train,user_scores
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from experiments.scent_v2.recommend import rank
from .model import fit as fit_bpr,scores
OUT=ROOT/'outputs/scent_v2/bpr_ranking'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    (OUT/name).chmod(0o600)


def guard():
    allowed={ROOT/'outputs/validation/train_exclude_3.json',ROOT/'outputs/improvement/candidates.json',ROOT/'Term-project-datasets/fra_cleaned.csv',ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json'}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();m=args[1];flags=args[2]
            writing=(isinstance(m,str) and any(c in m for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V28 output only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.csv','.json','.npz','.npy')) and p not in allowed and not p.is_relative_to(OUT):raise PermissionError('Old outputs/final labels forbidden')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded action denied')
    sys.addaudithook(audit)


def legacy_top(support,candidates,c,m,b,shared=None):
    return user_scores(dict(alpha=.25,ridge_scale=1.,center=False),support,candidates,c,m,b,shared)


def bpr_top(alpha,support,candidates,c,m,b,legacy,shared=None):
    pool=sorted(set(candidates)-{i for i,y in support});cs,bs=shared if shared is not None else (c.score(support,pool),b.score(pool));ms,diag=scores(m,support,pool)
    top=legacy_top(support,candidates,c,legacy,b,(cs,bs)) if ms is None else rank(pool,hybrid(cs,ms,alpha,bs))[:5]
    assert len(top)==len(set(top))==5 and not set(top)&{i for i,y in support} and set(top)<=set(candidates)
    return top,diag


def save_model(path,c,m,b,candidates,spec,cfg,legacy=None):
    tokens=sorted(c.idf);ids=sorted(candidates)
    meta=dict(spec=spec,mf_config=cfg,scope='V28 all50 developer refit; no independent final')
    values=dict(Q=m.Q,MF_items=np.asarray(sorted(m.items,key=m.items.get)),feature_items=np.asarray(ids),tokens=np.asarray(tokens),idf=np.asarray([c.idf[t] for t in tokens]),features=np.asarray([[c.vectors[i].get(t,0) for t in tokens] for i in ids]),popularity=np.asarray([b.counts[i] for i in ids]),popularity_maximum=np.asarray(b.maximum),metadata=np.asarray(json.dumps(meta)))
    if spec['family']=='bpr':
        values.update(temperature=np.asarray(m.temperature),fallback_Q=legacy.Q,fallback_items=np.asarray(sorted(legacy.items,key=legacy.items.get)))
    with path.open('xb') as f:np.savez_compressed(f,**values)


def load_model(path):
    with np.load(path,allow_pickle=False) as v:
        meta=json.loads(str(v['metadata']));spec=meta['spec'];cfg=meta['mf_config'];m=SimpleNamespace(Q=v['Q'].copy(),items={str(i):n for n,i in enumerate(v['MF_items'])},factors=cfg['factors'],reg=cfg['regularization']);m.Q.flags.writeable=False
        fallback=m
        if spec['family']=='bpr':
            m.variant='variant_a';m.temperature=float(v['temperature']);fallback=SimpleNamespace(Q=v['fallback_Q'].copy(),items={str(i):n for n,i in enumerate(v['fallback_items'])},factors=4,reg=.01);fallback.Q.flags.writeable=False
        c=Content();c.idf=dict(zip(map(str,v['tokens']),map(float,v['idf'])));c.vectors={str(i):{str(v['tokens'][n]):float(w) for n,w in enumerate(row) if w} for i,row in zip(v['feature_items'],v['features'])}
        b=Baseline();b.counts=defaultdict(int,zip(map(str,v['feature_items']),map(int,v['popularity'])));b.maximum=float(v['popularity_maximum'])
        return c,m,b,fallback,meta


def main():
    OUT.chmod(0o700);write('experiment_config.json',CONFIG);guard()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates)
    expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text());assert len(cohort)==50 and source['developer_split_sha256']==expected['developer_split_sha256']
    parts=folds(cohort);catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');contexts=[];fits=[];table=[];stats={};specs={};cache={};cfgs={};pair_diagnostics={}
    def train(family,cfg,rows,excluded):
        assert len(fits)<CONFIG['max_actual_data_MF_fits'];validate_train(rows,excluded)
        entry=dict(number=len(fits)+1,family=family,config=cfg,train_users=len({u for u,i,y in rows}),ratings=len(rows));fits.append(entry)
        if family=='bpr':
            m,diag=fit_bpr(rows,excluded,**cfg);entry.update(diag)
        else:
            m=MatrixFactorization(**cfg).fit(rows);entry.update(loss_first=m.losses[0],loss_last=m.losses[-1]);m.Q.flags.writeable=False
            for key in ('P','users'):
                if hasattr(m,key):delattr(m,key)
        return m
    def assess(name,spec,models):
        summaries=[];diags=[];records=[]
        for n,(fold,c,b,legacy,shared) in enumerate(contexts):
            recs=[]
            for row in fold['evaluation']:
                support=row['support'];sh=shared[row['user']]
                if spec['family']=='legacy':top=user_scores(dict(alpha=spec['alpha'],ridge_scale=1.,center=False),support,candidates,c,legacy,b,sh)
                else:
                    top,d=bpr_top(spec['alpha'],support,candidates,c,models[n],b,legacy,sh);diags.append(d)
                # Answers become visible only after scoring completes.
                recs.append(dict(top=top,answers=row['answers'],accuracy=user_metrics(top,row['answers'])))
            summary=summarize(recs,candidates);summaries.append(summary);records.extend(recs)
            table.append(dict(model=name,fold=fold['fold'],family=spec['family'],factors=cfgs[spec['config']]['factors'] if spec['family']=='bpr' else 4,alpha=spec['alpha'],users=summary['users'],positive_users=summary['positive_users'],ndcg_at5=summary['ndcg'],recall_at5=summary['recall'],hit_rate_at5=summary['hit_rate']))
        stats[name]=dict(mean_ndcg=float(np.mean([s['ndcg'] for s in summaries])),mean_recall=float(np.mean([s['recall'] for s in summaries])),mean_hit_rate=float(np.mean([s['hit_rate'] for s in summaries])),fold_ndcg=[s['ndcg'] for s in summaries],folds=summaries,pooled_oof=summarize(records,candidates))
        if diags:pair_diagnostics[name]=dict(users=len(diags),success_users=sum(d['status']=='ok' for d in diags),success_fraction=sum(d['status']=='ok' for d in diags)/len(diags),support_pairs=sum(d['support_pairs'] for d in diags),fallback_reasons={k:sum(d['status']==k for d in diags) for k in sorted({d['status'] for d in diags})})
        specs[name]=spec
    for fold in parts:
        excluded=reserved|{r['user'] for r in fold['evaluation']};assert len({u for u,i,y in fold['train']})==40 and len(fold['evaluation'])==10
        c=Content().fit(catalog,{i for u,i,y in fold['train']});b=Baseline().fit(fold['train']);m=train('legacy',CONFIG['base_mf'],fold['train'],excluded);shared={}
        for row in fold['evaluation']:
            pool=sorted(set(candidates)-{i for i,y in row['support']});shared[row['user']]=(c.score(row['support'],pool),b.score(pool))
        contexts.append((fold,c,b,m,shared))
    for name,a in [('hybrid_baseline',.25),('pure_mf_baseline',0.)]:assess(name,dict(family='legacy',alpha=a),None)
    baseline=stats['hybrid_baseline']['mean_ndcg'];assert abs(baseline-CONFIG['baseline_expected_ndcg'])<1e-12
    print(f'Baseline reproduced: {baseline:.12f}',flush=True)
    def candidate(index,cfg):
        cfgs[index]=cfg;models=[]
        for fold,c,b,m,sh in contexts:
            models.append(train('bpr',cfg,fold['train'],reserved|{r['user'] for r in fold['evaluation']}))
            print(f'BPR config{index} fold{fold["fold"]} trained, pairs={fits[-1]["pair_statistics"]["pairs"]}, objective {fits[-1]["history"][0]["objective"]:.3f}->{fits[-1]["history"][-1]["objective"]:.3f}',flush=True)
        cache[index]=models
        for alpha in CONFIG['alphas']:assess(f'bpr{index}_a{alpha:g}',dict(family='bpr',config=index,alpha=alpha),models)
        print(json.dumps(dict(config=index,models={n:s['mean_ndcg'] for n,s in stats.items() if specs[n].get('config')==index})),flush=True)
    candidate(0,CONFIG['initial_bpr']);gate=max(s['mean_ndcg'] for n,s in stats.items() if specs[n]['family']=='bpr')>baseline+1e-12
    if gate:candidate(1,dict(CONFIG['initial_bpr'],factors=8))
    else:print('Initial BPR below baseline: extra training pruned',flush=True)
    key=lambda n:(round(stats[n]['mean_ndcg'],12),round(stats[n]['mean_recall'],12),round(stats[n]['mean_hit_rate'],12),-abs(specs[n]['alpha']-.25),-cfgs[specs[n]['config']]['factors'] if specs[n]['family']=='bpr' else -4)
    best_bpr=max((n for n in stats if specs[n]['family']=='bpr'),key=key);hybrids=[n for n in stats if specs[n]['family']=='bpr' and specs[n]['alpha']>0];best_hybrid=max(hybrids,key=key)
    eligible=[n for n in stats if specs[n]['family']=='bpr' and stats[n]['mean_ndcg']>baseline+1e-12];selected=max(eligible,key=key) if eligible else 'hybrid_baseline';spec=specs[selected];cfg=cfgs[spec['config']] if spec['family']=='bpr' else CONFIG['base_mf']
    for n,s in stats.items():
        s['folds_better_than_baseline']=sum(v>b+1e-12 for v,b in zip(s['fold_ndcg'],stats['hybrid_baseline']['fold_ndcg']));s['folds_worse_than_baseline']=sum(v<b-1e-12 for v,b in zip(s['fold_ndcg'],stats['hybrid_baseline']['fold_ndcg']))
    full=[(r['user'],i,y) for r in cohort for i,y in r['support']+r['answers']];c=Content().fit(catalog,{i for u,i,y in full});b=Baseline().fit(full);m=train(spec['family'],cfg,full,reserved)
    fallback=train('legacy',CONFIG['base_mf'],full,reserved) if spec['family']=='bpr' else m
    save_model(OUT/'best_model.npz',c,m,b,candidates,spec,cfg,fallback);lc,lm,lb,lf,meta=load_model(OUT/'best_model.npz')
    support=[(i,.1+.15*n) for n,i in enumerate(sorted(candidates)[:5])]
    pred=lambda c,m,b,f: bpr_top(spec['alpha'],support,candidates,c,m,b,f)[0] if spec['family']=='bpr' else legacy_top(support,candidates,c,m,b)
    assert pred(c,m,b,fallback)==pred(lc,lm,lb,lf) and np.array_equal(m.Q,lm.Q)
    write('evaluation_results.json',dict(status='COMPLETED_DEVELOPER_CV_ONLY',source=source,models=stats,selected=selected,selected_spec=spec,selected_config=cfg,best_bpr=best_bpr,best_bpr_hybrid=best_hybrid,relative_improvement_percent=(stats[selected]['mean_ndcg']/baseline-1)*100,actual_data_MF_fit_count=len(fits),fits=fits,bpr_foldin=pair_diagnostics,additional_gate_passed=gate,roundtrip_exact=True,reserved_rating_tokens_decoded=0,V24_output_reads=0,independent_final='NOT_EVALUATED',generalization_claim=False,serving_model_changed=False,model_selection='Mean fold NDCG then Recall/HitRate, developer set reused',MF_fits_not_shared=True))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    print(json.dumps(dict(selected=selected,baseline=baseline,best_bpr=stats[best_bpr]['mean_ndcg'],selected_ndcg=stats[selected]['mean_ndcg'],actual_data_MF_fit_count=len(fits))),flush=True)

if __name__=='__main__':main()
