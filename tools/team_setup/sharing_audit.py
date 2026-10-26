"""Explicit source candidate audit and local planned-source simulation, no Git mutation.

Uses STEP10 temporary_root receipt. Copies private assets only within same-machine
local verification folders; separate sharing and archive creation remain on hold.
"""
import json,hashlib,subprocess,re,shutil,tarfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/step10_sharing'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    temp=Path(json.loads((OUT/'temp_workspace.json').read_text())['temporary_root']);planned=temp/'planned-source';planned.mkdir()
    tracked=[p.decode() for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0') if p]
    candidates=set(tracked)|{'docs/archive/TEAM_SETUP_GUIDE.md','RUNTIME_MANIFEST.json'}
    for folder in ['experiments/development_v2','experiments/development_v3','experiments/step9_audit','tools/team_setup']:
        candidates|={str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    forbidden=('Term-project-datasets/','outputs/','web/evidence/','web/deployment/private-assets/')
    patterns=[r'\bgh[pousr]_[A-Za-z0-9]{20,}',r'\bgithub_pat_[A-Za-z0-9_]{30,}',r'\bsk-[A-Za-z0-9_-]{30,}',r'\bAKIA[A-Z0-9]{16}\b',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    inventory=[];findings=[];absolute=[]
    for name in sorted(candidates):
        p=ROOT/name;assert not name.startswith(forbidden) and p.suffix not in {'.npz','.npy','.pkl','.zip'}
        text=p.read_text(encoding='utf-8')
        if any(re.search(pattern,text) for pattern in patterns):findings.append({'path':name,'type':'credential pattern; value omitted'})
        # Literal personal home prefix; do not flag the scanner regex itself.
        if re.search(r'/Users/[A-Za-z0-9_.-]+/',text):absolute.append(name)
        ignored=subprocess.run(['git','check-ignore','-q',name],cwd=ROOT).returncode==0
        assert not ignored,(name,'Unexpected ignored source: request explicit approval')
        inventory.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p),'tracked':name in tracked,'ignored':ignored})
    assert not findings and not absolute,(findings,absolute)
    for row in inventory:
        p=planned/row['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/row['path'],p)
    # Original private bytes stay local, never packaged for sharing.
    m=json.loads((ROOT/'RUNTIME_MANIFEST.json').read_text())
    for row in m['files']:
        if row['private_runtime']:
            p=planned/row['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/row['path'],p)
    # Reuse only dependencies freshly installed in the independent clone, never original node_modules.
    fresh=temp/'github-verified/web/frontend/node_modules'
    shutil.copytree(fresh,planned/'web/frontend/node_modules',symlinks=True)
    result={'status':'PASS_SOURCE_REVIEW_WITH_MANUAL_LIMITS','tracked':len(tracked),'proposed_total':len(inventory),'new_source_candidates':len(inventory)-len(tracked),'files':inventory,'credential_findings':findings,'personal_absolute_paths':absolute,'private_runtime_separate_transfer':'ON HOLD per user','packaged':False,'planned_source_only_local':True,'scan_scope':'All explicit UTF8 source candidates; heuristic credential/path scan, not guarantee of every possible secret. Existing private reports/models/data excluded.','remote_commit':subprocess.check_output(['git','-C',str(temp/'github-verified'),'rev-parse','HEAD'],text=True).strip(),'remote_branch':subprocess.check_output(['git','-C',str(temp/'github-verified'),'branch','--show-current'],text=True).strip()}
    with (OUT/'source_candidates.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print('Source audit PASS:',len(tracked),'tracked +',len(inventory)-len(tracked),'new =',len(inventory),'explicit files. No credentials/personal absolute path found; no staging/transfer.')
if __name__=='__main__':main()
