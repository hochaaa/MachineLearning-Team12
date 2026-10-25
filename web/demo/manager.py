"""macOS local launcher: verify/reuse existing services; stop only owned identities.

Only stdlib and installed runtimes. No pip/npm install, network configuration,
external HTTP, training or evaluation. Public docs are explained in METHODS_EXPLAINED.
"""
import argparse
import fcntl
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import unicodedata
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT/'web/demo'
PYTHON = ROOT/'web/backend/.venv/bin/python'
FRONTEND = ROOT/'web/frontend'


class DemoError(Exception):
    """Fixed, non-sensitive operator instruction; never log exception payloads."""


def norm(value):
    """value: path/command text. Normalize macOS composed/decomposed Korean."""
    return unicodedata.normalize('NFC', str(value))


def capture(command):
    """command: trusted argv; short read-only process/runtime query, no shell."""
    result = subprocess.run(command, capture_output=True, text=True, timeout=8)
    return result.stdout.strip() if result.returncode == 0 else ''


def identity(pid):
    """pid: integer. Return uid/start/command/cwd; None if dead or unverifiable."""
    try:
        fields = capture(['/bin/ps','-p',str(int(pid)),'-o','uid=,lstart=,command=']).split(None,6)
        if len(fields) != 7:
            return None
        cwd_lines = capture(['/usr/sbin/lsof','-a','-p',str(int(pid)),'-d','cwd','-Fn']).splitlines()
        cwd = next((line[1:] for line in cwd_lines if line.startswith('n')), '')
        if not cwd:
            return None
        return {'uid':int(fields[0]), 'started':' '.join(fields[1:6]),
                'command':norm(fields[6]), 'cwd':norm(Path(cwd).resolve())}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def project_process(info, role, port):
    """Require same uid, exact project cwd and expected executable/module/port."""
    if not info or info['uid'] != os.getuid():
        return False
    command = info['command']
    if info['cwd'] not in (norm(ROOT), norm(FRONTEND)):
        return False
    if role == 'backend':
        return (info['cwd'] == norm(ROOT) and 'web.backend.app:app' in command
                and 'uvicorn' in command and re.search(r'--port\s+'+str(port)+r'(?:\s|$)',command) is not None
                and '--host 127.0.0.1' in command
                and ('web/backend/.venv/bin/python' in command))
    # Existing npm dev starts this project's Vite CLI; do not adopt a generic Node server.
    return (norm(FRONTEND) in command
            and any(v in command for v in ('/node_modules/.bin/vite','/node_modules/vite/bin/vite.js')) and 'node' in command
            and ('--host 127.0.0.1' in command))


def listener(port):
    """port: loopback service port. Multiple/unknown listeners are unsafe to adopt."""
    text = capture(['/usr/sbin/lsof','-nP','-t',f'-iTCP:{port}','-sTCP:LISTEN'])
    pids = set(text.split())
    if len(pids) > 1:
        raise DemoError(f'포트 {port}: 여러 프로세스가 점유합니다. 종료하지 않고 중단합니다.')
    if not pids:
        # lsof may be unable to reveal another owner's PID. A reachable port is
        # never treated as free merely because process metadata was unavailable.
        try:
            connection=socket.create_connection(('127.0.0.1',port),timeout=.3)
        except ConnectionRefusedError:
            pass
        except OSError:
            raise DemoError(f'포트 {port}의 점유 여부를 확인할 수 없어 중단합니다.') from None
        else:
            connection.close()
            raise DemoError(f'포트 {port}는 응답하지만 소유 PID를 확인할 수 없습니다. 종료하지 않고 중단합니다.')
    return int(next(iter(pids))) if pids else None


def get_local(url):
    """url: fixed loopback address. Ignore system HTTP proxies and reject redirects."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=3) as response:
        return response.status, response.read(2*1024*1024)


def ready(role, port):
    """Validate health479 or SCENT MATCH page; false on any transport/schema error."""
    try:
        code, body = get_local(f'http://127.0.0.1:{port}/api/health' if role=='backend' else f'http://127.0.0.1:{port}/')
        if role == 'frontend':
            return code == 200 and b'SCENT MATCH' in body and b'/src/main.tsx' in body
        data = json.loads(body)
        return code == 200 and data.get('model_loaded') is True and data.get('recommendation_ready') is True and data.get('candidate_count') == 479
    except Exception:
        return False


def verify_frozen():
    """Check original protected19 plus manifest against preserved pre-demo snapshot."""
    manifest = ROOT/'outputs/final/freeze.json'
    snapshot = ROOT/'web/evidence/final-demo/before.json'
    try:
        freeze = json.loads(manifest.read_text())
        before = json.loads(snapshot.read_text())
        paths = {**freeze['protected_sha256'], 'outputs/final/freeze.json':before['outputs/final/freeze.json']}
        if len(freeze['protected_sha256']) != 19:
            raise ValueError
        for relative, expected in paths.items():
            path = ROOT/relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != expected or digest != before[relative]:
                raise ValueError
    except Exception:
        raise DemoError('동결 필수 파일 누락/해시 불일치입니다. 원본을 확인하세요. 재동결하거나 검증을 끄지 마세요.') from None
    return True


def runtimes():
    """Find installed Node/npm via PATH, local hints or standard macOS locations."""
    hints_path = HERE/'runtime.local.json'
    try:
        hints = json.loads(hints_path.read_text()) if hints_path.exists() else {}
    except ValueError:
        hints = {}
    def find(name):
        options = [hints.get(name), shutil.which(name), str(Path.home()/'.volta/bin'/name),
                   '/opt/homebrew/bin/'+name, '/usr/local/bin/'+name]
        return next((Path(p) for p in options if p and Path(p).is_file() and os.access(p,os.X_OK)), None)
    node, npm = find('node'), find('npm')
    if not PYTHON.is_file() or not os.access(PYTHON, os.X_OK):
        raise DemoError('기존 Python 가상환경이 없습니다. 발표 전에 환경을 복구하세요. 자동 설치하지 않습니다.')
    if not node or not npm or not (FRONTEND/'node_modules/vite/bin/vite.js').is_file():
        raise DemoError('Node/npm 또는 기존 node_modules가 없습니다. 발표 전 준비된 환경을 확인하세요. 자동 설치하지 않습니다.')
    # Volta is a shim that can spawn a separate Node child. Launch the existing
    # real binary so the Popen PID is also the listening PID and can be verified.
    actual = capture([str(node),'-p','process.execPath'])
    if not actual or not Path(actual).is_file() or not os.access(actual,os.X_OK):
        raise DemoError('실제 Node 실행 파일을 확인할 수 없습니다. 강제 종료 없이 중단합니다.')
    node = Path(actual)
    return node, npm


def save_state(path, records):
    """path: private state JSON; records: owned processes only. Atomic local replace."""
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'root':norm(ROOT), 'owned':records}, ensure_ascii=False, indent=2))
    temporary.replace(path)


def stop_owned(path, log):
    """Recheck uid/start/command/cwd before SIGTERM; never kill mismatched/stale PID."""
    if not path.exists():
        print('발표 실행기가 시작한 서버가 없습니다. 기존 서버는 유지합니다.')
        return True
    try:
        state = json.loads(path.read_text())
        if state['root'] != norm(ROOT) or not isinstance(state['owned'], list):
            raise ValueError
    except (ValueError, KeyError):
        raise DemoError('실행 상태를 확인할 수 없습니다. 어떤 프로세스도 종료하지 않았습니다.') from None
    remaining=[]
    for record in reversed(state['owned']):
        current = identity(record['pid'])
        if current is None:
            # Distinguish dead process from insufficient observation permissions.
            try:
                os.kill(record['pid'],0)
            except ProcessLookupError:
                log.info('Owned process already exited: %s',record['role']); continue
            except PermissionError:
                pass
            remaining.append(record); log.warning('Stop blocked: process identity unavailable'); continue
        if current != record['identity'] or not project_process(current,record['role'],record['port']):
            remaining.append(record); log.warning('Stop blocked: process identity mismatch'); continue
        # Recheck immediately before signalling; PID metadata is never trusted alone.
        if identity(record['pid']) != current:
            remaining.append(record); continue
        os.kill(record['pid'],signal.SIGTERM)
        for _ in range(50):
            if listener(record['port']) != record['pid']:
                break
            time.sleep(.1)
        if listener(record['port']) == record['pid']:
            remaining.append(record); log.warning('Graceful stop pending; no forced kill')
        else:
            log.info('Owned %s stopped',record['role'])
    if remaining:
        save_state(path,list(reversed(remaining)))
        print('일부 서버의 신원을 확인할 수 없거나 종료 대기 중입니다. 강제 종료하지 않았습니다.')
        return False
    path.unlink(missing_ok=True)
    print('발표 실행기가 시작한 서버만 종료했습니다. 재사용한 기존 서버는 유지합니다.')
    return True


def start(args, state_path, log):
    """args: ports/no-browser; reuse verified project services, spawn only free ports."""
    verify_frozen(); node,npm = runtimes()
    env = os.environ.copy()
    env['PATH'] = str(node.parent)+os.pathsep+env.get('PATH','')
    env.update(PYTHONDONTWRITEBYTECODE='1', VITE_API_BASE_URL='',
               WEB_CORS_ORIGINS=f'http://127.0.0.1:{args.frontend_port},http://localhost:{args.frontend_port}',
               SCENT_DEMO_FRONT_PORT=str(args.frontend_port), SCENT_DEMO_BACK_PORT=str(args.backend_port),
               npm_config_offline='true', npm_config_update_notifier='false')
    versions = subprocess.run([str(npm),'--version'], env=env, capture_output=True,text=True,timeout=10)
    if versions.returncode:
        raise DemoError('기존 npm을 실행할 수 없습니다. PATH/Node 설치를 확인하세요.')
    log.info('Python %s; Node %s; npm %s',sys.version.split()[0],capture([str(node),'--version']),versions.stdout.strip())
    records=[]
    if state_path.exists():
        old=json.loads(state_path.read_text())
        if old.get('root') != norm(ROOT):
            raise DemoError('다른 프로젝트 실행 상태가 있습니다. 종료하지 않고 중단합니다.')
        records=old.get('owned',[])
    for role,port in [('backend',args.backend_port),('frontend',args.frontend_port)]:
        pid=listener(port)
        if pid:
            if not project_process(identity(pid),role,port) or not ready(role,port):
                raise DemoError(f'포트 {port}의 서비스를 안전하게 확인할 수 없습니다. 점유 프로그램을 종료하지 않고 중단합니다.')
            log.info('Reused healthy project %s on port %s (not adopted)',role,port)
            print(f'[PASS] 기존 {role} 서버 재사용 ({port})')
            continue
        command = ([str(PYTHON),'-B','-m','uvicorn','web.backend.app:app','--host','127.0.0.1','--port',str(port),'--no-access-log']
                   if role=='backend' else [str(node),str(FRONTEND/'node_modules/vite/bin/vite.js'),
                     '--config',str(HERE/'vite.demo.config.mjs'),'--host','127.0.0.1'])
        process=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        info=None
        for _ in range(20):
            info=identity(process.pid)
            if info: break
            if process.poll() is not None: break
            time.sleep(.1)
        if not project_process(info,role,port):
            raise DemoError(f'{role} 시작 프로세스를 확인할 수 없습니다. 로그 안내를 확인하세요.')
        record={'role':role,'port':port,'pid':process.pid,'identity':info}
        records=[r for r in records if r['role']!=role or r['port']!=port]+[record]
        save_state(state_path,records)
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if process.poll() is not None: break
            if listener(port)==process.pid and ready(role,port): break
            time.sleep(.25)
        else:
            raise DemoError(f'{role} 준비 시간이 초과됐습니다. 모델/포트/환경을 확인하세요.')
        if process.poll() is not None or not ready(role,port):
            raise DemoError(f'{role} 시작 실패입니다. 필수 파일·환경·포트를 확인하세요.')
        log.info('Started owned %s on port %s; ready',role,port)
        print(f'[PASS] {role} 시작 완료 ({port})')
    url=f'http://127.0.0.1:{args.frontend_port}/'
    print('SCENT MATCH 준비 완료: '+url)
    log.info('Ready; frozen model loaded; candidates479')
    if not args.no_browser:
        subprocess.run(['/usr/bin/open',url],check=True)


def main():
    """start/stop; optional isolated test ports/state-dir; default is 8000/5173."""
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','stop'])
    parser.add_argument('--backend-port',type=int,default=8000)
    parser.add_argument('--frontend-port',type=int,default=5173)
    parser.add_argument('--state-dir',type=Path,default=HERE/'.state')
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not all(1024<=p<=65535 for p in (args.backend_port,args.frontend_port)) or args.backend_port==args.frontend_port:
        parser.error('Use two different unprivileged local ports')
    args.state_dir.mkdir(parents=True,exist_ok=True)
    logs=HERE/'logs';logs.mkdir(exist_ok=True)
    log=logging.getLogger('scent-demo');log.setLevel(logging.INFO)
    handler=RotatingFileHandler(logs/'demo.log',maxBytes=65536,backupCount=3,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));log.addHandler(handler)
    state=args.state_dir/'owned.json'
    try:
        with (args.state_dir/'manager.lock').open('w') as lock:
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise DemoError('다른 실행/종료 작업이 진행 중입니다. 잠시 후 다시 시도하세요.')
            if args.action=='start': start(args,state,log)
            elif not stop_owned(state,log): return 1
        return 0
    except DemoError as error:
        log.error('%s',error);print('[중단] '+str(error));return 1
    except Exception:
        log.error('Launcher failed; sensitive exception text omitted')
        print('[중단] 실행 환경을 확인할 수 없습니다. 자동 설치/강제 종료 없이 중단합니다.');return 1


if __name__=='__main__': raise SystemExit(main())
