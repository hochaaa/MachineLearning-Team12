"""CLI inference from the selected immutable model. Never reads evaluation answers."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from perfume.data import read_json,fragrantica
from perfume.frozen import load_frozen
from perfume.models import hybrid,knowledge


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support',required=True,help='JSON [[Fragrantica URL,rating 0..1], ...]')
    parser.add_argument('--required',action='append',default=[])
    parser.add_argument('--forbidden',action='append',default=[])
    parser.add_argument('--preferred',action='append',default=[])
    parser.add_argument('--k',type=int,default=10)
    args=parser.parse_args()
    if args.k<1:raise ValueError('k must be positive')
    freeze,mf,content,baseline=load_frozen('outputs/final')
    selected=freeze['selected']
    catalog,_=fragrantica('Term-project-datasets/fra_cleaned.csv')
    support=read_json(args.support)
    if len({i for i,_ in support})!=len(support):raise ValueError('Duplicate support item')
    for item,rating in support:
        if item not in catalog or not isinstance(rating,(int,float)) or not np.isfinite(rating) or not 0<=rating<=1:
            raise ValueError('Support requires catalog URLs and finite normalized ratings')
    seen={i for i,_ in support}
    pool=[i for i in read_json(freeze['candidates_path']) if i not in seen]
    vector=mf.fold_in(support)
    m=mf.score_vector(vector,pool) if vector is not None else np.full(len(pool),np.nan)
    c=content.score(support,pool)
    scores=hybrid(c,m,selected['alpha'],baseline.score(pool))
    result=knowledge(catalog,pool,scores,args.required,args.forbidden,args.preferred)[:args.k]
    print(json.dumps({'zero_policy':'exclude as analytical assumption; semantics unresolved',
       'threshold':selected['threshold'],'mf':selected['mf'],'alpha':selected['alpha'],
       'results':[{'item':i,'name':catalog[i]['name'],'brand':catalog[i]['brand'],'score':score,
                   'explanation':{**explanation,'factor_available':i in mf.items,
                    'shared_tokens':sorted(set(catalog[i]['tokens']) & {t for j,_ in support for t in catalog[j]['tokens']})}}
                  for i,score,explanation in result]},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
