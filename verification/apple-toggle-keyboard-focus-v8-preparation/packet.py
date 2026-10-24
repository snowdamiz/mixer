"""Read-only sealed host preflight; no native queries or execution."""
import hashlib
import json
import pathlib
import sys
BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
V7 = BASE.parent / 'apple-toggle-keyboard-focus-v7-preparation'
SELECTION = BASE.parent / 'apple-toggle-keyboard-focus-v7-root-review/v8-persistence-selection.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
PINS = {str(SELECTION.relative_to(ROOT)): 'b607b64d146e88d743da05739e341de24d01d3228d53c949f9dc72419c411fa4',
        str((V7/'packet-seal.json').relative_to(ROOT)): '1332308b51182f2ead68a774f135bc3121e00b7385cbd0337395a90d53175579',
        'verification/apple-toggle-keyboard-focus-v7-independent-review/review-seal.json': '6aacb2434dddd1ab41eecd2bd8f3c54b074322fdf372886adf6d4464452e91f3'}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def inputs():
    result = dict(PINS)
    for seal_name in list(PINS)[1:]:
        seal = read(ROOT/seal_name)
        result.update(seal['files'])
    reuse = read(V7/'immutable-reuse.json')
    result.update(reuse['historicalBindings'])
    for name in ['settings_telemetry.py','replay.py','run.py','fixtures.py','test_v7.py','runner-binary-receipt.json','build-products-manifest.json','test-runner-products.tar.gz']:
        result[str((V7/name).relative_to(ROOT))] = sha(V7/name)
    runner = read(V7/'build-products-manifest.json')
    result.update(runner['sourceFiles'])
    result.update(runner['toolFiles'])
    return result


def check_inputs(bindings):
    for name, expected in bindings.items():
        path = pathlib.Path(name) if name.startswith('/') else ROOT/name
        require(path.is_file() and (not path.is_symlink() or name in read(V7/'build-products-manifest.json')['toolFiles']) and sha(path) == expected, 'Input changed: '+name)
    require(all(sha(ROOT/name)==expected for name,expected in PINS.items()), 'Selected input seal changed')
    # The exact existing source manifest and runner product tree are reused.
    import run as r
    runner = read(V7/'build-products-manifest.json')
    require(r.h.tree(r.h.PRODUCTS)==runner['products'], 'Bound V7 runner products changed')
    r.h.product_archive_payload(runner)
    app = read(BASE/'built-app-manifest.json')
    r.runtime.artifact.archive_payload(BASE/'built-app.tar.gz',app,r.runtime.artifact.CONFIGS['diagnostic'])
    copies = read(BASE/'immutable-reuse.json')['exactCopies'] if (BASE/'immutable-reuse.json').exists() else {}
    for name, source in copies.items():
        require(sha(ROOT/name)==sha(ROOT/source), 'Immutable copy changed: '+name)


def verify_packet():
    seal = read(BASE/'packet-seal.json')
    require(seal['schema']=='mixer.apple-toggle.keyboard-v8-diagnostic.1','Wrong V8 packet')
    for name, expected in seal['files'].items():
        path=ROOT/name
        require(path.is_file() and not path.is_symlink() and sha(path)==expected,'Sealed V8 file changed: '+name)
    check_inputs(read(BASE/'input-bindings.json'))
    controls=read(BASE/'host-controls.json')
    require(controls['passed'] and all(sha(ROOT/name)==expected for name,expected in controls['sourceFiles'].items()),'Host controls changed/incomplete')
    old = read(V7/'packet-seal.json')
    return dict(schema='mixer.apple-toggle.keyboard-v8-host-preflight.1', sealSHA256=sha(BASE/'packet-seal.json'),
                candidateSourceClosureSHA256=old['candidateSourceClosureSHA256'], candidateArchiveSHA256=old['candidateArchiveSHA256'],
                testRunnerSourceTreeSHA256=old['testRunnerSourceTreeSHA256'], testRunnerProductTreeSHA256=old['testRunnerProductTreeSHA256'], testRunnerArchiveSHA256=old['testRunnerArchiveSHA256'],
                sourceRevisionContext=old['sourceRevisionContext'],expectedXCTestMethods=1,applicationCasesUnrun=old['applicationCasesUnrun'],
                rootSelectionSHA256=PINS[str(SELECTION.relative_to(ROOT))],status='DIAGNOSTIC_ONLY',nativeExecution=False,nativeInstancesQueried=False,runnerRecompiled=False,physicalPhones='disconnected-deferred',gaAccepted=False)
