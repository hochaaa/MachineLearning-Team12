"""Read-only independent Parfumo agreement analysis; never fit content vectors."""
from common import *
def compare(a,b):
    """Comparable iff both have at least one phrase; empty never equals true quality."""
    return {'comparable':bool(a and b),'jaccard':jaccard(a,b) if a and b else None,'exact':a==b if a and b else None,'common':len(a&b),'fra_only':len(a-b),'parfumo_only':len(b-a)}
def main():
    catalog,fra=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
    par=read_csv('Term-project-datasets/parfumo_data_clean.csv')
    fi=defaultdict(list);pi=defaultdict(list)
    for r in fra:fi[identity(r['Brand'],r['Perfume'])].append(r)
    for r in par:pi[identity(r['Brand'],r['Name'])].append(r)
    statuses=Counter(); comparisons=[];examples=[]
    for key,ps in pi.items():
        fs=fi.get(key,[])
        if not fs:statuses['no_exact_key']+=len(ps);continue
        if len(ps)!=1 or len(fs)!=1:statuses['ambiguous_key']+=len(ps);continue
        a,b=fs[0],ps[0]
        if conflict(versions(a['Perfume']),versions(b['Name'],b['Concentration'])):statuses['version_conflict']+=1;continue
        ya,yb=normalize(a['Year']),normalize(b['Release_Year'])
        if ya.isdigit() and yb.isdigit() and ya!=yb:statuses['year_conflict']+=1;continue
        statuses['accepted_exact_conservative']+=1
        notes_a=set().union(*(fields(a[k]) for k in ['Top','Middle','Base']))
        notes_b=set().union(*(fields(b[k]) for k in ['Top_Notes','Middle_Notes','Base_Notes']))
        accord_a=set().union(*(fields(a[f'mainaccord{n}']) for n in range(1,6)))
        accord_b=fields(b['Main_Accords'])
        rec={'brand':a['Brand'],'name':a['Perfume'],'concentration_verified_both':bool(versions(a['Perfume'])&{'edt','edp','edc','parfum','extrait'} and versions(b['Name'],b['Concentration'])&{'edt','edp','edc','parfum','extrait'})}
        for prefix,x,y in [('notes',notes_a,notes_b),('accords',accord_a,accord_b)]:
            rec.update({prefix+'_'+k:v for k,v in compare(x,y).items()})
        comparisons.append(rec)
        if notes_a and notes_b and jaccard(notes_a,notes_b)<.2 and len(examples)<20:
            examples.append({'brand':a['Brand'],'name':a['Perfume'],'fra_notes':'; '.join(sorted(notes_a)),'parfumo_notes':'; '.join(sorted(notes_b)),'jaccard':jaccard(notes_a,notes_b)})
    results={}
    for group in ['notes','accords']:
        valid=[r for r in comparisons if r[group+'_comparable']]
        results[group]={'comparable':len(valid),'missing_one_or_both':len(comparisons)-len(valid),'exact_agreement':float(np.mean([r[group+'_exact'] for r in valid])) if valid else None,'mean_jaccard':float(np.mean([r[group+'_jaccard'] for r in valid])) if valid else None,'median_jaccard':float(np.median([r[group+'_jaccard'] for r in valid])) if valid else None,'mean_common':float(np.mean([r[group+'_common'] for r in valid])) if valid else None,'mean_fra_only':float(np.mean([r[group+'_fra_only'] for r in valid])) if valid else None,'mean_parfumo_only':float(np.mean([r[group+'_parfumo_only'] for r in valid])) if valid else None}
    strict={}
    for group in ['notes','accords']:
        subset=[r for r in comparisons if r['concentration_verified_both'] and r[group+'_comparable']]
        strict[group]={'comparable':len(subset),'exact_agreement':float(np.mean([r[group+'_exact'] for r in subset])) if subset else None,'mean_jaccard':float(np.mean([r[group+'_jaccard'] for r in subset])) if subset else None}
    missing={k:sum(not fields(r[k]) for r in par)/len(par) for k in par[0]}
    summary={'rows':len(par),'columns':list(par[0]),'normalized_identity_keys':len(pi),'duplicate_identity_rows':sum(len(v)-1 for v in pi.values()),'rows_in_duplicate_identity_groups':sum(len(v) for v in pi.values() if len(v)>1),'missing_fraction':missing,'match_status_rows':dict(statuses),'accepted_fraction_all_parfumo_rows':len(comparisons)/len(par),'concentration_explicit_both':sum(r['concentration_verified_both'] for r in comparisons),'agreement':results,'agreement_explicit_concentration':strict,'synonym_mapping':{},'known_limit':'Missing concentration/year remains unknown; name agreement is not manual identity certification. No brand alias or semantic synonym inference.'}
    save('parfumo_summary.json',summary);table('parfumo_comparisons.csv',comparisons);table('parfumo_disagreement_examples.csv',examples)
    bar('parfumo_agreement.svg','Matched metadata agreement (comparable pairs only)',['Notes exact','Notes mean Jaccard','Accords exact','Accords mean Jaccard'],[results[g][m] or 0 for g,m in [('notes','exact_agreement'),('notes','mean_jaccard'),('accords','exact_agreement'),('accords','mean_jaccard')]],'Source: Fragrantica + Parfumo local CSV; metadata agreement, not recommendation accuracy')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main_run(main,'parfumo_crosscheck')
