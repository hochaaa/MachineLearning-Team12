"""Reuse saved errors/rules; availability audit without scoring frozen models."""
from common import *
def main():
    val=load('outputs/improvement/validation_rating_errors.json')['3_2']
    internal=load('outputs/final/internal_rating_errors.json')
    records=[{'split':split,'model':model,**m,'source':path,'scope':'stored observed-rating error; no recomputation'} for split,values,path in [('validation',val,'outputs/improvement/validation_rating_errors.json#3_2'),('internal',internal,'outputs/final/internal_rating_errors.json')] for model,m in values.items()]
    table('saved_rating_errors.csv',records)
    rules=read_csv('outputs/validation/knowledge_rules.csv')
    table('saved_constraint_satisfaction.csv',[{'condition':r['required'],'requests':int(r['users']),'returned':int(r['returned']),'satisfied':int(r['satisfied']),'violated':int(r['returned'])-int(r['satisfied']),'empty_requests':int(r['empty_users']),'rate':float(r['constraint_satisfaction_rate']) if int(r['returned']) else None,'scope':'historical pre-improvement validation functional constraint check, not final preference accuracy'} for r in rules])
    _,fra=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');candidates=set(load('outputs/improvement/candidates.json'));current=[r for r in fra if r['url'] in candidates]
    seasonfields=[k for k in fra[0] if any(t in k.lower() for t in ['season','winter','summer','spring','autumn'])]
    pricefields=[k for k in fra[0] if any(t in k.lower() for t in ['price','currency','volume','cost'])]
    save('supplementary_summary.json',{'global_mean':'Already implemented Baseline.fit and rating_errors, explicit normalized rating prediction only; no tied-score ranking baseline added','rating_errors':records,'external_mae_rmse':'N/A: incompatible score semantics; not recalculated','constraints':'Existing 3 rules each168 requests /1680 returned /1680 satisfied /0violations /0empty; historical functional check reused, no new evaluation','zero':{'meaning':'UNRESOLVED','count':1309,'policy':'exclude_as_analysis_assumption','sensitivity_exists':True,'local_evidence':'reports/ZERO_POLICY.md; outputs/audit/zero_joint_distribution.json; outputs/improvement/zero_included_frozen_sensitivity.csv','new_source_investigation':'No network; prior investigation evidence reused, not independently reconfirmed'},'candidate_metadata':{'candidates':len(current),'season_fields':seasonfields,'season_valid_values':0 if not seasonfields else None,'price_fields':pricefields,'price_valid_values':0 if not pricefields else None,'currency':'N/A','volume':'N/A','collection_date':'UNKNOWN','source':'Fragrantica development CSV, not external Basenotes metadata','decision':'keep season/price disabled; external-only metadata cannot enable development filters'}})
    print('Existing global-mean/errors/constraint results reused; 479 candidate metadata audited; no new frozen inference.')
if __name__=='__main__':main_run(main,'supplementary_metrics')
