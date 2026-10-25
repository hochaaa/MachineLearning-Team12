"""Resolve exact-JSON order check with disclosed numeric tolerance; inference only."""
import sys,json
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from web.backend.adapter import FrozenService
s=FrozenService();support=[SimpleNamespace(perfume_id=i,rating=r) for i,r in zip(s.candidates,[9,1,6])]
a=s.recommend(support,'none');b=s.recommend(list(reversed(support)),'none')
ids_equal=[r['id'] for r in a['results']]==[r['id'] for r in b['results']]
delta=max(abs(x['score']-y['score']) for x,y in zip(a['results'],b['results']))
def without_scores(d):return {**d,'results':[{k:v for k,v in r.items() if k!='score'} for r in d['results']]}
report={'exact_json_equal':a==b,'same_ids_and_order':ids_equal,'max_absolute_score_difference':delta,'all_other_fields_equal':without_scores(a)==without_scores(b),'numeric_tolerance':1e-12,'numeric_parity_pass':ids_equal and delta<=1e-12 and without_scores(a)==without_scores(b),'interpretation':'Exact JSON check fails due to floating-point operation order. Rankings and metadata are unchanged; disclose, do not change frozen code.','service_modified':False,'mf_fits':0}
with (ROOT/'outputs/step9_audit/order_diagnostic.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2));assert report['numeric_parity_pass']
