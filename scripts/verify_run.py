"""Verify persisted real-data validation invariants without running internal/external test."""
import sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from perfume.data import read_json,write_json
from perfume.splits import assert_disjoint

manifest=read_json('outputs/validation/split_manifest.json')
users={r[0] for r in manifest['validation']}
checks={}
for policy in ('include','exclude'):
    previous=None
    for threshold in (5,4,3):
        train=read_json(f'outputs/validation/train_{policy}_{threshold}.json')
        assert_disjoint(train,manifest['validation'],manifest['test'])
        activity=Counter(u for u,_,_ in train)
        assert all(activity[u]>=3 for u in users)
        pairs={(u,i) for u,i,_ in train}
        if previous is not None: assert previous<=pairs
        previous=pairs
        checks[f'{policy}_{threshold}']='PASS disjoint labels; common users >=3 train; monotone expansion'
checks['validation_users']=len(users)
checks['positive_validation_users']=sum(r>=.7 for _,_,r in manifest['validation'])
checks['positive_labels_outside_common_candidates']=sum(r>=.7 and i not in manifest['candidates'] for _,i,r in manifest['validation'])
checks['validation_labels_outside_common_candidates']=sum(i not in manifest['candidates'] for _,i,_ in manifest['validation'])
checks['external_test']='NOT EXECUTED'
checks['internal_test']='NOT EXECUTED'
write_json('outputs/verification.json',checks)
print(__import__('json').dumps(checks,indent=2))
