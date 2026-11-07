"""Synthetic Content preflight; fixtures are never real rating data."""
import math,unittest
from perfume.models import Content
from experiments.scent_v2.expanded_content.models import ContentExperiment,canonical_id,project,candidate_gate,permission_allows
from experiments.scent_v2.expanded_content.evaluation import label_blind_split,user_metrics,summarize

def vectors():return {f'i{n}':{'note:rose':.6,'note:wood':.8} for n in range(12)}
def permission():return dict(scope='LOCAL_NONCOMMERCIAL_RECOMMENDATION_EXPERIMENT',reviewed=True,evidence_url='fixture_only',review_reference='TEST_NOT_ACTUAL_PERMISSION')
def candidate(**kw):return dict(dict(identity_verified='True',concentration='EDP',official_brand='Fixture',official_product_name='Fixture EDP',quality_status='PARTIALLY_VERIFIED'),**kw)
class ModelTests(unittest.TestCase):
    def test_01_legacy_vector_preservation(self):
        v=vectors();m=ContentExperiment(v);self.assertEqual(dict(m.vectors['i0']),v['i0'])
        with self.assertRaises(TypeError):m.vectors['i0']['note:rose']=1
    def test_02_ids_no_collision(self):
        self.assertNotEqual(canonical_id('B','N','EDP'),canonical_id('B','N','EDT'))
        self.assertFalse(canonical_id('B','N','EDP').startswith('https://'))
    def test_03_duplicate_gate(self):
        r=candidate();key=('fixture','fixture edp','edp')
        self.assertEqual(candidate_gate(r,{'note:rose':1},permission(),{key}),'HOLD_DUPLICATE')
    def test_04_identity_required(self):self.assertEqual(candidate_gate(candidate(identity_verified='False'),{'a':1},permission(),set()),'HOLD_IDENTITY')
    def test_05_idf_immutable(self):
        d={'note:a':2};self.assertEqual(project(['note:a'],d),{'note:a':1});self.assertEqual(d,{'note:a':2})
    def test_06_original_math_parity(self):
        v=vectors();support=[('i'+str(n),n/10) for n in range(5)];pool=sorted(set(v)-{i for i,y in support})
        original=Content();original.vectors=v;expected=original.score(support,pool)
        result=ContentExperiment(v).score(support,v)
        self.assertEqual(result['top'],pool[:5])
        for i,y in zip(pool,expected):self.assertAlmostEqual(result['all_scores'][i],y)
    def test_07_new_projection(self):self.assertEqual(project(['note:a','note:a','note:b'],{'note:a':3,'note:b':4}),{'note:a':.6,'note:b':.8})
    def test_08_oov(self):self.assertEqual(project(['note:x'],{'note:a':2}),{})
    def test_09_zero_excluded(self):self.assertEqual(candidate_gate(candidate(),{},permission(),set()),'HOLD_ZERO_OR_NO_NOTES')
    def test_10_notes_accords_distinct(self):self.assertEqual(project(['note:rose'],{'accord:rose':2}),{})
    def test_11_support5(self):
        m=ContentExperiment(vectors())
        with self.assertRaises(ValueError):m.score([('i1',.7)]*5,vectors())
        with self.assertRaises(ValueError):m.score([('i'+str(i),.7) for i in range(4)],vectors())
    def test_12_heldout_not_in_scoring(self):
        m=ContentExperiment(vectors());support=[('i'+str(n),.7) for n in range(5)]
        before=m.score(support,vectors());answers=[('i8',1)]
        answers[0]=('i10',0)
        self.assertEqual(before,m.score(support,vectors()))
    def test_13_split_by_ids(self):
        history=[('i'+str(n),n/10) for n in range(6)];s,a=label_blind_split(history,'fixture')
        self.assertFalse({i for i,y in s}&{i for i,y in a});self.assertEqual(len(s),5);self.assertEqual(len(a),1)
        s2,a2=label_blind_split([(i,1-y) for i,y in history],'fixture');self.assertEqual([i for i,y in s],[i for i,y in s2])
    def test_14_seen_excluded(self):
        support=[('i'+str(n),.7) for n in range(5)];result=ContentExperiment(vectors()).score(support,vectors())
        self.assertFalse(set(result['top'])&{i for i,y in support})
    def test_15_top5(self):self.assertEqual(len(ContentExperiment(vectors()).score([('i'+str(n),.7) for n in range(5)],vectors())['top']),5)
    def test_16_score_bounds(self):
        result=ContentExperiment(vectors()).score([('i'+str(n),.7) for n in range(5)],vectors())
        self.assertTrue(all(-1e-12<=v<=1+1e-12 for v in result['scores']))
    def test_17_determinism(self):
        m=ContentExperiment(vectors());s=[('i'+str(n),.7) for n in range(5)];self.assertEqual(m.score(s,vectors()),m.score(s,vectors()))
    def test_18_new_old_exposure(self):
        r=[dict(top=['a','b','c','d','e'],answers=[('a',1)],accuracy=user_metrics(['a'],[('a',1)]))]
        s=summarize(r,list('abcdef'),{'a','b'});self.assertEqual(s['new_slot_fraction'],.4);self.assertEqual(s['old_slot_fraction'],.6)
    def test_19_usage_not_metadata_status(self):
        self.assertEqual(candidate_gate(candidate(quality_status='VERIFIED'),{'a':1},{},set()),'HOLD_USAGE_SCOPE_UNVERIFIED')
        self.assertEqual(candidate_gate(candidate(),{'a':1},permission(),set()),'APPROVED_FOR_LOCAL_EXPERIMENT_ONLY')
    def test_20_all_zero_profile(self):self.assertEqual(ContentExperiment(vectors()).score([('i'+str(n),0) for n in range(5)],vectors())['status'],'NO_USABLE_PROFILE')
    def test_21_no_unknown_support_fallback(self):self.assertEqual(ContentExperiment(vectors()).score([('new'+str(n),.7) for n in range(5)],vectors())['top'],[])
    def test_22_invalid_ratings(self):
        for value in (-1,1.1,float('nan'),True):
            with self.assertRaises(ValueError):ContentExperiment(vectors()).score([('i'+str(n),value) for n in range(5)],vectors())
    def test_23_new5_supported_in_expanded_fixture(self):
        v=vectors();v.update({f'n{n}':{'note:rose':1} for n in range(6)})
        r=ContentExperiment(v).score([('n'+str(n),.7) for n in range(5)],v)
        self.assertEqual(len(r['top']),5);self.assertEqual(r['top'][0],'n5')

if __name__=='__main__':unittest.main()
