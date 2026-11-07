"""Fixed V33 policy audit, safe CSV harness and paired evaluation; no new model."""
import csv,json,hashlib,math
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from experiments.scent_v2.mf_accuracy_optimization.core import developer_data,read_identities,digest
from experiments.scent_v2.accuracy_root_cause.diagnostic import ROOT,CONFIG as V33_CONFIG,save_states,pack_state
from experiments.scent_v2.accuracy_root_cause.model import Structured,predict
from experiments.scent_v2.accuracy_root_cause.run import load_selected
from experiments.scent_v2.real_user_dataset.split_manager import support_split
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
from experiments.scent_v2.final_validation.analysis import paired_counts,final_uncertainty
OUT=ROOT/'outputs/scent_v2/structured_generalization'
SEED=12


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    Path(path).chmod(0o600)


def lock_policy():
    """Hash source/config/artifact, not a mutable permission/approval record."""
    previous=ROOT/'outputs/scent_v2/accuracy_root_cause';verification=json.loads((previous/'verification.json').read_text());assert verification['status']=='PASS' and sha(previous/'best_model.npz')==verification['model_sha256']
    for p,h in verification['source_sha256'].items():assert sha(ROOT/p)==h
    with np.load(previous/'best_model.npz',allow_pickle=False) as z:meta=json.loads(str(z['metadata']))
    assert meta['policy']=='structured' and meta['config']==V33_CONFIG
    structured=V33_CONFIG['structured'];assert structured['channel_weights']==[.25]*4 and structured['lambda']==.2
    source_paths=['experiments/scent_v2/accuracy_root_cause/model.py','experiments/scent_v2/accuracy_root_cause/config.json','experiments/scent_v2/accuracy_root_cause/diagnostic.py','experiments/scent_v2/similarity_reranking/core.py','experiments/scent_v2/similarity_reranking/config.json','src/perfume/models.py','experiments/scent_v2/mf_cv_optimization/core.py','experiments/scent_v2/recommend.py','experiments/scent_v2/real_user_dataset/split_manager.py','src/perfume/evaluation.py','experiments/scent_v2/structured_generalization/core.py','experiments/scent_v2/structured_generalization/prepare.py','experiments/scent_v2/structured_generalization/evaluate.py']
    policy=dict(version='V2-34 fixed V2-33 Structured',MF=V33_CONFIG['mf'],Hybrid=dict(Content=.25,MF=.75,MF_clip=[0,1],ridge='known_support_count * .01, fixed Q'),structured=structured,positive_support=.7,weak_similarity_floor=.05,Top50='Hybrid score only, rerank strictly inside50',Support=5,candidate_count=479,candidates_sha256=sha(ROOT/'outputs/improvement/candidates.json'),candidates_exclude_support=True,k=5,relevance=.7,metric_averaging='Positive-heldout users only; one new cohort mean, all users for exposure',ties='score descending then original item ID',new_CSV=dict(columns=['user_id','perfume_id','rating'],raw_min=0,raw_max=10,step=.5,normalization='rating/10',zero='Actual new-user0 is valid, never treated as missing'),eligibility='At least6 unique valid canonical479 ratings, selected by identity/count BEFORE held-out labels; no requirement for positive answer',Support_split='Reuse real_user_dataset.support_split hash12:realuser-support:user:perfume, first5',final_training='Background255 + developer50, exclude reserved25 and all evaluation input; one shared MF/Content state, no tuning',new_evaluation='Exactly baseline/structured on same input once, no user-specific selection',source_sha256={p:sha(ROOT/p) for p in source_paths},V33_CV_artifact_sha256=sha(previous/'best_model.npz'),training_source_sha256=sha(ROOT/'outputs/validation/train_exclude_3.json'))
    encoded=json.dumps(policy,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode();policy_hash=hashlib.sha256(encoded).hexdigest();lock=dict(policy=policy,policy_sha256=policy_hash)
    write(OUT/'locked_policy.json',lock);return lock


def verify_lock():
    lock=json.loads((OUT/'locked_policy.json').read_text());policy=lock['policy'];assert hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==lock['policy_sha256']
    for p,h in policy['source_sha256'].items():assert sha(ROOT/p)==h
    assert sha(ROOT/'outputs/improvement/candidates.json')==policy['candidates_sha256'] and sha(ROOT/'outputs/validation/train_exclude_3.json')==policy['training_source_sha256']
    if 'prepared_model_sha256' in lock:assert sha(OUT/'prepared_shared_model.npz')==lock['prepared_model_sha256']
    return lock


def load_csv_identities(path,candidates,forbidden_ids):
    """Keep ratings opaque; reject duplicates/history overlap and flag unknown items.

    Existing canonical CSV schema/raw0..10 retained. Unknown catalog rows excluded
    by fixed ID-only rule, never fuzzy mapped. No heldout-positive user selection.
    """
    groups=defaultdict(list);seen=set();excluded=Counter();total=0
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or not {'user_id','perfume_id','rating'}<=set(reader.fieldnames):raise ValueError('Need user_id,perfume_id,rating columns; raw0..10')
        for row in reader:
            total+=1;u=row['user_id'];i=row['perfume_id']
            if not u or not i or u.strip()!=u or i.strip()!=i:raise ValueError('Blank or whitespace-altered ID')
            if u in forbidden_ids:raise ValueError('Historical/training user overlap: evaluation denied')
            if (u,i) in seen:raise ValueError('Duplicate user-item: no label-dependent deduplication')
            seen.add((u,i))
            if row.get('source') in ('post_recommendation_feedback','post_recommendation_rating'):raise ValueError('Post-exposure ratings cannot be offline heldout')
            if row.get('experience') not in (None,'','EXPERIENCED'):excluded['not_experienced_or_unknown']+=1;continue
            if i not in candidates:excluded['outside_fixed479']+=1;continue
            groups[u].append(dict(perfume_id=i,rating_token=row['rating']))
    eligible=[]
    for u,rows in sorted(groups.items()):
        parts=support_split(u,rows)
        if parts['status']!='eligible':excluded['insufficient_unique_history_users']+=1;continue
        eligible.append(dict(user=u,support_tokens=[(r['perfume_id'],r['rating_token']) for r in parts['support']],answer_tokens=[(r['perfume_id'],r['rating_token']) for r in parts['heldout']]))
    return eligible,dict(source_rows=total,users_with_matched_items=len(groups),eligible_users=len(eligible),excluded=dict(excluded),eligibility_label_blind=True,ratings_decoded=0)


def decode(tokens):
    """Existing collection scale0..10 in .5 steps; genuine zero remains valid."""
    result=[]
    for i,value in tokens:
        if isinstance(value,bool):raise ValueError('Boolean rating forbidden')
        try:r=float(value)
        except (TypeError,ValueError):raise ValueError('Non-numeric rating') from None
        if not math.isfinite(r) or not 0<=r<=10 or abs(2*r-round(2*r))>1e-9:raise ValueError('Need finite raw0..10 in .5 steps')
        result.append((i,r/10))
    return result


def validate_provenance(path):
    """Operator-supplied factual provenance; no fabricated consent or independence."""
    p=json.loads(Path(path).read_text());keys=['real_user_data','not_used_for_model_selection','pre_recommendation_ratings_only','identity_disjoint_from_historical_people_attested','consent_for_local_evaluation_confirmed']
    if any(p.get(k) is not True for k in keys) or not isinstance(p.get('source_namespace'),str) or not p['source_namespace'].strip():raise ValueError('Unconfirmed input provenance; do not claim independent evaluation')
    return p


def forbidden_users():
    """Original330 identities only; reserved numeric labels never decoded."""
    ids={u for u,i,t in read_identities(ROOT/'outputs/validation/train_exclude_3.json')}
    legacy=Path.home()/'Downloads/scent-ratings.csv'
    if legacy.exists():
        with legacy.open(encoding='utf-8-sig',newline='') as f:ids|={r['participant_id'] for r in csv.DictReader(f)}
    return ids


def evaluate_csv(csv_path,provenance_path,result_dir,fixture=False,forbidden_override=None,model_override=None):
    """Only two fixed policies, score EVERY user before any answer decode.

    Fixture flag is internal test-only and cannot be selected from production CLI.
    No model fit, candidate selection or parameter adjustment occurs here.
    """
    result_dir=Path(result_dir)
    if not fixture and result_dir.parent.resolve()!=(OUT/'evaluations').resolve():raise ValueError('Use a direct run directory under evaluations/')
    result_dir.mkdir(parents=True,exist_ok=False);result_dir.chmod(0o700)
    lock=verify_lock() if not fixture else {'policy_sha256':'SYNTHETIC_TEST_ONLY'}
    provenance=validate_provenance(provenance_path)
    c,m,b,structure,reference,gate,meta=load_selected(OUT/'prepared_shared_model.npz') if model_override is None else model_override
    candidates=set(c.vectors)
    if not fixture:assert len(candidates)==479 and meta['policy_sha256']==lock['policy_sha256']
    excluded=forbidden_users() if forbidden_override is None else forbidden_override
    cohort,input_audit=load_csv_identities(csv_path,candidates,excluded)
    if not cohort:
        write(result_dir/'evaluation_results.json',dict(status='NOT_EVALUATED_NO_ELIGIBLE_USERS',input=input_audit,policy_sha256=lock['policy_sha256'],actual_accuracy_metrics=False));return None
    # This marker blocks repeat evaluation of the same underlying participant IDs,
    # even if input rows/filenames/order/labels are changed. Never contains raw IDs.
    participant_hashes={hashlib.sha256(('v234\0'+r['user']).encode()).hexdigest() for r in cohort}
    if not fixture:
        for marker in OUT.glob('evaluations/*/opened_once.json'):
            if participant_hashes&set(json.loads(marker.read_text())['participant_hashes']):raise RuntimeError('Participants previously opened; no repeated test selection')
    write(result_dir/'opened_once.json',dict(participant_hashes=sorted(participant_hashes),policy_sha256=lock['policy_sha256'],input_sha256=sha(csv_path),fixture_only=fixture))
    predictions=[]
    for row in cohort:
        support=decode(row['support_tokens']);pred={}
        for name in ['baseline','structured']:
            top,scores=predict(name,support,sorted(candidates),c,m,b,structure,reference,False);assert len(top)==len(set(top))==5 and not set(top)&{i for i,r in support};pred[name]=top
        predictions.append(pred)
    write(result_dir/'predictions_complete.json',dict(users=len(cohort),models=2,heldout_ratings_decoded=0))
    recs={name:[] for name in ['baseline','structured']};pairs=[]
    for row,pred in zip(cohort,predictions):
        answers=decode(row['answer_tokens'])
        for name in recs:recs[name].append(dict(top=pred[name],answers=answers,accuracy=user_metrics(pred[name],answers)))
        a,bm=recs['baseline'][-1]['accuracy'],recs['structured'][-1]['accuracy'];pairs.append(dict(fold=1,baseline_ndcg=a['ndcg'] if a else None,selected_ndcg=bm['ndcg'] if bm else None,delta=bm['ndcg']-a['ndcg'] if a else None,baseline_hit=a['hit_rate'] if a else None,selected_hit=bm['hit_rate'] if bm else None))
    summaries={name:summarize(rows,candidates) for name,rows in recs.items()};delta=summaries['structured']['ndcg']-summaries['baseline']['ndcg'] if summaries['baseline']['ndcg'] is not None else None
    valid=[p['delta'] for p in pairs if p['delta'] is not None];loo=[float(np.mean([d for k,d in enumerate(valid) if k!=n])) for n in range(len(valid))] if len(valid)>1 else []
    result=dict(status='SYNTHETIC_FUNCTIONAL_TEST_ONLY' if fixture else 'GENERALIZATION_IMPROVEMENT_OBSERVED' if delta is not None and delta>1e-12 else 'GENERALIZATION_NOT_EVALUATED' if delta is None else 'GENERALIZATION_IMPROVEMENT_NOT_OBSERVED',real_accuracy_evaluated=not fixture and delta is not None,policy_sha256=lock['policy_sha256'],input=input_audit,models=summaries,ndcg_delta=delta,paired=paired_counts(pairs),user_metric_changes_no_identifiers=pairs,paired_bootstrap=final_uncertainty(pairs),minimum_leave_one_user_out_delta=min(loo) if loo else None,small_sample_warning=len(valid)<30,independence='ID disjoint checked; physical-identity/no-prior-exposure provenance operator-attested, not inferred from namespace',no_retuning=True,service_changed=False)
    write(result_dir/'evaluation_results.json',result)
    with (result_dir/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['model','users','positive_users','ndcg_at5','recall_at5','hit_rate_at5']);w.writeheader()
        for name,s in summaries.items():w.writerow(dict(model=name,users=s['users'],positive_users=s['positive_users'],ndcg_at5=s['ndcg'],recall_at5=s['recall'],hit_rate_at5=s['hit_rate']))
    return result
