"""Read-only scan of the 479 metadata candidates; never merge or alter model IDs.

Run from project root: python -B -m web.backend.audit_search_catalog.
Reports catalog-level distinctions, not independent proof of all real-world variants.
"""
from collections import Counter,defaultdict
from difflib import SequenceMatcher
from itertools import combinations
import json
import re
from pathlib import Path
from .adapter import FrozenService,ROOT
from .search import normalize_search
from perfume.data import fragrantica

VERSION_WORDS=frozenset('edt edp edc parfum perfume elixir intense extreme absolu absolute extrait cologne toilette eau de intensement exclusif exclusive sport edition pour homme femme for men women'.split())


def version_base(name):
    """Heuristic family key only: remove listed version words and 4-digit years.

    This is audit candidate generation, never used by search or entity matching.
    Empty keys are ignored. Year/concentration evidence remains in output records.
    """
    return ' '.join(t for t in normalize_search(name).split() if t not in VERSION_WORDS and not re.fullmatch(r'(19|20)\d{2}',t))


def main():
    """Read catalog/frozen metadata, export aggregates/pairs/public product details."""
    service=FrozenService();catalog=service.catalog;_,raw=fragrantica('Term-project-datasets/fra_cleaned.csv')
    raw={r['url']:r for r in raw if r['url'] in service.allowed}
    brands=defaultdict(list);exact=defaultdict(list)
    for item in service.candidates:
        row=catalog[item];brand=normalize_search(row['brand']);name=normalize_search(row['name'])
        brands[brand].append(item);exact[(brand,name)].append(item)
    duplicates=[{'brand':b,'name':n,'ids':ids} for (b,n),ids in exact.items() if len(ids)>1]
    pairs=[];comparisons=0
    for brand,items in sorted(brands.items()):
        for left,right in combinations(sorted(items),2):
            comparisons+=1
            a,b=catalog[left],catalog[right];na,nb=normalize_search(a['name']),normalize_search(b['name'])
            va,vb=version_base(na),version_base(nb)
            ratio=SequenceMatcher(None,na,nb).ratio()
            same=na==nb;variant=bool(va) and va==vb and not same
            # Also screen names sharing >=2 leading words, or high character similarity.
            prefix=len(na.split())>=2 and len(nb.split())>=2 and na.split()[:2]==nb.split()[:2]
            if not (same or variant or ratio>=.70 or prefix):continue
            classification='검색 표시 중복 가능성' if same else '정상적인 제품 변형(카탈로그상)' if variant else '추가 확인 필요'
            pairs.append({'brand':brand,'left':left,'right':right,'left_name':a['name'],'right_name':b['name'],
                          'left_year':raw[left].get('Year'),'right_year':raw[right].get('Year'),
                          'same_normalized_brand_name':same,'variant_family_match':variant,
                          'character_similarity':round(ratio,4),'classification':classification})
    orchids=[]
    for item in service.candidates:
        if catalog[item]['brand']=='tom-ford' and catalog[item]['name'] in ('black-orchid','black-orchid-parfum'):
            orchids.append({**service.record(item),'catalog_id':item,'fragrantica_numeric_id':item.rsplit('-',1)[-1].removesuffix('.html'),
                            'year':raw[item].get('Year'),'candidate_member':True,'mf_factor':item in service.mf.items,
                            'explicit_version_in_name':'parfum' if catalog[item]['name'].endswith('-parfum') else None,
                            'raw_top':raw[item].get('Top'),'raw_middle':raw[item].get('Middle'),'raw_base':raw[item].get('Base')})
    result={'candidate_entries':len(service.candidates),'unique_urls':len(set(service.candidates)),
            'duplicate_urls':{k:v for k,v in Counter(service.candidates).items() if v>1},
            'same_normalized_brand_name_groups':duplicates,'within_brand_pairs_screened':comparisons,
            'flagged_pair_counts':dict(Counter(p['classification'] for p in pairs)),
            'pairs':pairs,'black_orchid':orchids,
            'limits':'Heuristic same-brand lexical screen; not proof of product equivalence/distinctness. No ID merged/removed.'}
    path=ROOT/'web/evidence/search-stage31/catalog-audit.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('pairs','black_orchid')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
