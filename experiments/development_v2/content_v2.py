"""Independent channel TF-IDF and signed preference profiles; no V1 mutations."""
import math
import numpy as np
from data import normalize
from perfume.models import Content
class ContentV2:
    """Separate accord/note or accord/top/middle/base channels, each unit normalized."""
    def __init__(self,config):self.config=dict(config)
    def fit(self,catalog,raw,train_items):
        self.catalog=catalog;self.ids=sorted(catalog);self.index={i:n for n,i in enumerate(self.ids)}
        if self.config['kind']=='v1':self.legacy=Content().fit(catalog,train_items);return self
        self.matrices={};self.idfs={}
        levels=['accord','note'] if self.config['kind']=='split' else ['accord','Top','Middle','Base']
        for level in levels:
            docs={}
            for i in self.ids:
                if level in ('accord','note'):docs[i]={t for t in catalog[i]['tokens'] if t.startswith(level+':')}
                else:docs[i]={normalize(t) for t in raw[i].get(level,'').split(',') if normalize(t) not in ('','na','unknown','nan')}
            train=sorted(set(train_items));vocab=sorted(set().union(*(docs[i] for i in train)));pos={t:n for n,t in enumerate(vocab)}
            idf=np.array([math.log((1+len(train))/(1+sum(t in docs[i] for i in train)))+1 for t in vocab]);self.idfs[level]=dict(zip(vocab,idf))
            matrix=np.zeros((len(self.ids),len(vocab)))
            for i in self.ids:
                for t in docs[i]:
                    if t in pos:matrix[self.index[i],pos[t]]=idf[pos[t]]
            norm=np.linalg.norm(matrix,axis=1);matrix/=np.where(norm>0,norm,1)[:,None];self.matrices[level]=matrix
        return self
    def score(self,support,candidates):
        if self.config['kind']=='v1':return self.legacy.score(support,candidates)
        known=[(i,r) for i,r in sorted(support) if i in self.index]
        if not known:return np.full(len(candidates),np.nan)
        ratings=np.array([r for _,r in known]);mode=self.config['mode']
        weights=ratings if mode=='rating' else ratings-(.5 if mode=='neutral' else ratings.mean())
        a=self.config.get('accord_weight',.5)
        channel_weights={'accord':a,'note':1-a}
        if self.config['kind']=='position':
            pw=np.array(self.config['position_weights'],dtype=float);pw/=pw.sum()
            channel_weights={'accord':a,**dict(zip(['Top','Middle','Base'],(1-a)*pw))}
        num=np.zeros(len(candidates));den=np.zeros(len(candidates))
        rows=[self.index[i] for i,_ in known];indices=[self.index.get(i,-1) for i in candidates]
        for level,matrix in self.matrices.items():
            profile=weights@matrix[rows];norm=np.linalg.norm(profile)
            if norm<1e-12:continue
            valid=np.array([n>=0 and np.linalg.norm(matrix[n])>0 for n in indices]);scores=np.zeros(len(candidates))
            if valid.any():scores[valid]=np.clip(matrix[np.array(indices)[valid]]@profile/norm,-1,1)
            if mode!='rating':scores=(scores+1)/2
            w=channel_weights[level];num[valid]+=w*scores[valid];den[valid]+=w
        return np.divide(num,den,out=np.full(len(candidates),np.nan),where=den>0)
