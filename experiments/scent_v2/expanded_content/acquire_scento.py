"""Download version-pinned public CC-BY metadata only; never transmit local ratings."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/scent_v2/expanded_content'
REPOSITORY='Scento-com/perfume-dataset'


def fetch(url):
    """Read-only public HTTPS GET with fixed limits; no credentials, IDs or ratings."""
    request=urllib.request.Request(url,headers={'User-Agent':'Team12-local-research','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as response:
        data=response.read(15_000_001)
    if len(data)>15_000_000:raise ValueError('Unexpectedly large metadata file')
    return data


def main():
    """Pin current public commit, check license and source policy BEFORE data download."""
    raw=OUT/'licensed_source';raw.mkdir(mode=0o700,exist_ok=True)
    if (raw/'provenance.json').exists():raise FileExistsError('Already acquired; do not overwrite')
    commit=json.loads(fetch(f'https://api.github.com/repos/{REPOSITORY}/commits/main'))['sha']
    base=f'https://raw.githubusercontent.com/{REPOSITORY}/{commit}/'
    license_bytes=fetch(base+'LICENSE');readme=fetch(base+'README.md')
    if b'CC BY 4.0' not in license_bytes or b'Sources policy' not in readme:raise PermissionError('License/provenance preflight failed')
    if b'Descriptions are written by Scento' not in readme:raise PermissionError('Original curation declaration missing')
    records=[]
    for name,content in [('LICENSE',license_bytes),('README.md',readme),('datapackage.json',fetch(base+'datapackage.json')),('perfumes.jsonl',fetch(base+'perfumes.jsonl'))]:
        p=raw/name
        with p.open('xb') as stream:stream.write(content)
        p.chmod(0o600)
        records.append(dict(path=name,url=base+name,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
    rows=[json.loads(line) for line in (raw/'perfumes.jsonl').read_text().splitlines() if line.strip()]
    provenance=dict(publisher='Scento',repository='https://github.com/'+REPOSITORY,commit=commit,acquired_date='2026-10-30',
        license='CC-BY-4.0',license_url='https://creativecommons.org/licenses/by/4.0/legalcode',
        attribution='Scento — https://www.scento.com/perfume-database',files=records,measured_rows=len(rows),
        source_policy='Publisher states house/authorized retailer facts checked; descriptions authored by Scento; no third-party text/source texts included',
        allowed_scope='Licensed metadata adaptation for isolated local noncommercial recommendation research; not approval of manufacturer-copy reuse',
        modifications='Only product identity, concentration and literal flat notes used; descriptions, ranks, seasons and accords/families not used in scoring',
        local_ratings_transmitted=False,V217_note_or_vector_data_used_for_scoring=False)
    with (raw/'provenance.json').open('x') as stream:json.dump(provenance,stream,ensure_ascii=False,indent=2)
    (raw/'provenance.json').chmod(0o600)
    print(json.dumps(dict(commit=commit,measured_rows=len(rows),schema=list(rows[0]),raw_metadata_bytes=sum(r['bytes'] for r in records)),ensure_ascii=False))

if __name__=='__main__':main()
