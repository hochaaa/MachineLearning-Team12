"""Read original479 identities/name/brand; no model or private-user loading.
Local search-normalization pattern: web/backend/search.py (Team12), display only.
"""
import csv,json,unicodedata,re
from .config import CANDIDATES,CATALOG


def normalize(value):
 text=unicodedata.normalize('NFKD',value.casefold());text=''.join(c for c in text if not unicodedata.combining(c));return ' '.join(re.findall(r'[^\W_]+',text))


def load_catalog(candidate_path=CANDIDATES,metadata_path=CATALOG):
 ids=json.loads(candidate_path.read_text());assert len(ids)==len(set(ids))==479
 with metadata_path.open(encoding='cp1252',newline='')as f:rows={r['url']:r for r in csv.DictReader(f,delimiter=';')}
 if not set(ids)<=rows.keys():raise ValueError('Candidate metadata missing')
 return {i:dict(id=i,name=rows[i]['Perfume'],brand=rows[i]['Brand'])for i in ids}


def search(catalog,query):
 """Literal name/brand tokens, compact spaces; original metadata, max10 IDs."""
 if not isinstance(query,str)or len(query)>100:raise ValueError('검색어는 100자 이하여야 합니다.')
 q=normalize(query)
 if not q:return []
 out=[]
 for i,r in catalog.items():
  full=normalize(r['brand']+' '+r['name']);compact=full.replace(' ','');qq=q.replace(' ','')
  if q in full or all(t in full for t in q.split())or(len(qq)>=3 and qq in compact):out.append((0 if q==normalize(r['name'])else 1 if full.startswith(q)else 2,normalize(r['brand']),normalize(r['name']),i))
 return [catalog[t[-1]]for t in sorted(out)[:10]]
