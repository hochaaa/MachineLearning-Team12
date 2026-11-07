"""Pre-learning checks for existing mapping/Fold-in/diagnostic arithmetic."""
import unittest
from types import SimpleNamespace
import numpy as np
from perfume.models import Content,Baseline
from experiments.scent_v2.mf_cv_optimization.core import ridge
from .diagnostic import component_arrays,train_reference,group_stats

class DiagnosticTests(unittest.TestCase):
    def context(self):
        ids=list('abcdefgh');c=Content();c.idf={'a':1,'b':1};c.vectors={i:{'a':1.} if n%2 else {'b':1.} for n,i in enumerate(ids)};m=SimpleNamespace(Q=np.random.default_rng(12).uniform(0,.2,(8,4)),items={i:n for n,i in enumerate(ids)},factors=4,reg=.01);rows=[('u',i,.2+.1*n) for n,i in enumerate(ids)];b=Baseline().fit(rows);return ids,c,m,rows,b
    def test_ridge_matches_equation(self):
        ids,c,m,rows,b=self.context();s=[(i,r) for u,i,r in rows[:5]];p,_=ridge(m,s);q=m.Q[:5];y=np.array([r for i,r in s]);expected=np.linalg.solve(np.einsum('ni,nj->ij',q,q)+5*.01*np.eye(4),np.einsum('ni,n->i',q,y));np.testing.assert_array_equal(p,expected)
    def test_permuted_item_mapping_consistent(self):
        ids,c,m,rows,b=self.context();s=[(i,r) for u,i,r in rows[:5]];old=component_arrays(s,ids,c,m,b);perm=list(reversed(range(8)));n=SimpleNamespace(Q=m.Q[perm],items={ids[p]:j for j,p in enumerate(perm)},factors=4,reg=.01);new=component_arrays(s,ids,c,n,b)
        np.testing.assert_array_equal(old['raw'],new['raw']);np.testing.assert_array_equal(old['hybrid'],new['hybrid'])
    def test_ranges_and_exclusion(self):
        ids,c,m,rows,b=self.context();x=component_arrays([(i,r) for u,i,r in rows[:5]],ids,c,m,b)
        for key in ['content','mf','hybrid']:self.assertTrue(((x[key]>=0)&(x[key]<=1)).all())
        self.assertFalse(set(x['pool'])&set(ids[:5]))
    def test_training_reference_only(self):
        ids,c,m,rows,b=self.context();q=m.Q.copy();ref,d=train_reference(rows,ids,c,m,b);self.assertEqual(d['reference_users'],1);self.assertLess(d['ridge_normal_equation_residual_max'],1e-10);self.assertTrue(d['fallback_probe_pass']);np.testing.assert_array_equal(q,m.Q)
    def test_untrained_item_fallback(self):
        ids,c,m,rows,b=self.context();s=[(i,r) for u,i,r in rows[:5]];del m.items['h'];x=component_arrays(s,ids,c,m,b);n=x['pool'].index('h');self.assertTrue(np.isnan(x['raw'][n]));self.assertEqual(x['hybrid'][n],x['content'][n])
        del c.vectors['h'];x=component_arrays(s,ids,c,m,b);self.assertEqual(x['hybrid'][n],x['popularity'][n])
    def test_group_distributions(self):
        d=group_stats([('u','a',.2),('u','b',.8),('v','a',1.)]);self.assertEqual(d['users'],2);self.assertEqual(d['ratings'],3);self.assertAlmostEqual(d['positive_rating_fraction'],2/3)

if __name__=='__main__':unittest.main()
