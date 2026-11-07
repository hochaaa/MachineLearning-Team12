"""Freeze V33, read-only data audit, prepare one shared305-user model, no eval."""
import csv,json,sqlite3,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline
from perfume.data import fragrantica
from experiments.scent_v2.real_rating_retraining.audit import match_one
from .core import ROOT,OUT,V33_CONFIG,lock_policy,verify_lock,write,sha,developer_data,Structured,pack_state,predict


def audit_sources(candidates,catalog,known_users):
    """Aggregate-only inventory, SQLite immutable read-only, no Store constructors."""
    inventory=[];source_users=set();eligible=0;csv_registry=[]
    for name in ['real_user_dataset','real_user_evaluation','unified_recommender','personalized_recommender']:
        folder=ROOT/'outputs/scent_v2'/name/'data'
        for p in sorted(folder.rglob('*.csv')):
            # Merged/training-ready exports are original historical source copies.
            if p.name in ('merged_real_ratings.csv','training_ready_ratings.csv'):continue
            with p.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f);rows=list(reader);columns=reader.fieldnames or []
            users={r['user_id'] for r in rows if 'user_id' in r};matched=Counter(r['user_id'] for r in rows if r.get('perfume_id',r.get('product_id')) in candidates and 'user_id' in r)
            item=dict(path=str(p.relative_to(ROOT)),rows=len(rows),user_count=len(users),historical_ID_overlap=len(users&known_users),matched_479_rows=sum(matched.values()),users_with6_matched=sum(n>=6 for n in matched.values()),columns=columns,sha256=sha(p))
            csv_registry.append(item);source_users|=users
            if rows and p.name in ('real_user_ratings.csv','v21_ratings.csv'):eligible+=sum(n>=6 for u,n in matched.items() if u not in known_users)
        for p in sorted(folder.rglob('*.sqlite3')):
            if Path(str(p)+'-wal').exists():
                inventory.append(dict(path=str(p.relative_to(ROOT)),status='WAL_PRESENT_NOT_READ_IMMUTABLY'));continue
            with sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as c:
                tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                counts={t:c.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
            inventory.append(dict(path=str(p.relative_to(ROOT)),tables=counts,sha256=sha(p),read_mode='ro immutable, no writes'))
    # Legacy85 is previously audited data; metadata-only exact identity check.
    legacy=Path.home()/'Downloads/scent-ratings.csv';legacy_report=dict(status='NOT_FOUND')
    if legacy.exists():
        with legacy.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        users={r['participant_id'] for r in rows};matches=[match_one(r,catalog,list(candidates)) for r in rows];counts=Counter(r['participant_id'] for r,(i,s) in zip(rows,matches) if i is not None)
        legacy_report=dict(status='HISTORICALLY_AUDITED_NOT_NEW',rows=len(rows),users=len(users),matched479_ratings=sum(counts.values()),users_with6_matched=sum(n>=6 for n in counts.values()),matching_statuses=dict(Counter(s for i,s in matches)),historical_source_ID_overlap=len(users&known_users),physical_person_overlap='Not inferable from namespaced IDs',sha256=sha(legacy),original_preserved=True,no_numeric_preference_values_decoded=True)
    # Empty actual stores are decisive here. A nonempty store needs source-specific
    # provenance review rather than automatic treatment as an independent cohort.
    nonempty_real_tables=sum(n for item in inventory for t,n in item.get('tables',{}).items() if t in ('ratings','v21_ratings'))
    return dict(collection_SQLite_inventory=inventory,collection_CSV_inventory=csv_registry,collection_actual_rating_rows_SQLite=nonempty_real_tables,new_collection_users_seen=len(source_users-known_users),potential_new_count_eligible_users=eligible,legacy85=legacy_report,new_evaluable_independent_users=0,reason='No actual ratings in collection stores; legacy records historically audited and no6 canonical479 histories',other_sources='Synthetic fixtures forbidden; merged source exports are historical330 duplicates; original Basenotes was already externally evaluated, not new users')


def main():
    OUT.chmod(0o700);lock=lock_policy();candidates=json.loads((ROOT/'outputs/improvement/candidates.json').read_text());bg,dev,reserved,source=developer_data(ROOT/'outputs/validation/train_exclude_3.json',candidates);expected=json.loads((ROOT/'outputs/scent_v2/mf_accuracy_optimization/development_split_summary.json').read_text());assert source==expected
    train=list(bg)+[(r['user'],i,y) for r in dev for i,y in r['support']+r['answers']];training_users={u for u,i,r in train};known_users=training_users|reserved
    assert len(training_users)==305 and len(train)==1554 and len(known_users)==330 and not training_users&reserved
    catalog,raw_rows=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');sources=audit_sources(set(candidates),catalog,known_users)
    if sources['collection_actual_rating_rows_SQLite'] or sources['potential_new_count_eligible_users']:raise RuntimeError('Nonempty new source requires independence review; do not silently ignore or evaluate')
    exposure={name:json.loads((ROOT/path).read_text()) for name,path in [('V24','outputs/scent_v2/accuracy_optimization/final_opened_once.json'),('V31','outputs/scent_v2/final_validation/final_opened_once.json')]}
    assert exposure['V24']['final_open_count']==1 and exposure['V31']['final_open_count_V31']==1
    audit=dict(exposure_markers=exposure,groups=dict(background_users=len({u for u,i,r in bg}),background_ratings=len(bg),developer_users=len(dev),developer_ratings=sum(len(r['support'])+len(r['answers']) for r in dev),reserved_users=len(reserved)),role_user_overlap=0,training_reserved_overlap=0,new_independent_eligible_users=0,reserved25=dict(previously_evaluated=['V2-24','V2-31'],pristine_independent=False,current_ratings_decoded=0,current_evaluations=0),developer50=dict(repeated_model_selection=True,pristine_independent=False),background255=dict(original_training_source=True,pristine_independent=False),exposure_history_evidence=['experiments/scent_v2/accuracy_optimization/run.py:open_final','experiments/scent_v2/final_validation/run.py:open_gate','experiments/scent_v2/accuracy_root_cause/run.py:selection'],historical_results_recomputed=False,source_checksums_match_V25=True,source_inventory=sources,identity_caveat='Exact IDs checked, actual-person identity across namespaces cannot be deduced; future provenance attestation required')
    write(OUT/'data_independence_audit.json',audit)
    # Preparation scope is fixed in locked_policy BEFORE reading any new outcomes:
    # all permitted background+development users, not the reserved25 or new users.
    c=Content().fit(catalog,{i for u,i,r in train});b=Baseline().fit(train);m=MatrixFactorization(**V33_CONFIG['mf']).fit(train);m.Q.flags.writeable=False
    structure=Structured(raw_rows,{i for u,i,r in train},candidates);state=pack_state(c,m,b,candidates);values={f'fold1_{k}':v for k,v in state.items()};values.update(fold1_struct_ids=np.asarray(structure.ids),fold1_struct_matrix=structure.matrix,fold1_calib_raw_reference=np.asarray([],float),fold1_calib_content_reference=np.asarray([],float),fold1_gate=np.asarray(False))
    meta=dict(policy='structured',mf_config=V33_CONFIG['mf'],folds=1,default_fold=1,policy_sha256=lock['policy_sha256'],artifact_type='ONE_SHARED_305_USER_GENERALIZATION_STATE_NOT_DEPLOYED',train_users=305,train_ratings=1554,reserved_users_excluded=25,structured_vocab=structure.vocab,scope='305 permitted historical training users; evaluation people excluded')
    values['metadata']=np.asarray(json.dumps(meta));path=OUT/'prepared_shared_model.npz'
    with path.open('xb') as f:np.savez_compressed(f,**values)
    path.chmod(0o600)
    from experiments.scent_v2.accuracy_root_cause.run import load_selected
    lc,lm,lb,ls,lr,gate,loaded=load_selected(path);synthetic=list(zip(sorted(candidates)[:5],[.9,.1,.7,.3,.5]));empty=dict(raw_reference=np.asarray([]),content_reference=np.asarray([]))
    for policy in ['baseline','structured']:assert predict(policy,synthetic,candidates,c,m,b,structure,empty,False)==predict(policy,synthetic,candidates,lc,lm,lb,ls,lr,False)
    lock['prepared_model_sha256']=sha(path);(OUT/'locked_policy.json').write_text(json.dumps(lock,indent=2,ensure_ascii=False));verify_lock()
    write(OUT/'preparation_results.json',dict(status='READY_NOT_DEPLOYED',actual_MF_fits=1,Content_fits=1,train_users=305,train_ratings=1554,training_user_reserved_overlap=0,source=source,MF_loss_first=m.losses[0],MF_loss_last=m.losses[-1],both_models_share_Q_Content_popularity=True,roundtrip_ID_order_scores_exact=True,policy_sha256=lock['policy_sha256'],prepared_model_sha256=sha(path),V33_CV_artifact_used_as_operating_model=False,training_scope_difference='V33 CV train40 per fold; shared preparation train305, same algorithm but different fit scope, do not transfer CV metrics'))
    write(OUT/'evaluation_results.json',dict(status='NOT_EVALUATED',conclusion='GENERALIZATION_NOT_EVALUATED',reason='No eligible new independent user ratings in existing stores; legacy85 not new and not matched to479',real_accuracy_evaluated=False,eligible_new_users=0,policy_sha256=lock['policy_sha256'],models={'baseline':'NOT_EVALUATED','structured':'NOT_EVALUATED'},service_changed=False,decision='Keep existing Hybrid; preserve Structured as developer-CV candidate',no_retuning=True))
    with (OUT/'model_comparison.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['model','status','users','positive_users','ndcg_at5','recall_at5','hit_rate_at5']);w.writeheader()
        for name in ['baseline','structured']:w.writerow(dict(model=name,status='NOT_EVALUATED'))
    (OUT/'new_user_ratings_template.csv').write_text('user_id,perfume_id,rating\n')
    write(OUT/'provenance_template.json',dict(real_user_data=False,not_used_for_model_selection=False,pre_recommendation_ratings_only=False,identity_disjoint_from_historical_people_attested=False,consent_for_local_evaluation_confirmed=False,source_namespace='',instructions='Fill only verified facts for a future real dataset; template is not authorization or generated approval'))
    print(json.dumps(dict(status='GENERALIZATION_NOT_EVALUATED',new_users=0,training_users=305,training_ratings=1554,MF_fits=1,policy_sha256=lock['policy_sha256'],saved_inference_exact=True)),flush=True)

if __name__=='__main__':main()
