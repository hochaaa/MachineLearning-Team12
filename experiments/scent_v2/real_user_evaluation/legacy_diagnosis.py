"""Identity-only diagnosis of original85. No notes/scoring/fitting or retroactive consent."""
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path
from experiments.scent_v2.real_user_dataset.storage import atomic_write,csv_bytes
from experiments.scent_v2.real_rating_retraining.audit import read_csv
from experiments.scent_v2.expanded_content.catalog import licensed_match
from .app import ROOT,OUT


def main():
    """--csv: authorized existing85 original; emit aggregate identity-review evidence only."""
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--csv',type=Path,required=True);a=p.parse_args()
    before=hashlib.sha256(a.csv.read_bytes()).hexdigest();ratings,audit=read_csv(a.csv)
    prev=ROOT/'outputs/scent_v2/expanded_content';summary=json.loads((prev/'expanded_feature_summary.json').read_text());mapping=summary['canonical_mapping']
    provenance=json.loads((prev/'licensed_source/provenance.json').read_text())
    assert provenance['license']=='CC-BY-4.0' and provenance['commit']=='58da85556a4bb42a7d56279d66fbec4dbf42cc4a'
    for entry in provenance['files']:assert hashlib.sha256((prev/'licensed_source'/entry['path']).read_bytes()).hexdigest()==entry['sha256']
    source=[json.loads(line) for line in (prev/'licensed_source/perfumes.jsonl').read_text().splitlines() if line.strip()]
    previous={r['source_product_id']:r['status'] for r in csv.DictReader((prev/'candidate_review.csv').open())}
    products={r['product_id']:(r['brand'],r['product_name'],r['source_type']) for r in ratings};counts=Counter(r['product_id'] for r in ratings);reviews=[]
    for pid,(brand,full,kind) in sorted(products.items()):
        if pid in mapping:continue
        names=[];exact=None
        if kind=='catalog' and ' · ' in full:
            name,form=full.rsplit(' · ',1);exact=licensed_match(brand,name,form,source)
            # Identity-only lexical exact names; not a concentration match and never accepted.
            from perfume.data import normalize
            names=[r for r in source if normalize(r['house'])==normalize(brand) and normalize(r['name'])==normalize(name)]
        reason='EXACT_LICENSED_IDENTITY_REVIEW_REQUIRED' if exact else 'NAME_ONLY_CONCENTRATION_NOT_CONFIRMED' if names else 'NO_EXACT_LICENSED_IDENTITY'
        reviews.append(dict(source_product_id=pid,brand=brand,original_product_name=full,associated_ratings=counts[pid],previous_status=previous[pid],
            identity_diagnostic=reason,exact_licensed_name=exact['name'] if exact else '',exact_declared_concentration=exact['concentration'] if exact else '',
            note='DIAGNOSIS_ONLY: not appended to catalog, not scored, no fuzzy translation/version inference'))
    result=dict(source='Existing voluntarily supplied12-person85-rating data; original project-local consent, not V2-21 new collection',
        source_sha256=before,raw_users=audit['users'],raw_ratings=len(ratings),source_products=len(products),
        current_licensed_catalog_linked_ratings=sum(r['product_id'] in mapping for r in ratings),unlinked_ratings=sum(r['product_id'] not in mapping for r in ratings),
        unlinked_products=len(reviews),by_previous_status={s:dict(products=sum(r['previous_status']==s for r in reviews),ratings=sum(r['associated_ratings'] for r in reviews if r['previous_status']==s)) for s in sorted({r['previous_status'] for r in reviews})},
        identity_diagnosis={s:dict(products=sum(r['identity_diagnostic']==s for r in reviews),ratings=sum(r['associated_ratings'] for r in reviews if r['identity_diagnostic']==s)) for s in sorted({r['identity_diagnostic'] for r in reviews})},
        newly_linked=0,new_candidates=0,training_or_scoring=False,old_files_modified=False,
        new_consent_or_delete_policy_applied_to_existing85=False,
        alternatives=['Ask original respondent to confirm exact full product/concentration without rewriting original CSV; use separate reviewed identity link table.',
            'Preserve unmatched preferences as coverage/experience-mismatch evidence and recruitment planning, not candidate-ranking accuracy labels.',
            'Acquire rights-cleared exact product metadata for unresolved identities under a separately approved catalog version; do not infer notes/variants.',
            'Evaluate approved18 with additional experienced users; existing8 users37 linked ratings remain valid local research input but not independent new collection.'])
    assert before==hashlib.sha256(a.csv.read_bytes()).hexdigest()
    with (OUT/'legacy85_diagnosis.json').open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False)
    atomic_write(OUT/'legacy85_product_review.csv',csv_bytes(list(reviews[0]),reviews))
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
