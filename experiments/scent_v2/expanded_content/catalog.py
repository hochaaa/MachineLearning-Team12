"""Only the independently licensed snapshot supplies new inference metadata."""
import csv,hashlib,json
from collections import defaultdict
from pathlib import Path
from perfume.data import normalize
from .models import canonical_id,project
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/scent_v2/expanded_content'


def concentration(value):
    """Normalize explicit declared form, preserving named variants; no missing inference."""
    value=normalize(value)
    return {'eau de parfum':'edp','eau de toilette':'edt','eau de cologne':'edc','cologne':'edc'}.get(value,value)


def licensed_match(brand,name,form,rows):
    """Full identity exact match; explicitly named Absolu variant exception only."""
    hits=[]
    for r in rows:
        if normalize(r['house'])!=normalize(brand):continue
        if normalize(r['name'])==normalize(name) and concentration(r['concentration'])==concentration(form) and r['concentration']:
            hits.append(r)
        elif concentration(form)=='absolu de parfum' and normalize(r['name'])==normalize(name+' '+form) and concentration(r['concentration']) in ('parfum','absolu de parfum'):
            hits.append(r)
    return hits[0] if len(hits)==1 else None


def build(existing_vectors,idf,old_catalog,original_products):
    """Return isolated catalog, source mapping and gates; no unlicensed notes loaded."""
    raw=OUT/'licensed_source';provenance=json.loads((raw/'provenance.json').read_text())
    if provenance['license']!='CC-BY-4.0':raise PermissionError('Pinned licensed source required')
    for entry in provenance['files']:
        if hashlib.sha256((raw/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Licensed snapshot changed')
    if 'CC BY 4.0' not in (raw/'LICENSE').read_text():raise PermissionError('License changed')
    source=[json.loads(line) for line in (raw/'perfumes.jsonl').read_text().splitlines() if line.strip()]
    # Read only the prior RESEARCH IDENTITY exclusion flags, never notes/accords/vectors.
    identity=list(csv.DictReader((ROOT/'outputs/scent_v2/perfume_catalog_expansion/perfume_identity_mapping.csv').open()))
    denied={r['source_product_id'] for r in identity if r['identity_verified']!='True'}
    old_ids=set(existing_vectors);vectors={i:dict(v) for i,v in existing_vectors.items()};mapping={};review=[];new={};seen_keys=set()
    old_keys={(normalize(r['brand']),normalize(r['name'])) for i,r in old_catalog.items() if i in old_ids}
    for pid,brand,full,kind in original_products:
        if pid in denied:
            review.append(dict(source_product_id=pid,brand=brand,name=full,status='HOLD_V217_UNRESOLVED_IDENTITY'));continue
        if kind!='catalog' or ' · ' not in full:
            review.append(dict(source_product_id=pid,brand=brand,name=full,status='HOLD_NO_EXACT_LICENSED_BILINGUAL_MATCH'));continue
        name,form=full.rsplit(' · ',1)
        row=licensed_match(brand,name,form,source)
        if row is None:
            review.append(dict(source_product_id=pid,brand=brand,name=full,status='HOLD_NO_UNIQUE_LICENSED_NAME_CONCENTRATION'));continue
        if (normalize(brand),normalize(name)) in old_keys:
            review.append(dict(source_product_id=pid,brand=brand,name=full,status='HOLD_EXISTING_DUPLICATE_REVIEW'));continue
        if not isinstance(row['notes'],list) or not all(isinstance(t,str) for t in row['notes']):raise ValueError('Notes array schema')
        tokens={'note:'+normalize(t) for t in row['notes'] if normalize(t) not in ('','unknown','nan','na')}
        vector=project(tokens,idf)
        if not vector:
            review.append(dict(source_product_id=pid,brand=brand,name=full,status='HOLD_ZERO_PROJECTED_LICENSED_NOTES'));continue
        key=(normalize(brand),normalize(row['name']),concentration(row['concentration']))
        if key in seen_keys:
            review.append(dict(source_product_id=pid,brand=brand,name=full,status='HOLD_DUPLICATE_NEW_CANONICAL_IDENTITY'));continue
        seen_keys.add(key);cid=canonical_id(*key)
        if cid in vectors:raise ValueError('Candidate ID collision')
        vectors[cid]=vector;mapping[pid]=cid
        new[cid]=dict(id=cid,source_product_id=pid,brand=row['house'],name=row['name'],concentration=row['concentration'],
            licensed_product_id=row['id'],licensed_url=row['url'],notes=list(row['notes']),tokens=sorted(tokens),
            known_tokens=len(vector),oov_tokens=sorted(tokens-set(idf)),license='CC-BY-4.0',source_commit=provenance['commit'],
            metadata_quality='EXACT_LICENSED_NOTES_IDENTITY; no general accords provided',
            modifications='Literal notes normalized and frozen-IDF projected; source descriptions/ranks/families not used')
        review.append(dict(source_product_id=pid,brand=brand,name=full,status='INCLUDED_LICENSED_EXACT_NONZERO'))
    if any(vectors[i]!=existing_vectors[i] for i in old_ids):raise AssertionError('Legacy vector mutation')
    return vectors,new,mapping,review,provenance
