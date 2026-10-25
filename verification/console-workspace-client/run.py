#!/usr/bin/env python3
"""Bound current console client/UI host checks without browser or native activity."""
from pathlib import Path
import datetime, hashlib, json, platform, shutil, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent
out=BASE/'attempts'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out.mkdir(parents=True,exist_ok=False)
paths=['console/src/api/workspace-client.ts','console/src/domain/workspace-directory.ts','console/src/components/WorkspaceDirectory.tsx','console/src/components/workspace-directory.css','console/src/brand.css','console/src/styles.css','console/src/App.tsx','console/src/main.tsx','console/src/domain/build-overview.ts','console/src/domain/release-check-summary.ts','console/src/components/BuildOverview.tsx','console/src/components/build-overview.css','console/src/components/ReleaseChecks.tsx','console/src/preview/BuildOverviewPreview.tsx','console/src/preview/ReleaseChecksPreview.tsx','console/package.json','console/package-lock.json','console/tsconfig.json','console/vite.config.ts','website/src/styles.css','hosted/lib/mixer_hosted/authorization/scope.ex','docs/console-workspace-client.md','verification/console-workspace-client/run.py']
paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'console/tests').iterdir()) if p.is_file()]
manifest={}
for rel in paths:
 p=ROOT/rel; target=out/'inputs'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);manifest[rel]=hashlib.sha256(target.read_bytes()).hexdigest()
receipt={'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_tree_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),'inputs':manifest,'platform':platform.platform(),'commands':[],'scope':'TypeScript client/complete console host tests, standalone SSR and staticbuild only. Includes synthetic Node HTTP listener; no production login/App composition, browser/native/deployment/GA evidence.'}
for label,argv in [('node-version',['node','--version']),('npm-version',['npm','--version']),('all-tests',['npm','test']),('typecheck-build',['npm','run','build'])]:
 r=subprocess.run(argv,cwd=ROOT/'console',capture_output=True,timeout=120)
 (out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr)
 receipt['commands'].append({'label':label,'argv':argv,'cwd':'console','exit_code':r.returncode,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()})
 if r.returncode:break
receipt['live_source_changes']=[p for p,h in manifest.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
receipt['owned_client_scratch_remaining']=[str(p) for p in Path(tempfile.gettempdir()).glob('mixer-workspace-client-*')]
receipt['passed']=all(c['exit_code']==0 for c in receipt['commands']) and len(receipt['commands'])==4 and not receipt['live_source_changes'] and not receipt['owned_client_scratch_remaining']
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'receipt':str(out/'receipt.json'),'passed':receipt['passed'],'commands':[(c['label'],c['exit_code']) for c in receipt['commands']],'live_source_changes':receipt['live_source_changes'],'scratch_remaining':receipt['owned_client_scratch_remaining']}))
raise SystemExit(0 if receipt['passed'] else 1)
