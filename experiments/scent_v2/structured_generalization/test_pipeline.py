"""Temporary SYNTHETIC functional fixtures only; no actual accuracy claims."""
import csv,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from perfume.models import Content,Baseline
from experiments.scent_v2.accuracy_root_cause.model import Structured
from .core import load_csv_identities,decode,validate_provenance,evaluate_csv

class PipelineTests(unittest.TestCase):
    def write_csv(self,path,rows):
        with path.open('w',newline='') as f:w=csv.writer(f);w.writerow(['user_id','perfume_id','rating']);w.writerows(rows)
    def provenance(self,path):
        p=dict(real_user_data=True,not_used_for_model_selection=True,pre_recommendation_ratings_only=True,identity_disjoint_from_historical_people_attested=True,consent_for_local_evaluation_confirmed=True,source_namespace='SYNTHETIC_FUNCTIONAL_FIXTURE_NOT_REAL');path.write_text(json.dumps(p))
    def model(self,n=12):
        ids=[f'i{k:03}' for k in range(n)];c=Content();c.idf={'a':1.,'b':1.};c.vectors={i:{'a':1.} if k%2 else {'b':1.} for k,i in enumerate(ids)};m=SimpleNamespace(Q=np.random.default_rng(12).uniform(0,.2,(n,4)),items={i:k for k,i in enumerate(ids)},factors=4,reg=.01);b=Baseline().fit([('train',i,.8) for i in ids]);raw=[dict(url=i,Top='rose' if k%2 else 'wood',Middle='iris',Base='musk',mainaccord1='floral') for k,i in enumerate(ids)];st=Structured(raw,set(ids),ids);return ids,(c,m,b,st,{},False,{'policy_sha256':'test-lock'})
    def test_minimum6_and_no_positive_filter(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r.csv';self.write_csv(p,[('u',str(i),'0') for i in range(6)]+[('short',str(i),'10') for i in range(5)]);cohort,a=load_csv_identities(p,set(map(str,range(12))),set());self.assertEqual(len(cohort),1);self.assertEqual(len(cohort[0]['support_tokens']),5);self.assertEqual(len(cohort[0]['answer_tokens']),1);self.assertEqual(a['ratings_decoded'],0)
    def test_split_label_blind(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r.csv';self.write_csv(p,[('u',str(i),'BAD_OPAQUE') for i in range(8)]);a,_=load_csv_identities(p,set(map(str,range(8))),set());self.write_csv(p,[('u',str(i),'10') for i in reversed(range(8))]);b,_=load_csv_identities(p,set(map(str,range(8))),set());self.assertEqual([i for i,r in a[0]['support_tokens']],[i for i,r in b[0]['support_tokens']])
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r.csv';self.write_csv(p,[('u','a','8'),('u','a','1')])
            with self.assertRaises(ValueError):load_csv_identities(p,{'a'},set())
    def test_historical_user_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r.csv';self.write_csv(p,[('historical','a','8')])
            with self.assertRaises(ValueError):load_csv_identities(p,{'a'},{'historical'})
    def test_unknown_items_not_force_mapped(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r.csv';self.write_csv(p,[('u','unknown','8')]);a,d=load_csv_identities(p,{'a'},set());self.assertEqual(a,[]);self.assertEqual(d['excluded']['outside_fixed479'],1)
    def test_rating_scale_and_zero(self):
        self.assertEqual(decode([('a','0'),('b','10'),('c','7.5')]),[('a',0.),('b',1.),('c',.75)])
        for r in ['NaN','Infinity','-1','10.5','1.2','true',True]:
            with self.assertRaises(ValueError):decode([('a',r)])
    def test_provenance_never_auto_approved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'provenance.json';p.write_text('{}')
            with self.assertRaises(ValueError):validate_provenance(p)
    def test_post_exposure_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r.csv';p.write_text('user_id,perfume_id,rating,source\nu,a,8,post_recommendation_feedback\n')
            with self.assertRaises(ValueError):load_csv_identities(p,{'a'},set())
    def test_complete_synthetic_flow_and_answer_boundary(self):
        ids,model=self.model()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'r.csv';prov=root/'p.json';self.provenance(prov);self.write_csv(p,[(u,i,'8') for u in ['fixture1','fixture2'] for i in ids[:6]]);order=[]
            real_decode=decode
            def tracked(tokens):order.append('support' if len(tokens)==5 else 'answers');return real_decode(tokens)
            with patch('experiments.scent_v2.structured_generalization.core.decode',side_effect=tracked):result=evaluate_csv(p,prov,root/'out',fixture=True,forbidden_override=set(),model_override=model)
            self.assertEqual(order,['support','support','answers','answers']);self.assertEqual(result['status'],'SYNTHETIC_FUNCTIONAL_TEST_ONLY');self.assertFalse(result['real_accuracy_evaluated']);self.assertEqual(result['models']['baseline']['users'],2);self.assertTrue((root/'out/model_comparison.csv').exists())
    def test_no_positive_answers_not_fabricated_accuracy(self):
        ids,model=self.model()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'r.csv';prov=root/'p.json';self.provenance(prov);self.write_csv(p,[('fixture',i,'0') for i in ids[:6]]);result=evaluate_csv(p,prov,root/'out',fixture=True,forbidden_override=set(),model_override=model)
            self.assertIsNone(result['models']['baseline']['ndcg']);self.assertFalse(result['real_accuracy_evaluated'])
    def test_repeat_participants_blocked_even_after_failed_open(self):
        ids,model=self.model(479)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'r.csv';prov=root/'p.json';self.provenance(prov);self.write_csv(p,[('fixture',i,'8') for i in ids[:6]])
            with patch('experiments.scent_v2.structured_generalization.core.OUT',root),patch('experiments.scent_v2.structured_generalization.core.verify_lock',return_value={'policy_sha256':'test-lock'}),patch('experiments.scent_v2.structured_generalization.core.predict',side_effect=RuntimeError('SYNTHETIC_STOP_BEFORE_SCORING')):
                with self.assertRaisesRegex(RuntimeError,'SYNTHETIC_STOP'):evaluate_csv(p,prov,root/'evaluations/first',forbidden_override=set(),model_override=model)
                with self.assertRaisesRegex(RuntimeError,'previously opened'):evaluate_csv(p,prov,root/'evaluations/second',forbidden_override=set(),model_override=model)
            self.assertFalse((root/'evaluations/first/evaluation_results.json').exists())

if __name__=='__main__':unittest.main()
