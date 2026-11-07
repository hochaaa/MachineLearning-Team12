"""Zero-fit replay of V2-1 inner contexts, diagnostic-only counterfactuals."""
import csv,hashlib,json,os,sys,subprocess,platform
from collections import defaultdict,Counter
from pathlib import Path
from .config import ROOT,HEAD,OUT,BASE,TUNING,CANDIDATES,CATALOG,POLICY


def save_json(name,value):
    """Exclusive local diagnostic output; private files are never shared."""
    with (OUT/name).open('x')as f:json.dump(value,f,indent=2,allow_nan=False)


def save_csv(name,rows):
    """Union-schema CSV for heterogeneous diagnostics, no overwriting."""
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def guard_install():
    """Restrict data reads to catalog/candidates/V2-1 inner artifacts; forbid fits."""
    allowed={CATALOG.resolve(),CANDIDATES.resolve()}
    def guard(event,args):
        if event=='open'and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            writing=(isinstance(args[1],str)and any(c in args[1]for c in 'wax+'))or(isinstance(args[2],int)and args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise RuntimeError('Protected write')
            if not writing and p.is_relative_to(ROOT)and p.suffix in ('.json','.csv','.npz','.npy'):
                inner=p.is_relative_to(TUNING)and (p.name.startswith('outer')and ('inner'in p.name)or p.name in ('inner_results.private.json','fit_ledger.json'))
                if p not in allowed and not inner and not p.is_relative_to(OUT):raise RuntimeError('Forbidden old answer/model input')
        if event in ('os.remove','os.rmdir','os.rename','os.link','os.symlink','subprocess.Popen'):raise RuntimeError('Forbidden mutation/process')
        if event=='os.mkdir'and not Path(args[0]).resolve().is_relative_to(OUT):raise RuntimeError('Unexpected mkdir')
    sys.addaudithook(guard)


def main():
    """Replay 150 contexts x3 lambdas. No fitting, calibration or selection."""
    os.chdir(ROOT)
    if subprocess.check_output(['git','--no-optional-locks','rev-parse','HEAD'],text=True).strip()!=HEAD:raise RuntimeError('HEAD mismatch')
    if subprocess.check_output(['git','--no-optional-locks','branch','--show-current'],text=True).strip()!='development-v2':raise RuntimeError('Branch mismatch')
    if OUT.exists():raise RuntimeError('Existing diagnostic output: STOP, do not overwrite')
    # Hashing protects files without interpreting any old outer preference labels.
    pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for directory in (BASE,TUNING)for p in directory.rglob('*')if p.is_file()}
    guard_install()
    import numpy as np
    from perfume.models import Content,MatrixFactorization,Baseline,hybrid
    from perfume.data import fragrantica
    from experiments.scent_v2.recommend import score
    from experiments.scent_v2.robustness import compare
    from experiments.scent_v2.evaluate import metrics
    from experiments.scent_v2.lambda_tuning.evaluate import view,bootstrap_delta
    from .analysis import distribution,mean_finite,correlation,reconstruct,rank_info,user_means,STATS
    # Training of ANY original SGD implementation is prohibited in this process.
    fit_calls=[]
    def no_fit(frame,event,arg):
        if event=='call'and frame.f_code.co_name=='fit'and 'perfume'in frame.f_code.co_filename:
            fit_calls.append(frame.f_code.co_filename);raise RuntimeError('Diagnostics must never fit a model')
    sys.setprofile(no_fit)
    catalog,_=fragrantica(CATALOG);candidates=json.loads(CANDIDATES.read_text())
    old=json.loads((TUNING/'inner_results.private.json').read_text())
    old_acc={(r['outer'],r['inner'],r['lambda'],r['user'],r['method']):r for r in old['accuracy']if r['track']=='A'}
    fit_ledger=json.loads((TUNING/'fit_ledger.json').read_text())['fits']
    OUT.mkdir();save_json('policy.json',POLICY);save_json('protected_result_sha256.json',pins)
    contexts=[];details=[];corr_rows=[];cf_rows=[];fallback_types=[];fallback_adv=[];contributions=[]
    score_sets=defaultdict(list);array_archive=defaultdict(list);meta_archive=[]
    q_checks=[];parity=0;maxdiff=0.;cf_label='VIRTUAL_DIAGNOSTIC_NOT_A_DEPLOYED_POLICY'
    for outer in range(1,4):
        folds=json.loads((TUNING/f'outer{outer}_inner_splits.private.json').read_text())
        for f in folds:
            inner=f['fold'];stem=f'outer{outer}_inner{inner}'
            model=json.loads((TUNING/(stem+'_model.private.json')).read_text())
            with np.load(TUNING/(stem+'_Q.npz'))as a:q=a['Q'].copy()
            q.flags.writeable=False;qh=hashlib.sha256(q.tobytes()).hexdigest()
            ledger=next(r for r in fit_ledger if r['outer']==outer and r['inner']==inner)
            if qh!=ledger['q_sha256']:raise RuntimeError('Q hash mismatch')
            if hashlib.sha256(json.dumps(f['train']).encode()).hexdigest()!=ledger['train_sha256']:raise RuntimeError('Train boundary mismatch')
            if {u for u,i,r in f['train']}&set(f['users']):raise RuntimeError('Inner user leakage')
            mf=MatrixFactorization(factors=4,epochs=160,learning_rate=.01,regularization=.01,seed=12)
            mf.items=model['items'];mf.Q=q
            content=Content();content.idf=model['content_idf'];content.vectors={}
            for item,row in catalog.items():
                vec={t:content.idf[t]for t in set(row['tokens'])if t in content.idf}
                norm=sum(v*v for v in vec.values())**.5
                content.vectors[item]={t:v/norm for t,v in vec.items()}if norm else {}
            pop=Baseline();pop.counts=Counter(i for u,i,r in f['train']);pop.maximum=max(pop.counts.values())
            for u in f['users']:
                support=f['support'][u]
                assert len(support)==5 and not {i for i,r in support}&{i for i,r in f['answers'][u]}
                base_by_lambda={}
                for lam in POLICY['lambdas']:
                    result=reconstruct(support,candidates,content,mf,pop,lam)
                    actual=score(support,candidates,content,view(mf,lam),pop)
                    pool=result['pool'];arrays=result['arrays'];lookup={i:n for n,i in enumerate(pool)}
                    factor=result['factors'];fallback=result['fallback'];h=arrays['hybrid'];c=arrays['content'];raw=arrays['mf_raw'];m=arrays['mf_clipped']
                    info={key:rank_info(pool,arrays[key])for key in ('content','mf_raw','mf_clipped','hybrid')}
                    top=info['hybrid']['top'];idx=np.array([lookup[i]for i in top]);top20=np.array([lookup[i]for i in info['hybrid']['order'][:20]])
                    for method,key in [('content','content'),('mf','mf_clipped'),('hybrid','hybrid')]:
                        saved=old_acc[outer,inner,lam,u,method]
                        if info[key]['top']!=saved['top']or actual['methods'][method]['top']!=saved['top']:raise RuntimeError('Rank parity failed')
                        diff=max(abs(arrays[key][lookup[i]]-s)for i,s in zip(top if method=='hybrid'else info[key]['top'],saved['top_scores']))
                        maxdiff=max(maxdiff,diff)
                        if diff>1e-12:raise RuntimeError('Score parity failed')
                        parity+=1
                    tag=dict(outer=outer,inner=inner,user=u,**{'lambda':lam})
                    for name,values in arrays.items():
                        own_key=name if name in info else 'hybrid'
                        scopes={'all':np.arange(len(pool)),'own_top5':np.array([lookup[i]for i in info[own_key]['top']]),'hybrid_top5':idx}
                        for scope,indices in scopes.items():score_sets[lam,name,scope].append((u,np.asarray(values[indices])))
                    corr_lookup={}
                    masks={'all_pairwise_finite':np.ones(len(pool),dtype=bool),'factor_present':factor,'no_fallback':~fallback,
                           'hybrid_top20':np.isin(np.arange(len(pool)),top20)}
                    for scope,mask in masks.items():
                        for x,y in [('content','mf_raw'),('content','mf_clipped'),('content','hybrid'),('mf_clipped','hybrid')]:
                            for kind in ('pearson','spearman'):
                                value,reason,n=correlation(arrays[x][mask],arrays[y][mask],kind=='spearman')
                                corr_rows.append(dict(**tag,scope=scope,pair=x+'~'+y,kind=kind,value=value,reason=reason,pairs=n))
                                if scope=='factor_present'and kind=='pearson':corr_lookup[x+'~'+y]=value
                    finite=np.isfinite(raw);upper=raw>1;lower=raw<0
                    mf_idx=np.array([lookup[i]for i in info['mf_clipped']['top']]);mf_order=info['mf_clipped']['order']
                    boundary=[lookup[i]for i in mf_order[4:6]]
                    boundary_cliptie=len(boundary)==2 and m[boundary[0]]==m[boundary[1]]and bool((upper|lower)[boundary].any())
                    row=dict(**tag,known_support=result['known_support'],vector_norm=result['vector_norm'],
                        mf_raw_mean=float(np.mean(raw[finite])),mf_clipped_mean=float(np.mean(m[finite])),content_mean=float(np.mean(c[np.isfinite(c)])),
                        hybrid_mean=float(np.mean(h)),upper_count=int(upper.sum()),lower_count=int(lower.sum()),
                        factor_count=int(factor.sum()),upper_rate=float(upper.sum()/finite.sum())if finite.any()else None,
                        lower_rate=float(lower.sum()/finite.sum())if finite.any()else None,
                        any_clip=float(bool((upper|lower).any())),unique_clipped_items=[pool[n]for n in np.flatnonzero(upper|lower)],
                        mf_top5_clip=int((upper|lower)[mf_idx].sum()),hybrid_top5_clip=int((upper|lower)[idx].sum()),
                        mf_first_clip=int((upper|lower)[mf_idx[0]])if len(mf_idx)else None,
                        hybrid_first_clip=int((upper|lower)[idx[0]])if len(idx)else None,
                        mf_boundary_clipping_tie=int(boundary_cliptie),hybrid_margin56=info['hybrid']['margin'],mf_margin56=info['mf_clipped']['margin'],
                        mf_adjacent_ties=info['mf_clipped']['adjacent_ties'],fallback_top5=int(fallback[idx].sum()),fallback_top20=int(fallback[top20].sum()),
                        fallback_first=int(fallback[idx[0]]),fallback_h_mean=mean_finite(h[fallback]),known_h_mean=mean_finite(h[factor]),
                        c_m_raw_corr=corr_lookup.get('content~mf_raw'),c_m_clip_corr=corr_lookup.get('content~mf_clipped'),
                        overlap_content=len(set(top)&set(info['content']['top'])),overlap_mf=len(set(top)&set(info['mf_clipped']['top'])),
                        top=top)
                    # All inference/counterfactual scores exist before reading preference labels.
                    raw_h=hybrid(c,raw,.25,pop.score(pool))
                    for method,baseline_key,virtual in [('mf','mf_clipped',raw),('hybrid','hybrid',raw_h)]:
                        before=info[baseline_key];after=rank_info(pool,virtual)
                        cf_rows.append(dict(**tag,scenario='remove_clipping',status=cf_label,method=method,
                            before_pool=len(before['order']),after_pool=len(after['order']),
                            **compare(before,after),before_margin56=before['margin'],after_margin56=after['margin'],
                            before_adjacent_ties=before['adjacent_ties'],after_adjacent_ties=after['adjacent_ties']))
                    reduced=[pool[n]for n in range(len(pool))if not fallback[n]]
                    reduced_scores=np.array([h[lookup[i]]for i in reduced]);after=rank_info(reduced,reduced_scores)
                    cf_rows.append(dict(**tag,scenario='exclude_fallback',status=cf_label,method='hybrid',
                        before_pool=len(pool),after_pool=len(reduced),**compare(info['hybrid'],after),
                        before_margin56=info['hybrid']['margin'],after_margin56=after['margin'],
                        before_adjacent_ties=info['hybrid']['adjacent_ties'],after_adjacent_ties=after['adjacent_ties']))
                    orderpos={i:n+1 for n,i in enumerate(info['hybrid']['order'])};content_absent=np.array([not bool(content.vectors.get(i))for i in pool])
                    types={'mf_factor_absent':~factor,'content_feature_absent':content_absent,'both_absent':~factor&content_absent,
                           'content_score_unavailable':~np.isfinite(c),
                           'support_partial':np.full(len(pool),0<result['known_support']<5),'support_none':np.full(len(pool),result['known_support']==0)}
                    for name,mask in types.items():
                        indices=np.flatnonzero(mask);top_indices=[n for n in idx if mask[n]]
                        fallback_types.append(dict(**tag,type=name,candidates=len(indices),top5=len(top_indices),top1=int(mask[idx[0]]),
                            rank_mean=mean_finite([orderpos[pool[n]]for n in indices]),
                            top5_rank_mean=mean_finite([orderpos[pool[n]]for n in top_indices]),hybrid_mean=mean_finite(h[indices])))
                    for name,mask in [('factor_present',factor),('factor_absent',~factor)]:
                        indices=np.flatnonzero(mask);size=len(indices);v=h[indices];top5_count=int(mask[idx].sum());top20_count=int(mask[top20].sum())
                        fallback_adv.append(dict(**tag,group=name,candidates=size,hybrid_mean=mean_finite(v),
                            p50=float(np.quantile(v,.5))if size else None,p90=float(np.quantile(v,.9))if size else None,p99=float(np.quantile(v,.99))if size else None,
                            top5_count=top5_count,top20_count=top20_count,top5_rate=top5_count/size if size else None,
                            top20_rate=top20_count/size if size else None,top5_share=top5_count/5,
                            top5_enrichment=(top5_count/5)/(size/len(pool))if size else None,
                            upper10_probability=float(np.mean(v>=np.quantile(h,.9)))if size else None,
                            upper1_probability=float(np.mean(v>=np.quantile(h,.99)))if size else None))
                    applied=[arrays[k]for k in ('applied_content','applied_mf','fallback_contribution')]
                    variance=[float(np.var(v))for v in applied];covsum=sum(float(np.mean((a-a.mean())*(b-b.mean())))for n,a in enumerate(applied)for b in applied[n+1:])
                    assert abs(sum(variance)+2*covsum-float(np.var(h)))<1e-12
                    contributions.append(dict(**tag,scope='all_candidates',content_variance=variance[0],mf_variance=variance[1],fallback_variance=variance[2],
                        twice_covariance=2*covsum,hybrid_variance=float(np.var(h)),
                        top5_content_mean=float(np.mean(applied[0][idx])),top5_mf_mean=float(np.mean(applied[1][idx])),top5_fallback_mean=float(np.mean(applied[2][idx])),
                        content_top5_overlap=row['overlap_content'],mf_top5_overlap=row['overlap_mf']))
                    top6=info['hybrid']['order'][:6]
                    for n in range(5):
                        a,b=lookup[top6[n]],lookup[top6[n+1]];dc=applied[0][a]-applied[0][b];dm=applied[1][a]-applied[1][b];df=applied[2][a]-applied[2][b]
                        assert abs(dc+dm+df-(h[a]-h[b]))<1e-12
                        details.append(dict(**tag,rank_pair=f'{n+1}-{n+2}',d_content=float(dc),d_mf=float(dm),d_fallback=float(df),d_hybrid=float(h[a]-h[b]),any_fallback=bool(fallback[a]or fallback[b])))
                    answer=f['answers'][u];accuracy=metrics(top,answer)
                    row.update(ndcg=accuracy['ndcg']if accuracy else None,positive_answers=sum(r>=.7 for i,r in answer),
                               trained_positive_answers=sum(r>=.7 and i in mf.items for i,r in answer))
                    contexts.append(row);base_by_lambda[lam]=row
                    for name,arr in arrays.items():array_archive[name].append(arr)
                    array_archive['factor_exists'].append(factor);array_archive['fallback'].append(fallback)
                    meta_archive.append(dict(**tag,pool=pool))
                # Same candidate/fallback scores should remain exactly invariant across lambda.
                for lam in (.1,1.):
                    before=base_by_lambda[.01];after=base_by_lambda[lam]
                    cf_rows.append(dict(tag,**{'lambda':lam},scenario='lambda_vs_0.01',status='OBSERVED_FIXED_Q_DIAGNOSTIC',method='hybrid',
                        **compare({'top':before['top']},{'top':after['top']}),before_pool=474,after_pool=474,
                        before_margin56=before['hybrid_margin56'],after_margin56=after['hybrid_margin56']))
            assert hashlib.sha256(q.tobytes()).hexdigest()==qh
            q_checks.append(dict(outer=outer,inner=inner,q_sha256=qh,unchanged=True,lambdas_share_Q=True))
            print(f'{stem}: score replay, parity and diagnostic counterfactuals complete',flush=True)
    sys.setprofile(None);assert not fit_calls
    assert len(contexts)==450 and len({r['user']for r in contexts})==75
    np.savez_compressed(OUT/'candidate_scores.private.npz',**{k:np.array(v)for k,v in array_archive.items()})
    save_json('candidate_metadata.private.json',meta_archive)
    save_json('context_results.private.json',dict(contexts=contexts,correlations=corr_rows,counterfactuals=cf_rows,
        fallback_types=fallback_types,fallback_advantage=fallback_adv,contributions=contributions,pair_contributions=details))
    # Distribution summaries: pooled candidate, mean context distribution, mean user distribution.
    dist_rows=[]
    for (lam,name,scope),entries in score_sets.items():
        distributions=[distribution(v)for u,v in entries];users=defaultdict(list)
        for u,v in entries:users[u].append(v)
        ud=[distribution(np.concatenate(v))for v in users.values()]
        pooled=distribution(np.concatenate([v for u,v in entries]))
        for mode,stats in [('pooled_candidates',pooled),('context_macro',{k:mean_finite([v[k]for v in distributions])for k in STATS}),
                           ('user_macro_distribution',{k:mean_finite([v[k]for v in ud])for k in STATS})]:
            dist_rows.append(dict(**{'lambda':lam},score=name,scope=scope,aggregation=mode,contexts=len(entries),users=len(users),**stats))
    save_csv('distributions.csv',dist_rows)
    def aggregate_rows(rows,groupkeys,keys):
        groups=defaultdict(list);output=[]
        for row in rows:groups[tuple(row[k]for k in groupkeys)].append(row)
        for group,rs in groups.items():
            out=dict(zip(groupkeys,group));out.update(contexts=len(rs),users=len({r['user']for r in rs}))
            for key in keys:
                out[key+'_context_mean']=mean_finite([r.get(key)for r in rs]);out[key+'_user_mean']=mean_finite(list(user_means(rs,key).values()))
            output.append(out)
        return output
    save_csv('correlations.csv',[dict(row,
        valid_contexts=sum(r['reason']=='ok'for r in corr_rows if all(r[k]==row[k]for k in ('lambda','scope','pair','kind'))),
        invalid_constant=sum(r['reason']=='constant'for r in corr_rows if all(r[k]==row[k]for k in ('lambda','scope','pair','kind'))),
        invalid_insufficient=sum(r['reason']=='insufficient'for r in corr_rows if all(r[k]==row[k]for k in ('lambda','scope','pair','kind'))))
        for row in aggregate_rows(corr_rows,('lambda','scope','pair','kind'),('value','pairs'))])
    save_csv('counterfactuals.csv',aggregate_rows(cf_rows,('lambda','scenario','method','status'),
        ('replacement','first','set_same','order_same','jaccard','rank_move','before_pool','after_pool','before_margin56','after_margin56','before_adjacent_ties','after_adjacent_ties')))
    type_summary=aggregate_rows(fallback_types,('lambda','type'),('candidates','top5','top1','rank_mean','top5_rank_mean','hybrid_mean'))
    for row in type_summary:
        subset=[r for r in fallback_types if r['lambda']==row['lambda']and r['type']==row['type']]
        row.update(affected_users=len({r['user']for r in subset if r['candidates']>0}),
                   affected_contexts=sum(r['candidates']>0 for r in subset),
                   candidate_occurrences=sum(r['candidates']for r in subset),
                   top5_entries=sum(r['top5']for r in subset),top1_entries=sum(r['top1']for r in subset))
    save_csv('fallback_types.csv',type_summary)
    save_csv('fallback_advantage.csv',aggregate_rows(fallback_adv,('lambda','group'),('candidates','hybrid_mean','p50','p90','p99','top5_count','top20_count','top5_rate','top20_rate','top5_share','top5_enrichment','upper10_probability','upper1_probability')))
    save_csv('contributions.csv',aggregate_rows(contributions,('lambda','scope'),('content_variance','mf_variance','fallback_variance','twice_covariance','hybrid_variance','top5_content_mean','top5_mf_mean','top5_fallback_mean','content_top5_overlap','mf_top5_overlap')))
    save_csv('pair_contributions.csv',aggregate_rows(details,('lambda','rank_pair'),('d_content','d_mf','d_fallback','d_hybrid')))
    scalar_keys=('vector_norm','known_support','mf_raw_mean','mf_clipped_mean','content_mean','hybrid_mean','upper_count','lower_count','upper_rate','lower_rate','any_clip',
        'mf_top5_clip','hybrid_top5_clip','mf_first_clip','hybrid_first_clip','mf_boundary_clipping_tie','mf_margin56','hybrid_margin56','mf_adjacent_ties','fallback_top5','fallback_top20','fallback_first','fallback_h_mean','known_h_mean','overlap_content','overlap_mf')
    clip_summary=aggregate_rows(contexts,('lambda',),scalar_keys)
    for row in clip_summary:
        subset=[r for r in contexts if r['lambda']==row['lambda']]
        row.update(clipping_contexts=sum(r['any_clip']for r in subset),clipping_unique_users=len({r['user']for r in subset if r['any_clip']}),
            clipping_candidate_occurrences=sum(r['upper_count']+r['lower_count']for r in subset),unique_clipped_items=len({i for r in subset for i in r['unique_clipped_items']}))
    save_csv('lambda_clipping_summary.csv',clip_summary)
    user_rates=[]
    for lam in POLICY['lambdas']:
        for key in ('upper_rate','lower_rate','any_clip'):
            user_rates.append(dict(**{'lambda':lam},metric=key,**distribution(list(user_means(contexts,key,lambda r:r['lambda']==lam).values()))))
    save_csv('clipping_user_distributions.csv',user_rates)
    # Success labels are assigned AFTER inference, clustered by user; no-positive != failure.
    success=[];boot=[]
    for lam in POLICY['lambdas']:
        rs=[r for r in contexts if r['lambda']==lam];by=defaultdict(list)
        for r in rs:by[r['user']].append(r)
        group_rows=defaultdict(list)
        for u,values in by.items():
            ndcg=mean_finite([r['ndcg']for r in values]);group='no_positive'if ndcg is None else ('hit'if ndcg>0 else 'zero')
            counts=Counter(i for r in values for i in r['top']);slots=sum(counts.values())
            row={key:mean_finite([r.get(key)for r in values])for key in ('known_support','vector_norm','any_clip','fallback_top5','c_m_raw_corr','hybrid_margin56','positive_answers','trained_positive_answers')}
            row.update(user=u,ndcg=ndcg,personal_top1_slot_share=max(counts.values())/slots,personal_hhi=sum((n/slots)**2 for n in counts.values()))
            group_rows[group].append(row)
        for group,values in group_rows.items():
            success.append(dict(**{'lambda':lam},group=group,users=len(values),contexts=sum(len(by[v['user']])for v in values),
                **{k:mean_finite([r[k]for r in values])for k in values[0]if k!='user'}))
        for key in ('vector_norm','hybrid_mean','fallback_top5'):
            a=user_means(contexts,key,lambda r:r['lambda']==lam);b=user_means(contexts,key,lambda r:r['lambda']==.01)
            if lam!=.01:boot.append(dict(**{'lambda':lam},comparison='versus_.01',metric=key,**bootstrap_delta(a,b)))
    save_csv('success_groups.csv',success);save_csv('bootstrap.csv',boot)
    save_json('verification.json',dict(status='PASS',new_model_fits=0,contexts_per_lambda=150,unique_users=75,
        parity_comparisons=parity,maximum_score_difference=maxdiff,contribution_identity=True,counterfactuals_not_selected=True,
        q_checks=q_checks,python=platform.python_version(),numpy=np.__version__,old_test_answers_loaded=False,
        code_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path(__file__).parent.rglob('*.py')}))
    print(f'PASS: 0 fits; {parity} score/rank replays; max error {maxdiff:g}',flush=True)


if __name__=='__main__':main()
