"""Freeze development-selected models BEFORE any test-label evaluation. Refuses overwrite."""
import sys
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from perfume.data import read_json,write_json,fragrantica
from perfume.improvements import make_mf,ProfileContent
from perfume.models import Baseline
from perfume.frozen import sha256


def main():
    directory=Path('outputs/final')
    directory.mkdir(exist_ok=True)
    if (directory/'freeze.json').exists():raise FileExistsError('A final configuration is already frozen')
    selected=read_json('outputs/improvement/selection.json')
    train_path=Path(f'outputs/validation/train_exclude_{selected["threshold"]}.json')
    train=read_json(train_path)
    catalog,_=fragrantica('Term-project-datasets/fra_cleaned.csv')
    mf=make_mf(selected['mf'],selected['seed']).fit(train)
    content=ProfileContent(selected['profile_mode'],selected['relevance']).fit(catalog,mf.items)
    baseline=Baseline().fit(train)
    arrays={name:getattr(mf,name) for name in ('P','Q','user_bias','item_bias') if hasattr(mf,name)}
    np.savez(directory/'model.npz',**arrays)
    metadata={'users':mf.users,'items':mf.items,'global_mean':baseline.mean,
              'popularity_counts':dict(baseline.counts),'popularity_maximum':baseline.maximum}
    if hasattr(mf,'mean'):metadata['mean']=mf.mean
    write_json(directory/'model.json',metadata)
    write_json(directory/'content.json',{'idf':content.idf,'vectors':content.vectors})
    files=[train_path,Path('outputs/improvement/candidates.json'),Path('outputs/improvement/selection.json'),
           Path('configs/improvement.json'),Path('Term-project-datasets/fra_cleaned.csv'),
           *Path('src/perfume').glob('*.py'),Path('scripts/final_evaluate.py'),Path('scripts/freeze.py'),
           *[directory/name for name in ('model.npz','model.json','content.json')]]
    freeze={'selected':selected,'train_path':str(train_path),'candidates_path':'outputs/improvement/candidates.json',
            'protected_sha256':{str(p):sha256(p) for p in files},
            'external_raw_sha256':{str(p):sha256(p) for p in Path('Term-project-datasets').glob('*.json')},
            'note':'Created after validation-only selection; no internal or external test metrics read for selection'}
    with (directory/'freeze.json').open('x') as stream:json.dump(freeze,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'frozen':True,'selected':selected},ensure_ascii=False))


if __name__=='__main__':main()
