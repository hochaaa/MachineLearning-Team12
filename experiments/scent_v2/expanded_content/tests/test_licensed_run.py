"""Post-run source isolation and actual catalog boundary checks; no new scoring data."""
import csv,hashlib,json,math,unittest
from pathlib import Path
from experiments.scent_v2.expanded_content.catalog import OUT,licensed_match
from experiments.scent_v2.expanded_content.models import ContentExperiment
from experiments.scent_v2.expanded_content.evaluation import label_blind_split

class LicensedTests(unittest.TestCase):
    def test_01_unknown_concentration_not_imputed(self):
        r=[dict(house='Brand',name='Example',concentration='',notes=['Rose'])]
        self.assertIsNone(licensed_match('Brand','Example','EDP',r))
    def test_02_edt_edp_not_merged(self):
        r=[dict(house='Brand',name='Example',concentration='eau-de-toilette',notes=['Rose'])]
        self.assertIsNone(licensed_match('Brand','Example','EDP',r))
    def test_03_explicit_absolu_only(self):
        r=[dict(house='Brand',name='Example Absolu de Parfum',concentration='parfum',notes=['Rose'])]
        self.assertIs(licensed_match('Brand','Example','Absolu de Parfum',r),r[0])
        self.assertIsNone(licensed_match('Brand','Example','EDP',r))
    def test_04_duplicate_provider_records_not_first_wins(self):
        r=dict(house='Brand',name='Example',concentration='eau-de-parfum',notes=['Rose'])
        self.assertIsNone(licensed_match('Brand','Example','EDP',[r,r.copy()]))
    def test_05_snapshot_and_license(self):
        raw=OUT/'licensed_source';p=json.loads((raw/'provenance.json').read_text())
        self.assertEqual(p['license'],'CC-BY-4.0');self.assertEqual(p['measured_rows'],1479)
        for e in p['files']:self.assertEqual(hashlib.sha256((raw/e['path']).read_bytes()).hexdigest(),e['sha256'])
    def test_06_actual_candidates_and_legacy_preserved(self):
        f=json.loads((OUT/'expanded_feature_summary.json').read_text());rows=list(csv.DictReader((OUT/'expanded_catalog.csv').open()))
        self.assertEqual(len(rows),497);self.assertEqual(len({r['canonical_id'] for r in rows}),497)
        self.assertEqual(sum(r['origin']=='existing479' for r in rows),479)
        self.assertEqual(sum(r['origin']=='licensed_notes_new' for r in rows),18)
        self.assertFalse(f['unlicensed_V217_notes_or_vectors_read'])
    def test_07_no_family_accord_inference(self):
        f=json.loads((OUT/'expanded_feature_summary.json').read_text())
        for r in f['new_items'].values():
            self.assertTrue(all(t.startswith('note:') for t in r['tokens']));self.assertGreater(r['known_tokens'],0)
    def test_08_actual_small_cohort_not_evaluated(self):
        e=json.loads((OUT/'evaluation_eligibility.json').read_text());d=json.loads((OUT/'recommendation_diagnostics.json').read_text())
        self.assertEqual(e['matched6plus_users'],1);self.assertEqual(d['track_B']['ndcg'],'NOT_EVALUATED')
        self.assertEqual(d['track_B']['actual_positive_hits'],'NOT_EVALUATED')
    def test_09_regression_track_A(self):
        d=json.loads((OUT/'recommendation_diagnostics.json').read_text())
        self.assertEqual(d['track_A']['users'],75);self.assertEqual(d['track_A']['positive_users'],69)
        self.assertEqual(d['trackA_max_score_delta'],0);self.assertTrue(d['trackA_exact_top5_parity'])
    def test_10_split_poisoned_answer_unread_by_scorer(self):
        class Poison:
            def __float__(self):raise AssertionError('Held-out rating read')
            def __lt__(self,other):raise AssertionError('Held-out rating compared')
            def __ge__(self,other):raise AssertionError('Held-out rating compared')
        h=[('id'+str(n),.7) for n in range(6)];s,a=label_blind_split(h,'test')
        answer_id=a[0][0];poisoned=[(i,Poison() if i==answer_id else y) for i,y in h]
        s2,a2=label_blind_split(poisoned,'test')
        m=ContentExperiment({i:{'note:rose':1} for i,y in h})
        self.assertEqual(m.score(s,h and [i for i,y in h]),m.score(s2,[i for i,y in h]))
    def test_11_no_fits_and_actual_input_exclusion(self):
        d=json.loads((OUT/'recommendation_diagnostics.json').read_text());demo=json.loads((OUT/'synthetic_input_demo.json').read_text())
        self.assertEqual(d['MF_fit_calls'],0);self.assertEqual(d['Content_fit_calls'],0)
        self.assertEqual(d['unlicensed_manufacturer_note_inferences'],0)
        self.assertFalse({i for i,y in demo['support']}&set(demo['result']['top']))
        self.assertEqual(len(demo['result']['top']),5);self.assertTrue(demo['same_input_exact'])

if __name__=='__main__':unittest.main()

class SourceIsolationTest(unittest.TestCase):
    def test_12_unlicensed_note_files_are_not_opened_by_catalog_builder(self):
        from unittest.mock import patch
        from deployment.final_v1.config import assets_path
        from perfume.data import fragrantica
        from experiments.scent_v2.expanded_content.catalog import build,ROOT
        from experiments.scent_v2.perfume_catalog_expansion.build import product_inventory
        import os
        source=os.environ.get('SCENT_V218_ORIGINAL_CSV')
        if not source:self.skipTest('Set original CSV for source-isolation postflight')
        payload=json.loads((assets_path()/'content.json').read_text());cat,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
        original_open=Path.open;opened=[]
        def guarded(path,*args,**kwargs):
            text=str(path);opened.append(text)
            if 'outputs/scent_v2/perfume_catalog_expansion/' in text and path.name!='perfume_identity_mapping.csv':
                raise AssertionError('Unlicensed V2-17 feature data opened')
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):
            vectors,new,mapping,review,provenance=build(payload['vectors'],payload['idf'],cat,product_inventory(Path(source)))
        self.assertEqual(len(new),18);self.assertEqual(len(vectors),497)
        self.assertFalse(any(p.endswith('research_vectors.json') or p.endswith('perfume_notes.csv') for p in opened))
