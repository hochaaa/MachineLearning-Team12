"""Count ACTUAL MF.fit entries, including V2 early-stop probes; hard61/phase caps."""
import sys,time,json,hashlib
from v3_data import digest,save
from mf_v3 import MFV3
from mf_v2 import BiasMF
from perfume.models import MatrixFactorization
class FitBudget:
    def __init__(self,caps):self.caps=caps;self.used={k:0 for k in ['primary','seed','final']};self.records=[];self.cache={};self.pending=None;self.reuses=[]
    def check(self,phase):
        if self.used[phase]>=self.caps[phase] or sum(self.used.values())>=self.caps['total']:raise RuntimeError('FIT BUDGET EXCEEDED; STOP')
    def profile(self,frame,event,arg):
        if event=='call' and frame.f_code.co_name=='fit' and isinstance(frame.f_locals.get('self'),(MFV3,BiasMF,MatrixFactorization)):
            if self.pending is None:raise RuntimeError('Unmetered MF.fit forbidden')
            self.check(self.pending['phase']);self.used[self.pending['phase']]+=1;self.records.append(dict({k:v for k,v in self.pending.items() if k!='observed'},fit_number=sum(self.used.values()),status='entered'));self.pending['observed']+=1;self.persist()
    def persist(self):save('diagnostics/fit_ledger.json',{'counts':self.used,'total':sum(self.used.values()),'caps':self.caps,'records':self.records,'cache_reuses':self.reuses})
    def invoke(self,model,rows,phase,tag,stop=()):
        key=digest((type(model).__name__,model.config if hasattr(model,'config') else {'factors':model.factors,'epochs':model.epochs,'lr':model.lr,'reg':model.reg},getattr(model,'seed',12),digest(rows),digest(stop)))
        if key in self.cache:
            self.reuses.append({'key':key,'phase':phase,'tag':tag,'training_digest':digest(rows),'stop_digest':digest(stop),'verified_identical_key':True});self.persist();return self.cache[key]
        self.check(phase);self.pending={'phase':phase,'tag':tag,'training_digest':digest(rows),'stop_digest':digest(stop),'seed':model.seed,'config':getattr(model,'config',None),'key':key,'observed':0};start=time.perf_counter()
        try:
            result=model.fit(rows,stop) if isinstance(model,BiasMF) else model.fit(rows)
            assert self.pending['observed']==1
            self.records[-1].update(status='completed',observed_calls=self.pending['observed'],seconds=time.perf_counter()-start,epochs=getattr(result,'best_epoch',getattr(result,'epochs',None)));self.cache[key]=result;return result
        finally:self.pending=None;self.persist()
