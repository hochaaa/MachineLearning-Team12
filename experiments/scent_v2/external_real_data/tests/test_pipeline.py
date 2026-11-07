"""All row fixtures here are artificial; they are NEVER acquired dataset records."""
import hashlib, json, math, os, tempfile, unittest
from pathlib import Path
from experiments.scent_v2.external_real_data.license_audit import require_permission, verified_file
from experiments.scent_v2.external_real_data.schema_inspection import validate, read_original
from experiments.scent_v2.external_real_data.perfume_matching import match, normalized
from experiments.scent_v2.external_real_data.rating_normalization import normalize_rating
from experiments.scent_v2.external_real_data.user_id_mapping import pseudonym
from experiments.scent_v2.external_real_data.deduplication import deduplicate
from experiments.scent_v2.external_real_data.dataset_builder import prepare, assemble
from experiments.scent_v2.external_real_data.quality_report import summarize
from experiments.scent_v2.synthetic_data.boundary import evaluation_users, safe_train
SECRET=b'TEST_FIXTURE_NOT_A_REAL_SECRET___'
CAT={'id1':dict(brand='Fixture',name='Example EDP'),'id2':dict(brand='Fixture',name='Example EDT')}
SCALE=dict(minimum=0, maximum=10, zero='valid', evidence='fixture_spec')
def evidence():
    return dict(source='fixture',status='APPROVED_LOCAL',download=True,academic_use=True,derivatives=True,
        privacy_review=True,upstream_terms=True,version='fixture_only',evidence_urls=['fixture_spec'],review_reference='TEST_ONLY')
def row(**kwargs):
    return dict(dict(user_id='fixture_person',item_id='external1',brand='Fixture',name='Example EDP',rating=8,
        explicit_rating=True,is_synthetic=False),**kwargs)

class PipelineTests(unittest.TestCase):
    def test_01_provenance_required(self):
        e=evidence();del e['version']
        with self.assertRaises(PermissionError):require_permission(e)
    def test_02_license_hold(self):
        e=evidence();e['status']='HOLD_LICENSE_UNCLEAR'
        with self.assertRaises(PermissionError):require_permission(e)
    def test_03_gate_before_file_open(self):
        with self.assertRaises(PermissionError):verified_file('/does/not/exist',{})
    def test_04_hash_and_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.csv';p.write_text('user_id,item_id,rating\na,b,5\n');e=evidence()
            e['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(len(read_original(p,e)),1)
            p.write_text('changed')
            with self.assertRaises(ValueError):verified_file(p,e)
    def test_05_schema(self):
        r=row();r.pop('brand')
        with self.assertRaises(ValueError):validate(r)
    def test_06_no_user(self):
        with self.assertRaises(ValueError):validate(row(user_id=''))
    def test_07_aggregate_not_explicit(self):
        with self.assertRaises(ValueError):validate(row(source_kind='aggregate'))
        with self.assertRaises(ValueError):validate(row(explicit_rating=False))
    def test_08_id_consistency(self):
        self.assertEqual(match(row(item_id='id1',id_system='fragrantica_url'),CAT)['item'],'id1')
        self.assertIsNone(match(row(item_id='id2',id_system='fragrantica_url'),CAT)['item'])
    def test_09_brand_name(self):
        self.assertEqual(match(row(brand='FIXTURE',name=' example   edp '),CAT)['item'],'id1')
    def test_10_concentration_collision(self):
        self.assertEqual(match(row(name='Example EDT'),CAT)['item'],'id2')
        self.assertIsNone(match(row(name='Example'),CAT)['item'])
        self.assertIsNone(match(row(name='Example Parfum'),CAT)['item'])
    def test_11_fuzzy_never_accepts(self):
        self.assertIsNone(match(row(name='Exampel EDP'),CAT)['item'])
    def test_12_scale(self):
        self.assertEqual(normalize_rating(1,dict(SCALE,minimum=1,maximum=5))['normalized_rating'],0)
        self.assertEqual(normalize_rating(5,dict(SCALE,minimum=1,maximum=5))['normalized_rating'],10)
        for v in (-1,11,True,float('nan'),float('inf')):
            with self.assertRaises(ValueError):normalize_rating(v,SCALE)
    def test_13_missing(self):
        self.assertIsNone(normalize_rating(None,SCALE));self.assertIsNone(normalize_rating('',SCALE))
    def test_14_zero_meaning(self):
        self.assertEqual(normalize_rating(0,SCALE)['normalized_rating'],0)
        self.assertIsNone(normalize_rating(0,dict(SCALE,zero='missing')))
        with self.assertRaises(ValueError):normalize_rating(0,dict(SCALE,zero='unknown'))
    def test_15_namespace_privacy(self):
        a=pseudonym('fixture','raw_person',SECRET)
        self.assertNotIn('raw_person',a);self.assertEqual(a,pseudonym('fixture','raw_person',SECRET))
        self.assertNotEqual(a,pseudonym('other','raw_person',SECRET))
    def test_16_dedup_conflicts(self):
        a=dict(source='fixture',user_id='u',perfume_id='id1',normalized_rating=8)
        b=dict(a,normalized_rating=4)
        accepted,audit,conflicts=deduplicate([a,a,b])
        self.assertEqual(accepted,[]);self.assertEqual(audit['exact_duplicates'],1);self.assertEqual(len(conflicts),2)
    def test_17_candidates_not_expanded(self):
        with self.assertRaises(ValueError):assemble([], [dict(user_id='u',perfume_id='outside')],CAT,set())
    def test_18_evaluation_skipped_before_decode(self):
        manifest='[{"users":["eval"],"answers":[{"forbidden":true}]}]'
        ids,audit=evaluation_users(manifest)
        rows,users,audit=safe_train('[["eval", {"forbidden":"item"}, {"forbidden":"rating"}], ["train","id1",0.8]]',ids)
        self.assertEqual(rows,[('train','id1',0.8)]);self.assertEqual(audit['numeric_ratings_decoded'],1)
        with self.assertRaises(ValueError):assemble([('eval','id1',0.8)],[],CAT,ids)
    def test_19_independent_and_protected_sources(self):
        with self.assertRaises(ValueError):validate(row(role='independent'))
        for source in ('basenotes','laure','atrafshan','v2-14'):
            with self.assertRaises(PermissionError):require_permission(dict(evidence(),source=source))
    def test_20_synthetic(self):
        with self.assertRaises(ValueError):validate(row(is_synthetic=True))
    def test_21_frozen19(self):
        root=Path.cwd();manifest=json.loads((root/'outputs/final/freeze.json').read_text())
        self.assertEqual(len(manifest['protected_sha256']),19)
        for p,digest in manifest['protected_sha256'].items():self.assertEqual(hashlib.sha256((root/p).read_bytes()).hexdigest(),digest)
    def test_22_original_data_unchanged(self):self.check_prefix('Term-project-datasets/')
    def test_23_service_unchanged(self):
        self.check_prefix('web/');self.check_prefix('deployment/')
    def test_24_previous_results_unchanged(self):
        before=self.snapshot()
        for p,h in before.items():
            if p.startswith('outputs/'):
                self.assertEqual(hashlib.sha256(Path(p).read_bytes()).hexdigest(),h,p)
    def snapshot(self):
        location=os.environ.get('SCENT_V215_BEFORE_SNAPSHOT')
        if not location: self.skipTest('Set SCENT_V215_BEFORE_SNAPSHOT for existing-file integrity checks')
        return json.loads(Path(location).read_text())
    def check_prefix(self,prefix):
        before=self.snapshot()
        matched=[p for p in before if p.startswith(prefix)];self.assertTrue(matched)
        for p in matched:self.assertEqual(hashlib.sha256(Path(p).read_bytes()).hexdigest(),before[p],p)
    def test_25_variant_metadata(self):
        for k in ('year','gender','edition','concentration'):
            self.assertIsNone(match(row(**{k:'unverified'}),CAT)['item'])
        c=dict(CAT);c['collision']=dict(CAT['id1'])
        self.assertIsNone(match(row(),c)['item'])
    def test_26_cross_source_unknown_quarantined(self):
        ext=[dict(user_id='external_fixture_u',perfume_id='id1',normalized_rating=8,source='fixture')]
        result,audit=assemble([('legacy','id2',0.8)],ext,CAT,set())
        self.assertEqual(len(result),1);self.assertEqual(audit['external_quarantined'],1)
    def test_27_pipeline_minimizes_identity(self):
        prepared,audit,conflicts=prepare([row()],evidence(),SCALE,CAT,SECRET)
        self.assertEqual(len(prepared),1);self.assertNotIn('fixture_person',json.dumps(prepared))
        self.assertNotIn('brand',prepared[0]);self.assertEqual(prepared[0]['raw_rating'],8)
        class ForbiddenRows:
            def __iter__(self):raise AssertionError('Should not inspect records')
        with self.assertRaises(PermissionError):prepare(ForbiddenRows(),{},SCALE,CAT,SECRET)
    def test_28_quality_and_no_rows(self):
        self.assertEqual(summarize([],CAT)['status'],'NOT_MEASURED_NO_ACQUIRED_DATA')
        rows=[dict(user_id='a',perfume_id='id1',normalized_rating=8),dict(user_id='b',perfume_id='id1',normalized_rating=4)]
        q=summarize(rows,CAT,{'id2':1})
        self.assertEqual(q['components'],1);self.assertEqual(q['user_pairs_with_shared_item'],1)
        self.assertEqual(q['density'],0.5);self.assertEqual(q['unobserved_candidates'],1)
    def test_29_duplicate_timelines_quarantined(self):
        a=dict(source='fixture',user_id='u',perfume_id='id1',normalized_rating=8,rating_timestamp='2020-01-01')
        b=dict(a,rating_timestamp='2021-01-01')
        self.assertEqual(len(deduplicate([a,b])[2]),2)
        result,audit,conflicts=prepare([row(rating_timestamp='2020-01-01'),row(rating_timestamp='2021-01-01')],evidence(),SCALE,CAT,SECRET)
        self.assertEqual(result,[]);self.assertEqual(len(conflicts),2)
    def test_30_unicode_version(self):
        self.assertEqual(normalized('Café'),normalized('Cafe\u0301'))
        self.assertNotEqual(normalized('Example Elixir 2020'),normalized('Example EDP 2021'))

if __name__=='__main__':unittest.main()
