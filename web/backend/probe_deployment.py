"""Local cold-process load/inference resource probe with synthetic input only.

No fit, no evaluation labels, no ranking accuracy metrics, no bundle conversion.
Run from project root: python -B -m web.backend.probe_deployment.
"""
import time
PROCESS_START=time.perf_counter()
import hashlib
import json
import platform
import resource
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .adapter import FrozenService,ROOT
from .app import Rating
import numpy as np


def rss_bytes():
    """Process high-water RSS; macOS returns bytes, Linux returns KiB."""
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if platform.system()=='Darwin' else value*1024


def state_hash(service):
    """Hash in-memory MF arrays/content/popularity stats without emitting user values."""
    digest=hashlib.sha256()
    for key,value in sorted(vars(service.mf).items()):
        if isinstance(value,np.ndarray):digest.update(key.encode());digest.update(value.tobytes())
    for value in [service.content.idf,service.content.vectors,dict(service.baseline.counts)]:
        digest.update(json.dumps(value,sort_keys=True).encode())
    return digest.hexdigest()


def main():
    """Measure a single fresh service,20 sequential+16 concurrent synthetic inferences."""
    start=time.perf_counter();s=FrozenService();load=time.perf_counter()-start
    load_rss=rss_bytes();ready=time.perf_counter()-PROCESS_START
    ratings=[Rating(perfume_id=i,rating=r*10) for i,r in json.loads((ROOT/'demos/stage2/synthetic_woody.json').read_text())]
    before=state_hash(s);timings=[];expected=None
    for _ in range(20):
        start=time.perf_counter();result=s.recommend(ratings,'none');timings.append(time.perf_counter()-start)
        if expected is None:expected=result
        assert result==expected
    with ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(lambda _:s.recommend(ratings,'none'),range(16)))
    assert all(r==expected for r in results)
    unchanged=before==state_hash(s);assert unchanged
    paths=set(s.freeze['protected_sha256'])|{'outputs/final/freeze.json'}
    files=[]
    for path in sorted(paths):
        sensitive=path in ('outputs/validation/train_exclude_3.json','outputs/final/model.json','outputs/final/model.npz')
        role='private user history / user mapping / user factors' if sensitive else 'catalog or learned representation; rights review' if path.endswith('content.json') or path.endswith('fra_cleaned.csv') else 'code/config/aggregate; owner review'
        files.append({'path':path,'bytes':(ROOT/path).stat().st_size,'classification':role})
    with np.load(ROOT/'outputs/final/model.npz') as a:shapes={k:list(a[k].shape) for k in a.files}
    metadata=json.loads((ROOT/'outputs/final/model.json').read_text())
    report={'platform':platform.platform(),'python':platform.python_version(),'numpy':np.__version__,
            'load_seconds':load,'process_imports_and_load_seconds':ready,'peak_rss_after_load_bytes':load_rss,
            'peak_rss_after_probe_bytes':rss_bytes(),'sequential_requests':len(timings),
            'first_request_seconds':timings[0],'median_request_seconds':statistics.median(timings),
            'p95_request_seconds':sorted(timings)[18],'maximum_request_seconds':max(timings),
            'concurrent_requests':16,'workers':4,'concurrent_outputs_identical':True,'in_memory_model_state_unchanged':unchanged,
            'required_files':files,'total_required_bytes':sum(r['bytes'] for r in files),'array_shapes':shapes,
            'model_user_mapping_count':len(metadata['users']),'model_item_mapping_count':len(metadata['items']),
            'limits':'One local Mac fresh-process probe; OS cache not cleared. Not cloud startup, end-to-end latency, sustained load, or a memory guarantee.'}
    out=ROOT/'web/evidence/search-stage32/deployment-probe.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='required_files'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
