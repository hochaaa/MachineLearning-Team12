"""Build source-linked 58-product research artifacts; never read ratings into models."""
import argparse,csv,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
from .compatibility import feature_tokens,transform,coverage
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/scent_v2/perfume_catalog_expansion'
DATE='2026-10-30'
TERM_SOURCES={
 'byredo.com':'https://www.byredo.com/ca_en/terms-of-use',
 'diptyqueparis.com':'https://us.diptyqueparis.com/en-us/policies/legal-notice',
 'lelabofragrances.com':'https://www.lelabofragrances.com/terms-and-conditions.html',
 'jomalone.com':'https://www.jomalone.com/terms-conditions',
 'malaysia.aesop.com':'https://malaysia.aesop.com/pages/terms-conditions'}


def write_json(name,data):
    """Exclusive new-output JSON; no pre-existing result is overwritten."""
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)


def write_csv(name,rows):
    """Source/status columns ensure missing evidence never looks like a verified fact."""
    if not rows:raise ValueError('No evidence rows; do not fake an acquired dataset')
    with (OUT/name).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def product_inventory(path):
    """Read only source product fields; never retain/return user/score/time fields.

    The CSV parser sees raw lines for parsing, but only four product columns are
    selected; no participant IDs or rating values are analyzed or persisted.
    """
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.reader(stream);header=next(reader)
        ix=[header.index(k) for k in ('product_id','brand','product_name','source_type')]
        products={tuple(row[n] for n in ix) for row in reader}
    if len({r[0] for r in products})!=len(products):raise ValueError('Source ID metadata collision')
    return sorted(products)


def canonical_brand(brand):
    """Manually researched bilingual brand labels; never merge product variants."""
    return {'조말론':'Jo Malone London','르라보':'Le Labo','더바디샵':'The Body Shop','러쉬':'Lush','러쉬 LUSH':'Lush',
            '마르지엘라':'Maison Margiela','엑스니힐로':'EX NIHILO','클린':'CLEAN','아리아나그란데향수':'Ariana Grande','샤넬':'Chanel'}.get(brand,brand)


def main():
    """--csv local input contains products; curated source facts are reviewed offline."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--csv',type=Path,required=True)
    a=parser.parse_args()
    if (OUT/'feature_compatibility.json').exists():raise FileExistsError('V2-17 already built; preserve outputs')
    original_hash=hashlib.sha256(a.csv.read_bytes()).hexdigest();products=product_inventory(a.csv)
    evidence=json.loads((OUT/'research_evidence.json').read_text())
    assert len(products)==len(evidence)==58
    assert {b+'|'+n for _,b,n,_ in products}==set(evidence)
    from perfume.data import fragrantica,identity
    from deployment.final_v1.config import assets_path,inspect_assets
    directory=assets_path();runtime_integrity=inspect_assets(directory)
    idf=json.loads((directory/'content.json').read_text())['idf'];idf_hash=hashlib.sha256((directory/'content.json').read_bytes()).hexdigest()
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());assert len(candidates)==len(set(candidates))==479
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
    active={t for i in candidates for t in catalog[i]['tokens']}
    source_roles=defaultdict(set);source_fields=defaultdict(set)
    identities=[];metadata=[];notes_rows=[];accord_rows=[];unresolved=[];compat=[];all_qualified_tokens=set();vectors={}
    prospective=defaultdict(list)
    for pid,brand,name,kind in products:
        e=evidence[brand+'|'+name];prospective[e['official_url'].split('?')[0]].append(pid)
    for pid,brand,name,kind in products:
        e=evidence[brand+'|'+name];url=e['official_url'];note_url=e['notes_url']
        source_roles[url].add('official_product_or_reference_identity');source_fields[url].update(('name','concentration','status'))
        source_roles[note_url].add('official_notes_reference');source_fields[note_url].update(('notes','explicit_named_accords'))
        found_notes=[n for values in e['notes'].values() for n in values]
        eligible=e['identity_verified'] and bool(found_notes)
        if 'family-level' in e['review_reason']:eligible=False
        # VERIFIED is deliberately stringent for this research: exact identity,
        # source-declared notes and at least one literally named accord, no conflicts.
        if 'Only official shower gel' in e['review_reason']:status='UNRESOLVED'
        elif not e['identity_verified']:status='NEEDS_REVIEW'
        elif not e['review_reason'] and found_notes and e['explicit_accords']:status='VERIFIED'
        else:status='PARTIALLY_VERIFIED'
        verified_name=e['official_name'] if e['identity_verified'] else ''
        brand_official=canonical_brand(brand)
        # Conservative proof of duplicates only. Official suffix spelling may give
        # false negatives; no product is accepted as different merely by this test.
        duplicate_ids=[i for i in candidates if e['identity_verified'] and identity(catalog[i]['brand'],catalog[i]['name'])==identity(brand_official,verified_name)]
        possible=[other for other in prospective[url.split('?')[0]] if other!=pid]
        identities.append(dict(source_product_id=pid,source_type=kind,original_brand=brand,original_product_name=name,
            official_brand=brand_official,official_product_name=verified_name,reference_product_name=e['official_name'],
            concentration=e['concentration'],product_variant='Preserve supplied concentration/Absolu/edition; original batch/year unspecified',
            product_status=e['product_status'] if status!='UNRESOLVED' else 'UNRESOLVED; discontinued only stated in original input',
            official_product_url=url if e['identity_verified'] else '',reference_url=url,identity_verified=e['identity_verified'],
            quality_status=status,possible_duplicate_source_ids='|'.join(possible),confirmed_existing479_ids='|'.join(duplicate_ids),
            duplicate_check='Exact full-name only; semantic duplicate manual review remains',checked_date=DATE,review_reason=e['review_reason']))
        metadata.append(dict(source_product_id=pid,quality_status=status,identity_verified=e['identity_verified'],
            confirmed_notes_usable_for_compatibility=eligible,notes_provided_count=len(found_notes),explicit_named_accord_count=len(e['explicit_accords']),
            accords_scope='Literally named composition accords; not inferred/main-accord intensity profile',
            official_scent_descriptors=e['official_scent_descriptors'],descriptors_used_as_accords=False,
            pyramid_scope='Only source-declared layers; unspecified stays unspecified',
            source_url=note_url,identity_source_url=url,checked_date=DATE,usage_status=e['usage'],
            rollout_ready=False,limitations=e['review_reason'] or 'Manufacturer notes are not complete formula; main-accord profile/intensities not supplied'))
        for layer,values in e['notes'].items():
            for label in values:
                token=next(iter(feature_tokens([label],[])))
                notes_rows.append(dict(source_product_id=pid,layer=layer,original_note_label=label,normalized_token=token,
                    in_frozen_idf=token in idf,in_active479_features=token in active,
                    identity_scope_confirmed=eligible,source_type='manufacturer_declared_note',source_url=note_url,checked_date=DATE))
        for label in e['explicit_accords']:
            token=next(iter(feature_tokens([],[label])))
            accord_rows.append(dict(source_product_id=pid,original_accord_label=label,normalized_token=token,
                accord_kind='official_named_composition_accord',main_accord_intensity='NOT_PUBLISHED',
                in_frozen_idf=token in idf,in_active479_features=token in active,identity_scope_confirmed=eligible,
                source_url=note_url,checked_date=DATE))
        if status!='VERIFIED':unresolved.append(dict(source_product_id=pid,quality_status=status,original_brand=brand,original_product_name=name,
            reason=e['review_reason'] or 'Identity/notes available; independent main-accord set not established',
            reference_url=url,checked_date=DATE,next_action='Confirm original concentration/batch or missing accord evidence; no automatic merge or expansion'))
        tokens=feature_tokens(found_notes,e['explicit_accords']) if eligible else set()
        vector=transform(tokens,idf) if eligible else None
        if vector is not None:vectors[pid]=vector;all_qualified_tokens.update(tokens)
        compat.append(dict(source_product_id=pid,identity_verified=e['identity_verified'],metadata_assessed=eligible,
            vector_state='NOT_ASSESSED_IDENTITY_OR_METADATA' if vector is None else 'NONZERO' if vector else 'ZERO_ALL_OBSERVED_TOKENS_OOV',
            observed_tokens=len(tokens) if eligible else None,known_frozen_tokens=len(vector) if vector is not None else None,
            note_coverage=coverage(tokens,idf)['note'] if eligible else None,accord_coverage=coverage(tokens,idf)['accord'] if eligible else None,
            production_eligible=False))
    write_csv('perfume_identity_mapping.csv',identities);write_csv('perfume_metadata_research.csv',metadata)
    write_csv('perfume_notes.csv',notes_rows);write_csv('perfume_accords.csv',accord_rows);write_csv('unresolved_perfumes.csv',unresolved)
    for url in list(source_roles):
        for domain,terms in TERM_SOURCES.items():
            if domain in url:source_roles[terms].add('terms_review');source_fields[terms].add('access_and_reuse_conditions')
    registry=[]
    for n,url in enumerate(sorted(source_roles),1):
        registry.append(dict(source_id=f'S{n:03}',url=url,source_roles='|'.join(sorted(source_roles[url])),
            fields_checked='|'.join(sorted(source_fields[url])),checked_date=DATE,source_authority='Official manufacturer/distributor website',
            evidence_method='Targeted web search/page review; no page-dump downloader or database scraper',
            reuse_policy='Factual local research/reference only; permission for ML deployment/public data redistribution not established',
            copyright_material_copied='No images, reviews, prose descriptions or full pages stored',
            terms_status='Terms page inspected; no new license granted' if 'terms_review' in source_roles[url] else 'Linked terms reviewed where registry lists one; otherwise UNVERIFIED',
            uncertainty='Region/SKU/current page may not match original rated bottle batch'))
    write_csv('source_registry.csv',registry)
    summary=dict(research_date=DATE,source_product_ids=len(products),identity_verified=sum(r['identity_verified'] for r in identities),
        confirmed_notes_products=sum(r['metadata_assessed'] for r in compat),reference_notes_products=sum(bool(e['notes']) and any(e['notes'].values()) for e in evidence.values()),
        confirmed_explicit_named_accord_products=sum(bool(evidence[b+'|'+n]['explicit_accords']) and evidence[b+'|'+n]['identity_verified'] for _,b,n,k in products),
        accords_note='Named composition accords differ from main accord profiles; official aroma/family descriptors not converted into accords',
        quality_counts=dict(Counter(r['quality_status'] for r in identities)),
        exact_full_name_existing479_duplicate_records=sum(bool(r['confirmed_existing479_ids']) for r in identities),
        duplicate_limit='Exact key only cannot prove zero semantic duplicates; unresolved custom IDs are not counted as distinct expansion items',
        possible_new_duplicate_groups=sum(len(pids)>1 for pids in prospective.values()),
        frozen_idf_vocabulary=len(idf),active_existing479_features=len(active),
        aggregate_unique_token_coverage_frozen=coverage(all_qualified_tokens,idf),
        aggregate_unique_token_coverage_active479=coverage(all_qualified_tokens,active),
        representable_nonzero=sum(r['vector_state']=='NONZERO' for r in compat),
        confirmed_zero_vectors=sum(r['vector_state']=='ZERO_ALL_OBSERVED_TOKENS_OOV' for r in compat),
        not_assessed=sum(not r['metadata_assessed'] for r in compat),
        not_assessed_is_not_zero=True,vector_semantic_quality='Not validated by nonzero vector existence',
        production_catalog_expanded=False,MF_factors_created=False,model_fits=0,recommendations=0,evaluations=0,
        idf_payload_sha256=idf_hash,runtime_integrity=runtime_integrity['status'],original_csv_sha256=original_hash,
        per_product=compat)
    write_json('feature_compatibility.json',summary);write_json('research_vectors.json',vectors)
    if hashlib.sha256(a.csv.read_bytes()).hexdigest()!=original_hash:raise AssertionError('Original CSV changed')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('per_product','aggregate_unique_token_coverage_frozen','aggregate_unique_token_coverage_active479')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
