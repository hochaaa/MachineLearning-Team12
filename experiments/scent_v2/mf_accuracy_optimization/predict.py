"""Inference of the saved raw-alpha model; no fit or answer input."""
import argparse,json
from pathlib import Path
from .core import components,hybrid
from .run import load_model
from experiments.scent_v2.recommend import rank


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--support',type=Path,required=True);a=p.parse_args()
    rows=json.loads(a.support.read_text())
    if not isinstance(rows,list) or len(rows)!=5 or any(isinstance(r.get('rating'),bool) or not isinstance(r.get('rating'),(int,float)) or not 0<=r['rating']<=10 for r in rows):raise ValueError('Need5 distinct product_id / raw rating0..10 records')
    c,m,b,meta=load_model(a.model);support=[(r['product_id'],r['rating']/10) for r in rows]
    if any(i not in c.vectors for i,r in support):raise ValueError('Support outside479')
    x=components(support,sorted(c.vectors),c,m,b);scores=hybrid(x['content'],x['mf'],meta['spec']['alpha'],b.score(x['pool']));lookup=dict(zip(x['pool'],map(float,scores)));top=rank(x['pool'],scores)[:5]
    print(json.dumps(dict(alpha=meta['spec']['alpha'],results=[dict(id=i,rank=n+1,score=lookup[i]) for n,i in enumerate(top)]),ensure_ascii=False))

if __name__=='__main__':main()
