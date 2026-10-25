"""Train-only allowlist, original-file protection, independent V3 outputs."""
import sys,json,hashlib,subprocess,os
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/development_v3'
sys.path.insert(1,str(ROOT/'src'));sys.path.insert(2,str(ROOT/'experiments/development_v2'))
from perfume.data import fragrantica,normalize
READS=Counter()

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def save(name,value):
    p=(OUT/name).resolve()
    if OUT not in p.parents:raise ValueError('V3 output boundary')
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2))

def guard():
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT).decode().strip()=='development-v2'
    p=ROOT/'outputs/final/freeze.json';assert sha(p)=='3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130'
    f=json.loads(p.read_text());assert all(sha(ROOT/p)==h for p,h in f['protected_sha256'].items())

def deny(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
    p=Path(os.fsdecode(args[0])).resolve()
    if p==ROOT/'outputs/improvement/validation.json':raise PermissionError('No legacy validation')
    if ROOT/'outputs/final' in p.parents and p.name not in {'freeze.json','model.json','model.npz','content.json'}:raise PermissionError('No old Test/results')
    if ROOT/'outputs/validation' in p.parents and p.name!='train_exclude_3.json':raise PermissionError('No old split/answer files')
    if p.parent==ROOT/'Term-project-datasets' and p.name!='fra_cleaned.csv':raise PermissionError('No raw interaction/external files')
    if p.parent==ROOT/'outputs/improvement' and p.name not in {'candidates.json','selection.json'}:raise PermissionError('No old experiment results')
    if ROOT/'outputs' in p.parents and OUT not in p.parents:READS[str(p.relative_to(ROOT))]+=1

def load_train():
    rows=[tuple(r) for r in json.loads((ROOT/'outputs/validation/train_exclude_3.json').read_text())];pool=sorted(json.loads((ROOT/'outputs/improvement/candidates.json').read_text()));catalog,raw=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv');allowed=set(pool)|{i for _,i,_ in rows}
    assert len(rows)==1805 and len(pool)==479 and len(set(pool))==479
    return rows,pool,{i:catalog[i] for i in allowed},{r['url']:r for r in raw if r['url'] in allowed}

def histories(rows):
    h=defaultdict(list)
    for u,i,r in sorted(rows):h[u].append((i,r))
    return h

def digest(rows):return hashlib.sha256(json.dumps(list(rows),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def snapshot():
    tracked=[s.decode() for s in subprocess.check_output(['git','ls-files','-z']).split(b'\0') if s];f=json.loads((ROOT/'outputs/final/freeze.json').read_text());paths=set(tracked)|set(f['protected_sha256'])|{'outputs/final/freeze.json'}
    for folder in [ROOT/'experiments/development_v2',ROOT/'outputs/development_v2']:
        paths.update(str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'reports').glob('*.md'))
    stats={}
    for folder in [ROOT/'Term-project-datasets',ROOT/'outputs/final',ROOT/'outputs/validation',ROOT/'web']:
        for p in folder.rglob('*'):
            if p.is_file() and not set(p.parts)&{'.venv','node_modules','__pycache__','dist','.state','logs'}:
                s=p.stat();stats[str(p.relative_to(ROOT))]={'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
    return {'sha256':{p:sha(ROOT/p) for p in sorted(paths)},'stat_only':stats}
