"""Isolated supplementary experiment utilities; never write into frozen paths."""
import csv,hashlib,json,sys,time,html
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from perfume.data import normalize, identity, fragrantica
OUT=ROOT/'outputs/proposal_completion'

def load(path):
    """Read JSON path relative to ROOT; callers restrict which data they request."""
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))

def save(name,value):
    """Save aggregate or public product metadata only under supplementary OUT."""
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def table(name,rows):
    """Write common-key rows; no individual user histories are allowed as outputs."""
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        if rows:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def read_csv(path,encoding='utf-8-sig',delimiter=','):
    """Read CSV using explicit encoding and delimiter."""
    with (ROOT/path).open(encoding=encoding,newline='') as f:return list(csv.DictReader(f,delimiter=delimiter))

def fields(value):
    """Comma-separated phrases, normalized separately; no semantic synonym merging."""
    return {normalize(v) for v in str(value or '').split(',') if normalize(v) not in ('','na','nan','unknown','none')}

def jaccard(a,b):
    """Intersection/union; both empty is undefined (None), never perfect agreement."""
    return len(a&b)/len(a|b) if a|b else None

def versions(name,concentration=''):
    """Extract explicit versions; absent tag is unknown, not proof of equivalence."""
    words=set(normalize(name+' '+concentration).split())
    return words&{'edt','edp','edc','parfum','extrait','elixir','intense','extreme','sport','limited'}

def conflict(a,b):
    """Known mutually different concentrations or asymmetric flankers reject a link."""
    conc={'edt','edp','edc','parfum','extrait'}
    x,y=a&conc,b&conc
    flank={'elixir','intense','extreme','sport','limited'}
    return bool((x and y and x!=y) or (a&flank)!=(b&flank))

def sha(path):
    """Stream SHA256 without exposing input contents."""
    h=hashlib.sha256()
    with (ROOT/path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def guard():
    """Raise before work if original frozen19 or known manifest differs."""
    expected='3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130'
    if sha('outputs/final/freeze.json')!=expected:raise RuntimeError('Freeze manifest mismatch: STOP')
    f=load('outputs/final/freeze.json')
    if any(sha(p)!=h for p,h in f['protected_sha256'].items()):raise RuntimeError('Protected file mismatch: STOP')

def bar(name,title,labels,values,subtitle=''):
    """Dependency-free static SVG chart; values are measured aggregates, not user rows."""
    width=940; height=150+len(labels)*32; maxv=max(values,default=1) or 1
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>',f'<text x="24" y="30" font-family="sans-serif" font-size="20">{html.escape(title)}</text>',f'<text x="24" y="55" font-family="sans-serif" font-size="12">{html.escape(subtitle)}</text>']
    for n,(label,v) in enumerate(zip(labels,values)):
        y=82+n*32
        parts.extend([f'<text x="24" y="{y+16}" font-family="sans-serif" font-size="12">{html.escape(str(label))}</text>',f'<rect x="270" y="{y}" width="{560*v/maxv}" height="22" fill="#326d83"/>',f'<text x="{280+560*v/maxv}" y="{y+16}" font-family="sans-serif" font-size="12">{v:.5g}</text>'])
    parts.append('</svg>');(OUT/'figures'/name).write_text(''.join(parts))

def main_run(fn,name):
    """Guard, time one independent supplementary command, then guard again."""
    guard(); start=time.perf_counter(); fn(); guard()
    inputs={
        'parfumo_crosscheck':['Term-project-datasets/fra_cleaned.csv','Term-project-datasets/parfumo_data_clean.csv'],
        'knn_baselines':['outputs/validation/train_exclude_3.json','outputs/improvement/validation.json','outputs/improvement/candidates.json'],
        'kmeans_analysis':['Term-project-datasets/fra_cleaned.csv'],
        'fuzzy_match_audit':['Term-project-datasets/fra_cleaned.csv','outputs/audit/atrafshan_matching.csv','outputs/audit/external_matching.csv',*[f'Term-project-datasets/{n}.json' for n in ['perfumes','brand','notes','category','season']]],
        'supplementary_metrics':['outputs/improvement/validation_rating_errors.json','outputs/final/internal_rating_errors.json','outputs/validation/knowledge_rules.csv','Term-project-datasets/fra_cleaned.csv','outputs/improvement/candidates.json']}[name]
    save(name+'_run.json',{'inputs_sha256':{p:sha(p) for p in inputs},'source_sha256':{f'experiments/proposal_completion/{n}.py':sha(f'experiments/proposal_completion/{n}.py') for n in ['common',name]},'command':f'PYTHONDONTWRITEBYTECODE=1 web/backend/.venv/bin/python -B experiments/proposal_completion/{name}.py','seconds':time.perf_counter()-start,'seed':12,'python':sys.version,'numpy':np.__version__})
