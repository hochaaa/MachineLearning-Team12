"""Fixed reconstructed new-user folds: conditioning/latent attribution, no evaluation/tuning."""
import sys,json,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from failure_diagnosis import ROOT,OUT,DOUT,guard,sha,bundle,newuser_folds,train_mf,fold_in,deny_legacy

def main():
    guard();target=DOUT/'ridge_stability.json'
    if target.exists():raise RuntimeError('Do not overwrite stability results')
    sys.addaudithook(deny_legacy)
    config=json.loads((OUT/'models/model.json').read_text())['config'];receipts=json.loads((DOUT/'reconstructed_model_receipts.json').read_text())
    train,pool,catalog,raw=bundle();records=[];reg=config['foldin_regularization']
    for fold,fit,p,supports,answers,excluded,held in newuser_folds(train,pool):
        epochs=next(r['v2_epochs'] for r in receipts if r['protocol']=='newuser' and r['fold']==fold)
        model=train_mf(fit,dict(config['mf_config'],epochs=epochs,early=False),12);q0=model.Q.copy()
        for history in supports.values():
            known=sorted(history);a=np.array([np.r_[model.Q[model.items[i]],1.] for i,_ in known]);y=np.array([r-model.mean-model.bi[model.items[i]] for i,r in known])
            gram=a.T@a+len(known)*reg*np.eye(a.shape[1]);z=fold_in(model,known,reg)
            records.append({'fold':fold,'support_n':len(known),'condition_number':float(np.linalg.cond(gram)),'min_eigenvalue':float(np.linalg.eigvalsh(gram).min()),'normal_equation_residual_norm':float(np.linalg.norm(gram@z-a.T@y)),'user_vector_norm':float(np.linalg.norm(z[:-1]))})
        assert np.array_equal(q0,model.Q)
    result={'scope':'fixed STEP5 new-user fold models/epochs reconstructed; no ranking/accuracy evaluation, no new regularization values','regularization':reg,'users':len(records),'mean_condition_number':float(np.mean([r['condition_number'] for r in records])),'max_condition_number':max(r['condition_number'] for r in records),'minimum_eigenvalue':min(r['min_eigenvalue'] for r in records),'maximum_normal_residual':max(r['normal_equation_residual_norm'] for r in records),'per_request_anonymous':records,'item_factors_unchanged':True}
    target.write_text(json.dumps(result,indent=2));guard();print({k:v for k,v in result.items() if k!='per_request_anonymous'})
if __name__=='__main__':main()
