"""Verify mathematical transform and source attribution; never train or rank."""
import csv,json,math,os,unittest
from pathlib import Path
from experiments.scent_v2.perfume_catalog_expansion.compatibility import feature_tokens,transform,coverage
from experiments.scent_v2.perfume_catalog_expansion.build import OUT,product_inventory

class TransformTests(unittest.TestCase):
    def test_01_separate_channels(self):self.assertEqual(feature_tokens(['Woody'],['Woody']),{'note:woody','accord:woody'})
    def test_02_original_normalization(self):self.assertEqual(feature_tokens(['Café','Cafe\u0301'],[]),{'note:cafe'})
    def test_03_no_synonym_guess(self):self.assertEqual(transform(feature_tokens(['Musks'],[]),{'note:musk':2}),{})
    def test_04_no_accord_inference(self):self.assertEqual(feature_tokens(['Rose'],[]),{'note:rose'})
    def test_05_literal_accord_name(self):self.assertEqual(feature_tokens([],['Marine accord']),{'accord:marine accord'})
    def test_06_binary_tf(self):self.assertEqual(transform(['note:a','note:a'],{'note:a':2}),{'note:a':1})
    def test_07_l2_equation(self):
        idf={'note:a':3,'accord:b':4};old=idf.copy();v=transform(idf,idf)
        self.assertEqual(v,{'note:a':.6,'accord:b':.8});self.assertEqual(idf,old)
    def test_08_missing_and_oov(self):
        self.assertEqual(feature_tokens(['','unknown','nan','na'],[]),set())
        self.assertIsNone(coverage(set(),{})['note']['known_fraction'])
        self.assertEqual(transform(['note:new'],{}),{})
    def test_09_invalid_idf(self):
        for v in (-1,0,float('nan'),float('inf')):
            with self.assertRaises(ValueError):transform(['note:a'],{'note:a':v})

class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identities=list(csv.DictReader((OUT/'perfume_identity_mapping.csv').open()))
        cls.metadata=list(csv.DictReader((OUT/'perfume_metadata_research.csv').open()))
        cls.notes=list(csv.DictReader((OUT/'perfume_notes.csv').open()))
        cls.accords=list(csv.DictReader((OUT/'perfume_accords.csv').open()))
        cls.sources={r['url'] for r in csv.DictReader((OUT/'source_registry.csv').open())}
        cls.compat=json.loads((OUT/'feature_compatibility.json').read_text())
    def test_10_full_inventory(self):
        self.assertEqual(len(self.identities),58);self.assertEqual(len({r['source_product_id'] for r in self.identities}),58)
        source=os.environ.get('SCENT_V217_ORIGINAL_CSV')
        if source:self.assertEqual({r[0] for r in product_inventory(Path(source))},{r['source_product_id'] for r in self.identities})
    def test_11_source_date_required(self):
        for r in self.notes+self.accords:
            self.assertIn(r['source_url'],self.sources);self.assertEqual(r['checked_date'],'2026-10-30')
            self.assertTrue(r['source_url'].startswith('https://'))
    def test_12_no_inferred_pyramid(self):
        dip_ids={r['source_product_id'] for r in self.identities if r['original_brand']=='Diptyque'}
        self.assertTrue(all(r['layer']=='unspecified' for r in self.notes if r['source_product_id'] in dip_ids))
    def test_13_no_ingredient_or_description_dump(self):
        self.assertTrue(all(r['source_type']=='manufacturer_declared_note' for r in self.notes))
        self.assertTrue(all(r['descriptors_used_as_accords']=='False' for r in self.metadata))
    def test_14_status_accounting(self):
        q=self.compat['quality_counts'];self.assertEqual(sum(q.values()),58)
        self.assertEqual(q,dict(VERIFIED=6,PARTIALLY_VERIFIED=40,NEEDS_REVIEW=11,UNRESOLVED=1))
    def test_15_ambiguous_not_transformed(self):
        for r in self.compat['per_product']:
            if not r['identity_verified']:self.assertFalse(r['metadata_assessed'])
    def test_16_never_merge_concentrations(self):
        def pick(name):return next(r for r in self.identities if r['original_product_name']==name)
        self.assertNotEqual(pick('Tam Dao · EDT')['reference_url'],pick('Tam Dao · EDP')['reference_url'])
        self.assertNotEqual(pick('Mojave Ghost · EDP')['reference_url'],pick('Mojave Ghost · Absolu de Parfum')['reference_url'])
    def test_17_vector_scope(self):
        c=self.compat
        self.assertEqual((c['representable_nonzero'],c['confirmed_zero_vectors'],c['not_assessed']),(45,1,12))
        self.assertEqual(c['frozen_idf_vocabulary'],604);self.assertEqual(c['active_existing479_features'],574)
        self.assertTrue(c['not_assessed_is_not_zero'])
    def test_18_normalized_vectors(self):
        vectors=json.loads((OUT/'research_vectors.json').read_text())
        self.assertEqual(len(vectors),46)
        for v in vectors.values():
            if v:self.assertAlmostEqual(sum(n*n for n in v.values()),1)
    def test_19_no_production_or_models(self):
        for key in ('production_catalog_expanded','MF_factors_created'):self.assertFalse(self.compat[key])
        for key in ('model_fits','recommendations','evaluations'):self.assertEqual(self.compat[key],0)
    def test_20_product_only_fields(self):
        for name in ('perfume_identity_mapping.csv','perfume_metadata_research.csv','perfume_notes.csv','perfume_accords.csv'):
            columns=next(csv.reader((OUT/name).open()))
            self.assertFalse({'participant_id','user_id','score','rating','created_at','updated_at'}&set(columns))

if __name__=='__main__':unittest.main()
