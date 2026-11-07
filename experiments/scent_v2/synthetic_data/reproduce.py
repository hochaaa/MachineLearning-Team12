"""Fresh-process reproduction from saved aggregate parameters, no rule refitting."""
import json,csv,math,hashlib
import numpy as np
from .config import OUT,CATALOG,CANDIDATES,TRAIN
from .boundary import Cursor
from .generator import generate
from .run import digest_rows,write_json
from perfume.data import fragrantica


def main():
    """Only source IDs are decoded; all item/rating values structurally skipped."""
    if(OUT/'reproduction_check.json').exists():raise RuntimeError('Existing reproduction evidence')
    c=Cursor(TRAIN.read_text());c.take('[');IDs=set()
    while True:
        c.ws()
        if c.text[c.pos]==']':c.pos+=1;break
        c.take('[');IDs.add(c.string());c.take(',');c.skip();c.take(',');c.skip();c.take(']');c.ws()
        if c.text[c.pos]==',':c.pos+=1
    assert c.numeric_decodes==0
    params=json.loads((OUT/'generator_parameters.private.json').read_text());v=json.loads((OUT/'generator_vocabulary.json').read_text());candidates=json.loads(CANDIDATES.read_text());catalog,_=fragrantica(CATALOG);lookup={t:n for n,t in enumerate(v['tokens'])};X=np.zeros((len(candidates),len(lookup)))
    for n,item in enumerate(candidates):
        vec={t:v['idf'][t]for t in catalog[item]['tokens']if t in v['idf']};norm=math.sqrt(sum(x*x for x in vec.values()))
        for t,x in vec.items():X[n,lookup[t]]=x/norm if norm else 0.
    r,u,a,p,t=generate(params,X,v['tokens'],candidates,IDs,12,1000,150);expected=json.loads((OUT/'synthetic_quality_report.json').read_text())['reproducibility']['hashes'];actual=dict(ratings=digest_rows(r),users=digest_rows(u),audit=digest_rows(a));assert actual==expected
    # Persisted CSV round trips must also equal the generated datasets, not just logs.
    arrays={}
    for name,key in [('synthetic_ratings_pilot.csv','ratings'),('synthetic_users_pilot.csv','users'),('synthetic_generation_audit.csv','audit')]:
        with(OUT/name).open()as f:rows=list(csv.DictReader(f))
        for row in rows:
            for k in row:
                if k in('rating_count','seed','proposed_support_count'):row[k]=int(row[k])
                elif k in('rating','user_bias_raw','noise_sigma_raw','feature_signal_sd_raw','latent_affinity','feature_signal_raw','no_noise_latent','noise_raw','unmapped_latent'):row[k]=float(row[k])
                elif k=='preference_is_synthetic_assumption':row[k]=row[k]=='True'
        arrays[key]=digest_rows(rows)
    assert arrays==actual
    write_json(OUT/'reproduction_check.json',dict(status='PASS',fresh_process=True,saved_parameters_only_no_reestimate=True,source_rating_numeric_decodes=0,seed=12,hashes=actual,persisted_CSV_roundtrip_hashes=arrays,recommender_operations=0))
    print('PASS: fresh-process generation from saved parameters equals all original CSV rows;0 source rating decodes')

if __name__=='__main__':main()
