"""Fixed final-model synthetic integration tests and cold request timings; no MF fitting."""
import sys,time,resource
import numpy as np
from v3_data import ROOT,OUT,save,guard,sha
from recommend_v3 import ServiceV3,synthetic_support

def stable(result):return {k:v for k,v in result.items() if k!='foldin_seconds'}

def no_mf_fit(frame,event,arg):
    if event=='call' and frame.f_code.co_name=='fit' and type(frame.f_locals.get('self')).__name__ in {'MFV3','BiasMF','MatrixFactorization'}:raise RuntimeError('Runtime inference must not fit MF')

def main():
    guard();before=sha(OUT/'diagnostics/fit_ledger.json');sys.setprofile(no_mf_fit);service=ServiceV3();q=service.model.Q.copy();records=[];times={5:[],10:[]};foldtime=[]
    for scenario in ['high','low','mixed','equal','zeros','tens']:
        support=synthetic_support(service,scenario)
        for condition in ['none','woody','floral','rose']:
            for k in [5,10]:
                t=time.perf_counter();a=service.recommend(support,condition,k=k);times[k].append(time.perf_counter()-t);foldtime.append(a['foldin_seconds']);b=service.recommend(list(reversed(support)),condition,k=k)
                assert stable(a)==stable(b);assert len(a['results'])<=k;assert len({r['perfume_id'] for r in a['results']})==len(a['results']);assert not {i for i,_ in support}&{r['perfume_id'] for r in a['results']};assert all(np.isfinite(r['score']) and r['condition_satisfied'] for r in a['results'])
                records.append({'scenario':scenario,'condition':condition,'k':k,'returned':len(a['results']),'deterministic_order':True,'valid_unique_unseen_results':True})
    s=synthetic_support(service);bad=[[],s[:2],[s[0]]*3,[('unknown',5),s[1],s[2]],[(i,11) for i,r in s],[(i,-1) for i,r in s],[(i,float('nan')) for i,r in s],[(i,float('inf')) for i,r in s]]
    for x in bad:
        try:service.recommend(x)
        except ValueError:continue
        raise AssertionError('Invalid request accepted')
    normalized=[(i,r/10) for i,r in s];assert stable(service.recommend(s))==stable(service.recommend(normalized,rating_scale=1))
    again=ServiceV3();assert stable(service.recommend(s))==stable(again.recommend(s));np.testing.assert_array_equal(q,service.model.Q);assert before==sha(OUT/'diagnostics/fit_ledger.json')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    save('diagnostics/runtime.json',{'load_seconds':service.load_seconds,'top5_seconds_median':float(np.median(times[5])),'top10_seconds_median':float(np.median(times[10])),'top5_seconds_p95':float(np.quantile(times[5],.95)),'top10_seconds_p95':float(np.quantile(times[10],.95)),'foldin_seconds_median':float(np.median(foldtime)),'peak_process_rss_bytes':rss if sys.platform=='darwin' else rss*1024,'valid_scenarios':records,'invalid_rejected':len(bad),'integer_float_zero_ten_tested':True,'normalized_raw_scale_parity':True,'reload_parity':True,'Q_unchanged':True,'mf_fits':0,'fit_ledger_unchanged':True,'real_user_satisfaction_study':False})
    print('Runtime PASS:48valid configurations,8invalid rejected;integer/float/raw-normalized/reload parity; MF fits0')
if __name__=='__main__':main()
