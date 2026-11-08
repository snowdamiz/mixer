"""Selected-file inspection only. Never enters a native or process entrypoint."""
import datetime
import difflib
import importlib.util
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
CANDIDATE = BASE / 'pair9-api28-controller-fix-r3'
R2 = BASE / 'pair9-api28-controller-fix-r2'
EXPECTED = {'run_api28.py': '99bd6a11679ca86fbbc1ae591401bba2c5b9db6dce3a0430fd31517d24f619b3',
            'controller-packet.json': '20b512f3cce5bec220f558c0cf4392813f9e9f868702a7c9e1b6e28c6905f03b',
            'cleanup_control.py': '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'}
spec = importlib.util.spec_from_file_location('read_only_candidate', CANDIDATE/'run_api28.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
phase = sys.argv[1]
for name, sha in EXPECTED.items():
    r.require(r.identity(CANDIDATE/name)['sha256'] == sha, 'requested identity drift: '+name)
frozen = r.load(CANDIDATE/'controller-packet.json')
packet = r.verify_bindings(frozen)
old = r.load(R2/'controller-packet.json')
external = {k:v for k,v in frozen['bindings'].items() if not k.startswith(str(CANDIDATE)+'/')}
old_external = {k:v for k,v in old['bindings'].items() if not k.startswith(str(R2)+'/')}
r.require(external == old_external and len(external) == 1164, 'external binding drift')
r.require(len(frozen['bindings']) == 1169, 'binding count')
for key in ('bounds', 'limits', 'topology', 'sourceDigest101', 'adapter24Digest', 'apkSHA256', 'apkBytes'):
    r.require(frozen[key] == old[key], 'R2 invariant changed: '+key)
source2 = (R2/'run_api28.py').read_text()
addition = "                   ADB_SERVER_SOCKET='tcp:127.0.0.1:' + str(serverport),\n                   ANDROID_ADB_SERVER_ADDRESS='127.0.0.1',\n"
r.require((CANDIDATE/'run_api28.py').read_text().replace(addition, '', 1) == source2, 'non-environment controller change')
selected = list(p for p in CANDIDATE.iterdir() if p.is_file())
for directory in ('first-control-failure', 'control-supervisor', 'corrected-control-supervisor', 'inherited-client-refusal'):
    selected.extend(p for p in (CANDIDATE/directory).iterdir() if p.is_file())
selected.extend(R2/name for name in ('official-client-commandline.cpp', 'official-client-adb_client.cpp',
    'official-socket_spec.cpp', 'official-adb.h', 'official-sources.json', 'installed-adb-local-socket-disassembly.txt',
    'installed-adb-version-callback.txt', 'installed-adb-version-disassembly.txt', 'inspection-receipt.json'))
review2 = BASE/'pair9-api28-controller-review-r2'
manifest = r.load(review2/'artifact-manifest.json')
for name, expected in manifest.items():
    path = review2/name
    r.require(r.identity(path) == expected, 'retained R2 artifact drift: '+name)
    selected.append(path)
selected.append(BASE/'pair9-api28-controller-review/review.json')
files = {str(p):r.identity(p) for p in sorted(set(selected))}
if phase == 'postflight':
    pre = r.load(OUT/'frozen-preflight.json')
    r.require(pre['selectedFiles'] == files, 'selected review/candidate evidence changed')
failure = r.load(CANDIDATE/'first-control-failure/host-normal.json')
r.require(failure['status'] == 'failed' and failure['tests'] == 52, 'first failure not retained')
fixture_diff = ''.join(difflib.unified_diff((CANDIDATE/'first-control-failure/host_controls.py').read_text().splitlines(True),
    (CANDIDATE/'host_controls.py').read_text().splitlines(True), fromfile='retained-first-fixture', tofile='final-fixture'))
if phase == 'preflight': (OUT/'fixture-correction.diff').write_text(fixture_diff)
report = {'status':'passed', 'phase':phase, 'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command':[sys.executable, '-B', str(Path(__file__).resolve()),phase], 'python':sys.version,
    'scope':'Pure selected-file verification; no native invocation or process/device query',
    'sourceRevision':'62ce9b76840b2fa56306736fc4c4fe2962780adf', 'sourceTree':'fc205cd742c9d60de31623d8120e57a12f89bbc8',
    'gitVersion':'2.56.0', 'packetBindingsVerified':len(frozen['bindings']), 'externalBindingsUnchanged':len(external),
    'sourceDigest101':r.SOURCE_SHA, 'adapter24Digest':r.ADAPTER_SHA,
    'sdk22Digest':r.load(review2/'review.json')['sdk22Digest'],
    'apk':r.identity(packet['apk']['path']), 'bounds':frozen['bounds'], 'limits':frozen['limits'],
    'selectedFiles':files, 'controllerOnlyChange':'Two inherited numeric loopback environment assignments',
    'retainedR2ManifestVerified':len(manifest), 'retainedFirstFailureTests':failure['tests'],
    'nativeCommands':0, 'childrenSpawned':0}
r.save(OUT/('frozen-'+phase+'.json'),report)
print(json.dumps({k:v for k,v in report.items() if k != 'selectedFiles'}))
