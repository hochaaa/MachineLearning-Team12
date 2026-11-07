"""Synthetic tests for metric concentration, opaque labels and one-time gate."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .analysis import paired_counts,fold_mean_delta,stability,final_uncertainty
from .run import reserved_tokens,decode,open_gate,BASE,SELECTED


def metric(f,a,b):return dict(fold=f,baseline_ndcg=a,selected_ndcg=b,delta=b-a if a is not None else None,baseline_hit=int(a>0) if a is not None else None,selected_hit=int(b>0) if b is not None else None)

class ValidationTests(unittest.TestCase):
    def test_only_two_fixed_policies(self):
        self.assertEqual(SELECTED,dict(signal='max',mode='top50',**{'lambda':.2}));self.assertEqual(BASE['lambda'],0.)
    def test_positive_user_counts(self):
        result=paired_counts([metric(1,0,.2),metric(1,.3,0),metric(1,.2,.2),metric(1,None,None)])
        self.assertEqual((result['positive_users'],result['improved'],result['worsened'],result['tied']),(3,1,1,1));self.assertEqual(result['hit_gained'],1);self.assertEqual(result['hit_lost'],1)
    def test_fold_macro_denominators(self):
        pairs=[metric(1,0,.4),metric(1,0,0),metric(2,0,.3),metric(2,0,0),metric(2,0,0)]
        self.assertAlmostEqual(fold_mean_delta(pairs),.15);self.assertAlmostEqual(fold_mean_delta(pairs,[0]),.05)
        result=stability(pairs,draws=100);self.assertAlmostEqual(sum(p['macro_delta_contribution'] or 0 for p in result['per_user_metrics_no_identifiers']),.15)
    def test_one_user_concentration(self):
        result=stability([metric(1,0,.6),metric(1,0,0),metric(2,0,0),metric(2,0,0)],draws=100)
        self.assertTrue(result['concentration']['any_single_exclusion_eliminates_improvement']);self.assertEqual(result['concentration']['largest1_positive_share'],1)
    def test_distributed_gain_and_seed(self):
        pairs=[metric(f,0,.2) for f in [1,1,1,2,2,2]];a=stability(pairs,draws=100);b=stability(pairs,draws=100)
        self.assertFalse(a['concentration']['any_single_exclusion_eliminates_improvement']);self.assertEqual(a,b)
    def test_final_bootstrap(self):
        result=final_uncertainty([metric(1,0,.2),metric(1,None,None)],draws=100)
        self.assertEqual(result['users'],1);self.assertAlmostEqual(result['low95'],.2);self.assertAlmostEqual(result['high95'],.2)
    def test_id_only_reserved_split(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'raw.json';rows=[['reserved',str(i),'DO_NOT_DECODE'] for i in range(6)]+[['other','a',True]];path.write_text(json.dumps(rows))
            r=reserved_tokens(path,[str(i) for i in range(6)],{'reserved'});self.assertEqual(len(r),1);self.assertEqual(len(r[0]['support_tokens']),5);self.assertEqual(len(r[0]['answer_tokens']),1)
            with self.assertRaises(ValueError):decode(r[0]['support_tokens'])
    def test_decode_boundaries_and_invalid(self):
        self.assertEqual(decode([('a','0'),('b','1'),('c','0.4')]),[('a',0.),('b',1.),('c',.4)])
        for token in ['true','NaN','Infinity','-0.1','1.1','"rating"']:
            with self.assertRaises(ValueError):decode([('a',token)])
    def test_one_time_open_gate(self):
        with tempfile.TemporaryDirectory() as d,patch('experiments.scent_v2.final_validation.run.OUT',Path(d)),patch('experiments.scent_v2.final_validation.run.check_lock'):
            with self.assertRaises(RuntimeError):open_gate({})
            self.assertFalse((Path(d)/'final_opened_once.json').exists())
            for name in ['development_stability.json','independence_audit.json']:(Path(d)/name).write_text('{}')
            open_gate({});self.assertTrue((Path(d)/'final_opened_once.json').exists())
            with self.assertRaises(FileExistsError):open_gate({})

if __name__=='__main__':unittest.main()
