"""Local saved model inference, no user ID, learning or answer labels."""
import argparse,json
from pathlib import Path
from .run import load_model
from .core import predict


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--support',type=Path,required=True);a=p.parse_args()
    rows=json.loads(a.support.read_text())
    if not isinstance(rows,list) or len(rows)!=5 or any(isinstance(r.get('rating'),bool) or not isinstance(r.get('rating'),(float,int)) or not 0<=r['rating']<=10 for r in rows):raise ValueError('Need5 product_id / raw0..10 records')
    c,m,b,meta=load_model(a.model);support=[(r['product_id'],r['rating']/10) for r in rows]
    if any(i not in c.vectors for i,y in support):raise ValueError('Outside479')
    print(json.dumps(dict(model=meta['spec'],top5=predict(meta['spec'],support,sorted(c.vectors),c,m,b)),ensure_ascii=False))

if __name__=='__main__':main()
