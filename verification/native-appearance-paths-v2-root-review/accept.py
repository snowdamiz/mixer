from pathlib import Path
import datetime, hashlib, json, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
bindings = {}
def read(path): return json.loads((ROOT/path).read_text())
def bind(path, expected=None):
    digest=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    if expected is not None and digest != expected: raise RuntimeError(path)
    bindings[path]=digest
    return digest

apple_base='verification/apple-appearance-native-paths-v2/candidate-2/'
android_base='verification/android-appearance-native-paths-v2/candidate-3/'
apple=read(apple_base+'receipt.json');android=read(android_base+'receipt.json')
assert apple['status']=='passed-native-primitive-host-and-ios-compilation'
assert android['status']=='passed-compile-and-native-emulator'
assert all(c['total']==131 and len(c['newTests'])==4 for c in apple['testCounts'].values())
assert android['native']['checks']==5610 and android['native']['native_paths']==45
for receipt,base,key in [(apple,apple_base,'inputManifest'),(android,android_base,'sourceManifest')]:
    for relative,digest in receipt[key].items():
        bind(relative,digest);bind(base+'inputs/'+relative,digest)
    for command in receipt['commands']:
        assert command.get('exit',command.get('exitCode'))==0
        bind(command.get('log',command.get('output')),command['sha256'])
for relative,artifact in apple['outputs'].items():
    assert (ROOT/relative).stat().st_size==artifact['bytes']
    bind(relative,artifact['sha256'])
for relative,digest in read(android_base+'artifact-seal.json').items():
    bind(android_base+relative,digest)
for path in [apple_base+'receipt.json',android_base+'receipt.json',android_base+'artifact-seal.json',
    'verification/android-appearance-native-paths-v2/emulator-session.json',
    'docs/apple-appearance-native-paths-v2.md',str(Path(__file__).relative_to(ROOT))]: bind(path)
out=dict(schema=1,status='accepted-native-closed-path-primitives',reviewer='root',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    appleSDKTestsPerMode=131,appleNewTestsPerMode=4,androidNativeChecks=5610,
    androidNativePaths=45,androidNativeVerbs=630,
    scope='Actual macOS CoreGraphics and API37 Android emulator Path/PathMeasure/software Canvas consumption of closed V2 curves; Apple iOS17 modules and Android minimumAPI28 Java/D8 compilation.',
    sourceReview='Direct closed-operation conversion, empty-density rejection, fractional controls, fresh ownership and native coordinate/fill/clip tests reviewed. Native float versus CGFloat precision is explicit. Neither adapter integrates into the existing renderer.',
    limitations=['No native renderer/style/resource/font/environment/atomic attachment or display proof.',
        'No physical device, cross-screen visual parity, hardware Android Canvas or API28/34 runtime qualification.',
        'No signed V2, immutable published FieldLog or GA qualification.'],
    retainedFailures='Apple candidate1 omitted test fixtures and used the wrong bitmap coordinate convention; corrected harness in candidate2, same product code. Android prior passing candidates retain final test API-overload correction in candidate3.',
    bindings=dict(sorted(bindings.items())))
(HERE/'acceptance.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status=out['status'],bindings=len(bindings))))
