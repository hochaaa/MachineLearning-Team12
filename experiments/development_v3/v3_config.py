"""Approved STEP7 A-F transcription; no extra candidate/outer-driven changes."""
from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[2]
POLICIES=[]
for name,f,b,fl,a,method in [('A',2,.01,1.,.25,'linear'),('B',2,.1,1.,.25,'linear'),('C',2,.1,.1,.25,'linear'),('D',4,.1,.1,.25,'linear'),('E',2,.1,.1,.75,'linear'),('F',2,.1,.1,.25,'minmax')]:
    POLICIES.append({'id':name,'factors':f,'bias_l2':b,'latent_l2':.01,'epochs':40,'learning_rate':.01,'fold_latent':fl,'fold_bias':1.,'fusion':method,'alpha':a,'content':'neutral'})
V1={'id':'V1','factors':4,'epochs':160,'learning_rate':.01,'regularization':.01,'content':'v1','fusion':'linear','alpha':.25,'fold_latent':.01,'fold_bias':.01}
V2={'id':'V2','factors':8,'epochs':120,'learning_rate':.01,'regularization':.01,'early':True,'content':'neutral','fusion':'rrf','alpha':.25,'fold_latent':1.,'fold_bias':1.}
SETTINGS={'split_seed':20261109,'seed':12,'diagnostic_seed':29,'outer_folds':3,'inner_folds':2,'support':3,'candidates':479,'k':10,'positive':.7,'caps':{'primary':54,'seed':6,'final':1,'total':61},'min_inner_positive':20,'min_outer_positive':30,'ndcg_tie':.002,'coverage_min_ratio':.8,'concentration_max_increase':.1,'no_eligible':'V1','outer_candidate_evaluation':'only selected policy; unselected candidates N/A','final_selection':'aggregate six inner folds, lock before all outer evaluations','guardrail_aggregation':'unweighted mean inner-fold coverage/Top10 concentration vs same-fold V1','tie_order':'smaller factors; stronger bias then fold-in regularization; A-F ID, V1 retention always available','hard_seconds':1200}

def verify_source():
    """Check executable policies exactly against original report table and approved review."""
    report=ROOT/'reports/V3_PERSONALIZATION_FEASIBILITY.md';blue=ROOT/'outputs/development_v2/diagnostics/step7/v3_design_blueprint.json';review=json.loads((ROOT/'outputs/development_v3/configs/step8_preflight_review.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(report)==review['source_report_sha256'] and sha(blue)==review['source_blueprint_sha256']
    text=report.read_text();found={}
    for line in text.splitlines():
        bits=[x.strip() for x in line.split('|')[1:-1]]
        if len(bits)==5 and bits[0] in 'ABCDEF' and len(bits[0])==1:
            f1,f2=map(float,bits[3].split('/'));method='minmax' if 'minmax' in bits[4] else 'linear';alpha=float(re.search(r'Content([.\d]+)',bits[4]).group(1));found[bits[0]]=(int(bits[1]),float(bits[2]),f1,f2,method,alpha)
    assert len(found)==6
    for p in POLICIES:assert found[p['id']]==(p['factors'],p['bias_l2'],p['fold_latent'],p['fold_bias'],p['fusion'],p['alpha'])
    assert 'lr.01,latentL2.01,epoch40고정' in text
    return {'report_sha256':sha(report),'blueprint_sha256':sha(blue),'six_policies_exact':True,'approval':'User approved total61; primary54/seed6/final1; no old design changes'}
