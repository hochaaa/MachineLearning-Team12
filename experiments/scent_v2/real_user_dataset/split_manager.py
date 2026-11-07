"""Participant role fixed at registration, before any ratings exist."""
import hashlib


def assign_role(user_id):
 fraction=int.from_bytes(hashlib.sha256(('12:realuser-split:'+user_id).encode()).digest()[:8],'big')/2**64
 return 'development'if fraction<.60 else 'independent'


def support_split(user_id,rows):
 """Future evaluation eligibility/ID-only support order; no values used for selection."""
 if len({r['perfume_id']for r in rows})!=len(rows):raise ValueError('Duplicate user/item')
 if len(rows)<6:return dict(status='insufficient_support'if len(rows)<5 else'no_target',support=[],heldout=[])
 ordered=sorted(rows,key=lambda r:hashlib.sha256(f"12:realuser-support:{user_id}:{r['perfume_id']}".encode()).hexdigest())
 return dict(status='eligible',support=ordered[:5],heldout=ordered[5:])
