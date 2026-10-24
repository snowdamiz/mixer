"""Official binary/SDK provenance only; no native instances or application execution."""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import run
BASE,ROOT=run.BASE,run.ROOT
assert not (BASE/'packet-seal.json').exists(),'Sealed preparation is immutable'
manifest=run.read(BASE/'build-products-manifest.json');payload=run.inherited.product_archive_payload(manifest)
names=['Debug-iphonesimulator/MixerToggleUITests-Runner.app/MixerToggleUITests-Runner','Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']
commands=[]
def command(argv):
    p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,env={**os.environ,'DEVELOPER_DIR':str(run.inherited.DEVELOPER)},timeout=30)
    commands.append({'argv':list(map(str,argv)),'DEVELOPER_DIR':str(run.inherited.DEVELOPER),'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if p.returncode:raise RuntimeError(p.stderr)
    return p.stdout
binaries={}
for name in names:
    path=run.inherited.PRODUCTS/name
    build=command(['/usr/bin/xcrun','vtool','-show-build',str(path)])
    architecture=command(['/usr/bin/xcrun','lipo','-info',str(path)])
    assert 'platform IOSSIMULATOR' in build
    binaries[name]={'sha256':hashlib.sha256(payload[name]).hexdigest(),'officialBuildVersionOutput':build,'officialArchitectureOutput':architecture}
help_argv=['/usr/bin/xcrun','xcresulttool','export','attachments','--help'];help_text=command(help_argv)
(BASE/'official/xcresulttool-export-help.json').write_text(json.dumps(commands[-1],indent=2)+'\n')
(BASE/'binary-provenance-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
value={'schema':'mixer.apple-toggle.keyboard-runner-binary.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve().relative_to(ROOT))],'sourceRevisionContext':run.prerequisite()['sourceRevisionContext'],'sourceTreeSHA256':hashlib.sha256(run.inherited.json_bytes(manifest['sourceFiles'])).hexdigest(),'productTreeSHA256':manifest['productTreeSHA256'],'archiveSHA256':manifest['productArchiveSHA256'],'binaries':binaries,'versions':manifest['versions'],'buildCommands':manifest['buildCommands'],'nativeExecuted':False,'scope':'Official cross-built public7methodXCTest bundle targets simulator minimum26.0 SDK26.5; Xcode-supplied launcher reports its own minimum14.0 SDK26.4. Neither build qualifies keyboard/focus runtime.'}
(BASE/'runner-binary-receipt.json').write_text(json.dumps(value,indent=2)+'\n')
files=[ROOT/'docs/apple-toggle-keyboard-focus-contract.md',run.PAN/'packet-seal.json',run.PAN/'observation_reader.py',ROOT/'verification/apple-toggle-pan-commit-harness-v2-root-review/runtime-review.json',run.PAN/'runtime/runtime-verdict.json',run.PAN/'runtime/lifecycle.json']
(BASE/'preparation-selection.json').write_text(json.dumps({'schema':'mixer.apple-toggle.keyboard-preparation-selection.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'private-source-host-and-runner-preparation-only','sourceRevisionContext':run.prerequisite()['sourceRevisionContext'],'prerequisite':run.prerequisite(),'bindings':{str(p.relative_to(ROOT)):run.sha(p) for p in files},'selectedScope':'Public Settings gate, sixappcases, public typeKey/hasFocus, closed same-endpoint witnesses/fixed fixture command phases; fixed owned xcresult export on success/failure/timeout. Root owns runtime.','nativeExecuted':False,'physicalDevicesQueried':False},indent=2)+'\n')
print(json.dumps({'status':'official-binary-provenance-recorded','binaries':len(binaries),'productTreeSHA256':manifest['productTreeSHA256'],'runnerArchiveSHA256':manifest['productArchiveSHA256'],'nativeExecuted':False}))
