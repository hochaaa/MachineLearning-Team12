"""Synthetic preflight, no training. Real input and preservation checked separately."""
import csv,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experiments.scent_v2.real_rating_retraining.audit import *
from experiments.scent_v2.synthetic_data.boundary import evaluation_users,safe_train
from experiments.scent_v2.evaluate import metrics

CANDIDATES=['id'+str(n) for n in range(479)]
CATALOG={i:dict(brand='Fixture',name='Example '+i) for i in CANDIDATES}
CATALOG['id0']=dict(brand='Fixture',name='Example EDP')
CATALOG['id1']=dict(brand='Fixture',name='Example EDT')
def row(**kw):
    return dict(dict(participant_id='fixture_person',product_id='id0',brand='Fixture',product_name='Example EDP',score='7.5',source_type='catalog',created_at='2026-10-30',updated_at='2026-10-30'),**kw)

class AuditTests(unittest.TestCase):
    def parse(self,rows):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.csv'
            with p.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(FIELDS));writer.writeheader();writer.writerows(rows)
            return read_csv(p)
    def test_01_csv_schema(self):self.assertEqual(self.parse([row()])[1]['rows'],1)
    def test_02_users(self):self.assertEqual(self.parse([row(),row(participant_id='other')])[1]['users'],2)
    def test_03_counts(self):self.assertEqual(self.parse([row(),row(product_id='id1',product_name='Example EDT')])[1]['unique_product_ids'],2)
    def test_04_range(self):
        for v in ('-1','11','NaN','Inf'):
            with self.assertRaises(ValueError):self.parse([row(score=v)])
    def test_05_step(self):
        self.parse([row(score='0')]);self.parse([row(score='10')])
        with self.assertRaises(ValueError):self.parse([row(score='7.25')])
    def test_06_duplicates(self):
        with self.assertRaises(ValueError):self.parse([row(),row()])
    def test_07_missing(self):
        with self.assertRaises(ValueError):self.parse([row(score='')])
    def test_08_exact_catalog(self):self.assertEqual(match_one(row(),CATALOG,CANDIDATES)[0],'id0')
    def test_09_custom_review(self):
        self.assertIsNone(match_one(row(product_id='custom',product_name='Unknown',source_type='custom'),CATALOG,CANDIDATES)[0])
    def test_10_fixed479(self):
        with self.assertRaises(ValueError):match_one(row(),CATALOG,CANDIDATES[:-1])
    def test_11_old_eval_excluded_before_values(self):
        ids,a=evaluation_users('[{"users":["evaluation"],"answers":{"never_decode":true}}]')
        rows,users,a=safe_train('[["evaluation",{"never":"item"},{"never":"rating"}],["train","id0",0.7]]',ids)
        self.assertEqual(len(rows),1);self.assertEqual(a['excluded_user_rating_values_decoded'],0)
    def test_12_new_eval_training_excluded(self):
        with self.assertRaises(ValueError):validate_training([('eval','id0',.7)],{'eval'},CANDIDATES)
    def test_13_support_heldout(self):
        h=[('id'+str(n),n/10) for n in range(6)];s,a=support_answers(h)
        self.assertEqual(len(s),5);self.assertEqual(len(a),1);self.assertFalse({i for i,r in s}&{i for i,r in a})
        with self.assertRaises(ValueError):support_answers(h[:5])
        s2,a2=support_answers([(i,1-r) for i,r in h]);self.assertEqual([i for i,r in s],[i for i,r in s2])
    def test_14_content_structure(self):self.assertIn('Existing Content',POLICY['content'])
    def test_15_mf_policy(self):self.assertEqual(MF_POLICY,dict(factors=4,epochs=160,learning_rate=.01,regularization=.01,seed=12))
    def test_16_alpha(self):self.assertEqual(POLICY['alpha'],.25);self.assertEqual(POLICY['foldin_ridge'],.01)
    def test_17_candidate_exclusion(self):
        with self.assertRaises(ValueError):validate_training([('u','outside',.7)],set(),CANDIDATES)
    def test_18_no_fuzzy_or_version_loss(self):
        self.assertIsNone(match_one(row(product_id='unknown',product_name='Example'),CATALOG,CANDIDATES)[0])
        self.assertIsNone(match_one(row(product_id='unknown',product_name='Exampel EDP'),CATALOG,CANDIDATES)[0])
        self.assertEqual(match_one(row(product_id='other',product_name='Example EDT'),CATALOG,CANDIDATES)[0],'id1')
    def test_19_zero_additions_prevents_training(self):
        with self.assertRaises(ValueError):require_training_additions([])
    def test_20_five_not_evaluable(self):
        rows=[row(participant_id='one') for _ in range(5)];matches=[('id'+str(n),'fixture') for n in range(5)]
        ids,a=split_eligibility(rows,matches);self.assertEqual(ids,set());self.assertEqual(a['support5_only_users'],1)
    def test_21_synthetic_and_independent_training_rejected(self):
        for r in ({'synthetic':True},{'role':'independent'}):
            with self.assertRaises(ValueError):require_training_additions([r])
    def test_22_metrics(self):
        self.assertEqual(metrics(['id1','id2'],[('id1',1)])['ndcg'],1)
        self.assertIsNone(metrics(['id1'],[('id2',.1)]))
        self.assertEqual(metrics(['id1'],[('id2',1)])['recall'],0)
    def test_23_pseudonym_namespace(self):
        value=pseudonym('fixture_person',b'x'*32)
        self.assertNotIn('fixture_person',value);self.assertEqual(value,pseudonym('fixture_person',b'x'*32))
    def test_24_product_id_metadata_collision(self):
        with self.assertRaises(ValueError):self.parse([row(),row(participant_id='other',product_name='Wrong')])

if __name__=='__main__':unittest.main()
