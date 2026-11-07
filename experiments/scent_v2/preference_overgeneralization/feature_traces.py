"""Posthoc weaker Accord-overlap traces; NEVER scoring or family-dislike labels."""
import json,csv
from pathlib import Path
from collections import Counter
from experiments.scent_v2.mf_cv_optimization.core import ROOT,developer_cohort,folds
from perfume.data import fragrantica
from experiments.scent_v2.accuracy_root_cause.model import structural_phrases
from .analysis import label
OUT=ROOT/'outputs/scent_v2/preference_overgeneralization'


def main():
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());cohort,reserved,source=developer_cohort(ROOT/'outputs/validation/train_exclude_3.json',candidates);catalog,raw=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');features={r['url']:structural_phrases(r) for r in raw};history={};support={};fold_of={};n=0
    for f in folds(cohort):
        for row in f['evaluation']:
            n+=1;alias=f'U{n:02}';history[alias]=dict(row['support']+row['answers']);support[alias]=dict(row['support']);fold_of[alias]=f['fold']
    with (OUT/'user_pair_analysis.csv').open() as f:pairs=list(csv.DictReader(f))
    with (OUT/'recommendation_error_analysis.csv').open() as f:recs=list(csv.DictReader(f))
    traces=[]
    for p in pairs:
        if p['status']!='CONFIRMED_PRODUCT_PARTIAL_PREFERENCE_DIFFERENCE':continue
        ua,ub=p['user_A'],p['user_B'];extras=json.loads(p['opposition_extra_accords']);common=json.loads(p['common_positive_product_ids'])
        for i in json.loads(p['opposed_product_ids']):
            source,target=(ua,ub) if label(history[ua][i])=='POSITIVE' else (ub,ua)
            if fold_of[source]==fold_of[target]:continue
            for r in recs:
                overlap=set(extras[i])&set(json.loads(r['Main_Accords']))
                if r['user_alias']!=target or not overlap:continue
                traces.append(dict(source_alias=source,recipient_alias=target,model=r['model'],shared_positive_products=[dict(perfume_id=j,name=catalog[j]['name'],accords=sorted(features[j]['accords'])) for j in common],opposed_same_product=dict(perfume_id=i,name=catalog[i]['name'],accords=sorted(features[i]['accords']),source_label='POSITIVE',recipient_label='NEGATIVE',recipient_negative_in_support=i in support[target]),recommended_product=dict(perfume_id=r['perfume_id'],name=r['perfume_name'],rank=int(r['rank']),heldout_class=r['heldout_class'],extra_accord_overlap=sorted(overlap),positive_similarity=r['positive_support_similarity'] or None,negative_similarity=r['negative_support_similarity'] or None),source_in_recipient_training=True,evidence='Exact product preference difference + recommendation Accord overlap ONLY; isolated Accord dislike and causal transfer not identified'))
    by={m:[x for x in traces if x['model']==m] for m in ['Hybrid','Structured']};summary=dict(trace_count=len(traces),distinct_recipient_recommendation_slots={m:len({(x['recipient_alias'],x['recommended_product']['perfume_id']) for x in v}) for m,v in by.items()},actual_negative_recommendations=sum(x['recommended_product']['heldout_class']=='NEGATIVE' for x in traces),traces=traces,model_inference_runs=0,new_fits=0,reserved_labels_decoded=0)
    with (OUT/'feature_level_traces.json').open('x') as f:json.dump(summary,f,indent=2,ensure_ascii=False,allow_nan=False)
    report=json.loads((OUT/'preference_analysis.json').read_text());report['weaker_accord_overlap_trace_summary']={k:v for k,v in summary.items() if k!='traces'};(OUT/'preference_analysis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False))
    if by['Hybrid']:
        cases=json.loads((OUT/'case_studies.json').read_text());cases['case1']=dict(status='FEATURE_ONLY_SUSPECTED_NOT_CONFIRMED_ERROR',example=by['Hybrid'][0],no_exact_negative_Top5_chain=True,causal_transfer_unproven=True);(OUT/'case_studies.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False,allow_nan=False))
    print(json.dumps({k:v for k,v in summary.items() if k!='traces'},ensure_ascii=False))

if __name__=='__main__':main()
