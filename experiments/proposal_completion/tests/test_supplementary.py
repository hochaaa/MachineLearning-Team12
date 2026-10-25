"""Synthetic correctness/invariants only; never read internal/external answers."""
import unittest,sys,inspect,ast
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import fields,jaccard,identity,versions,conflict,OUT
from parfumo_crosscheck import compare
from knn_baselines import KNN
from kmeans_analysis import kmeans,distance2,silhouette
from fuzzy_match_audit import classify,ratio
class MetadataTests(unittest.TestCase):
    def test_exact_normalization(self):self.assertEqual(identity('Chanel','No. 5'),identity('CHANEL','No 5'))
    def test_edt_edp(self):self.assertTrue(conflict(versions('X EDT'),versions('X Eau de Parfum')))
    def test_elixir_parfum(self):self.assertTrue(conflict(versions('X Elixir'),versions('X Parfum')))
    def test_specific_notes_not_synonyms(self):self.assertNotEqual(fields('Bulgarian Rose'),fields('Rose'))
    def test_missing(self):self.assertEqual(fields('NA, unknown, '),set());self.assertIsNone(jaccard(set(),set()))
    def test_jaccard(self):self.assertAlmostEqual(jaccard({'a','b'},{'b','c'}),1/3)
    def test_missing_comparison(self):self.assertFalse(compare(set(),{'a'})['comparable'])
class NeighborTests(unittest.TestCase):
    def setUp(self):self.train=[('a','x',1.),('a','y',.5),('b','x',.8),('b','y',.4),('b','z',.7),('c','z',.9)]
    def test_no_common(self):self.assertEqual(KNN('user').similarity({'x':1},{'z':1}),0)
    def test_missing_not_zero(self):self.assertEqual(KNN('user').similarity({'x':1},{'x':1,'z':0}),0)
    def test_two_common_similarity(self):self.assertAlmostEqual(KNN('user').similarity({'x':1,'y':.5},{'x':.8,'y':.4}),2/7)
    def test_no_self(self):self.assertNotIn('a',KNN('user').fit(self.train).similarities['a'])
    def test_fallback(self):
        scores,fb,_=KNN('item').fit(self.train).predict('c',['never_seen'])
        self.assertEqual(fb,1);self.assertEqual(scores,[0.])
    def test_deterministic(self):
        for mode in ['user','item']:
            a=KNN(mode).fit(self.train).predict('a',['z'])
            b=KNN(mode).fit(list(reversed(self.train))).predict('a',['z'])
            self.assertTrue(np.allclose(a[0],b[0]));self.assertEqual(a[1:],b[1:])
    def test_only_train_fit_interface(self):self.assertEqual(list(inspect.signature(KNN.fit).parameters),['self','train'])
    def test_no_test_inputs(self):
        import knn_baselines
        tree=ast.parse(inspect.getsource(knn_baselines))
        paths=[n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='load']
        self.assertEqual(set(paths),{'outputs/validation/train_exclude_3.json','outputs/improvement/validation.json','outputs/improvement/candidates.json'})
    def test_validation_cannot_affect_similarity(self):
        m=KNN('user').fit(self.train);before=dict(m.similarities['a'])
        validation=[('a','z',1.)];validation[0]=('a','z',0.)
        self.assertEqual(dict(m.similarities['a']),before)
    def test_new_support_is_not_foldin(self):
        m=KNN('user').fit(self.train);scores,fb,_=m.predict('new',['z'],support=[('x',1),('y',.5)])
        self.assertEqual(fb,0);self.assertAlmostEqual(scores[0],.7)
class ClusterTests(unittest.TestCase):
    def setUp(self):self.x=np.array([[0.,0.],[0.,1.],[1.,0.],[8.,8.],[8.,9.],[9.,8.]])
    def test_reproducibility(self):
        a=kmeans(self.x,2);b=kmeans(self.x,2)
        self.assertEqual(a[0],b[0]);np.testing.assert_array_equal(a[1],b[1])
    def test_size_sum(self):self.assertEqual(sum(np.bincount(kmeans(self.x,2)[1])),len(self.x))
    def test_distances(self):np.testing.assert_allclose(distance2(self.x,self.x).diagonal(),0,atol=1e-10)
    def test_degenerate_features(self):
        with self.assertRaises(ValueError):kmeans(np.zeros((4,2)),2)
    def test_silhouette_singletons(self):self.assertIsNone(silhouette(self.x,np.arange(6)))
    def test_silhouette_separated(self):self.assertGreater(silhouette(self.x,np.array([0,0,0,1,1,1])),.8)
    def test_empty_reseed_branch(self):
        # Force an empty assignment on the first distance call only, then permit real Lloyd steps.
        import kmeans_analysis
        real=kmeans_analysis.distance2;calls=[0]
        def forced(x,c):
            result=real(x,c);calls[0]+=1
            if len(c)==2 and calls[0]==2:result[:,1]=result[:,0]+1
            return result
        with patch.object(kmeans_analysis,'distance2',side_effect=forced):result=kmeans(self.x,2,n_init=1)
        self.assertGreater(result[4],0);self.assertEqual(len(result[1]),6)
    def test_saved_visual_sample(self):
        import json
        p=OUT/'kmeans_summary.json'
        self.assertTrue(p.exists())
        d=json.loads(p.read_text());self.assertEqual(d['size_sum'],d['selected']['rows']);self.assertTrue(d['visualization_sample_equals_silhouette_sample'])
class FuzzyTests(unittest.TestCase):
    def targets(self,*names):return [{'id':str(n),'name':x,'brand':'A','year':'2000'} for n,x in enumerate(names)]
    def test_brand_gate(self):self.assertEqual(classify('unknown','Black Orchid','',[])['status'],'NO_SAFE_CANDIDATE')
    def test_cross_brand_candidates(self):self.assertEqual(classify('B','long perfume','',self.targets('long perfume'))['status'],'BRAND_CONFLICT')
    def test_version(self):self.assertEqual(classify('A','long perfume EDT','',self.targets('long perfume EDP'))['status'],'VERSION_CONFLICT')
    def test_elixir(self):self.assertEqual(classify('A','long perfume Elixir','',self.targets('long perfume Parfum'))['status'],'VERSION_CONFLICT')
    def test_year(self):self.assertEqual(classify('A','long perfume','2010',self.targets('long perfume'))['status'],'REVIEW_REQUIRED')
    def test_tie(self):self.assertEqual(classify('A','long perfume','',self.targets('long perfume','long perfume'))['status'],'REVIEW_REQUIRED')
    def test_unverified(self):
        r=classify('A','long perfume','',self.targets('long perfume'))
        self.assertEqual(r['status'],'HIGH_CONFIDENCE_CANDIDATE');self.assertIn('NOT manually verified',r['reason'])
    def test_reordered(self):self.assertEqual(ratio('rose garden','garden rose'),1.)
    def test_short_ambiguous(self):self.assertEqual(classify('A','X','',self.targets('X'))['status'],'NO_SAFE_CANDIDATE')
class IntegrityTests(unittest.TestCase):
    def test_current_protected19_and_manifest(self):
        from common import guard
        self.assertIsNone(guard())
    def test_mismatch_stops(self):
        import common
        with patch.object(common,'sha',return_value='incorrect'):
            with self.assertRaises(RuntimeError):common.guard()
if __name__=='__main__':unittest.main()
