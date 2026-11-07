"""ID-only check that merged training exports are not new independent users."""
import csv,json
from pathlib import Path
from .core import ROOT,OUT,read_identities,write


def main():
    known={u for u,i,t in read_identities(ROOT/'outputs/validation/train_exclude_3.json')};report=[]
    for name in ['merged_real_ratings.csv','training_ready_ratings.csv']:
        path=ROOT/'outputs/scent_v2/real_user_dataset/data'/name
        with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        users={r['user_id'] for r in rows};report.append(dict(path=str(path.relative_to(ROOT)),rows=len(rows),users=len(users),known_original_users=len(users&known),new_user_IDs=len(users-known),rating_numeric_values_decoded=0))
    assert all(r['new_user_IDs']==0 for r in report),'Unexpected new identities in merged exports: review, no automatic evaluation'
    write(OUT/'historical_export_check.json',dict(status='HISTORICAL_COPIES_ONLY',exports=report))
    audit=json.loads((OUT/'data_independence_audit.json').read_text());audit['historical_merged_exports']=report;(OUT/'data_independence_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False))
    print('Merged/training-ready exports:0 new IDs; no numeric ratings decoded')

if __name__=='__main__':main()
