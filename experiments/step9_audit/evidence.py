"""Aggregate-only evidence comparison, environment and source publication inventory.

No evaluation functions, model fit, private answer or per-user result parsing.
Candidate source scanning is heuristic and never emits matched secret values.
"""
import csv,json,sys,subprocess,statistics,re,platform,importlib.metadata,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/step9_audit'
def load(p):return json.loads((ROOT/p).read_text())
def rows(p):
    with (ROOT/p).open(newline='') as f:return list(csv.DictReader(f))
def save(n,v):
    with (OUT/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def main():
    v1=rows('outputs/improvement/frozen_results.csv');assert len(v1)==12
    expected={'validation':[.032790,.028903,.023056,.043185],'internal_test':[.030404,.019920,.041180,.038533],'external_test':[.023583,.003364,.050456,.026365]}
    for split,values in expected.items():
        for method,x in zip(['popularity','content','mf','hybrid'],values):
            row=next(r for r in v1 if r['split']==split and r['method']==method);assert abs(float(row['ndcg'])-x)<.00000051
    v2=rows('outputs/development_v2/metrics/newuser_cv.csv');v2summary={name:statistics.mean(float(r['ndcg']) for r in v2 if r['name']==({'v2_hybrid':'neutral__bias_f8_r0.01__rrf_a0.25'}.get(name,name)) and float(r['ridge'])==({'v1_hybrid':.01,'v2_hybrid':1.}[name])) for name in ['v1_hybrid','v2_hybrid']}
    assert abs(v2summary['v1_hybrid']-.047663)<.00000051 and abs(v2summary['v2_hybrid']-.032505)<.00000051
    v3=load('outputs/development_v3/metrics/final_summary.json');outer=rows('outputs/development_v3/metrics/outer.csv')
    for s in v3['primary_outer']:
        assert abs(s['ndcg']-statistics.mean(float(r['ndcg']) for r in outer if r['policy']==s['model']))<1e-14
    lock=load('outputs/development_v3/configs/selections_locked.json');policy=lock['full_train_policy']
    expected_policy={'id':'F','factors':2,'latent_l2':.01,'bias_l2':.1,'learning_rate':.01,'epochs':40,'fold_latent':.1,'fold_bias':1.,'fusion':'minmax','alpha':.25,'content':'neutral'}
    assert policy==expected_policy and v3['final_policy']==expected_policy
    run=load('outputs/development_v3/configs/run_complete.json');ledger=load('outputs/development_v3/diagnostics/fit_ledger.json');assert run['actual_mf_fits']==ledger['total']==58
    # Compare only aggregate metadata, never users mapping or raw labels.
    save('metric_consistency.json',{'status':'PASS','v1_historical_aggregate':v1,'step5_newuser_ndcg':v2summary,'step8_outer':v3['primary_outer'],'v3_policy':policy,'outer_selection':v3['outer_workflow_policies'],'fit_counts':run['phase_counts'],'total_fits':58,'ci':load('outputs/development_v3/diagnostics/paired_bootstrap.json'),'test_labels_or_peruser_results_read':False,'new_metrics_evaluated':False,'note':'Only arithmetic means of existing aggregate rows and agreement checks; no new evaluation or bootstrap.'})
    node=json.loads((ROOT/'web/demo/runtime.local.json').read_text())['node']
    packages={name:load('web/frontend/node_modules/'+name+'/package.json')['version'] for name in ['react','react-dom','vite','typescript','tailwindcss']}
    env={'python':platform.python_version(),'platform':platform.system(),'machine':platform.machine(),'python_prefix_is_venv':sys.prefix!=sys.base_prefix,'base_prefix_exists':Path(sys.base_prefix).exists(),'packages':{p:importlib.metadata.version(p) for p in ['numpy','fastapi','pydantic','uvicorn','httpx']},'node':subprocess.check_output([node,'--version'],text=True).strip(),'js_packages_installed':packages}
    save('environment.json',env)
    tracked=[p.decode() for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0') if p]
    new=[p for folder in ['experiments/development_v2','experiments/development_v3','experiments/step9_audit'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    source=[ROOT/p for p in tracked if (ROOT/p).is_file()]+new
    secret_patterns=[re.compile(p) for p in [r'\bgh[pousr]_[A-Za-z0-9]{20,}',r'\bgithub_pat_[A-Za-z0-9_]{30,}',r'\bsk-[A-Za-z0-9_-]{30,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'\bAKIA[A-Z0-9]{16}\b']]
    findings=[];paths=[]
    for p in source:
        try:s=p.read_text()
        except (UnicodeError,OSError):continue
        if any(pattern.search(s) for pattern in secret_patterns):findings.append({'path':str(p.relative_to(ROOT)),'risk':'HIGH','kind':'credential pattern; actual value omitted'})
        if re.search(r'/Users/[^\s/]+/',s):paths.append(str(p.relative_to(ROOT)))
    assert not findings,'Secret-like high-risk value found; stop and review paths only'
    envfiles=[str(p.relative_to(ROOT)) for folder in ['web','experiments'] for p in (ROOT/folder).rglob('.env*') if not set(p.parts)&{'node_modules','.venv'}]
    manifests={};excluded={'node_modules','.venv','.git','__pycache__','dist'}
    for folder in ROOT.iterdir():
        if folder.is_dir() and folder.name not in excluded:
            files=[p for p in folder.rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts)&excluded]
            manifests[folder.name]={'files':len(files),'bytes':sum(p.stat().st_size for p in files)}
    save('git_source_inventory.json',{'tracked_count':len(tracked),'tracked_files':tracked,'untracked_source_review_candidates':[str(p.relative_to(ROOT)) for p in new],'source_files_scanned':len(source),'credential_pattern_findings':findings,'personal_absolute_path_files':paths,'environment_file_paths':envfiles,'inventory_without_dependencies':manifests,'ignore_reports_rule':subprocess.run(['git','check-ignore','-v','reports/SCENT_MATCH_FINAL_PROJECT_REPORT.md'],cwd=ROOT,text=True,capture_output=True).stdout.strip(),'remote_configuration':subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip(),'remote_live_access_verified':False,'scan_limit':'Heuristic source scan; datasets/private model mappings not inspected for publication; manual license/PII review still required.'})
    print('PASS:12 V1 aggregate rows; STEP5/STEP8 CSV consistency; F config;58fit; source scan',len(source),'files, secret-pattern0; absolute-path files',len(paths));print(json.dumps(env,ensure_ascii=False))
if __name__=='__main__':main()
