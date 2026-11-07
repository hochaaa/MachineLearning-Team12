"""Profile disjoint Train-only data; generate/validate pilot; never call a recommender."""
import os,sys,json,csv,hashlib,subprocess,platform
from pathlib import Path
from collections import Counter
from .config import ROOT,HEAD,TRAIN,MANIFEST,CATALOG,CANDIDATES,OUT,POLICY


def native(value):
    """Strict JSON conversion of aggregate NumPy scalars, never mask NaN/Inf."""
    import numpy as np
    if isinstance(value,dict):return {str(k):native(v)for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [native(v)for v in value]
    if isinstance(value,np.ndarray):return native(value.tolist())
    if isinstance(value,np.generic):return value.item()
    return value


def write_json(path,value):
    with path.open('x')as f:json.dump(native(value),f,ensure_ascii=False,indent=2,allow_nan=False)


def write_csv(path,rows):
    with path.open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])if rows else []);w.writeheader();w.writerows(rows)


def digest_rows(rows):
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()


def main():
    os.chdir(ROOT)
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=HEAD:raise RuntimeError('HEAD mismatch')
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='development-v2':raise RuntimeError('Branch mismatch')
    if OUT.exists():raise RuntimeError('Existing output: STOP, no overwrite')
    state={'integrity':False};allowed={TRAIN.resolve(),MANIFEST.resolve(),CANDIDATES.resolve(),CATALOG.resolve()};protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for d in(ROOT/'experiments/scent_v2',ROOT/'outputs/scent_v2',ROOT/'docs/presentation')for p in d.rglob('*')if p.is_file()}
    def guard(event,args):
        if event=='open'and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve();writing=(isinstance(args[1],str)and any(c in args[1]for c in 'wax+'))or(isinstance(args[2],int)and args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing and not p.is_relative_to(OUT):raise RuntimeError('Protected file write')
            if not writing and p.is_relative_to(ROOT)and p.suffix in('.json','.csv','.npz','.npy'):
                if p not in allowed and not p.is_relative_to(OUT)and not(state['integrity']and str(p.relative_to(ROOT))in protected):raise RuntimeError('Forbidden model/evaluation/raw-rating access')
        if event in('os.remove','os.rmdir','os.rename','os.link','os.symlink','os.truncate','subprocess.Popen'):raise RuntimeError('Forbidden mutation/process')
        if event=='os.mkdir'and not Path(args[0]).resolve().is_relative_to(OUT):raise RuntimeError('Unexpected mkdir')
    sys.addaudithook(guard)
    forbidden=[]
    def no_model(frame,event,arg):
        if event=='call'and frame.f_code.co_name in('fit','score','ranking_metrics','fold_in')and('perfume/'in frame.f_code.co_filename or 'scent_v2/recommend.py'in frame.f_code.co_filename):forbidden.append(frame.f_code.co_name);raise RuntimeError('No recommender fit/inference/evaluation')
    sys.setprofile(no_model)
    import numpy as np
    from perfume.data import fragrantica
    from .boundary import evaluation_users,safe_train
    from .profiling import basic,features,structure,stats
    from .generator import estimate,generate
    from .quality import evaluate
    excluded,manifest_audit=evaluation_users(MANIFEST.read_text());assert len(excluded)==75 and manifest_audit['folds']==3
    safe,allIDs,boundary=safe_train(TRAIN.read_text(),excluded);assert not({u for u,i,y in safe}&excluded);candidates=json.loads(CANDIDATES.read_text());assert len(candidates)==479 and len(set(candidates))==479
    catalog,raw=fragrantica(CATALOG);assert all(i in catalog for i in candidates);cset=set(candidates);eligible=[r for r in safe if r[1]in cset];profile_all=basic(safe,candidates);profile=basic(eligible,candidates)
    assert profile['duplicates']==0 and profile['missing']==0 and profile['invalid']==0
    X,vocab,idf,feature_rows,co,means,effects=features(eligible,catalog,candidates);pref=structure(eligible,X,candidates)
    print(f'Boundary PASS: {boundary["source_rows"]} source rows; {boundary["excluded_user_rows_skipped_before_rating_decode"]} excluded rows never decoded; {len(safe)} safe rows',flush=True)
    print(f'Generator reference: {profile["users"]} users/{profile["perfumes"]} items/{profile["ratings"]} ratings; feature structure supported={pref["matched_feature_evidence"]}',flush=True)
    params=estimate(eligible,X,vocab,candidates,effects,pref['matched_feature_evidence'])
    ratings,users,audit,prob,tops=generate(params,X,vocab,candidates,allIDs,12,1000,150)
    again=generate(params,X,vocab,candidates,allIDs,12,1000,150)
    hashes=dict(ratings=digest_rows(ratings),users=digest_rows(users),audit=digest_rows(audit));assert hashes==dict(ratings=digest_rows(again[0]),users=digest_rows(again[1]),audit=digest_rows(again[2]));assert np.array_equal(prob,again[3])and tops==again[4];del again
    quality=evaluate(eligible,ratings,users,audit,X,candidates,allIDs,tops);quality.update(reproducibility=dict(seed=12,independent_full_generation_runs=2,identical_hashes=True,hashes=hashes),cohort_design=dict(activity_matched=150,support_target_enriched=850),preference_evidence_from_real=pref['matched_feature_evidence'])
    assert quality['hard_checks_PASS']
    OUT.mkdir();write_json(OUT/'config.json',POLICY);write_json(OUT/'boundary_audit.json',dict(manifest=manifest_audit,filter=boundary,all_excluded_users_removed=True,generator_reference_candidate_aligned=True,no_evaluation_rating_or_item_decodes=True))
    feature_scope=dict(candidate_features=len(feature_rows),candidate_notes=sum(r['kind']=='note'for r in feature_rows),candidate_accords=sum(r['kind']=='accord'for r in feature_rows),generator_vocabulary=len(vocab),generator_notes=sum(t.startswith('note:')for t in vocab),generator_accords=sum(t.startswith('accord:')for t in vocab),features_per_candidate=stats([len(catalog[i]['tokens'])for i in candidates]),empty_generator_vectors=int(np.sum(np.linalg.norm(X,axis=1)==0)))
    schema=dict(normalized_pool=dict(path=str(TRAIN.relative_to(ROOT)),format='UTF8 JSON list of positional triples',source_rows_IDcount_only=boundary['source_rows'],source_user_IDs=boundary['source_user_IDs'],columns=['user_sha256','Fragrantica_url','normalized_rating'],user_ID_column='position0',item_column='position1',rating_column='position2',source='Atrafshan -> conservative Fragrantica brand/name alignment; see src/perfume/data.py and data/README.md',historical_full_item_count_538='user/historical reference, NOT remeasured because protected item IDs skipped'),raw_Atrafshan=dict(path='Term-project-datasets/atrafshan_data.json',format='JSON list per documented existing adapter',row_count='NOT_READ_PROTECTED',column_count='nested_not_tabular_NOT_REAUDITED',documented_fields=['user_id','perfume_id','perfume_name','perfume_brand','user_vote_on_perfume.votes.رایحه'],raw_records_not_loaded=True),metadata=dict(path=str(CATALOG.relative_to(ROOT)),format='semicolon CSV cp1252',rows=len(raw),columns=list(raw[0]),column_count=len(raw[0]),item_ID='url',notes=['Top','Middle','Base'],accords=[f'mainaccord{i}'for i in range(1,6)],source='Fragrantica item metadata',aggregate_item_rating_fields_not_used=True),candidate_file=str(CANDIDATES.relative_to(ROOT)),candidate_count=479,split=dict(original_train='original validation/internal/external labels remain unread',Nested='user-disjoint Outer3/Inner2; all75 evaluation IDs excluded entirely via manifest users fields; support/answers structurally skipped'))
    write_json(OUT/'real_data_profile.json',dict(schema=schema,all_disjoint_Train=profile_all,generator_candidate_aligned_Train=profile,feature_scope=feature_scope,zero_policy='Original zero-excluded Train analytical assumption retained; zero semantics not resolved'))
    write_json(OUT/'preference_structure.json',pref);write_csv(OUT/'feature_statistics.csv',feature_rows);write_csv(OUT/'feature_cooccurrence.csv',co);write_json(OUT/'generator_parameters.private.json',params);write_json(OUT/'generator_vocabulary.json',dict(tokens=vocab,idf=idf))
    write_csv(OUT/'synthetic_ratings_pilot.csv',ratings);write_csv(OUT/'synthetic_users_pilot.csv',users);write_csv(OUT/'synthetic_generation_audit.csv',audit);write_json(OUT/'synthetic_quality_report.json',quality)
    dist=[];activity=[];pop=[]
    for scope,rows in [('eligible_all',safe),('eligible_candidates',eligible)]+[(k,[(r['synthetic_user_id'],r['perfume_id'],r['rating']/10)for r in ratings if k=='synthetic_combined'or r['cohort']==k])for k in('synthetic_combined','activity_matched','support_target_enriched')]:
        rc=Counter(float(y*10)for u,i,y in rows);ac=Counter(Counter(u for u,i,y in rows).values())
        for value in np.arange(0,10.01,.5):dist.append(dict(scope=scope,rating=float(value),count=rc[float(value)],fraction=rc[float(value)]/len(rows)))
        for n in range(1,21):activity.append(dict(scope=scope,ratings_per_user=n,users=ac[n],fraction=ac[n]/sum(ac.values())))
    realcount=Counter(i for u,i,y in eligible);sc=Counter(r['perfume_id']for r in ratings)
    for n,i in enumerate(candidates):pop.append(dict(perfume_id=i,eligible_Train_count=realcount[i],synthetic_count=sc[i],base_sampling_probability=params['base_selection_probabilities'][n],mean_user_sampling_probability=float(prob[n])))
    write_csv(OUT/'rating_distribution.csv',dist);write_csv(OUT/'user_activity_distribution.csv',activity);write_csv(OUT/'perfume_popularity_distribution.csv',pop)
    sys.setprofile(None);assert not forbidden;state['integrity']=True;assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in protected.items())
    write_json(OUT/'verification.json',dict(status='PASS',source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in allowed},boundary=boundary,manifest=manifest_audit,real_reference_rows=len(eligible),real_reference_users=profile['users'],synthetic_users=len(users),synthetic_ratings=len(ratings),same_seed_exact=True,recommendation_fit_inference_eval_calls=0,original_validation_internal_external_data_read=False,python=platform.python_version(),numpy=np.__version__,code_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path(__file__).parent.rglob('*.py')}));print(f'PASS: {len(users)} synthetic users/{len(ratings)} ratings; two-run hashes identical; no recommender fit/evaluation',flush=True)

if __name__=='__main__':main()
