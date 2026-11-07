#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import shutil

ROUND=Path(__file__).resolve().parents[1]
OWNED=ROUND.parent
OLD=OWNED/'review-round-1/portable-root/runs/actual-host-explicit'
DEST=ROUND/'parser-originals'
(DEST/'api').mkdir(parents=True)
(DEST/'diagnostics').mkdir()
records=[]
for source,target in [(p,DEST/'api'/p.name) for p in sorted((OLD/'pack/api').glob('*.rs'))]+[(p,DEST/'diagnostics'/p.name) for p in sorted((OLD/'commands').glob('api-negative-*.stderr'))]:
    shutil.copyfile(source,target)
    records.append({'source':str(source.relative_to(OWNED.parent.parent)),'target':str(target.relative_to(ROUND)),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
old=json.loads((OLD/'receipt.json').read_bytes())
prior=json.loads((OWNED/'compiler-preaccess-supplement/input-audit.json').read_bytes())
versions={'1.99.0':old['rustc']['version_verbose'],'1.98.1':prior['prior_ci_identity_observed']['compiler']['version_verbose']}
(DEST/'versions.json').write_text(json.dumps(versions,indent=2,sort_keys=True)+'\n')
shutil.copyfile(OWNED.parent/'swift-envelope-ci-root-review/api-span-correction-targets.json',DEST/'span-map.json')
with (DEST/'provenance.json').open('x') as stream:json.dump({'schema':1,'scope':'Preserved real compiler diagnostics/source/version bytes only; no old runner execution.','files':records},stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'sources':9,'diagnostics':8,'real_versions':2},sort_keys=True))
