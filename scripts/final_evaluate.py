"""One-time frozen internal and external assessment. Not imported by tuning code."""
import hashlib
import json
import sys
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from perfume.data import read_json,write_json,write_csv,fragrantica,laure_catalog,matcher,match,normalize
from perfume.frozen import load_frozen,score_frozen,sha256
from perfume.external_protocol import external_partition
from perfume.evaluation import evaluate,rating_errors


def aggregate_with_intervals(predictions,answers,k,relevance,seed):
    """Fixed metrics plus descriptive paired-user bootstrap intervals; no model selection."""
    summaries,per=evaluate(predictions,answers,k,relevance)
    for row in summaries:
        values=np.array([r['ndcg'] for r in per if r['method']==row['method']])
        if len(values):
            rng=np.random.default_rng(seed)
            means=np.mean(values[rng.integers(0,len(values),size=(2000,len(values)))],axis=1)
            row['ndcg_bootstrap_low'],row['ndcg_bootstrap_high']=map(float,np.quantile(means,[.025,.975]))
        else:row['ndcg_bootstrap_low']=row['ndcg_bootstrap_high']=None
    return summaries,per


def internal(directory,freeze,mf,content,baseline):
    """Read internal test labels only after frozen scorer predictions for all fixed cohort users."""
    selected=freeze['selected']
    train=read_json(freeze['train_path'])
    candidates=read_json(freeze['candidates_path'])
    histories=defaultdict(list)
    for u,i,r in train:histories[u].append((i,r))
    # User cohort is known from the original validation design, not selected from test labels.
    users=sorted({u for u,_,_ in read_json('outputs/improvement/validation.json')})
    predictions={u:score_frozen(histories[u],candidates,mf,content,baseline,selected['alpha'],selected['k'],user=u) for u in users}
    answers=read_json('outputs/improvement/test.json')
    summaries,per=aggregate_with_intervals(predictions,answers,selected['k'],selected['relevance'],selected['seed'])
    write_csv(directory/'internal_metrics.csv',summaries)
    write_csv(directory/'internal_per_user.csv',per)
    write_json(directory/'internal_rankings.json',predictions)
    write_json(directory/'internal_rating_errors.json',rating_errors(answers,mf,baseline))
    return {'users':len(users),'answers':len(answers),'positive_users':summaries[0]['positive_users'],
            'answers_outside_candidates':sum(i not in candidates for _,i,_ in answers)}


def external(directory,freeze,mf,content,baseline):
    """External answer values stay in evaluation harness; scoring takes only support.

    Cohort and support/held-out assignment use IDs only. A fixed candidate catalog is not
    constructed from answer positives. All cohort users are scored before labels are evaluated.
    """
    selected=freeze['selected'];protocol=selected['external_protocol']
    for path,expected in freeze['external_raw_sha256'].items():
        if sha256(path)!=expected:raise ValueError('External raw data changed after freeze')
    candidates=read_json(freeze['candidates_path']);pool=set(candidates)
    catalog,_=fragrantica('Term-project-datasets/fra_cleaned.csv');index=matcher(catalog)
    source_catalog,fk=laure_catalog('Term-project-datasets')
    mapping={i:target for i,row in source_catalog.items() if (target:=match(index,row['brand'],row['name'])[0])}
    raw=read_json('Term-project-datasets/reviews.json')
    grouped=defaultdict(list)
    for row in raw:
        fields=row['fields'];source=str(fields['perfume'])
        if source not in mapping or mapping[source] not in pool:continue
        user=hashlib.sha256(('basenotes:'+str(fields['user'])).encode()).hexdigest()
        grouped[user,mapping[source]].append(fields['rate'])
    # Quarantine duplicate canonical pairs by identity, independently of their rating values.
    unique={key:values[0] for key,values in grouped.items() if len(values)==1}
    duplicates=sum(len(v) for v in grouped.values() if len(v)>1)
    selected_ids,excluded=external_partition(list(unique),set(mf.items),protocol['min_history'],protocol['support_seed'])
    lo,hi=protocol['rating_min'],protocol['rating_max']
    invalid=sum(not isinstance(r,(int,float)) or not np.isfinite(r) or not lo<=r<=hi for r in unique.values())
    if invalid:
        write_json(directory/'external_blocked.json',{'reason':'Frozen rating scale failed contract','invalid_values':invalid})
        return {'status':'BLOCKED: rating-scale contract failed; no external metrics computed'}
    support={};answers=[]
    for user,(support_items,answer_items) in selected_ids.items():
        support[user]=[(i,(unique[user,i]-lo)/(hi-lo)) for i in support_items]
        answers.extend((user,i,(unique[user,i]-lo)/(hi-lo)) for i in answer_items)
    # Save separate artifacts; score_frozen cannot open or accept answer records.
    write_json(directory/'external_support.json',support)
    write_json(directory/'external_answers_private.json',answers)
    before=hashlib.sha256(mf.Q.tobytes()).hexdigest()
    predictions={u:score_frozen(support[u],candidates,mf,content,baseline,selected['alpha'],selected['k']) for u in sorted(selected_ids)}
    assert before==hashlib.sha256(mf.Q.tobytes()).hexdigest()
    summaries,per=aggregate_with_intervals(predictions,answers,selected['k'],protocol['relevance'],selected['seed'])
    write_csv(directory/'external_metrics.csv',summaries)
    write_csv(directory/'external_per_user.csv',per)
    write_json(directory/'external_rankings.json',predictions)
    write_json(directory/'external_manifest.json',{'protocol':protocol,'by_user':selected_ids,
               'assignment_depends_on_values':False,'factor_sha256_unchanged':True})
    counts=Counter(u for u,_ in unique)
    source_rated={str(r['fields']['perfume']) for r in raw}
    # Shared-feature audit uses catalog notes only, no external rating preference values.
    external_notes=[{'note:'+normalize(t) for field in ('top_notes','heart_notes','base_notes')
                     for t in row[field]} for source,row in source_catalog.items()
                    if source in mapping and mapping[source] in pool]
    total_tokens=sum(len(row) for row in external_notes)
    matched_tokens=sum(sum(t in content.idf for t in row) for row in external_notes)
    features={'matched_candidate_catalog_items':len(external_notes),
              'nonempty_note_documents':sum(bool(row) for row in external_notes),
              'documents_with_train_vocabulary':sum(any(t in content.idf for t in row) for row in external_notes),
              'shared_note_tokens':matched_tokens,'all_external_note_tokens':total_tokens,
              'train_vocabulary_token_coverage':matched_tokens/total_tokens if total_tokens else None,
              'inference_uses':'Frozen Fragrantica vectors for matched products; external notes transformed/audited but not used to retune profiles'}
    feasibility={'status':'EVALUATED_ONCE','raw_reviews':len(raw),'source_rated_items':len(source_rated),
                 'content_matched_rated_items':len(source_rated&mapping.keys()),
                 'candidate_matched_source_rated_items':len({i for i in source_rated if i in mapping and mapping[i] in pool}),
                 'factor_matched_source_rated_items':len({i for i in source_rated if i in mapping and mapping[i] in mf.items}),
                 'candidate_unique_interactions':len(unique),'canonical_duplicate_rows_quarantined':duplicates,
                 'candidate_matched_users':len(counts),'history_ge2':sum(v>=2 for v in counts.values()),
                 'history_ge3':sum(v>=3 for v in counts.values()),'history_ge5':sum(v>=5 for v in counts.values()),
                 'eligible_users':len(selected_ids),'excluded_users':excluded,
                 'support_interactions':sum(len(r) for r in support.values()),'held_out_interactions':len(answers),
                 'positive_held_out_interactions':sum(r>=protocol['relevance'] for _,_,r in answers),
                 'positive_users':summaries[0]['positive_users'] if summaries else 0,
                 'no_positive_users':summaries[0]['no_positive_users'] if summaries else 0,
                 'support_factor_interactions':sum(i in mf.items for rows in support.values() for i,_ in rows),
                 'shared_feature_audit':features,'fk_audit':fk,'rate_value_counts':dict(Counter(str(r) for r in unique.values())),
                 'external_mae_rmse':'N/A: cross-source score semantics not independently validated; ordinal linear mapping assumption for support only',
                 'feature_scope':'Frozen Fragrantica matched catalog; no external feature fitting, no claim of unseen-item feature transfer'}
    write_json(directory/'external_feasibility.json',feasibility)
    return feasibility


def main():
    directory=Path('outputs/final')
    freeze,mf,content,baseline=load_frozen(directory)
    # Fail closed on retries. A failed attempt must be inspected, not blindly rerun.
    with (directory/'evaluation_started.json').open('x') as stream:
        json.dump({'freeze_sha256':sha256(directory/'freeze.json'),'policy':'One attempt; no tuning after test'},stream)
    internal_summary=internal(directory,freeze,mf,content,baseline)
    write_json(directory/'internal_summary.json',internal_summary)
    external_summary=external(directory,freeze,mf,content,baseline)
    write_json(directory/'evaluation_complete.json',{'internal':internal_summary,'external':external_summary,
               'freeze_sha256':sha256(directory/'freeze.json')})
    print(json.dumps({'internal':internal_summary,'external':external_summary},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
