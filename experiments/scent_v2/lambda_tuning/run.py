"""Six inner SGD fits, immutable selection lock, then verified outer-Q reuse."""
import hashlib,json,os,sys,subprocess,platform
from collections import defaultdict
from pathlib import Path
from .config import ROOT,HEAD,OUT,BASE,LAMBDAS,POLICY
from experiments.scent_v2.config import TRAIN,CANDIDATES,CATALOG
from experiments.scent_v2.run import write_json,write_csv


def make_inner(outer,candidates):
    """Two alternating hash-ordered user folds inside outer TRAIN, never outer answers."""
    from experiments.scent_v2.splits import digest,validate
    hist=defaultdict(list)
    for u,i,r in outer['train']:hist[u].append((i,r))
    eligible=sorted([u for u,h in hist.items()if len(h)>=6 and sum(i in candidates for i,r in h)>=5],
                    key=lambda u:digest(f'12:user:{u}'))
    result=[]
    for n in range(2):
        users=eligible[n::2];excluded=set(users);support={};answers={}
        for u in users:
            ids=sorted([i for i,r in hist[u]if i in candidates],key=lambda i:digest(f'12:support:{u}:{i}'))
            seen=set(ids[:5]);support[u]=sorted((i,r)for i,r in hist[u]if i in seen)
            answers[u]=sorted((i,r)for i,r in hist[u]if i not in seen)
        f=dict(fold=n+1,users=users,train=[r for r in outer['train']if r[0]not in excluded],support=support,answers=answers)
        validate(f,candidates)
        if set(users)&set(outer['users']):raise ValueError('Outer user in inner eval')
        result.append(f)
    return result


def evaluate_context(fold,outer_id,phase,lam,content,mf,pop,candidates):
    """Inference gets only support; answer-based metric aggregation is separate."""
    from .evaluate import view
    from experiments.scent_v2.recommend import score
    from experiments.scent_v2.evaluate import metrics
    from experiments.scent_v2.robustness import measure
    m=view(mf,lam);acc=[];rob=[];diag=[]
    for u in fold['users']:
        support=fold['support'][u];known=sum(i in mf.items for i,r in support)
        for track,pool in [('A',candidates),('B_partial',[i for i in candidates if i in mf.items])]:
            base=score(support,pool,content,m,pop)
            changes=measure(support,pool,content,m,pop,base)
            # Scoring and perturbation are finished before the local answer list is used.
            answers=fold['answers'][u]
            names=['content','mf','mf_fallback','hybrid']if track=='A'else ['content','mf','hybrid']
            for scope in [track]+(['B_full5']if track=='B_partial'and known==5 else []):
                for method in names:
                    acc.append(dict(phase=phase,outer=outer_id,inner=fold['fold']if phase=='inner'else None,
                        **{'lambda':lam},track=scope,method=method,user=u,
                        accuracy=metrics(base['methods'][method]['top'],answers),**base['methods'][method]))
                for r in changes:
                    if r['method']in names:rob.append(dict(phase=phase,outer=outer_id,
                        inner=fold['fold']if phase=='inner'else None,**{'lambda':lam},track=scope,user=u,**r))
            diag.append(dict(phase=phase,outer=outer_id,inner=fold['fold']if phase=='inner'else None,
                track=track,user=u,**{'lambda':lam},known_support=known,upper=base['upper'],lower=base['lower'],
                margin56={k:v['margin56']for k,v in base['methods'].items()},
                positive_answers=sum(r>=.7 for i,r in answers),positive_untrained=sum(r>=.7 and i not in mf.items for i,r in answers)))
    return acc,rob,diag


def main():
    """No tuning other than predeclared fold lambda; refuse output collision."""
    os.chdir(ROOT)
    if subprocess.check_output(['git','--no-optional-locks','rev-parse','HEAD'],text=True).strip()!=HEAD:raise RuntimeError('HEAD mismatch')
    if subprocess.check_output(['git','--no-optional-locks','branch','--show-current'],text=True).strip()!='development-v2':raise RuntimeError('Branch mismatch')
    if OUT.exists():raise RuntimeError('Existing experiment output: STOP, never overwrite')
    baseline_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in BASE.rglob('*')if p.is_file()}
    metadata=json.loads((BASE/'run_metadata.json').read_text())
    for p,h in {**metadata['code_sha256'],**metadata['inputs_sha256']}.items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise RuntimeError('V2-0 code/input changed')
    state={'outer_unlocked':False}
    allowed={TRAIN.resolve(),CANDIDATES.resolve(),CATALOG.resolve()}
    def guard(event,args):
        if event=='open'and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            writing=(isinstance(args[1],str)and any(c in args[1]for c in 'wax+'))or(isinstance(args[2],int)and args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise RuntimeError('Protected write')
            if not writing and p.is_relative_to(ROOT)and p.suffix in ('.json','.csv','.npz','.npy'):
                permitted=p in allowed or p.is_relative_to(OUT)or(state['outer_unlocked']and p.is_relative_to(BASE))
                if not permitted:raise RuntimeError('Forbidden old data/outer access before lock')
        if event in ('os.remove','os.rename','os.rmdir','os.link','os.symlink','subprocess.Popen'):raise RuntimeError('Forbidden mutation/process')
        if event=='os.mkdir'and not Path(args[0]).resolve().is_relative_to(OUT):raise RuntimeError('Directory outside experiment')
    sys.addaudithook(guard)
    import numpy as np
    from perfume.data import fragrantica
    from perfume.models import Content,MatrixFactorization,Baseline
    from experiments.scent_v2.splits import build
    from experiments.scent_v2.train import fit_fold
    from .evaluate import summarize,comparisons,select_inner,bootstrap_delta,metric_map
    rows=json.loads(TRAIN.read_text());candidates=json.loads(CANDIDATES.read_text());outers=build(rows,candidates)
    assert [len(f['train'])for f in outers]==[1531,1481,1493]
    catalog,_=fragrantica(CATALOG);OUT.mkdir()
    write_json(OUT/'policy.json',POLICY);write_json(OUT/'v20_sha256.json',baseline_hashes)
    write_json(OUT/'outer_splits.private.json',outers)
    ledger=[];entries=[];all_acc=[];all_rob=[];all_diag=[];selections=[];fold_acc=[];fold_rob=[];fold_pairs=[]
    policy_hash=hashlib.sha256((OUT/'policy.json').read_bytes()).hexdigest()
    def profile(frame,event,arg):
        if event=='call'and frame.f_code is MatrixFactorization.fit.__code__:
            entries.append(len(entries)+1)
            if len(entries)>6:raise RuntimeError('Fit budget exceeded')
    sys.setprofile(profile)
    expected=[(1207,1219),(1207,1169),(1219,1169)]
    for outer in outers:
        o=outer['fold'];aa=[];rr=[]
        inners=make_inner(outer,candidates)
        assert tuple(len(f['train'])for f in inners)==expected[o-1]
        write_json(OUT/f'outer{o}_inner_splits.private.json',inners)
        for inner in inners:
            n=inner['fold'];print(f'outer{o}/inner{n}: fit {len(inner["train"])} rows; Q shared by 3 lambdas',flush=True)
            content,mf,pop,evidence=fit_fold(inner['train'],set(inner['users'])|set(outer['users']),catalog)
            del mf.P
            evidence.update(outer=o,inner=n,candidate_factors=len(set(candidates)&mf.items.keys()))
            np.savez(OUT/f'outer{o}_inner{n}_Q.npz',Q=mf.Q)
            write_json(OUT/f'outer{o}_inner{n}_model.private.json',dict(items=mf.items,content_idf=content.idf,losses=mf.losses))
            for lam in LAMBDAS:
                a,r,d=evaluate_context(inner,o,'inner',lam,content,mf,pop,candidates)
                aa+=a;rr+=r;all_diag+=d
                assert mf.reg==.01 and hashlib.sha256(mf.Q.tobytes()).hexdigest()==evidence['q_sha256']
            ledger.append(evidence)
        selection=dict(outer=o,**select_inner(aa,rr));selections.append(selection)
        a,r=summarize(aa,rr);fold_acc += [dict(outer=o,**v)for v in a];fold_rob += [dict(outer=o,**v)for v in r]
        fold_pairs += [dict(outer=o,**v)for v in comparisons(aa,rr)]
        all_acc+=aa;all_rob+=rr
        print(f'outer{o}: inner-only lambda selection locked = {selection["selected_lambda"]}',flush=True)
    sys.setprofile(None);assert len(entries)==6
    write_json(OUT/'selection_locked.json',dict(policy_sha256=policy_hash,outer_results_seen=False,selections=selections))
    locked_hash=hashlib.sha256((OUT/'selection_locked.json').read_bytes()).hexdigest()
    write_json(OUT/'inner_results.private.json',dict(accuracy=all_acc,robustness=all_rob,diagnostics=all_diag))
    write_json(OUT/'fit_ledger.json',dict(actual_new_mf_fits=len(entries),fits=ledger,outer_fits=0))
    write_csv(OUT/'inner_accuracy_by_outer.csv',fold_acc);write_csv(OUT/'inner_robustness_by_outer.csv',fold_rob)
    write_csv(OUT/'inner_paired_by_outer.csv',fold_pairs)
    a,r=summarize(all_acc,all_rob);write_csv(OUT/'inner_accuracy_pooled.csv',a);write_csv(OUT/'inner_robustness_pooled.csv',r)
    write_csv(OUT/'inner_paired_pooled.csv',comparisons(all_acc,all_rob))
    # Only now may old outer artifact metadata/results be parsed.
    state['outer_unlocked']=True
    original=json.loads((BASE/'user_results.private.json').read_text())
    old_ledger=json.loads((BASE/'fit_ledger.json').read_text())['fits']
    oa=[];orr=[];od=[];reuse=[];parity_cases=0;parity_diff=0.
    for outer,selection in zip(outers,selections):
        o=outer['fold'];old=old_ledger[o-1]
        train_digest=hashlib.sha256(json.dumps(outer['train']).encode()).hexdigest()
        if train_digest!=old['train_sha256']:raise RuntimeError('Outer train changed')
        for key,value in [('factors',4),('epochs',160),('learning_rate',.01),('regularization',.01),('seed',12)]:
            if old['policy'][key]!=value:raise RuntimeError('Outer settings mismatch')
        meta=json.loads((BASE/f'fold{o}_model.private.json').read_text())
        mf=MatrixFactorization(factors=4,epochs=160,learning_rate=.01,regularization=.01,seed=12)
        mf.items=meta['items']
        with np.load(BASE/f'fold{o}_factors.npz')as archive:mf.Q=archive['Q'].copy()
        mf.Q.flags.writeable=False
        if hashlib.sha256(mf.Q.tobytes()).hexdigest()!=old['q_sha256']:raise RuntimeError('Outer Q mismatch')
        if set(mf.items)!={i for u,i,r in outer['train']}:raise RuntimeError('Outer item mapping mismatch')
        content=Content().fit(catalog,{i for u,i,r in outer['train']});pop=Baseline().fit(outer['train'])
        if content.idf!=meta['content_idf']:raise RuntimeError('Outer IDF mismatch')
        base_a,base_r,base_d=evaluate_context(outer,o,'outer',.01,content,mf,pop,candidates)
        old_a={(r['track'],r['method'],r['user']):r for r in original['accuracy']if r['fold']==o}
        old_r={(r['track'],r['method'],r['user'],r['amplitude']):r for r in original['robustness']if r['fold']==o}
        for row in base_a:
            saved=old_a[row['track'],row['method'],row['user']]
            if row['top']!=saved['top']:raise RuntimeError('V2-0 ID/order parity failed')
            diff=max(abs(x-y)for x,y in zip(row['top_scores'],saved['top_scores']));parity_diff=max(parity_diff,diff)
            if diff>1e-12 or row['accuracy']!=saved['accuracy']:raise RuntimeError('V2-0 numerical parity failed')
            parity_cases+=1
        for row in base_r:
            saved=old_r[row['track'],row['method'],row['user'],row['amplitude']]
            for key in ('replacement','first','set_same','order_same','jaccard','rank_move'):
                if row[key]!=saved[key]:raise RuntimeError('V2-0 robustness parity failed')
        for label,lam in [('baseline',.01),('selected',selection['selected_lambda'])]:
            if lam==.01:a,r,d=base_a,base_r,base_d
            else:a,r,d=evaluate_context(outer,o,'outer',lam,content,mf,pop,candidates)
            oa += [dict(r,policy=label)for r in a];orr += [dict(v,policy=label)for v in r];od += [dict(v,policy=label)for v in d]
        reuse.append(dict(outer=o,train_sha256=train_digest,q_sha256=old['q_sha256'],settings_verified=True,Q_unchanged=hashlib.sha256(mf.Q.tobytes()).hexdigest()==old['q_sha256']))
        print(f'outer{o}: verified V2-0 Q reused; selected lambda={selection["selected_lambda"]}',flush=True)
    outer_acc=[];outer_rob=[]
    for label in ('baseline','selected'):
        # Relabel only for aggregation; selected policy can have fold-specific lambdas.
        a,r=summarize([dict(v,**{'lambda':.01})for v in oa if v['policy']==label],
                      [dict(v,**{'lambda':.01})for v in orr if v['policy']==label])
        outer_acc += [dict(v,policy=label)for v in a];outer_rob += [dict(v,policy=label)for v in r]
    pairs=[]
    for track in sorted({r['track']for r in oa}):
        for method in ('content','mf','mf_fallback','hybrid'):
            for metric,source,amp in [('ndcg',oa,None),('recall',oa,None)]+[(key,orr,amp)for amp in (.5,1.)for key in ('replacement','first')]:
                maps=[]
                for label in ('selected','baseline'):
                    subset=[dict(v,**{'lambda':.01})for v in source if v['policy']==label]
                    maps.append(metric_map(subset,.01,track,method,metric,amp))
                if not maps[0]:continue
                d=bootstrap_delta(*maps)
                pairs.append(dict(track=track,method=method,metric=metric,amplitude=amp,**d))
    write_csv(OUT/'outer_accuracy.csv',outer_acc);write_csv(OUT/'outer_robustness.csv',outer_rob);write_csv(OUT/'outer_paired.csv',pairs)
    write_json(OUT/'outer_results.private.json',dict(accuracy=oa,robustness=orr,diagnostics=od))
    assert hashlib.sha256((OUT/'selection_locked.json').read_bytes()).hexdigest()==locked_hash
    assert hashlib.sha256((OUT/'policy.json').read_bytes()).hexdigest()==policy_hash
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in baseline_hashes.items())
    write_json(OUT/'verification.json',dict(status='PASS',new_mf_fits=6,reused_outer_Q=3,outer_new_fits=0,
        selection_locked_before_outer_access=True,selection_sha256=locked_hash,policy_sha256=policy_hash,
        baseline_top5_parity_cases=parity_cases,baseline_max_score_difference=parity_diff,
        baseline_robustness_exact=True,reuse_evidence=reuse,old_test_answers_loaded=False,
        python=platform.python_version(),numpy=np.__version__,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path(__file__).parent.rglob('*.py')}))
    print('PASS: six new MF fits, three verified outer Q reuses, no outer reselection',flush=True)


if __name__=='__main__':main()
