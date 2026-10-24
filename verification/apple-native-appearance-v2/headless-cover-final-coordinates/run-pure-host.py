#!/usr/bin/env python3
"""Execute only the macOS CoreGraphics arithmetic fixture, with exact source/binary binding."""
import hashlib
import json
import pathlib
import subprocess

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
HOST = pathlib.Path('/tmp/mixer-native-appearance-v2-cover-final-host')
source = json.loads((OUT/'source-lock.json').read_text())
manifest = json.loads((OUT/'artifact-members.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert all(sha(ROOT/path) == value for path,value in source['sha256'].items()), 'source drift'
for name in ['cover-geometry-definitions','libMixerCore.dylib','libMixerUI.dylib']:
    assert sha(HOST/name) == manifest['host/'+name]['sha256'], 'host artifact drift'
argv = [str(HOST/'cover-geometry-definitions')]
run = subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
(OUT/'host-pure-stdout.json').write_text(run.stdout)
(OUT/'host-pure-stderr.txt').write_text(run.stderr)
outcomes = json.loads(run.stdout) if run.returncode == 0 else []
result = dict(argv=argv,exitCode=run.returncode,sourceClosureSHA256=source['sourceClosureSHA256'],
              executable=manifest['host/cover-geometry-definitions'],
              passed=run.returncode == 0 and len(outcomes) == 8 and all(item['passed'] for item in outcomes),
              outcomes=outcomes,scope='macOS CoreGraphics arithmetic only; production Geometry helper; no UIKit/app/window/simulator/GUI/capture',
              hostPureExecuted=True,nativeExecuted=False,guiExecuted=False,visualQualified=False)
(OUT/'host-pure-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
assert result['passed'], 'pure host regression failed; raw output retained'
print(json.dumps(dict(passed=True,outcomes=len(outcomes),nativeExecuted=False)))
