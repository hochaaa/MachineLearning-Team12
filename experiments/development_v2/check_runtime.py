"""Post-selection synthetic inference checks/timing; not rating-ground-truth evaluation."""
import json,time,resource,sys
import numpy as np
from data import OUT,write,guard
from recommend_v2 import ServiceV2,demo_support

def substantive(result):
    """Strip nondeterministic timing field for exact regression comparison."""
    return {k:v for k,v in result.items() if k!='foldin_seconds'}

def main():
    guard();service=ServiceV2();q=service.model.Q.copy();records=[];times=[];foldtimes=[]
    for scenario in ['high','low','mixed','equal','zeros']:
        support=demo_support(service,scenario)
        for condition in ['none','woody','floral','rose']:
            start=time.perf_counter();a=service.recommend(support,condition);times.append(time.perf_counter()-start);foldtimes.append(a['foldin_seconds'])
            b=service.recommend(list(reversed(support)),condition);assert substantive(a)==substantive(b)
            assert len(a['results'])<=5 and all(r['filter_satisfied'] and np.isfinite(r['score']) for r in a['results'])
            assert not {i for i,_ in support}&{r['perfume_id'] for r in a['results']}
            records.append({'scenario':scenario,'condition':condition,'returned':len(a['results']),'order_repeat_exact':True,'scores_finite':True,'rules_satisfied':True})
    invalid=[[],[('unknown',.5)]*3,[('x',float('nan'))]*3]
    support=demo_support(service)
    invalid += [[support[0]]*3,support[:2],[(i,1.2) for i,_ in support],[(i,float('inf')) for i,_ in support],[(i,float('nan')) for i,_ in support]]
    for case in invalid:
        try:service.recommend(case)
        except ValueError:continue
        raise AssertionError('Invalid support accepted')
    # Vectorized factor products must match a scalar reference (optimization regression).
    from foldin_v2 import fold_in,score_vector
    z=fold_in(service.model,support,service.config['foldin_regularization']);pool=service.pool
    if hasattr(service.model,'bu'):
        reference=np.array([np.clip(service.model.mean+service.model.bi[service.model.items[i]]+z[-1]+z[:-1]@service.model.Q[service.model.items[i]],0,1) for i in pool])
        np.testing.assert_array_equal(reference,score_vector(service.model,z,pool))
    np.testing.assert_array_equal(q,service.model.Q)
    second=ServiceV2();assert substantive(service.recommend(support))==substantive(second.recommend(support))
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;rss_bytes=rss if sys.platform=='darwin' else rss*1024
    write('diagnostics/runtime_checks.json',{'load_seconds':service.load_seconds,'recommend_seconds_median':float(np.median(times)),'recommend_seconds_p95':float(np.quantile(times,.95)),'foldin_seconds_median':float(np.median(foldtimes)),'peak_process_rss_bytes':rss_bytes,'memory_scope':'whole standalone process peak, not isolated model size','valid_behavior_cases':records,'invalid_cases_rejected':len(invalid),'item_factors_unchanged':True,'reload_same_output':True,'legacy_test_read':False,'real_user_study':False,'performance':'no prior V2 optimization baseline; scalar arithmetic equality checked only'})
    print('Runtime PASS:',len(records),'valid cases;',len(invalid),'invalid cases rejected; fixed Q; reload parity')
if __name__=='__main__':main()
