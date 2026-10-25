"""Minimal launcher safety tests. Does not kill or replace real project services."""
import json
import logging
import os
from pathlib import Path
import signal
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from . import manager as m


class LauncherTests(unittest.TestCase):
    def info(self):
        return {'uid':os.getuid(),'started':'Fri Oct 23 17:00:00 2026','cwd':m.norm(m.ROOT),
                'command':m.norm(str(m.PYTHON))+' -B -m uvicorn web.backend.app:app --host 127.0.0.1 --port 8000 --no-access-log'}

    def test_identity_parser(self):
        sample=f'{os.getuid()} Fri Oct 23 17:00:00 2026 {self.info()["command"]}'
        with patch.object(m,'capture',side_effect=[sample,'p123\nfcwd\nn'+str(m.ROOT)]):
            self.assertEqual(m.identity(123),self.info())

    def test_project_uid_path_module_port_checks(self):
        info=self.info();self.assertTrue(m.project_process(info,'backend',8000))
        for changes in [{'uid':os.getuid()+1},{'cwd':'/private/tmp'},
                        {'command':info['command'].replace('8000','80001')},
                        {'command':'python -m http.server 8000'}]:
            self.assertFalse(m.project_process({**info,**changes},'backend',8000))

    def test_existing_frontend_command(self):
        info={**self.info(),'command':'node '+m.norm(m.FRONTEND)+'/node_modules/.bin/vite --host 127.0.0.1'}
        self.assertTrue(m.project_process(info,'frontend',5173))
        self.assertFalse(m.project_process({**info,'cwd':'/private/tmp'},'frontend',5173))

    def state(self,path):
        m.save_state(path,[{'pid':12345,'role':'backend','port':8000,'identity':self.info()}])

    def test_no_state_never_signals(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m.os,'kill') as kill:
            self.assertTrue(m.stop_owned(Path(d)/'owned.json',logging.getLogger('test')))
            kill.assert_not_called()

    def test_mismatched_pid_never_signals(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m.os,'kill') as kill:
            p=Path(d)/'owned.json';self.state(p)
            with patch.object(m,'identity',return_value={**self.info(),'started':'different process'}):
                self.assertFalse(m.stop_owned(p,logging.getLogger('test')))
            kill.assert_not_called();self.assertTrue(p.exists())

    def test_dead_pid_cleans_only_ownership_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'owned.json';self.state(p)
            with patch.object(m,'identity',return_value=None),patch.object(m.os,'kill',side_effect=ProcessLookupError) as kill:
                self.assertTrue(m.stop_owned(p,logging.getLogger('test')))
                kill.assert_called_once_with(12345,0)
            self.assertFalse(p.exists())

    def test_owned_matching_identity_only_sigterm(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'owned.json';self.state(p)
            with patch.object(m,'identity',return_value=self.info()),patch.object(m,'listener',return_value=None),patch.object(m.os,'kill') as kill:
                self.assertTrue(m.stop_owned(p,logging.getLogger('test')))
                kill.assert_called_once_with(12345,signal.SIGTERM)
            self.assertFalse(p.exists())

    def test_multiple_listeners_stop_without_adoption(self):
        with patch.object(m,'capture',return_value='123\n456'):
            with self.assertRaises(m.DemoError):m.listener(8000)

    def test_reachable_port_without_visible_pid_is_not_free(self):
        with patch.object(m,'capture',return_value=''),patch.object(m.socket,'create_connection') as connect:
            with self.assertRaises(m.DemoError):m.listener(8000)
            connect.return_value.close.assert_called_once()

    def test_unknown_port_owner_aborts_without_spawn_or_signal(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,'verify_frozen',return_value=True),\
             patch.object(m,'runtimes',return_value=(Path('/usr/bin/node'),Path('/usr/bin/npm'))),\
             patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='10.8.2')),\
             patch.object(m,'capture',return_value='v20.20.0'),patch.object(m,'listener',return_value=999),\
             patch.object(m,'identity',return_value={**self.info(),'cwd':'/private/tmp'}),\
             patch.object(m.subprocess,'Popen') as spawn,patch.object(m.os,'kill') as kill:
            with self.assertRaises(m.DemoError):
                m.start(SimpleNamespace(backend_port=8000,frontend_port=5173,no_browser=True),Path(d)/'owned.json',logging.getLogger('test'))
            spawn.assert_not_called();kill.assert_not_called()

    def test_browser_target_is_only_fixed_loopback(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,'verify_frozen',return_value=True),\
             patch.object(m,'runtimes',return_value=(Path('/usr/bin/node'),Path('/usr/bin/npm'))),\
             patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='10.8.2')) as run,\
             patch.object(m,'capture',return_value='v20.20.0'),patch.object(m,'listener',return_value=123),\
             patch.object(m,'project_process',return_value=True),patch.object(m,'ready',return_value=True):
            m.start(SimpleNamespace(backend_port=8000,frontend_port=5173,no_browser=False),Path(d)/'owned.json',logging.getLogger('test'))
            self.assertEqual(run.call_args.args[0],['/usr/bin/open','http://127.0.0.1:5173/'])


if __name__=='__main__':unittest.main(verbosity=2)
