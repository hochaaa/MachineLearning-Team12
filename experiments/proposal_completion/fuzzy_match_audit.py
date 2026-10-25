"""Generate public-product review candidates only; no accepted mapping writes."""
from difflib import SequenceMatcher,get_close_matches
from common import *
from perfume.data import laure_catalog

def ratio(a,b):
    """Max of phrase/token-sorted character ratios; high score is not identity proof."""
    a,b=normalize(a),normalize(b)
    return max(SequenceMatcher(None,a,b,autojunk=False).ratio(),SequenceMatcher(None,' '.join(sorted(a.split())),' '.join(sorted(b.split())),autojunk=False).ratio())

def classify(brand,name,year,targets):
    """Return best same-brand candidate, mark version/year conflicts and score ties."""
    if targets and any(normalize(r['brand'])!=normalize(brand) for r in targets):
        return {'status':'BRAND_CONFLICT','similarity':0.,'margin':0.,'target_brand':'','target_name':'','reason':'cross-brand candidates prohibited'}
    if not targets:return {'status':'NO_SAFE_CANDIDATE','similarity':0.,'margin':0.,'target_brand':'','target_name':'','reason':'no exact-normalized brand candidates'}
    ranked=sorted([(ratio(name,r['name']),r) for r in targets],key=lambda x:(-x[0],x[1]['name'],x[1]['id']))
    score,r=ranked[0];margin=score-ranked[1][0] if len(ranked)>1 else score
    tags_a,tags_b=versions(name),versions(r['name'])
    ya,yb=normalize(year),normalize(r.get('year',''))
    if score<.72 or len(normalize(name))<4:status='NO_SAFE_CANDIDATE';reason='score below .72 or name too short'
    elif conflict(tags_a,tags_b):status='VERSION_CONFLICT';reason='explicit concentration/flanker conflict'
    elif ya.isdigit() and yb.isdigit() and ya!=yb:status='REVIEW_REQUIRED';reason='known year mismatch'
    elif margin<.08:status='REVIEW_REQUIRED';reason='tie or margin below .08'
    elif tags_a!=tags_b:status='REVIEW_REQUIRED';reason='asymmetric explicit concentration/version; absent means unknown'
    elif score>=.94:status='HIGH_CONFIDENCE_CANDIDATE';reason='score >=.94, margin >=.08; still NOT manually verified'
    else:status='REVIEW_REQUIRED';reason='plausible name similarity, not identity proof'
    return {'status':status,'similarity':score,'margin':margin,'target_brand':r['brand'],'target_name':r['name'],'reason':reason}

def main():
    catalog,fra=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');bybrand=defaultdict(list)
    for r in fra:bybrand[normalize(r['Brand'])].append({'id':r['url'],'brand':r['Brand'],'name':r['Perfume'],'year':r['Year']})
    existing_a=read_csv('outputs/audit/atrafshan_matching.csv')
    existing_b=read_csv('outputs/audit/external_matching.csv')
    bas,_=laure_catalog(ROOT/'Term-project-datasets')
    launch={str(r['pk']):str(r['fields'].get('launch_date') or '')[:4] for r in load('Term-project-datasets/perfumes.json')}
    brand_near={}
    groups={'atrafshan':[(r['source_item'],r['brand'],r['name'],'') for r in existing_a if r['status']!='accepted'],
            'basenotes':[(r['source_item'],bas[r['source_item']]['brand'],bas[r['source_item']]['name'],launch.get(r['source_item'],'')) for r in existing_b if r['status']!='accepted' and r['source_item'] in bas]}
    results=[];summaries={}
    for source,items in groups.items():
        statuses=Counter();generated=0
        for source_id,brand,name,year in items:
            targets=bybrand.get(normalize(brand),[])
            rec=classify(brand,name,year,targets)
            if not targets and normalize(brand) not in brand_near:
                brand_near[normalize(brand)]=bool(get_close_matches(normalize(brand),bybrand.keys(),n=1,cutoff=.85))
            if not targets and brand_near[normalize(brand)]:
                rec['status']='BRAND_CONFLICT';rec['reason']='only approximate brand spelling available; cross-brand candidate prohibited'
            generated+=bool(targets) and rec['similarity']>=.72
            statuses[rec['status']]+=1
            results.append({'source':source,'source_brand':brand,'source_name':name,'source_year':year,**rec,'manual_status':'NOT_MANUALLY_VERIFIED','applied_to_frozen_data':False})
        originals=existing_a if source=='atrafshan' else existing_b
        summaries[source]={'existing_exact_accepted':sum(r['status']=='accepted' for r in originals),'unmatched_or_ambiguous_analyzed':len(items),'candidate_generated_score_ge_072':generated,'statuses':dict(statuses),'source_year_available':source=='basenotes','known_source_years':sum(normalize(year).isdigit() for _,_,_,year in items),'source_concentration_separate_field_available':False}
        print(source,summaries[source],flush=True)
    table('fuzzy_candidates_review.csv',results);save('fuzzy_summary.json',{'sources':summaries,'same_brand_only':True,'min_score':.72,'high_score':.94,'min_margin':.08,'manually_verified':0,'applied_matches':0,'scope':'catalog metadata only; no reviews/rating values used; no automatic mapping changes'})
    counts=Counter(r['status'] for r in results)
    bar('fuzzy_status.svg','Fuzzy matching review status (catalog metadata only)',list(counts),list(counts.values()),'Existing exact accepted links excluded; no candidate is manually verified or applied')
if __name__=='__main__':main_run(main,'fuzzy_match_audit')
