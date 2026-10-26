"""Cross-platform opt-in setup. Installs source only; never downloads runtime assets."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import signal
import subprocess
import sys
import time
import venv

# Direct script entry works without importing any model code.
if __package__ in (None, ''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from deployment.final_v1.config import (ROOT,HERE,LOCAL,UI_FILES,MANIFEST_PIN,SetupError,
    assets_path,inspect_assets,tools,python_path,check_ui,npm_argv)


def install():
    """Prepare isolated venv/UI copy under new .local; preserve source/assets."""
    versions=tools()
    LOCAL.mkdir(exist_ok=True)
    for name in UI_FILES:
        source=ROOT/'web/frontend'/name; target=LOCAL/'frontend'/name
        if target.exists() and target.read_bytes()!=source.read_bytes():
            raise SetupError('Local frontend copy differs. Review it; installer will not overwrite it.')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(source,target)
    py=python_path()
    if not py.is_file():venv.EnvBuilder(with_pip=True).create(LOCAL/'venv')
    subprocess.run([str(py),'-m','pip','install','-r',str(ROOT/'web/backend/requirements-lock.txt')],check=True)
    subprocess.run([str(py),'-m','pip','check'],check=True)
    npm=npm_argv()
    subprocess.run(npm+['ci','--ignore-scripts','--no-audit','--no-fund'],cwd=LOCAL/'frontend',check=True)
    subprocess.run(npm+['run','build'],cwd=LOCAL/'frontend',env={**os.environ,'VITE_API_BASE_URL':'http://127.0.0.1:8004'},check=True)
    return {'status':'SOURCE_INSTALL_PASS','versions':versions,'ui':check_ui(),
            'runtime_assets_downloaded':False,'real_inference_started':False,'usage_rights':'Not assessed or granted by this installer'}


def dependencies():
    """Verify imports in isolated interpreter; imports only, no old loader or models."""
    py=python_path()
    if not py.is_file() or not (LOCAL/'frontend/node_modules/vite/bin/vite.js').is_file():
        raise SetupError('Dependencies missing. Run install first; never copy another computer\'s venv.')
    subprocess.run([str(py),'-B','-c','import fastapi,uvicorn,numpy,pydantic'],check=True)
    subprocess.run([str(py),'-m','pip','check'],check=True,stdout=subprocess.DEVNULL)
    return {'status':'PASS'}


def plan(asset_dir):
    """Return exact unchanged UI / original app wiring; no process launch."""
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',
         'SCENT_MATCH_STANDALONE_ASSETS':str(asset_dir),
         'SCENT_MATCH_STANDALONE_MANIFEST_SHA256':MANIFEST_PIN,
         'WEB_CORS_ORIGINS':'http://127.0.0.1:5177', 'VITE_API_BASE_URL':'http://127.0.0.1:8004'}
    # Obsolete review variables cannot affect the local execution path.
    env.pop('SCENT_MATCH_FINAL_AUTHORIZATION',None)
    env.pop('SCENT_MATCH_FINAL_PURPOSE',None)
    backend=[str(python_path()),'-B','-m','uvicorn','deployment.final_v1.app:create_app','--factory','--host','127.0.0.1','--port','8004','--no-access-log']
    frontend=npm_argv()+['run','dev','--','--host','127.0.0.1','--port','5177','--strictPort']
    return backend,frontend,env


def free_ports():
    """Check our two loopback ports, never stop another process."""
    for port in (8004,5177):
        with socket.socket() as s:
            try:s.bind(('127.0.0.1',port))
            except OSError as exc:raise SetupError(f'Port {port} unavailable. Do not kill unrelated servers.') from exc


def start(asset_dir):
    """Verify immutable assets, dependencies, UI and ports; start both services."""
    inspect_assets(asset_dir)
    tools();dependencies();check_ui();free_ports()
    backend,frontend,env=plan(asset_dir)
    processes=[]
    try:
        processes.append(subprocess.Popen(backend,cwd=ROOT,env=env,start_new_session=os.name!='nt'))
        # Wait for backend readiness; never silently run UI against another service.
        import urllib.request
        for _ in range(60):
            if processes[0].poll() is not None:raise SetupError('Backend startup failed. Inspect local assets/dependencies; no Demo fallback.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8004/api/health',timeout=.5) as response:health=json.load(response)
            except (OSError,ValueError):
                time.sleep(.2)
                continue
            if not health.get('recommendation_ready') or health.get('candidate_count')!=479:
                raise SetupError('Frozen V1 backend not ready; check runtime files. No Demo fallback.')
            break
        else:raise SetupError('Backend readiness timeout.')
        processes.append(subprocess.Popen(frontend,cwd=LOCAL/'frontend',env=env,start_new_session=os.name!='nt'))
        print('Frozen V1 local execution: http://127.0.0.1:5177/ ; Ctrl+C stops only launched child processes.',flush=True)
        while all(p.poll() is None for p in processes):time.sleep(.25)
        raise SetupError('A server stopped. Restart after checking its error; no automatic model replacement.')
    except KeyboardInterrupt:
        return {'status':'STOPPED','owned_children_only':True}
    finally:
        for child in reversed(processes):
            if os.name=='nt':
                if child.poll() is None:
                    subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                # Each child got its own session; stop only the group we created.
                try:os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError:pass
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name=='nt':child.kill()
                else:
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                child.wait()



def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','check','start'])
    parser.add_argument('--assets')
    args=parser.parse_args(argv)
    try:
        if args.action=='install':result=install()
        elif args.action=='start':
            result=start(assets_path(args.assets))
        else:
            result={'model_loaded':False,'inference_calls':0}
            for name,check in [('tools',tools),('dependencies',dependencies),('frontend',check_ui),('runtime',lambda:inspect_assets(assets_path(args.assets)))]:
                try:result[name]=check()
                except (OSError,ValueError,subprocess.SubprocessError) as exc:result[name]={'status':'ERROR','detail':str(exc) if isinstance(exc,SetupError) else 'Dependency or file check failed.'}
            result['status']='PASS' if all(result[k].get('status') not in ('ERROR',) for k in ('tools','dependencies','frontend','runtime')) else 'ERROR'
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 2 if result.get('status')=='ERROR' else 0
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'ERROR','detail':str(exc) if isinstance(exc,SetupError) else 'Setup/dependency failure; inspect local installer output.','real_inference_started':False},ensure_ascii=False))
        return 2
if __name__=='__main__':raise SystemExit(main())
