"""Read-only CSV validation and exact, version-preserving catalog matching."""
import csv, hashlib, hmac, math, re, unicodedata
from collections import Counter, defaultdict
from statistics import mean, median, pstdev
from pathlib import Path

FIELDS={'participant_id','product_id','brand','product_name','score','source_type','created_at','updated_at'}
MF_POLICY=dict(factors=4,epochs=160,learning_rate=.01,regularization=.01,seed=12)
POLICY=dict(mf=MF_POLICY,foldin_ridge=.01,alpha=.25,support=5,k=5,relevance=.7,
            candidates=479,rating_scale='explicit source 0..10; raw score preserved; model normalization score/10',
            content='Existing Content structure/features shared by A/B; no fit executed without matched additions',
            tie='score descending then original item ID ascending',filters=False,
            selection='No tuning, no performance-based model selection',
            evaluation='No evaluation until a nonempty exact-match training/evaluation plan exists')

def norm(value):
    """NFC/casefold, preserve accents and all words/numbers/variant tokens."""
    text=unicodedata.normalize('NFC',value).casefold()
    for a,b in [('eau de parfum','edp'),('eau de toilette','edt'),('eau de cologne','edc')]:text=text.replace(a,b)
    return ' '.join(re.findall(r'[^\W_]+',text))

def pseudonym(user, secret):
    """Source-specific local HMAC; original IDs are never written to output."""
    if len(secret)<32:raise ValueError('Private 32-byte key required')
    return 'real_v216_'+hmac.new(secret,('v216\0'+user).encode(),hashlib.sha256).hexdigest()

def stats(values):
    """Descriptive population statistics, not a confidence interval."""
    if not values:return {'status':'NO_ROWS'}
    return dict(count=len(values),minimum=min(values),maximum=max(values),mean=mean(values),median=median(values),
                population_std=pstdev(values),maximum_score10_fraction=sum(v==10 for v in values)/len(values),
                low_below5_fraction=sum(v<5 for v in values)/len(values),histogram=dict(Counter(values)))

def read_csv(path):
    """Return validated actual rows and aggregate audit. Fail on bad rows, never impute."""
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);columns=reader.fieldnames;rows=list(reader)
    if not columns or set(columns)!=FIELDS:raise ValueError('Unexpected schema')
    missing=sum(not isinstance(r.get(k),str) or not r[k].strip() for r in rows for k in FIELDS)
    duplicates=len(rows)-len({(r['participant_id'],r['product_id']) for r in rows})
    if missing or duplicates:raise ValueError('Missing fields or duplicate user/product records')
    for r in rows:
        value=float(r['score'])
        if not math.isfinite(value) or not 0<=value<=10 or abs(value*2-round(value*2))>1e-10:raise ValueError('Invalid score')
        if r['source_type'] not in ('catalog','custom'):raise ValueError('Unknown source type')
        r['numeric_score']=value
    by_user=defaultdict(list)
    for r in rows:by_user[r['participant_id']].append(r)
    product_identities=defaultdict(set)
    for r in rows:product_identities[r['product_id']].add((r['brand'],r['product_name'],r['source_type']))
    if any(len(v)!=1 for v in product_identities.values()):raise ValueError('Product ID metadata collision')
    return rows,dict(columns=columns,rows=len(rows),users=len(by_user),unique_product_ids=len(product_identities),
        unique_brand_name_keys=len({(norm(r['brand']),norm(r['product_name'])) for r in rows}),
        user_activity_histogram=dict(Counter(len(h) for h in by_user.values())),
        sources=dict(Counter(r['source_type'] for r in rows)),missing_cells=missing,duplicate_user_product_records=duplicates,
        half_point_compliance=True,score=stats([r['numeric_score'] for r in rows]),
        original_user_IDs_in_public_output=False)

def match_one(row,catalog,candidates):
    """Only trusted same URL identity or unique exact normalized brand+full-version name.

    Unknown source IDs cannot be reverse-guessed from hashes. Missing EDP/EDT
    tokens are not stripped. Registered search aliases are not product identity.
    Custom unmatched rows always remain reviewable, not fuzzy-accepted.
    """
    if len(candidates)!=479 or len(set(candidates))!=479:raise ValueError('Fixed479 required')
    key=norm(row['brand']),norm(row['product_name'])
    if row['product_id'] in candidates:
        c=catalog[row['product_id']]
        if (norm(c['brand']),norm(c['name']))!=key:return None,'REVIEW_ID_METADATA_CONFLICT'
        return row['product_id'],'EXACT_CATALOG_URL'
    hits=[i for i in candidates if (norm(catalog[i]['brand']),norm(catalog[i]['name']))==key]
    if len(hits)==1:return hits[0],'EXACT_BRAND_FULL_NAME'
    if len(hits)>1:return None,'REVIEW_AMBIGUOUS_IDENTITY'
    if row['source_type']=='custom':return None,'REVIEW_CUSTOM_NO_EXACT_IDENTITY'
    if norm(row['brand']) not in {norm(catalog[i]['brand']) for i in candidates}:
        return None,'OUTSIDE_FIXED_CATALOG_EXACT_BRAND_INDEX'
    return None,'REVIEW_VARIANT_OR_PRODUCT_NOT_FOUND'

def split_eligibility(rows, matches):
    """Only matched unique histories >=6 can supply five support + held-out.

    Count eligibility is label-blind and does not establish statistical power.
    No user labels/scores are used to choose users. Return IDs only internally.
    """
    counts=Counter(r['participant_id'] for r,(i,status) in zip(rows,matches) if i is not None)
    eligible={u for u,n in counts.items() if n>=6}
    return eligible,dict(matched_user_activity_histogram=dict(Counter(counts.values())),
        matched_users=len(counts),support5_plus_heldout_users=len(eligible),
        support5_only_users=sum(n==5 for n in counts.values()),
        raw_activity_eligible_users=len({u for u,n in Counter(r['participant_id'] for r in rows).items() if n>=6}))

def require_training_additions(matched_rows):
    """No MF fit, A/B evaluation or model weights can be produced with zero additions."""
    if not matched_rows:raise ValueError('BLOCKED_NO_EXACT_479_MATCHES')
    if any(r.get('role')=='independent' or r.get('synthetic',False) for r in matched_rows):raise ValueError('Forbidden training source')
    return True

def support_answers(history,seed=12):
    """Five support by item hash only; disjoint remainder, never sort by ratings."""
    if len(history)<6 or len({i for i,r in history})!=len(history):raise ValueError('Insufficient unique matched history')
    order=sorted(history,key=lambda p:hashlib.sha256(f'{seed}:v216:support:{p[0]}'.encode()).hexdigest())
    return order[:5],order[5:]

def validate_training(train,evaluation_users,candidates):
    """Reject evaluation users and non-candidates, without fitting any model."""
    if {u for u,i,r in train}&set(evaluation_users):raise ValueError('Evaluation user reached training')
    if any(i not in candidates for u,i,r in train):raise ValueError('Outside479 training item')
    return True
