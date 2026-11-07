"""Future actual-user CSV evaluation; two locked models, no fit/tuning."""
import argparse,json,re
from .core import OUT,evaluate_csv


def main():
    p=argparse.ArgumentParser(description='One-time real-user evaluation of frozen V33 policy')
    p.add_argument('--csv',required=True);p.add_argument('--provenance',required=True);p.add_argument('--run-id',required=True);args=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.run_id):raise ValueError('run-id: letters/digits/_/- only')
    result=evaluate_csv(args.csv,args.provenance,OUT/'evaluations'/args.run_id)
    print(json.dumps(dict(status=result['status'] if result else 'NOT_EVALUATED_NO_ELIGIBLE_USERS'),ensure_ascii=False))

if __name__=='__main__':main()
