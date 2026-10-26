"""Setup unit fixtures. Live inference is tested separately without training."""
import json
import tempfile
import unittest
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
    def test_cross_platform_interpreter_selection(self):
        self.assertTrue(str(config.python_path(self.root,windows=True)).endswith('venv/Scripts/python.exe'))
        self.assertTrue(str(config.python_path(self.root,windows=False)).endswith('venv/bin/python'))
    def test_no_import_before_hash_check(self):
        with patch.object(app,'inspect_assets',side_effect=config.SetupError('hash')),patch.object(app.importlib,'import_module') as load:
            with self.assertRaises(config.SetupError):app.create_app()
            load.assert_not_called()
    def test_exact_original_factory_delegation(self):
        sentinel=object();factory=Mock(return_value=sentinel);module=Mock(create_app=factory)
        with patch.object(app,'inspect_assets'),patch.object(app.importlib,'import_module',return_value=module) as load,patch.object(app,'assets_path',return_value=self.assets):
            self.assertIs(app.create_app(),sentinel)
        load.assert_called_once_with('deployment.standalone_v1.app')
        factory.assert_called_once_with(directory=self.assets,expected_manifest_sha256=config.MANIFEST_PIN)
    def test_command_wiring_and_no_demo_fallback(self):
        backend,frontend,env=manage.plan(self.assets)
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
        with patch.object(manage,'inspect_assets'),patch.object(manage,'tools'),patch.object(manage,'dependencies'),patch.object(manage,'check_ui'),patch.object(manage,'free_ports'),patch.object(manage.subprocess,'Popen',side_effect=[backend,frontend]) as spawn,patch('urllib.request.urlopen',return_value=health),patch.object(manage.time,'sleep',side_effect=KeyboardInterrupt),patch.object(manage.os,'killpg') as stop,contextlib.redirect_stdout(io.StringIO()):
            out=manage.start(self.assets)
        self.assertEqual(out['status'],'STOPPED')
        self.assertEqual(spawn.call_count,2)
        self.assertEqual({c.args[0] for c in stop.call_args_list},{811001,811002})

    def test_authorization_functions_removed(self):
        self.assertFalse(hasattr(config,'authorization'))
        self.assertFalse(hasattr(config,'authorization_path'))
    def test_old_environment_does_not_gate_or_propagate(self):
        with patch.dict('os.environ',{'SCENT_MATCH_FINAL_AUTHORIZATION':'missing.json','SCENT_MATCH_FINAL_PURPOSE':'HOLD'}):
            _,_,env=manage.plan(self.assets)
        self.assertNotIn('SCENT_MATCH_FINAL_AUTHORIZATION',env)
        self.assertNotIn('SCENT_MATCH_FINAL_PURPOSE',env)
    def test_check_passes_without_review_json(self):
        import contextlib,io
        output=io.StringIO()
        with patch.object(manage,'tools',return_value={}),patch.object(manage,'dependencies',return_value={'status':'PASS'}),patch.object(manage,'check_ui',return_value={'status':'PASS'}),patch.object(manage,'inspect_assets',return_value={'status':'PASS'}),contextlib.redirect_stdout(output):
            code=manage.main(['check'])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['status'],'PASS')
        self.assertNotIn('rights',json.loads(output.getvalue()))
    def test_removed_cli_option_rejected(self):
        import contextlib,io
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as exc:
            manage.main(['start','--authorization','not-used.json'])
        self.assertEqual(exc.exception.code,2)
    def test_missing_assets_still_prevent_start(self):
        with patch.object(manage.subprocess,'Popen') as launch:
            with self.assertRaises(config.SetupError):manage.start(self.root/'absent')
        launch.assert_not_called()
    def test_unready_backend_never_launches_frontend(self):
        import io
        backend=Mock(pid=811003);backend.poll.return_value=None
        health=io.BytesIO(b'{"recommendation_ready":false,"candidate_count":0}')
        with patch.object(manage,'inspect_assets'),patch.object(manage,'tools'),patch.object(manage,'dependencies'),patch.object(manage,'check_ui'),patch.object(manage,'free_ports'),patch.object(manage.subprocess,'Popen',return_value=backend) as spawn,patch('urllib.request.urlopen',return_value=health),patch.object(manage.os,'killpg') as stop:
            with self.assertRaisesRegex(config.SetupError,'not ready'):manage.start(self.assets)
        self.assertEqual(spawn.call_count,1);stop.assert_called_once()

    def test_ui_copy_byte_check(self):
        source=self.root/'web/frontend';local=self.root/'local'
        for name in config.UI_FILES:
            a=source/name;b=local/'frontend'/name;a.parent.mkdir(parents=True,exist_ok=True);b.parent.mkdir(parents=True,exist_ok=True);a.write_text('fictional source');b.write_text('fictional source')
        self.assertEqual(config.check_ui(self.root,local)['identical_frontend_files'],len(config.UI_FILES))
        (local/'frontend/src/main.tsx').write_text('changed')
        with self.assertRaises(config.SetupError):config.check_ui(self.root,local)

if __name__=='__main__':unittest.main(verbosity=2)
