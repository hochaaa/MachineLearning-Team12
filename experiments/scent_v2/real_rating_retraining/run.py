"""Audit the consented local CSV; fail closed before any fit if exact matching is empty."""
import argparse,csv,hashlib,json,os,secrets,subprocess
from collections import Counter,defaultdict
from pathlib import Path
from unittest.mock import patch
from .audit import POLICY,read_csv,match_one,split_eligibility,stats,pseudonym,require_training_additions,norm
from experiments.scent_v2.synthetic_data.boundary import evaluation_users,safe_train
from experiments.scent_v2.external_real_data.quality_report import summarize
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/scent_v2/real_rating_retraining'

def json_file(name,data):
    """Exclusively create local aggregate/private JSON, chmod0600; never overwrite."""
    p=OUT/name
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
    p.chmod(0o600)

def csv_file(name,rows):
    """Write nonempty reviewed records; private outputs never enter Git."""
    if not rows:return
    p=OUT/name
    with p.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    p.chmod(0o600)

def main():
    """--csv original readonly; --consent-confirmed actual user attestation; --snapshot pre-task hashes."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path,required=True)
    parser.add_argument('--consent-confirmed',action='store_true')
    parser.add_argument('--snapshot',type=Path,required=True)
    args=parser.parse_args()
    if not args.consent_confirmed:raise PermissionError('Local storage/training/evaluation/aggregate presentation consent must be confirmed')
    if (OUT/'data_validation.json').exists():raise FileExistsError('Existing V2-16 outputs cannot be overwritten')
    before=json.loads(args.snapshot.read_text());raw_sha=hashlib.sha256(args.csv.read_bytes()).hexdigest()
    from perfume.data import fragrantica
    from perfume.models import MatrixFactorization
    from deployment.final_v1.config import assets_path,inspect_assets
    candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text())
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
    assert len(candidates)==len(set(candidates))==479
    # An attempted MF fit is blocked in this run: zero exact additions were established
    # by the initial schema/matching preflight. No counterfactual model is fabricated.
    with patch.object(MatrixFactorization,'fit',side_effect=AssertionError('MF fit forbidden in no-match audit')) as fit_guard:
        rows,validation=read_csv(args.csv)
        matches=[match_one(r,catalog,candidates) for r in rows]
        matched=[(r,i) for r,(i,s) in zip(rows,matches) if i is not None]
        eligible,eligibility=split_eligibility(rows,matches)
        if matched:
            raise RuntimeError('Nonempty matches contradict this blocked preflight; stop and freeze an A/B protocol before fitting')
        try:require_training_additions(matched)
        except ValueError as exc:block_reason=str(exc)
        else:raise AssertionError('Zero-match gate did not block')
        original_eval,identity_audit=evaluation_users((ROOT/'outputs/scent_v2/baseline/split_manifest.private.json').read_text())
        legacy,old_users,boundary=safe_train((ROOT/'outputs/validation/train_exclude_3.json').read_text(),original_eval)
        strict=[dict(user_id=u,perfume_id=i,normalized_rating=y*10) for u,i,y in legacy if i in candidates]
        baseline_quality=summarize(strict,candidates)
        runtime_dir=assets_path();runtime_integrity=inspect_assets(runtime_dir)
        content_metadata=json.loads((runtime_dir/'content.json').read_text())
        content_features=len(content_metadata['idf'])
        actual_fits=fit_guard.call_count
    OUT.mkdir(parents=True,exist_ok=True);OUT.chmod(0o700)
    private=OUT/'private';private.mkdir(mode=0o700)
    secret=secrets.token_bytes(32);key=private/'identity.key';key.write_bytes(secret);key.chmod(0o600)
    validation.update(original_filename=args.csv.name,original_sha256=raw_sha,
        consent=dict(status='USER_CONFIRMED_LOCAL_SCOPE',date='2026-10-30',scope='local storage, training, evaluation, non-identifying aggregate presentation',
                     redistribution='NOT_GRANTED_BY_THIS_ATTESTATION'),
        exact_candidate_URL_ID_records=sum(r['product_id'] in candidates for r in rows),
        normalized_brand_name_user_duplicates=len(rows)-len({(r['participant_id'],norm(r['brand']),norm(r['product_name'])) for r in rows}),
        cross_language_same_product_duplicates='UNKNOWN_PENDING_CUSTOM_REVIEW')
    json_file('data_validation.json',validation)
    profiles=defaultdict(list)
    for r in rows:profiles[r['participant_id']].append(r)
    distributions=[]
    for n,history in enumerate(sorted(profiles.values(),key=lambda h:-len(h)),1):
        distributions.append(dict(anonymous_activity_rank=n,ratings=stats([r['numeric_score'] for r in history]),
            sources=dict(Counter(r['source_type'] for r in history)),distinct_brands=len({r['brand'] for r in history}),
            matched479_ratings=sum(match_one(r,catalog,candidates)[0] is not None for r in history),
            existing_feature_coverage=0,notes_accords_diversity='NOT_MEASURED_NO_COMPATIBLE_METADATA'))
    json_file('user_rating_distribution.json',dict(activity_rank_not_user_ID=True,private_local_only=True,
        raw_activity_histogram=validation['user_activity_histogram'],profiles=distributions,
        note='Ranks summarize distributions without original IDs or user/item rows; do not infer poor data quality from high scores'))
    products=defaultdict(list)
    for r,m in zip(rows,matches):products[(r['product_id'],r['brand'],r['product_name'],r['source_type'])].append(m)
    csv_file('perfume_matching_report.csv',[dict(source_type=k[3],brand=k[1],product_name=k[2],ratings=len(v),
        matched_item=v[0][0] or '',status=v[0][1],source_ID_matches_candidate_URL=k[0] in candidates,
        preserve_concentration_version=True) for k,v in products.items()])
    processed=[]
    for r,(i,s) in zip(rows,matches):
        processed.append(dict(user_id=pseudonym(r['participant_id'],secret),source_product_id=r['product_id'],
            brand=r['brand'],product_name=r['product_name'],raw_score=r['score'],normalized_score=r['numeric_score']/10,
            source_type=r['source_type'],match_status=s,matched_candidate=i or '',training_role='QUARANTINED_NO_EXACT_MATCH'))
    csv_file('private/unmatched_ratings.csv',processed)
    status_counts=dict(Counter(s for i,s in matches))
    summary=dict(status='BLOCKED_NO_EXACT_479_MATCHES',new_users=validation['users'],new_ratings=len(rows),new_perfumes=validation['unique_product_ids'],
        matched_ratings=len(matched),matched_perfumes=0,matched_users=0,known_outside_exact_brand_index=status_counts.get('OUTSIDE_FIXED_CATALOG_EXACT_BRAND_INDEX',0),
        uncertain_ratings=sum(s.startswith('REVIEW') for i,s in matches),status_counts=status_counts,
        actual_added_training_users=0,actual_added_training_ratings=0,existing_new_person_overlap='UNKNOWN; IDs/namespaces alone cannot establish independence',
        v214_independent_rows_read=0,synthetic_training_rows=0,combined_training_file='NOT_CREATED',eligible_new_evaluation=eligibility,
        quarantine='private/unmatched_ratings.csv preserves all raw scores without original participant IDs')
    json_file('dataset_integration_summary.json',summary)
    json_file('training_config.json',dict(policy=POLICY,status='NOT_FITTED_NO_MATCHED_ADDITIONS',
        original_content_feature_dimensions=content_features,content_payload_sha256=hashlib.sha256((runtime_dir/'content.json').read_bytes()).hexdigest(),
        model_fit_attempts=actual_fits,hyperparameter_searches=0,plan_requires_label_blind_user_split_before_future_nonempty_run=True,
        feature_space_scope=dict(candidate479_metadata_active_tokens=len({t for i in candidates for t in catalog[i]['tokens']}),
            frozen_idf_vocabulary=content_features,explanation='Active candidate metadata tokens and frozen IDF entries have different scopes; neither changed')))
    json_file('training_data_summary.json',dict(strict_existing_baseline=baseline_quality,boundary=boundary,
        identity_only_manifest=identity_audit,additional_training_users=0,additional_training_ratings=0,
        newly_observed_items=0,unobserved_items_remaining=baseline_quality['unobserved_candidates'],
        connectivity_change='NO_ADDITIONS; no new graph or model trained',
        actual_outer_fold_training='Not 823: historical original folds 1531/1481/1493 rows; no historical fold training rerun',
        training_A='NOT_RUN',training_B='NOT_RUN',model_weight_files=[]))
    json_file('evaluation_summary.json',dict(status='NOT_EVALUATED',reason=block_reason,
        raw_5_or_more_users=sum(len(h)>=5 for h in profiles.values()),raw_6_or_more_users=sum(len(h)>=6 for h in profiles.values()),
        matched_support5_plus_heldout_users=len(eligible),positive_evaluation_users='NOT_EVALUATED',
        old_outer_reruns=0,old_final_validation_internal_external_answer_parses=0,
        new_recommendation_inference_calls=0,metrics=dict(ndcg_at5='NOT_EVALUATED',recall_at5='NOT_EVALUATED',hit_rate_at5='NOT_EVALUATED',
        coverage_at5='NOT_EVALUATED',top1_concentration='NOT_EVALUATED',top5_concentration='NOT_EVALUATED',observed_hits='NOT_EVALUATED'),
        bootstrap='NOT_RUN_NO_EVALUABLE_COHORT',per_user_change='NOT_EVALUATED',
        independence='No new validation claim. Historical Outer numbers are repeatedly analyzed exploratory evidence only'))
    accuracy=list(csv.DictReader((ROOT/'outputs/scent_v2/baseline/accuracy.csv').open()))
    comparison=[dict(protocol='HISTORICAL_V2_0_OUTER3',model=r['method'],users=r['users'],positive_users=r['positive_users'],
        ndcg_at5=r['ndcg'],status='PREVIOUSLY_MEASURED_NOT_RERUN',source='outputs/scent_v2/baseline/accuracy.csv')
        for r in accuracy if r['track']=='A' and r['method'] in ('content','mf','hybrid')]
    comparison += [dict(protocol='V2_16_FIXED_STRUCTURE_A_B',model=m,users='NOT_EVALUATED',positive_users='NOT_EVALUATED',
        ndcg_at5='NOT_EVALUATED',status='BLOCKED_NO_ADDITIONS',source='evaluation_summary.json') for m in ('Model A existing-only','Model B new-real-added')]
    csv_file('model_comparison.csv',comparison)
    if hashlib.sha256(args.csv.read_bytes()).hexdigest()!=raw_sha:raise AssertionError('Original CSV changed')
    json_file('preflight_checks.json',dict(synthetic_tests=24,fit_attempts=actual_fits,original_csv_unchanged=True,
        candidate_count=479,new_exact_matched=0,new_eligible_evaluation_users=0,runtime_integrity=runtime_integrity['status']))
    print(json.dumps(dict(status=summary['status'],rows=len(rows),users=validation['users'],products=validation['unique_product_ids'],
        matched=0,training_added=0,MF_fit_calls=actual_fits,content_dimensions=content_features),ensure_ascii=False))

if __name__=='__main__':main()
