"""Version-identical developer split without decoding reserved V24 final ratings."""
import json,math,hashlib
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from perfume.models import Content,MatrixFactorization,Baseline,hybrid
from experiments.scent_v2.accuracy_optimization.core import components,validate_train
from experiments.scent_v2.recommend import rank
from experiments.scent_v2.expanded_content.evaluation import user_metrics,summarize
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'outputs/scent_v2/mf_accuracy_optimization'
CONFIG=json.loads((Path(__file__).parent/'config.json').read_text())


def digest(text):return hashlib.sha256(text.encode()).hexdigest()


def read_identities(path):
    """Parse only ID/item strings. Rating substrings stay opaque until user exclusion.

    Source schema is JSON array of [string,string,number] triples. Reading bytes is
    necessary to skip records, but final-user numeric labels are NEVER decoded,
    validated, summarized, returned to a model or compared with old final results.
    """
    text=Path(path).read_text();decoder=json.JSONDecoder();n=len(text);p=0;rows=[]
    def ws(i):
        while i<n and text[i].isspace():i+=1
        return i
    p=ws(p)
    if text[p]!='[':raise ValueError('Train array required')
    p=ws(p+1)
    while p<n and text[p]!=']':
        if text[p]!='[':raise ValueError('Triple required')
        user,p=decoder.raw_decode(text,ws(p+1));p=ws(p)
        if text[p]!=',':raise ValueError('Comma required')
        item,p=decoder.raw_decode(text,ws(p+1));p=ws(p)
        if text[p]!=',' or not isinstance(user,str) or not isinstance(item,str):raise ValueError('Identity schema')
        start=ws(p+1);end=text.find(']',start)
        if end<0:raise ValueError('Unclosed row')
        token=text[start:end].strip()
        rows.append((user,item,token));p=ws(end+1)
        if text[p]==',':p=ws(p+1)
        elif text[p]!=']':raise ValueError('Array delimiter')
    if p>=n or text[ws(p+1):].strip():raise ValueError('Trailing JSON')
    return rows


def developer_data(path,candidates):
    """Reproduce V24 Train/dev identity boundaries; do not construct a final cohort."""
    opaque=read_identities(path);pool=set(candidates)
    if len({(u,i) for u,i,t in opaque})!=len(opaque):raise ValueError('Duplicate pair')
    counts=Counter(u for u,i,t in opaque);inpool=Counter(u for u,i,t in opaque if i in pool)
    eligible=sorted((u for u,n in counts.items() if n>=6 and inpool[u]>=5),key=lambda u:digest('12:v224:role:'+u))
    if len(eligible)<30:raise ValueError('Too few existing eligible users')
    n=math.ceil(len(eligible)/3);reserved=set(eligible[:n]);dev_users=eligible[n:];histories=defaultdict(list);train=[];decoded=0
    for u,i,token in opaque:
        if u in reserved:continue # Never json.loads/float/check any reserved label.
        r=json.loads(token)
        if isinstance(r,bool) or not isinstance(r,(int,float)) or not math.isfinite(r) or not 0<=r<=1:raise ValueError('Invalid retained rating')
        decoded+=1
        if u in set(dev_users):histories[u].append((i,float(r)))
        else:train.append((u,i,float(r)))
    dev=[]
    for u in dev_users:
        items=sorted((i for i,r in histories[u] if i in pool),key=lambda i:digest('12:v224:support:'+u+':'+i));seen=set(items[:5])
        support=sorted((i,r) for i,r in histories[u] if i in seen);answers=sorted((i,r) for i,r in histories[u] if i not in seen)
        if len(support)!=5 or not answers or {i for i,r in support}&{i for i,r in answers}:raise ValueError('Bad split')
        dev.append(dict(user=u,support=support,answers=answers))
    validate_train(train,reserved|set(dev_users))
    return train,dev,reserved,dict(source_rows=len(opaque),retained_rating_tokens_decoded=decoded,reserved_rating_tokens_decoded=0,reserved_rows_skipped=sum(u in reserved for u,i,t in opaque),
        train_users=len({u for u,i,r in train}),train_ratings=len(train),development_users=len(dev),support_ratings=5*len(dev),heldout_ratings=sum(len(r['answers']) for r in dev),
        reserved_users=len(reserved),user_overlap=0,candidates=len(candidates),
        developer_split_sha256=digest(json.dumps(dev,sort_keys=True)),original_train_sha256=digest(json.dumps(train)))


def cache_scores(cohort,candidates,content,mf,pop):
    """One C/MF computation per user per MF fit, shared unchanged by all6 alphas."""
    cache=[]
    for row in cohort:
        x=components(row['support'],candidates,content,mf,pop);x['fallback']=pop.score(x['pool'])
        for key in ('content','mf','raw','fallback'):x[key].flags.writeable=False
        cache.append(x)
    return cache


def measure(alpha,cache,cohort,candidates):
    """Raw weighted blend only; no scaling/percentile/rating-profile transformation."""
    records=[]
    for x,row in zip(cache,cohort):
        values=hybrid(x['content'],x['mf'],alpha,x['fallback']);top=rank(x['pool'],values)[:5]
        if len(top)!=len(set(top)) or {i for i,r in row['support']}&set(top):raise ValueError('Invalid top5')
        records.append(dict(top=top,answers=row['answers'],accuracy=user_metrics(top,row['answers'])))
    return summarize(records,candidates),records


def tie_key(config_index,alpha):
    c=CONFIG['mf_grid'][config_index]
    return (config_index!=0,abs(alpha-.25),c['factors'],abs(math.log(c['regularization']/.01)),config_index)
