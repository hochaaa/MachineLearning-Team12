"""Existing85 product-only link table; no source mutation or catalog expansion beyond497."""
import argparse,csv,json
from pathlib import Path
from collections import Counter
from .engine import ROOT,OUT,Engine,MODES
from experiments.scent_v2.real_rating_retraining.audit import read_csv
from experiments.scent_v2.expanded_content.catalog import licensed_match,concentration
from experiments.scent_v2.expanded_content.models import canonical_id


def main():
    p=argparse.ArgumentParser();p.add_argument('--csv',type=Path,required=True);a=p.parse_args();rows,_=read_csv(a.csv);engine=Engine()
    old=engine.expanded['canonical_mapping'];products={r['product_id']:(r['brand'],r['product_name'],r['source_type']) for r in rows};counts=Counter(r['product_id'] for r in rows)
    previous=json.loads((ROOT/'outputs/scent_v2/real_user_evaluation/legacy85_diagnosis.json').read_text())
    review={r['source_product_id']:r for r in csv.DictReader((ROOT/'outputs/scent_v2/real_user_evaluation/legacy85_product_review.csv').open())}
    path=ROOT/'outputs/scent_v2/expanded_content/licensed_source';provenance=json.loads((path/'provenance.json').read_text());assert provenance['license']=='CC-BY-4.0'
    source=[json.loads(line) for line in (path/'perfumes.jsonl').read_text().splitlines() if line.strip()]
    table=[]
    for pid,(brand,full,kind) in sorted(products.items()):
        name,form=full.rsplit(' · ',1) if ' · ' in full else (full,'UNKNOWN')
        if pid in old:cid=old[pid];status='VERIFIED_ACTIVE497';evidence='Existing V2-18 exact brand/product/concentration mapping, preserved';need=False
        else:
            match=licensed_match(brand,name,form,source) if kind=='catalog' and form!='UNKNOWN' else None
            if match:
                cid=canonical_id(brand,match['name'],concentration(match['concentration']));status='VERIFIED_LICENSED_OUTSIDE_ACTIVE497' if cid not in engine.catalog else 'VERIFIED_ACTIVE497'
                evidence='Unique exact original brand/name/concentration == pinned Scento CC-BY-4.0 row; independent of V2-17 manufacturer metadata';need=False
            else:
                cid='';status=review[pid]['identity_diagnostic'];evidence='No unique full identity+concentration match in approved local snapshot; no fuzzy/translation/concentration inference';need=True
        table.append(dict(source_product_id=pid,original_brand=brand,original_product_name=name,original_concentration=form,canonical_product_id=cid,
            match_status=status,matching_evidence=evidence,review_required=need,active_catalog=cid in engine.catalog,associated_rating_count=counts[pid]))
    with (OUT/'catalog_mapping.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    summary=dict(raw_ratings=len(rows),products=len(products),active497_linked_ratings=sum(r['associated_rating_count'] for r in table if r['active_catalog']),
        identity_verified_ratings=sum(r['associated_rating_count'] for r in table if not r['review_required']),
        verified_outside497_ratings=sum(r['associated_rating_count'] for r in table if r['match_status']=='VERIFIED_LICENSED_OUTSIDE_ACTIVE497'),
        identity_unresolved_ratings=sum(r['associated_rating_count'] for r in table if r['review_required']),active_catalog_count=497,raw_users_exported=False,
        note='Identity linkage38 incl1 outside497; current usable linkage37 unchanged. No new product added to497.')
    with (OUT/'mapping_summary.json').open('x') as f:json.dump(summary,f,indent=2)
    # Recommendation functionality comparison, NOT ranking accuracy measurements.
    support=[dict(product_id=i,rating=7) for i in sorted(engine.new)[:5]];old_support=[dict(product_id=i,rating=7) for i in sorted(engine.old)[:5]]
    comparison=[]
    for m in MODES:
        s=old_support if m==MODES[0] else support;result=engine.recommend(s,m)
        comparison.append(dict(mode=m,candidates=479 if m==MODES[0] else 497,input_kind='SYNTHETIC_OLD5' if m==MODES[0] else 'SYNTHETIC_NEW5',top5=len(result),new_top5=sum(r['origin']=='new18' for r in result),MF_new_item_factors='NONE',accuracy='NOT_EVALUATED'))
    mixed=[dict(product_id=i,rating=7) for i in sorted(engine.new)[:2]+sorted(engine.old)[:3]]
    result=engine.recommend(mixed,MODES[2])
    comparison.append(dict(mode=MODES[2],candidates=497,input_kind='SYNTHETIC_MIXED_2NEW_3OLD',top5=len(result),new_top5=sum(r['origin']=='new18' for r in result),MF_new_item_factors='NONE',accuracy='NOT_EVALUATED'))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    print(json.dumps(summary))

if __name__=='__main__':main()
