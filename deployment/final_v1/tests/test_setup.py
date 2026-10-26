"""Synthetic setup-only fixtures. Never load real catalog/Q or perform inference."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch, Mock
from deployment.final_v1 import config, manage, app

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.assets=self.root/'assets';self.assets.mkdir()
        self.source=self.root/'fixture.py';self.source.write_text('# invented fixture, not model code\n')
        entries=[]
        for name in sorted(config.PAYLOADS):
            p=self.assets/name;p.write_bytes(b'SYNTHETIC BYTES; NOT REAL JSON OR MODEL PARAMETERS')
            entries.append({'path':name,'bytes':p.stat().st_size,'sha256':config.sha256(p)})
        self.manifest={'schema':1,'source_freeze_sha256':config.SOURCE_FREEZE,'files':entries,'source_code_sha256':{'fixture.py':config.sha256(self.source)}}
        self.write_manifest()
    def tearDown(self):self.temp.cleanup()
    def write_manifest(self):
        self.m=self.assets/'manifest.json';self.m.write_text(json.dumps(self.manifest));self.pin=config.sha256(self.m)
    def inspect(self):return config.inspect_assets(self.assets,self.root,self.pin)
    def review(self,**edits):
        # Fake review record belongs ONLY to temporary unit fixtures; no real grant.
        record={'schema':1,'status':'VERIFIED','asset_manifest_sha256':config.MANIFEST_PIN,
                'review_reference':'SYNTHETIC UNIT TEST — NOT PERMISSION','reviewed_by':'fictional test reviewer',
                'evidence_references':['SYNTHETIC TEST ONLY'],'expires_on':'2030-01-01',
                'covered_payloads':sorted(config.PAYLOADS),'permitted_actions':['local_inference','classroom_demo']}
        record.update(edits);p=self.root/'fake-review.json';p.write_text(json.dumps(record));return p
    def test_hash_only_five_files(self):
        out=self.inspect();self.assertEqual(len(out['files']),5);self.assertEqual(out['inference_calls'],0)
        self.assertFalse(out['model_loaded']) # Invalid fake Q bytes were never decoded.
    def test_missing_manifest(self):
        self.m.unlink()
        with self.assertRaisesRegex(config.SetupError,'Missing'):self.inspect()
    def test_manifest_pin(self):
        with self.assertRaisesRegex(config.SetupError,'SHA256'):config.inspect_assets(self.assets,self.root,'0'*64)
    def test_missing_payload(self):
        (self.assets/'catalog.json').unlink()
        with self.assertRaisesRegex(config.SetupError,'catalog.json'):self.inspect()
    def test_payload_tamper(self):
        (self.assets/'content.json').write_bytes(b'changed')
        with self.assertRaisesRegex(config.SetupError,'mismatch'):self.inspect()
    def test_symlink_rejected(self):
        p=self.assets/'item_factors.npy';p.unlink();p.symlink_to(self.source)
        with self.assertRaisesRegex(config.SetupError,'nonregular'):self.inspect()
    def test_duplicate_or_path_traversal(self):
        self.manifest['files'][0]['path']='../escape.json';self.write_manifest()
        with self.assertRaisesRegex(config.SetupError,'four'):self.inspect()
    def test_provenance_rejected(self):
        self.manifest['source_freeze_sha256']='wrong';self.write_manifest()
        with self.assertRaisesRegex(config.SetupError,'provenance'):self.inspect()
    def test_source_changed(self):
        self.source.write_text('changed')
        with self.assertRaisesRegex(config.SetupError,'source'):self.inspect()
    def test_source_path_escape(self):
        self.manifest['source_code_sha256']={'../escape.py':'x'};self.write_manifest()
        with self.assertRaises(config.SetupError):self.inspect()
    def test_malformed_manifest(self):
        self.m.write_text('{bad');self.pin=config.sha256(self.m)
        with self.assertRaisesRegex(config.SetupError,'Malformed'):self.inspect()
    def test_relative_assets_root_not_cwd(self):
        with patch.dict('os.environ',{},clear=True):
            self.assertEqual(config.assets_path('assets',self.root),self.assets)
    def test_assets_environment(self):
        with patch.dict('os.environ',{'SCENT_MATCH_STANDALONE_ASSETS':'assets'}):
            self.assertEqual(config.assets_path(root=self.root),self.assets)
    def test_review_path_root_and_environment(self):
        with patch.dict('os.environ',{'SCENT_MATCH_FINAL_AUTHORIZATION':'review.json'}):
            self.assertEqual(config.authorization_path(root=self.root),self.root/'review.json')
            self.assertEqual(config.authorization_path('other.json',self.root),self.root/'other.json')
    def test_cross_platform_interpreter_selection(self):
        self.assertTrue(str(config.python_path(self.root,windows=True)).endswith('venv/Scripts/python.exe'))
        self.assertTrue(str(config.python_path(self.root,windows=False)).endswith('venv/bin/python'))
    def test_rights_missing(self):
        with self.assertRaisesRegex(config.SetupError,'HOLD'):config.authorization(None)
    def test_rights_example_hold(self):
        with self.assertRaises(config.SetupError):config.authorization(config.HERE/'authorization.example.json')
    def test_rights_expired_or_scope(self):
        for edits in [{'expires_on':'2020-01-01'},{'permitted_actions':['local_inference']},{'evidence_references':[]},{'covered_payloads':['catalog.json']},{'status':'HOLD'}]:
            with self.subTest(edits=edits),self.assertRaises(config.SetupError):
                config.authorization(self.review(**edits),'classroom_demo',date(2026,10,26))
    def test_rights_fixture_accepts(self):
        self.assertEqual(config.authorization(self.review(),'classroom_demo',date(2026,10,26))['purpose'],'classroom_demo')
    def test_no_import_before_permission(self):
        with patch.object(app,'authorization',side_effect=config.SetupError('HOLD')),patch.object(app.importlib,'import_module') as load:
            with self.assertRaises(config.SetupError):app.create_app()
            load.assert_not_called()
    def test_no_import_before_hash_check(self):
        with patch.object(app,'authorization'),patch.object(app,'inspect_assets',side_effect=config.SetupError('hash')),patch.object(app.importlib,'import_module') as load:
            with self.assertRaises(config.SetupError):app.create_app()
            load.assert_not_called()
    def test_exact_original_factory_delegation(self):
        sentinel=object();factory=Mock(return_value=sentinel);module=Mock(create_app=factory)
        with patch.object(app,'authorization'),patch.object(app,'inspect_assets'),patch.object(app.importlib,'import_module',return_value=module) as load,patch.object(app,'assets_path',return_value=self.assets):
            self.assertIs(app.create_app(),sentinel)
        load.assert_called_once_with('deployment.standalone_v1.app')
        factory.assert_called_once_with(directory=self.assets,expected_manifest_sha256=config.MANIFEST_PIN)
    def test_start_hold_no_child_processes(self):
        with patch.object(manage.subprocess,'Popen') as launch:
            with self.assertRaises(config.SetupError):manage.start(self.assets,None,'local_inference')
            launch.assert_not_called()
    def test_command_wiring_and_no_demo_fallback(self):
        backend,frontend,env=manage.plan(self.assets,self.root/'missing-review.json','classroom_demo')
        self.assertIn('deployment.final_v1.app:create_app',backend)
        self.assertIn('8004',backend);self.assertIn('5177',frontend)
        self.assertEqual(env['VITE_API_BASE_URL'],'http://127.0.0.1:8004')
        self.assertEqual(env['SCENT_MATCH_STANDALONE_MANIFEST_SHA256'],config.MANIFEST_PIN)
        self.assertFalse(any('demo.backend' in x for x in backend))
    def test_windows_npm_without_batch_shell(self):
        cli=self.root/'node_modules/npm/bin/npm-cli.js';cli.parent.mkdir(parents=True);cli.write_text('// synthetic npm CLI fixture')
        args=config.npm_argv(str(self.root/'npm.cmd'),str(self.root/'node.exe'),windows=True)
        self.assertEqual(args,[str(self.root/'node.exe'),str(cli)])
        self.assertNotIn('cmd.exe',args)
    def test_owned_children_stop_on_interrupt(self):
        import io,contextlib
        backend=Mock(pid=811001);frontend=Mock(pid=811002)
        for child in (backend,frontend):child.poll.return_value=None
        health=io.BytesIO(b'{"recommendation_ready":true,"candidate_count":479}')
        with patch.object(manage,'authorization'),patch.object(manage,'inspect_assets'),patch.object(manage,'tools'),patch.object(manage,'dependencies'),patch.object(manage,'check_ui'),patch.object(manage,'free_ports'),patch.object(manage.subprocess,'Popen',side_effect=[backend,frontend]) as spawn,patch('urllib.request.urlopen',return_value=health),patch.object(manage.time,'sleep',side_effect=KeyboardInterrupt),patch.object(manage.os,'killpg') as stop,contextlib.redirect_stdout(io.StringIO()):
            out=manage.start(self.assets,'fictional-review','local_inference')
        self.assertEqual(out['status'],'STOPPED')
        self.assertEqual(spawn.call_count,2)
        self.assertEqual({c.args[0] for c in stop.call_args_list},{811001,811002})

    def test_ui_copy_byte_check(self):
        source=self.root/'web/frontend';local=self.root/'local'
        for name in config.UI_FILES:
            a=source/name;b=local/'frontend'/name;a.parent.mkdir(parents=True,exist_ok=True);b.parent.mkdir(parents=True,exist_ok=True);a.write_text('fictional source');b.write_text('fictional source')
        self.assertEqual(config.check_ui(self.root,local)['identical_frontend_files'],len(config.UI_FILES))
        (local/'frontend/src/main.tsx').write_text('changed')
        with self.assertRaises(config.SetupError):config.check_ui(self.root,local)

if __name__=='__main__':unittest.main(verbosity=2)
