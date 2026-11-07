"""Restrict this experiment to original Train and existing development artifacts."""
import sys,os
from pathlib import Path
from .diagnostic import ROOT,OUT


def guard():
    allowed={ROOT/p for p in ['outputs/validation/train_exclude_3.json','outputs/improvement/candidates.json','Term-project-datasets/fra_cleaned.csv','outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json','outputs/scent_v2/similarity_reranking/evaluation_results.json','outputs/scent_v2/background_data_recovery/best_model.npz','outputs/scent_v2/background_data_recovery/verification.json','outputs/scent_v2/background_data_recovery/evaluation_results.json']}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2];writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise PermissionError('V33 outputs only')
            if not writing and p.is_relative_to(ROOT) and (p.is_relative_to(ROOT/'outputs') or p.suffix in ('.csv','.json','.npz','.npy')) and p not in allowed and not p.is_relative_to(OUT) and not p.is_relative_to(ROOT/'experiments'):raise PermissionError('Old final/private data/models forbidden')
        if event in ('socket.connect','subprocess.Popen','os.rename','os.remove','os.rmdir','os.symlink'):raise PermissionError('Unneeded action denied')
    sys.addaudithook(audit)
