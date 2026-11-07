"""Run the predeclared V2-0 baseline once. Refuses an existing output directory."""
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from .config import ROOT, OUT, TRAIN, CANDIDATES, CATALOG, POLICY, HEAD


def install_guard():
    """Block writes outside new output and old answer/model/runtime asset reads.

    The guard is a process-local evidence/control mechanism, not an OS sandbox.
    Python source and libraries remain readable; only three original data inputs
    are allowed. No training cache or Frozen model is used.
    """
    allowed={TRAIN.resolve(),CANDIDATES.resolve(),CATALOG.resolve()}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            writing=(isinstance(args[1],str) and any(c in args[1] for c in 'wax+')) or (isinstance(args[2],int) and args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise RuntimeError('Write outside new output')
            if not writing and p.is_relative_to(ROOT) and p.suffix in ('.json','.csv','.npz','.npy'):
                if p not in allowed and not p.is_relative_to(OUT):raise RuntimeError('Forbidden data/artifact read')
        if event in ('os.remove','os.rmdir','os.rename','os.link','os.symlink','os.truncate','subprocess.Popen'):
            raise RuntimeError('Forbidden mutation/process action')
        if event=='os.mkdir' and not Path(args[0]).resolve().is_relative_to(OUT.parent):
            raise RuntimeError('Unexpected directory creation')
    sys.addaudithook(audit)


def write_json(path,value):
    """New-output-only JSON. Never overwrite even an earlier V2-0 output."""
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False)


def write_csv(path,rows):
    """Write common-schema aggregate records, exclusively to a new CSV."""
    with path.open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else [])
        writer.writeheader();writer.writerows(rows)


def main():
    """Exactly three fold fits; no hyperparameter search or access to old labels."""
    os.chdir(ROOT)
    if subprocess.check_output(['git','--no-optional-locks','rev-parse','HEAD'],text=True).strip()!=HEAD:
        raise RuntimeError('HEAD mismatch')
    if OUT.exists():raise RuntimeError('Output already exists; do not overwrite or automatically rerun')
    install_guard()
    import numpy as np
    from perfume.data import fragrantica
    from .splits import build
    from .train import fit_fold
    from .recommend import score
    from .evaluate import metrics,aggregate,paired
    from .robustness import measure,aggregate as aggregate_robustness
    rows=json.loads(TRAIN.read_text());candidates=json.loads(CANDIDATES.read_text())
    folds=build(rows,candidates)
    assert len(candidates)==479 and len(rows)==1805 and len({r[0]for r in rows})==330
    assert [len(f['users'])for f in folds]==[25,25,25]
    assert [len(f['train'])for f in folds]==[1531,1481,1493]
    catalog,_=fragrantica(CATALOG)
    OUT.mkdir(parents=True)
    write_json(OUT/'policy.json',POLICY)
    write_json(OUT/'split_manifest.private.json',folds)
    accuracy=[];robust=[];diagnostics=[];fit_log=[]
    # Count every real call to the original SGD implementation, including failed fits.
    from perfume.models import MatrixFactorization
    entered=[]
    def profile(frame,event,arg):
        if event=='call' and frame.f_code is MatrixFactorization.fit.__code__:
            entered.append(len(entered)+1)
            if len(entered)>3:raise RuntimeError('Baseline fit budget exceeded')
    sys.setprofile(profile)
    for fold in folds:
        n=fold['fold'];print(f'fold {n}: fitting independent MF on {len(fold["train"])} rows',flush=True)
        content,mf,pop,evidence=fit_fold(fold['train'],fold['users'],catalog)
        # No existing-user P is available at inference, even accidentally.
        del mf.P
        evidence['fold']=n;evidence['candidate_factors']=len(set(candidates)&mf.items.keys())
        evidence['final_epoch_loss']=mf.losses[-1]
        fit_log.append(evidence)
        np.savez(OUT/f'fold{n}_factors.npz',Q=mf.Q)
        write_json(OUT/f'fold{n}_model.private.json',dict(items=mf.items,losses=mf.losses,content_idf=content.idf))
        for u in fold['users']:
            support=fold['support'][u];answers=fold['answers'][u]
            known=sum(i in mf.items for i,_ in support)
            tracks={'A':candidates,'B_partial':[i for i in candidates if i in mf.items]}
            for track,pool in tracks.items():
                base=score(support,pool,content,mf,pop)
                changes=measure(support,pool,content,mf,pop,base)
                names=['content','mf','mf_fallback','hybrid'] if track=='A' else ['content','mf','hybrid']
                scopes=[track]+(['B_full5']if track=='B_partial' and known==5 else [])
                for scope in scopes:
                    for method in names:
                        accuracy.append(dict(track=scope,method=method,user=u,fold=n,
                                             accuracy=metrics(base['methods'][method]['top'],answers),
                                             **base['methods'][method]))
                    for r in changes:
                        if r['method']in names:robust.append(dict(track=scope,user=u,fold=n,**r))
                diagnostics.append(dict(track=track,user=u,fold=n,known_support=known,
                    upper=base['upper'],lower=base['lower'],candidate_pool=len(pool),
                    positive_answers=sum(r>=.7 for i,r in answers),
                    positive_untrained=sum(r>=.7 and i not in mf.items for i,r in answers),
                    held_outside_pool=sum(i not in pool for i,r in answers),
                    positive_outside_pool=sum(r>=.7 and i not in pool for i,r in answers),
                    hybrid_margin56=base['methods']['hybrid']['margin56']))
        assert hashlib.sha256(mf.Q.tobytes()).hexdigest()==evidence['q_sha256']
        print(f'fold {n}: inference/robustness complete; Q unchanged',flush=True)
        write_json(OUT/f'fold{n}_fit.json',evidence)
    sys.setprofile(None)
    assert len(entered)==3
    write_csv(OUT/'accuracy.csv',aggregate(accuracy))
    write_csv(OUT/'robustness.csv',aggregate_robustness(robust))
    write_csv(OUT/'paired.csv',paired(accuracy,robust))
    write_json(OUT/'user_results.private.json',dict(accuracy=accuracy,robustness=robust,diagnostics=diagnostics))
    write_json(OUT/'fit_ledger.json',dict(actual_mf_fit_calls=len(entered),fits=fit_log))
    write_json(OUT/'run_metadata.json',dict(status='PASS',python=platform.python_version(),numpy=np.__version__,
        actual_mf_fit_calls=len(entered),old_answers_read=False,old_factors_loaded=False,
        inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in (TRAIN,CANDIDATES,CATALOG)},
        code_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(Path(__file__).parent.rglob('*.py'))},
        notes='No selection; user OOF bootstrap is conditional/descriptive, folds share training users.'))
    print('PASS: exactly 3 MF fits; aggregates and private evidence saved in new output',flush=True)


if __name__=='__main__':main()
