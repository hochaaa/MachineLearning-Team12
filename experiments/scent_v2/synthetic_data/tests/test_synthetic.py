"""No real ratings or recommender fit required for these synthetic contracts."""
import json,unittest
import numpy as np
from experiments.scent_v2.synthetic_data.boundary import evaluation_users,safe_train
from experiments.scent_v2.synthetic_data.profiling import basic,features
from experiments.scent_v2.synthetic_data.generator import generate
from experiments.scent_v2.synthetic_data.quality import validate,js,distribution_difference


class SyntheticTests(unittest.TestCase):
    def fixture(self):
        p=dict(base_selection_probabilities=[.05]*20,item_effects=[0]*20,feature_global_score=[0]*20,feature_selection_probabilities=[.05]*20,residual_centers=[-1,0,1],residual_probabilities=[1/3]*3,residual_mean=0.,residual_sd=1.,activity_histogram={3:1,4:1},matched_feature_signal_supported=False,user_mean_location=7.5,user_mean_sd=.5,log_noise_mean=0.,log_noise_sd=.1,reference_ratings=[2,4,7,8,9,10])
        return p,np.eye(20),[f'note:t{i}'for i in range(20)],[f'item{i}'for i in range(20)]

    def test_manifest_numeric_values_skipped(self):
        text=json.dumps([dict(fold=1,train=[['hidden','secret',999999]],users=['eval'],support={'eval':[['secret',987654]]},answers={'eval':[['secret',876543]]})]);users,d=evaluation_users(text);self.assertEqual(users,{'eval'});self.assertEqual(d['manifest_numeric_decodes'],0)

    def test_forbidden_item_and_rating_not_decoded(self):
        # Excluded payload need not even have valid rating type: it is never decoded.
        text=json.dumps([['eval',{'hidden_item':'CANARY'},{'rating':999999}],['train','p',.8]])
        rows,ids,d=safe_train(text,{'eval'});self.assertEqual(rows,[('train','p',.8)]);self.assertEqual(d['numeric_ratings_decoded'],1);self.assertEqual(d['excluded_user_rating_values_decoded'],0)

    def test_string_escapes_and_nested_skip(self):
        text=json.dumps([dict(users=['e'],answers={'e':[['quote]brace}',{'x':[1,2]}]]})]);u,d=evaluation_users(text);self.assertEqual(u,{'e'})

    def test_no_cohort_overlap(self):
        with self.assertRaises(ValueError):evaluation_users(json.dumps([{'users':['e']},{'users':['e']}]))

    def test_rating_bands_no_overlap(self):
        values=[0,3,3.5,4.5,5,6.5,7,10];p=basic([('u',str(n),y/10)for n,y in enumerate(values)],[]);self.assertEqual(sum(p['rating_bands'].values()),8);self.assertEqual(p['rating_bands']['raw0_to3'],2)

    def test_density_and_units(self):
        p=basic([('u','a',.7),('u','b',.8),('v','a',.9)],['a','b','c']);self.assertEqual(p['density'],.75);self.assertEqual(p['half_point_compliance'],1.);self.assertEqual(p['item_frequency_bins']['unrated_candidates'],1)

    def test_seed_reproducibility(self):
        p,X,v,c=self.fixture();a=generate(p,X,v,c,set(),12,10,2);b=generate(p,X,v,c,set(),12,10,2);self.assertEqual(a[:3],b[:3]);np.testing.assert_array_equal(a[3],b[3]);self.assertEqual(a[4],b[4])

    def test_different_seed_changes(self):
        p,X,v,c=self.fixture();a=generate(p,X,v,c,set(),12,10,2);b=generate(p,X,v,c,set(),13,10,2);self.assertNotEqual(a[0],b[0])

    def test_all_quality_contracts(self):
        p,X,v,c=self.fixture();ratings,users,a,prob,tops=generate(p,X,v,c,{'real'},12,10,2);self.assertTrue(all(validate(ratings,users,c,{'real'}).values()));self.assertEqual(sum(u['cohort']=='activity_matched'for u in users),2);self.assertTrue(all(u['proposed_support_count']==5 for u in users if u['cohort']=='support_target_enriched'))

    def test_namespace_collision_stops(self):
        p,X,v,c=self.fixture()
        with self.assertRaises(ValueError):generate(p,X,v,c,{'synthetic_v210_user_000001'},12,10,2)

    def test_no_matched_feature_signal_if_unidentified(self):
        p,X,v,c=self.fixture();ratings,users,a,prob,tops=generate(p,X,v,c,set(),12,10,2);self.assertTrue(all(u['feature_signal_sd_raw']==0 for u in users[:2]));self.assertTrue(all(u['feature_signal_sd_raw']>0 for u in users[2:]));self.assertEqual(len({u['preference_vector_json']for u in users}),10)

    def test_distribution_metrics(self):
        self.assertAlmostEqual(js([1,1],[1,1]),0);self.assertAlmostEqual(js([1,0],[0,1]),1);self.assertEqual(distribution_difference([1,2],[1,2],[0,1,2])['histogram_KS'],0)

    def test_duplicate_detected(self):
        p,X,v,c=self.fixture();ratings,users,a,prob,tops=generate(p,X,v,c,set(),12,10,2);ratings.append(ratings[0]);self.assertFalse(validate(ratings,users,c,set())['pairs_unique'])

if __name__=='__main__':unittest.main()
