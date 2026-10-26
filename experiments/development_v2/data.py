"""Strict allowlisted inputs; internal/external test answer/result files never opened."""
import sys,json,hashlib,subprocess,os
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from perfume.data import fragrantica,normalize
OUT=ROOT/'outputs/development_v2'
INPUTS={'train':'outputs/validation/train_exclude_3.json','candidates':'outputs/improvement/candidates.json','catalog':'Term-project-datasets/fra_cleaned.csv','validation':'outputs/improvement/validation.json'}
MANIFEST='3bb906bd903085400c81c7172737ec6519660444a8ff87ea6eeb35c8f2049130'

def sha(path):
    """Hash a permitted/protected file, without interpreting record values."""
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def write(name,value):
    """Write only under ignored V2 outputs; no absolute destination accepted."""
    path=(OUT/name).resolve()
    if OUT not in path.parents:raise ValueError('Output escapes V2')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2))

def read_input(kind):
    """Allow train/pool/metadata; legacy validation unlocked only after CV selection receipt."""
    if kind not in INPUTS:raise ValueError('Not an allowed V2 input')
    if kind=='validation' and not (OUT/'experiments/selection_locked.json').exists():raise RuntimeError('Finish/fix CV selection before validation access')
    path=ROOT/INPUTS[kind]
    if kind=='catalog':return fragrantica(path)
    return json.loads(path.read_text())

def guard():
    """Require development-v2 and original protected19+manifest; never invoke V1 pipelines."""
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT).decode().strip()
    if branch!='development-v2':raise RuntimeError('STOP: development-v2 required')
    p=ROOT/'outputs/final/freeze.json'
    if sha(p)!=MANIFEST:raise RuntimeError('V1 manifest changed')
    f=json.loads(p.read_text())
    if any(sha(ROOT/p)!=h for p,h in f['protected_sha256'].items()):raise RuntimeError('V1 protected file changed')

def bundle():
    """Load unchanged train and content-only metadata, restricting transformed catalog size."""
    train=[tuple(r) for r in read_input('train')];pool=sorted(read_input('candidates'));catalog,raw=read_input('catalog')
    allowed=set(pool)|{i for _,i,_ in train};raw={r['url']:r for r in raw if r['url'] in allowed}
    return train,pool,{i:catalog[i] for i in allowed},raw

def histories(rows):
    """Group observed train edges only; deterministic item order."""
    out=defaultdict(list)
    for u,i,r in sorted(rows):out[u].append((i,r))
    return out

def hashed(seed,*parts):return hashlib.sha256((':'.join(map(str,(seed,*parts)))).encode()).hexdigest()

def known_folds(train,n=3,seed=12):
    """Per eligible >=4 train-user hold one different item per fold, retain >=3 support."""
    h=histories(train);eligible={u for u,v in h.items() if len(v)>=4}
    for fold in range(n):
        held={(u,sorted(h[u],key=lambda r:hashed(seed,u,r[0]))[fold][0]) for u in eligible}
        fit=[r for r in train if (r[0],r[1]) not in held];answer=[r for r in train if (r[0],r[1]) in held]
        assert not {(u,i) for u,i,_ in fit}&held
        yield fold,fit,answer

def inner_stop(train,seed=12):
    """Nested training-only stop split; no outer CV labels enter early stopping."""
    h=histories(train);held={(u,sorted(v,key=lambda r:hashed(seed,'stop',u,r[0]))[0][0]) for u,v in h.items() if len(v)>=4}
    return [r for r in train if (r[0],r[1]) not in held],[r for r in train if (r[0],r[1]) in held]

def newuser_folds(train,pool,n=3,seed=12):
    """User-group CV: remove entire held users, restrict to learned479-item intersection."""
    h=histories(train);eligible=sorted(u for u,v in h.items() if len(v)>=4)
    for fold in range(n):
        # Hash-sort round robin guarantees nonempty deterministic groups without rating access.
        held=set(sorted(eligible,key=lambda u:hashed(seed,'user',u))[fold::n])
        fit=[r for r in train if r[0] not in held];available=set(pool)&{i for _,i,_ in fit}
        supports={};answers=[];excluded=Counter()
        for u in sorted(held):
            known=sorted([(i,r) for i,r in h[u] if i in available],key=lambda r:hashed(seed,'support',u,r[0]))
            if len(known)<4:excluded['fewer_than4_candidate_factor_interactions']+=1;continue
            supports[u]=known[:3];answers.extend((u,i,r) for i,r in known[3:])
        assert not held&{u for u,_,_ in fit}
        assert not {(u,i) for u,v in supports.items() for i,_ in v}&{(u,i) for u,i,_ in answers}
        yield fold,fit,sorted(available),supports,answers,dict(excluded),len(held)
