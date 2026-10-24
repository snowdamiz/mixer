#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,subprocess,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE=HERE/'source-freeze';BASE.mkdir(exist_ok=True)
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');OUT=BASE/STAMP;OUT.mkdir()
encoded=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[ROOT/'vm/Cargo.toml',ROOT/'vm/Cargo.lock']+[p for d in ['src','tests','include'] for p in sorted((ROOT/'vm'/d).rglob('*')) if p.is_file()]
m={str(p.relative_to(ROOT/'vm')):sha(p) for p in files}
(OUT/'candidate-manifest.json').write_bytes(encoded(m))
with tarfile.open(OUT/'candidate-source.tar.gz','w:gz') as t:
 for p in files:t.add(p,arcname='vm/'+str(p.relative_to(ROOT/'vm')),recursive=False)
record=dict(observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sourceFiles=len(m),sourceTreeSHA256=hashlib.sha256(encoded(m)).hexdigest(),sourceArchiveSHA256=sha(OUT/'candidate-source.tar.gz'),scope='Private original-owner frame implementation; immutable source freeze for independent host review; no runtime/accounting acceptance implied')
(OUT/'freeze.json').write_bytes(encoded(record));(BASE/'latest.json').write_bytes(encoded(dict(directory=STAMP,sourceTreeSHA256=record['sourceTreeSHA256'])));print(json.dumps(record,indent=2))
