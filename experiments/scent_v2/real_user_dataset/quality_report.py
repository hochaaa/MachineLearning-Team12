"""Safe local dashboard: dev label distribution; independent counts only."""
import statistics,math,json
from collections import Counter,defaultdict


def distribution(values):
 return dict(count=len(values),mean=statistics.mean(values)if values else None,median=statistics.median(values)if values else None,sd=statistics.pstdev(values)if values else None,min=min(values)if values else None,max=max(values)if values else None)


def summarize(participants,roles,candidates,kind):
 def counts(rows):
  users=Counter(r['user_id']for r in rows);return dict(submitters=len(users),ratings=len(rows),rated_items=len({r['perfume_id']for r in rows}),unrated_items=candidates-len({r['perfume_id']for r in rows}),Support5_users=sum(n>=5 for n in users.values()),Support5_Target_users=sum(n>=6 for n in users.values()),users_lt5=sum(n<5 for n in users.values()),users_exact5=sum(n==5 for n in users.values()))
 dev=roles['development'];val=[r['rating']for r in dev];by=defaultdict(list)
 for r in dev:by[r['user_id']].append(r['rating'])
 per_item=Counter(r['perfume_id']for r in dev)
 result=dict(dataset_kind=kind,actual_new_real_ratings=sum(len(v)for v in roles.values())if kind=='real_user_collection'else 0,test_fixture_ratings=sum(len(v)for v in roles.values())if kind=='test_fixture'else 0,participants=len(participants),consented_participants=len(participants),development_participants=sum(p['role']=='development'for p in participants),independent_participants=sum(p['role']=='independent'for p in participants),development=counts(dev),independent=counts(roles['independent']),development_rating_distribution=distribution(val),development_positive_ge7_fraction=sum(y>=7 for y in val)/len(val)if val else None,development_low_lt5_fraction=sum(y<5 for y in val)/len(val)if val else None,development_zero_fraction=sum(y==0 for y in val)/len(val)if val else None,development_rating_histogram=[dict(rating=k/2,count=val.count(k/2))for k in range(21)],development_unit_errors=sum(not math.isfinite(y)or not 0<=y<=10 or y*2!=round(y*2)for y in val),development_user_activity_histogram=dict(Counter(len(v)for v in by.values())),development_user_distinct_rating_counts=distribution([len(set(v))for v in by.values()]),development_user_rating_range=distribution([max(v)-min(v)for v in by.values()if len(v)>=2]),development_item_count_histogram_including_zeros=dict(Counter([per_item[i]for i in per_item]+[0]*(candidates-len(per_item)))),independent_label_values_or_histograms='WITHHELD; counts/eligibility only',new_accuracy_measurement='NOT_RUN')
 result['development_new_dataset_long_tail']=dict(observed_items_n1=sum(n==1 for n in per_item.values()),observed_items_n_le2=sum(n<=2 for n in per_item.values()),ratings_on_items_n_le2=sum(n for n in per_item.values()if n<=2),definition='Counts within new development collection, not the original model training frequency')
 from .config import ROOT
 import csv
 path=ROOT/'outputs/scent_v2/data_evaluation_diagnostics/train_only/perfume_popularity.csv'
 if path.exists():
  with path.open(encoding='utf-8',newline='')as f:base={r['perfume_id']:int(r['observations'])for r in csv.DictReader(f)}
  result['development_legacy_tail_coverage']=dict(available=True,original_unobserved_items_newly_rated=sum(i in base and base[i]==0 for i in per_item),original_n_le2_items_newly_rated=sum(i in base and base[i]<=2 for i in per_item),new_ratings_on_original_n_le2_items=sum(n for i,n in per_item.items()if i in base and base[i]<=2),baseline_scope='V2-13 strict all75-evaluation-user-excluded Train counts; not actual per-fold Train')
 else:result['development_legacy_tail_coverage']=dict(available=False)
 return result


def main():
 import argparse
 from .catalog import load_catalog
 from .storage import Store,atomic_write
 from .config import DATA,OUT
 p=argparse.ArgumentParser();p.add_argument('--output',type=str);args=p.parse_args();s=Store(DATA,load_catalog());q=s.aggregate();target=OUT/'dataset_quality.json'if not args.output else __import__('pathlib').Path(args.output)
 # Outputs stay within this newly-created experiment directory.
 if not target.resolve().is_relative_to(OUT.resolve()):raise ValueError('Quality output must stay in new output directory')
 atomic_write(target,json.dumps(q,ensure_ascii=False,indent=2,allow_nan=False).encode());print(json.dumps(q,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
