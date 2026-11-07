"""No-fit synthetic checks of new structural/calibration policies and archive."""
import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from perfume.models import Content,Baseline
from .model import Structured,structural_phrases,cdf,predict,score
from .diagnostic import component_arrays,pack_state,save_states
from .run import load_selected

class ModelTests(unittest.TestCase):
    def raw(self):return [dict(url='a',Top='Rose',Middle='',Base='Wood',mainaccord1='woody'),dict(url='b',Top='Wood',Middle='',Base='Rose',mainaccord1='woody'),dict(url='c',Top='unseen',Middle='',Base='',mainaccord1='')]
    def test_stage_and_phrase_parser(self):
        p=structural_phrases(dict(Top='Rose, Pink Pepper, unknown',Middle='Rose',Base=None,mainaccord1='Woody'))
        self.assertEqual(p['Top'],{'rose','pink pepper'});self.assertEqual(p['Middle'],{'rose'});self.assertEqual(p['Base'],set());self.assertEqual(p['accords'],{'woody'})
    def test_roles_not_collapsed(self):
        st=Structured(self.raw(),{'a','b'},['a','b','c']);self.assertAlmostEqual(st.matrix[0,1],.25);self.assertAlmostEqual(st.matrix[0,0],.75)
    def test_train_only_vocabulary_and_missing(self):
        st=Structured(self.raw(),{'a','b'},['a','b','c']);self.assertNotIn('unseen',st.vocab['Top']);self.assertTrue(np.isnan(st.matrix[2]).all())
    def test_multi_hot_unit_channel(self):
        rows=[dict(url=i,Top='rose,wood',Middle='rose',Base='wood',mainaccord1='woody') for i in ['a','b']];st=Structured(rows,{'a'},['a','b']);self.assertAlmostEqual(st.matrix[0,1],1.)
    def test_no_positive(self):
        st=Structured(self.raw(),{'a','b'},['a','b','c']);self.assertTrue(np.isnan(st.max_signal([('a',.5)],['a','b'])).all())
    def test_cdf_train_ties(self):
        a=cdf(np.array([1.,2.,3.,np.nan]),np.array([1.,1.,2.,3.]),np.array([.1,.2,.3,np.nan]));np.testing.assert_array_equal(a[:3],[.25,.625,.875]);self.assertTrue(np.isnan(a[-1]))
    def test_cdf_constant_fallback(self):
        original=np.array([.2,.6]);np.testing.assert_array_equal(cdf(np.array([9.,10.]),np.ones(5),original),original)
    def context(self):
        ids=[str(n) for n in range(80)];raw=[dict(url=i,Top='rose' if n%2 else 'wood',Middle='iris',Base='musk',mainaccord1='woody') for n,i in enumerate(ids)];c=Content();c.idf={'a':1.,'b':1.};c.vectors={i:{'a':1.} if n%2 else {'b':1.} for n,i in enumerate(ids)};m=SimpleNamespace(Q=np.random.default_rng(12).uniform(0,.2,(80,4)),items={i:n for n,i in enumerate(ids)},factors=4,reg=.01);b=Baseline().fit([('train',i,.8) for i in ids]);st=Structured(raw,set(ids[:60]),ids);ref=dict(raw_reference=np.linspace(0,1.5,100),content_reference=np.linspace(0,1,100));support=list(zip(ids[:5],[.9,.1,.7,.3,.5]));return ids,c,m,b,st,ref,support
    def test_gate_preserves_baseline(self):
        ids,c,m,b,st,ref,s=self.context();self.assertEqual(predict('baseline',s,ids,c,m,b,st,ref,False),predict('train_cdf',s,ids,c,m,b,st,ref,False))
    def test_top5_valid_all_policies(self):
        ids,c,m,b,st,ref,s=self.context();old=m.Q.copy()
        for p in ['baseline','structured','train_cdf']:
            top,sc=predict(p,s,ids,c,m,b,st,ref,True);self.assertEqual(len(top),len(set(top)));self.assertEqual(len(top),5);self.assertFalse(set(top)&set(ids[:5]));self.assertTrue(np.isfinite(sc).all())
        np.testing.assert_array_equal(old,m.Q)
    def test_structured_top50_only(self):
        ids,c,m,b,st,ref,s=self.context();x=component_arrays(s,ids,c,m,b)
        from experiments.scent_v2.recommend import rank
        top,sc=score('structured',s,x,st,ref,True);self.assertTrue(set(top)<=set(rank(x['pool'],x['hybrid'])[:50]))
    def test_save_restore(self):
        ids,c,m,b,st,ref,s=self.context();state=pack_state(c,m,b,ids);extra={}
        for n in range(1,6):
            extra.update({f'fold{n}_calib_{k}':v for k,v in ref.items()});extra[f'fold{n}_gate']=np.asarray(True);extra[f'fold{n}_struct_ids']=np.asarray(st.ids);extra[f'fold{n}_struct_matrix']=st.matrix
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'best.npz';save_states(path,[state]*5,extra,'structured')
            for n in range(1,6):
                lc,lm,lb,ls,lr,gate,meta=load_selected(path,n)
                for p in ['baseline','structured','train_cdf']:self.assertEqual(predict(p,s,ids,c,m,b,st,ref,True),predict(p,s,ids,lc,lm,lb,ls,lr,gate))

if __name__=='__main__':unittest.main()
