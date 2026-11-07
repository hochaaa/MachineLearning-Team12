"""Saved all50 developer-refit inference only; not CV or independent evaluation."""
import argparse,json
from pathlib import Path
from .core import user_scores
from experiments.scent_v2.accuracy_optimization.run import load_model


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--support',type=Path,required=True);a=p.parse_args()
    rows=json.loads(a.support.read_text())
    if not isinstance(rows,list) or len(rows)!=5 or any(isinstance(r.get('rating'),bool) or not isinstance(r.get('rating'),(int,float)) or not 0<=r['rating']<=10 for r in rows):raise ValueError('Need5 product_id/raw0..10 records')
    c,m,b,meta=load_model(a.model);s=[(r['product_id'],r['rating']/10) for r in rows]
    if any(i not in c.vectors for i,y in s):raise ValueError('Support outside479')
    top=user_scores(meta['spec'],s,sorted(c.vectors),c,m,b);print(json.dumps(dict(top5=top,model=meta['spec'],candidate_count=479),ensure_ascii=False))

if __name__=='__main__':main()
