"""Run the saved developer-selected model locally; no learning or evaluation labels."""
import argparse,json
from pathlib import Path
from .run import load_model
from .core import score_variant


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--support',type=Path,required=True);a=p.parse_args()
    raw=json.loads(a.support.read_text())
    if len(raw)!=5 or any(not isinstance(r.get('rating'),(int,float)) or isinstance(r['rating'],bool) or not 0<=r['rating']<=10 for r in raw):raise ValueError('Five distinct product_id/rating0..10 records required')
    support=[(r['product_id'],r['rating']/10) for r in raw];c,m,b,meta=load_model(a.model)
    if any(i not in c.vectors for i,y in support):raise ValueError('Support not in common479')
    top=score_variant(meta['spec'],support,sorted(c.vectors),c,m,b)
    print(json.dumps(dict(top5=top,model=meta['spec'],candidate_count=479),ensure_ascii=False))

if __name__=='__main__':main()
