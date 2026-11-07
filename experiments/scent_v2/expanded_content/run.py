"""Version-locked Content experiment; no MF/IDF fits and no service mutation."""
import argparse,csv,hashlib,json,math,os
from collections import Counter,defaultdict
from pathlib import Path
from statistics import mean,median,pstdev
from unittest.mock import patch
from .policy import POLICY
from .models import ContentExperiment,project
from .catalog import build,ROOT,OUT
from .evaluation import user_metrics,summarize,label_blind_split


def write_json(name,data):
    """Create only new local outputs; private cases never contain original user IDs."""
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
    p.chmod(0o600)


def write_csv(name,rows):
    """Nonempty aggregate/model tables; no original user identity columns."""
    if not rows:return
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    p.chmod(0o600)


def density(vectors):
    """Actual sparse counts by channel, with no family inference."""
    lengths=[len(v) for v in vectors.values()]
    return dict(items=len(lengths),mean_tokens=mean(lengths) if lengths else None,median_tokens=median(lengths) if lengths else None,
        mean_note_tokens=mean(sum(t.startswith('note:') for t in v) for v in vectors.values()) if lengths else None,
        mean_accord_tokens=mean(sum(t.startswith('accord:') for t in v) for v in vectors.values()) if lengths else None)


def score_statistics(values):
    """Descriptive candidate-score distribution; no fitting/calibration."""
    values=list(values)
    return dict(count=len(values),minimum=min(values) if values else None,maximum=max(values) if values else None,
        mean=mean(values) if values else None,median=median(values) if values else None,std=pstdev(values) if values else None)


def top_diagnostics(top,vectors,metadata,new_ids):
    """Mean pairwise cosine and brand diversity within a generated Top5."""
    pair=[]
    for a in range(len(top)):
        for b in range(a+1,len(top)):
            x,y=vectors[top[a]],vectors[top[b]];pair.append(sum(v*y.get(t,0) for t,v in x.items()))
    return dict(new_slots=sum(i in new_ids for i in top),old_slots=sum(i not in new_ids for i in top),
        top5_pairwise_cosine=mean(pair) if pair else None,top5_brands=len({metadata[i]['brand'] for i in top}))


def main():
    """--csv approved local original; all model/feature/search choices are predeclared."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--csv',type=Path,required=True);a=parser.parse_args()
    if (OUT/'policy.json').exists():raise FileExistsError('Existing experiment; no automatic overwrite/rerun')
    write_json('policy.json',POLICY)
    from perfume.data import fragrantica
    from perfume.models import Content,MatrixFactorization
    from deployment.final_v1.config import assets_path,inspect_assets
    from experiments.scent_v2.perfume_catalog_expansion.build import product_inventory
    from experiments.scent_v2.real_rating_retraining.audit import read_csv
    from experiments.scent_v2.recommend import rank
    directory=assets_path();runtime_integrity=inspect_assets(directory)
    payload=json.loads((directory/'content.json').read_text());idf=payload['idf'];legacy=payload['vectors']
    old_ids=json.loads((ROOT/'outputs/improvement/candidates.json').read_text())
    assert len(old_ids)==len(set(old_ids))==479 and set(legacy)==set(old_ids)
    old_hash=hashlib.sha256(json.dumps(legacy,sort_keys=True).encode()).hexdigest()
    idf_hash=hashlib.sha256(json.dumps(idf,sort_keys=True).encode()).hexdigest()
    catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
    vectors,new,mapping,review,provenance=build(legacy,idf,catalog,product_inventory(a.csv))
    assert new and len(vectors)==479+len(new)
    assert all(vectors[i]==legacy[i] for i in old_ids)
    metadata={i:dict(brand=catalog[i]['brand'],name=catalog[i]['name'],origin='existing479',concentration='Legacy metadata preserved') for i in old_ids}
    metadata.update({i:dict(brand=r['brand'],name=r['name'],origin='licensed_notes_new',concentration=r['concentration']) for i,r in new.items()})
    expanded_ids=sorted(vectors);new_ids=set(new)
    write_csv('expanded_catalog.csv',[dict(canonical_id=i,origin=metadata[i]['origin'],brand=metadata[i]['brand'],name=metadata[i]['name'],
        concentration=metadata[i]['concentration'],source_product_id=new[i]['source_product_id'] if i in new else '',
        license='CC-BY-4.0' if i in new else 'Existing local-use contract unchanged',source_url=new[i]['licensed_url'] if i in new else i) for i in expanded_ids])
    write_csv('candidate_review.csv',review)
    write_json('expanded_feature_summary.json',dict(existing=479,new=len(new),total=len(vectors),
        legacy_vectors_sha256=old_hash,frozen_idf_sha256=idf_hash,idf_vocabulary=len(idf),
        existing_vector_density=density(legacy),new_vector_density=density({i:vectors[i] for i in new}),
        notes_and_accords='Original479 uses original notes+accords. New uses independently licensed literal notes only; no official accord/family fields converted.',
        source=provenance,unlicensed_V217_notes_or_vectors_read=False,V217_identity_denylist_only=True,
        newly_oov_unique=sorted({t for r in new.values() for t in r['oov_tokens']}),
        canonical_mapping=mapping,new_items=new,runtime_integrity=runtime_integrity['status']))
    records=[];changes=[];comparison=[];examples=[];diagnostics=[];trackA_scores=[]
    # These guards monitor/block any fit entry, including an accidental legacy fit.
    with patch.object(Content,'fit',side_effect=AssertionError('IDF fit forbidden')) as cf,patch.object(MatrixFactorization,'fit',side_effect=AssertionError('MF fit forbidden')) as mf:
        folds=json.loads((ROOT/'outputs/scent_v2/baseline/split_manifest.private.json').read_text())
        for fold in folds:
            stored=json.loads((ROOT/f'outputs/scent_v2/baseline/fold{fold["fold"]}_model.private.json').read_text())
            fold_idf=stored['content_idf']
            fold_vectors={i:project(catalog[i]['tokens'],fold_idf) for i in old_ids}
            original=Content();original.idf=fold_idf;original.vectors=fold_vectors
            experimental=ContentExperiment(fold_vectors)
            for user in fold['users']:
                support=fold['support'][user]
                # Scoring before any held-out answer lookup. Same479/support/exclusion.
                pool=sorted(set(old_ids)-{i for i,y in support})
                scores=original.score(support,pool);top=rank(pool,scores)[:5]
                result=experimental.score(support,old_ids)
                assert top==result['top']
                maxdiff=max(abs(float(y)-result['all_scores'][i]) for i,y in zip(pool,scores))
                if maxdiff>1e-12:raise AssertionError('TrackA original score regression')
                answers=fold['answers'][user]  # Harness only after scoring.
                acc=user_metrics(top,answers);accb=user_metrics(result['top'],answers)
                assert acc==accb
                records.append(dict(top=top,answers=answers,accuracy=acc))
                changes.append(dict(anonymous_case=len(changes)+1,fold=fold['fold'],ndcg_A=acc['ndcg'] if acc else None,
                    ndcg_B=accb['ndcg'] if accb else None,delta=0 if acc else None,max_score_delta=maxdiff,top5_equal=True))
                trackA_scores.extend(float(v) for v in scores)
        trackA=summarize(records,old_ids)
        target=next(r for r in csv.DictReader((ROOT/'outputs/scent_v2/baseline/accuracy.csv').open()) if r['track']=='A' and r['method']=='content')
        assert abs(trackA['ndcg']-float(target['ndcg']))<1e-12
        write_json('private/trackA_changes.json',changes)
        comparison += [dict(track='A_historical_fold479',model=model,users=trackA['users'],positive_users=trackA['positive_users'],
            ndcg_at5=trackA['ndcg'],recall_at5=trackA['recall'],hit_rate_at5=trackA['hit_rate'],coverage=trackA['coverage_fraction'],
            new_slot_fraction=0,status='MEASURED_REGRESSION_NOT_IMPROVEMENT',feature_scope='Existing fold-specific trained IDF, not global Frozen IDF') for model in ('A_original_fold_content','B_experimental_legacy479')]
        rows,_=read_csv(a.csv);histories=defaultdict(list);raw_users={r['participant_id'] for r in rows}
        for r in rows:
            if r['product_id'] in mapping:histories[r['participant_id']].append((mapping[r['product_id']],r['numeric_score']/10))
        if any(len(h)!=len({i for i,y in h}) for h in histories.values()):raise ValueError('Canonical user/item collision; do not deduplicate labels silently')
        eligible=sorted(u for u,h in histories.items() if len(h)>=6)
        enough=len(eligible)>=POLICY['min_new_accuracy_users']
        mapping_summary=dict(raw_users=len(raw_users),raw_ratings=len(rows),mapped_users=len(histories),mapped_ratings=sum(map(len,histories.values())),
            unmapped_ratings=sum(r['product_id'] not in mapping for r in rows),mapped_user_activity_histogram=dict(Counter(map(len,histories.values()))),
            original_score_policy='Raw score unchanged, normalized score/10 for profile only',
            existing_new_person_overlap='UNKNOWN; no independent-user or external validation claim',
            V214_independent_ratings_read=0,raw_user_IDs_in_outputs=False)
        write_json('rating_mapping_summary.json',mapping_summary)
        write_json('evaluation_eligibility.json',dict(candidate_count=len(vectors),matched6plus_users=len(eligible),support5_possible=len(eligible),
            minimum_accuracy_users=POLICY['min_new_accuracy_users'],accuracy_evaluation='MEASURED' if enough else 'NOT_EVALUATED_SMALL_COHORT',
            rule='Eligibility counts/IDs only; no relevance labels used to select users',
            heldout_used_for_scoring=False,all_observed_unknowns_not_negatives=True,
            seed=12,hash_policy='12:v218:support:{local-user-ID}:{canonical-item-ID}',
            privacy='Per-user manifest not exported; examples omit original IDs',policy=POLICY['minimum_cohort_reason']))
        modelB=ContentExperiment(vectors);modelA=ContentExperiment(legacy)
        modelA_adapter=ContentExperiment(vectors) # Same support vectors; pool remains old479.
        new_records=[];strict_unscorable=0
        for user in eligible:
            support,answers=label_blind_split(histories[user],user)
            result=modelB.score(support,expanded_ids);repeat=modelB.score(support,expanded_ids)
            assert result==repeat and len(result['top'])==5
            strict=modelA.score(support,old_ids)
            strict_unscorable+=strict['status']!='OK'
            control=modelA_adapter.score(support,old_ids)
            # <3 users: do not inspect held-out labels for accuracy/positive counts.
            accuracy=user_metrics(result['top'],answers) if enough else None
            new_records.append(dict(top=result['top'],accuracy=accuracy,answers=answers if enough else []))
            case=len(diagnostics)+1
            diagnostics.append(dict(anonymous_case=case,kind='REAL_SUPPORT_ONLY_TECHNICAL' if not enough else 'EXPLORATORY_REAL_USER_EVAL',
                support_size=5,heldout_size=len(answers),same_input_exact=True,
                strict_A_status=strict['status'],A_shared_input_adapter_top5=control['top'],
                expanded_top5=result['top'],top5=top_diagnostics(result['top'],vectors,metadata,new_ids),
                candidate_scores=score_statistics(result['all_scores'].values()),
                new_candidate_scores=score_statistics(v for i,v in result['all_scores'].items() if i in new_ids),
                old_candidate_scores=score_statistics(v for i,v in result['all_scores'].items() if i not in new_ids)))
            for rank_n,(item,value) in enumerate(zip(result['top'],result['scores']),1):
                examples.append(dict(track='B_support_only' if not enough else 'B_exploratory',anonymous_case=case,
                    evidence='Actual user support5; held-out labels not used for scores',rank=rank_n,item=item,brand=metadata[item]['brand'],name=metadata[item]['name'],
                    score=value,origin=metadata[item]['origin'],accuracy_status='MEASURED' if enough else 'NOT_EVALUATED_SMALL_COHORT'))
        trackB=summarize(new_records,expanded_ids,new_ids)
        if not enough:
            for k in ('ndcg','precision','recall','hit_rate','actual_positive_hits','ndcg_user_std','positive_users','no_positive_users'):trackB[k]='NOT_EVALUATED'
            trackB['accuracy_status']='NOT_EVALUATED_SMALL_COHORT'
            trackB['status']='TECHNICAL_INFERENCE_EXPOSURE_ONLY'
        comparison.append(dict(track='B_expanded',model='B_expanded_licensed_notes',users=len(eligible),positive_users=trackB.get('positive_users','NOT_EVALUATED'),
            ndcg_at5=trackB.get('ndcg','NOT_EVALUATED'),recall_at5=trackB.get('recall','NOT_EVALUATED'),hit_rate_at5=trackB.get('hit_rate','NOT_EVALUATED'),
            coverage=trackB.get('coverage_fraction','NOT_EVALUATED'),new_slot_fraction=trackB.get('new_slot_fraction','NOT_EVALUATED'),
            status=trackB['status'],feature_scope='Global frozen old479 + licensed new Notes-only; not comparable to TrackA folds'))
        comparison.append(dict(track='B_original_baseline',model='A_strict_existing479',users=len(eligible),positive_users='NOT_EVALUATED',ndcg_at5='NOT_EVALUATED',
            recall_at5='NOT_EVALUATED',hit_rate_at5='NOT_EVALUATED',coverage='NOT_EVALUATED',new_slot_fraction=0,
            status='UNSCORABLE_NEW_SUPPORT' if strict_unscorable else 'NOT_EVALUATED',feature_scope='Original vectors do not contain new input IDs; no fake score/fallback'))
        # A catalog-coverage control with common support projection is not the strict A.
        write_json('private/technical_cases.json',diagnostics)
        write_csv('recommendation_examples.csv',examples)
        # A reproducible synthetic INPUT demo uses real licensed features but no fake truth.
        if len(new)>=6:
            sample=sorted(new)[:5];demo_support=[(i,.7) for i in sample];demo=modelB.score(demo_support,expanded_ids)
            assert len(demo['top'])==5
            write_json('synthetic_input_demo.json',dict(kind='SYNTHETIC_INPUT_ONLY_NOT_REAL_USER_OR_ACCURACY',support=demo_support,
                result={k:v for k,v in demo.items() if k!='all_scores'},same_input_exact=demo==modelB.score(demo_support,expanded_ids)))
        assert cf.call_count==mf.call_count==0
    assert hashlib.sha256(json.dumps(legacy,sort_keys=True).encode()).hexdigest()==old_hash
    assert hashlib.sha256(json.dumps(idf,sort_keys=True).encode()).hexdigest()==idf_hash
    write_csv('model_comparison.csv',comparison)
    write_json('recommendation_diagnostics.json',dict(track_A=trackA,trackA_aggregate_scores=score_statistics(trackA_scores),
        trackA_exact_top5_parity=True,trackA_max_score_delta=max(r['max_score_delta'] for r in changes),
        track_B=trackB,real_support_technical_cases=diagnostics,
        strict_A_unscorable_new_support_users=strict_unscorable,
        support_adapter_control='Same new support vectors but old479 candidates; exposure-only coverage control, not unchanged service Model A',
        caution='Candidate/feature scopes differ. No accuracy improvement inferred from coverage/exposure or nonzero vectors.',
        MF_fit_calls=0,Content_fit_calls=0,unlicensed_manufacturer_note_inferences=0))
    print(json.dumps(dict(new_candidates=len(new),total_candidates=len(vectors),mapped_ratings=mapping_summary['mapped_ratings'],
        matched6plus_users=len(eligible),trackA_ndcg=trackA['ndcg'],trackB_status=trackB['status'],trackB_new_slot_fraction=trackB.get('new_slot_fraction')),ensure_ascii=False))

if __name__=='__main__':main()
