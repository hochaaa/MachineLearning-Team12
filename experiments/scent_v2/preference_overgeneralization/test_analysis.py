"""Focused synthetic observations only; no training or accuracy experiment."""
import unittest
import numpy as np
from .analysis import label,preferences,pair_analysis,max_similarity,suspected,component_alignment,summarize_recommendations


def features(a,b=()):return dict(Top=set(a),Middle=set(),Base=set(),accords=set(b))

class AnalysisTests(unittest.TestCase):
    def test_polarity_boundaries(self):
        self.assertEqual(label(.7),'POSITIVE');self.assertEqual(label(.3),'NEGATIVE');self.assertEqual(label(.6),'NEUTRAL');self.assertEqual(label(None),'UNOBSERVED')
    def test_compound_requires_distinct_products(self):
        f={'a':features(['rose'],['woody','floral']),'b':features(['wood'],['woody','fresh'])}
        self.assertFalse(preferences({'a':.9},f)['compound_mainaccord_product_proxy']);self.assertTrue(preferences({'a':.9,'b':.8},f)['compound_mainaccord_product_proxy'])
    def test_notes_accords_and_missing_separate(self):
        f={'a':features(['rose'],['woody']),'b':features(['wood'],['woody'])};p=preferences({'a':.8,'b':.1},f)
        self.assertEqual(p['channels']['Top']['overlap_features'],[]);self.assertEqual(p['channels']['accords']['overlap_features'],['woody']);self.assertFalse(p['channels']['Middle']['both_polarities_evaluable']);self.assertIsNone(p['channels']['Middle']['overlap_jaccard'])
    def test_no_negative_not_zero_overlap_evidence(self):
        f={'a':features(['rose'],['floral'])};p=preferences({'a':.9},f);self.assertIsNone(p['channels']['accords']['overlap_jaccard'])
    def test_feature_only_shared_not_confirmed_pair(self):
        f={'a':features([],['woody']),'b':features([],['woody'])};p=pair_analysis('A','B',{'a':.8},{'b':.1},f,1,2);self.assertEqual(p['status'],'INSUFFICIENT_EVIDENCE');self.assertEqual(p['common_rated_products'],0)
    def test_partial_pair_requires_same_product_opposition(self):
        f={'a':features([],['woody']),'b':features([],['floral'])};p=pair_analysis('A','B',{'a':.8,'b':.9},{'a':.9,'b':.2},f,1,2)
        self.assertEqual(p['status'],'CONFIRMED_PRODUCT_PARTIAL_PREFERENCE_DIFFERENCE');self.assertEqual(p['opposed_product_ids'],['b']);self.assertTrue(p['opposition_has_extra_accord_annotations']);self.assertFalse(p['causal_transfer_identified'])
    def test_same_fold_source_cannot_be_in_target_train(self):
        f={'a':features([],['woody']),'b':features([],['floral'])};p=pair_analysis('A','B',{'a':.8,'b':.9},{'a':.9,'b':.2},f,1,1);self.assertFalse(p['A_can_be_in_B_train'])
    def test_risk_needs_both_anchors(self):
        self.assertIsNone(suspected(np.nan,.8));self.assertFalse(suspected(.5,.5));self.assertTrue(suspected(.4,.6))
    def test_actual_matrix_max_and_missing_anchor(self):
        M=np.array([[1,.2],[.2,1.]]);items={'a':0,'b':1};np.testing.assert_array_equal(max_similarity(M,items,['a'],['a','b']),[1,.2]);self.assertTrue(np.isnan(max_similarity(M,items,[],['a'])).all())
    def test_rank_diagnostic_not_cause(self):
        self.assertEqual(component_alignment(1,20,True,True),'MF_ALIGNED');self.assertEqual(component_alignment(20,1,True,True),'CONTENT_ALIGNED');self.assertEqual(component_alignment(1,1,False,False),'POPULARITY_FALLBACK')
    def test_unknowns_not_negatives_and_denominators(self):
        rows=[dict(heldout_class=c,suspected_conflict=r,component_alignment='MF_ALIGNED',structured_promoted=False) for c,r in [('UNOBSERVED',None),('NEGATIVE',True),('POSITIVE',False),('NEUTRAL',None)]];s=summarize_recommendations(rows)
        self.assertEqual(s['negative_slots'],1);self.assertEqual(s['observed_rated_slots'],3);self.assertEqual(s['confirmed_negative_rate_among_observed'],1/3);self.assertEqual(s['suspected_conflict_fraction_evaluable'],.5);self.assertEqual(s['known_negative_slots_over_all_lower_bound'],.25)

if __name__=='__main__':unittest.main()
