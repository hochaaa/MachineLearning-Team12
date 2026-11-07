"""Two diagnosis-motivated policies; original MF/Hybrid untouched."""
import json
import numpy as np
from perfume.data import normalize
from perfume.models import hybrid
from experiments.scent_v2.recommend import rank
from experiments.scent_v2.similarity_reranking.core import rerank
from .diagnostic import CONFIG,component_arrays


def structural_phrases(row):
    """Existing Top/Middle/Base and5 accords only. Keep note phrases/stages intact."""
    missing={'','na','nan','unknown','none'};result={}
    for field in ['Top','Middle','Base']:
        result[field]={normalize(p) for p in str(row.get(field,'')).split(',')}-missing
    result['accords']={normalize(row.get(f'mainaccord{k}','')) for k in range(1,6)}-missing
    return result


class Structured:
    """Train-only per-stage multi-hot, equal-weight channel cosine matrix.

    No inferred family, country/gender, aggregate ratings, or unlisted notes.
    Missing channel gives0; no per-pair weight renormalization that inflates it.
    """
    def __init__(self,rows,train_items,candidates):
        raw={r['url']:structural_phrases(r) for r in rows};self.ids=sorted(candidates);self.items={i:n for n,i in enumerate(self.ids)};self.vocab={};self.coverage={};matrix=np.zeros((len(self.ids),len(self.ids)));present=np.zeros(len(self.ids),bool)
        for field,weight in zip(CONFIG['structured']['channels'],CONFIG['structured']['channel_weights']):
            vocab=sorted(set().union(*(raw[i][field] for i in train_items)));self.vocab[field]=vocab;X=np.asarray([[float(t in raw[i][field]) for t in vocab] for i in self.ids]);norm=np.sqrt(np.einsum('ij,ij->i',X,X));valid=norm>0;X[valid]/=norm[valid,None];present|=valid;matrix+=weight*np.einsum('it,jt->ij',X,X);self.coverage[field]=int(valid.sum())
        matrix[~present,:]=np.nan;matrix[:,~present]=np.nan;matrix.flags.writeable=False;self.matrix=matrix;self.coverage['any_channel']=int(present.sum())

    def max_signal(self,support,pool):
        known=[self.items[i] for i,r in support if r>=.7 and i in self.items and np.isfinite(self.matrix[self.items[i],self.items[i]])];columns=[self.items[i] for i in pool]
        if not known:return np.full(len(pool),np.nan)
        result=np.max(np.nan_to_num(self.matrix[known][:,columns],nan=0.),axis=0);valid=np.asarray([np.isfinite(self.matrix[i,i]) for i in columns]);result[~valid]=np.nan;return result


def cdf(values,reference,original):
    """Mid empirical CDF fitted ONLY on Train pseudoSupport component scores.

    No per-evaluation-user candidate ranking fit. Raw MF avoids clipped ties.
    Empty/constant reference falls back to the original bounded component.
    """
    result=original.copy();reference=np.sort(np.asarray(reference,float));reference=reference[np.isfinite(reference)]
    if not len(reference) or np.ptp(reference)<=1e-12:return result
    valid=np.isfinite(values);result[valid]=(np.searchsorted(reference,values[valid],side='left')+np.searchsorted(reference,values[valid],side='right'))/(2*len(reference));return result


def score(policy,support,x,structured,reference,calibration_gate):
    """Support-only inputs; exactly3 predefined policies, no tuning arguments."""
    pool=x['pool']
    if policy=='structured':
        cache=dict(pool=pool,hybrid=x['hybrid'],signals={'max':structured.max_signal(support,pool)},baseline_order=rank(pool,x['hybrid']))
        return rerank(dict(signal='max',mode='top50',**{'lambda':.2}),cache)
    if policy=='baseline' or policy=='train_cdf' and not calibration_gate:values=x['hybrid']
    elif policy=='train_cdf':values=hybrid(cdf(x['content'],reference['content_reference'],x['content']),cdf(x['raw'],reference['raw_reference'],x['mf']),.25,x['popularity'])
    else:raise ValueError('Unregistered policy')
    top=rank(pool,values)[:5];lookup=dict(zip(pool,map(float,values)));return top,[lookup[i] for i in top]


def predict(policy,support,candidates,c,m,b,structured,reference,calibration_gate):
    x=component_arrays(support,candidates,c,m,b);top,scores=score(policy,support,x,structured,reference,calibration_gate)
    if len(top)!=len(set(top)) or set(top)&{i for i,r in support}:raise ValueError('Invalid Top5')
    return top,scores
