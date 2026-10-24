"""Read-only sealed host preflight; no native queries or execution."""
import hashlib
import json
import pathlib
import sys
BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
V7 = BASE.parent / 'apple-toggle-keyboard-focus-v7-preparation'
V8 = BASE.parent / 'apple-toggle-keyboard-focus-v8-preparation'
SELECTION = BASE.parent / 'apple-toggle-keyboard-focus-v8-root-review/v9-commit-point-selection.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
PINS = {str(SELECTION.relative_to(ROOT)): 'cb3fe08781f93cae77c143676544c25c178e751146c8f45043d21875309da795',
        str((V8/'packet-seal.json').relative_to(ROOT)): '46e2c5a61fcce4137595da36af6d120ef476b2fb5889a1bd8cfb38d70f7a9b0f',
        'verification/apple-toggle-keyboard-focus-v8-independent-review/review-seal.json': 'ed10da1e0da527a1771b76b857047044a72db98bb24765ffa6c2a2840589eca4'}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def inputs():
    result = dict(PINS)
    for seal_name in list(PINS)[1:]:
        seal = read(ROOT/seal_name)
        result.update(seal['files'])
    result.update(read(V8/'input-bindings.json'))
    result.update(read(V8.parent/'apple-toggle-keyboard-focus-v8-independent-review/review-inputs.json'))
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
    require(seal['schema']=='mixer.apple-toggle.keyboard-v9-diagnostic.1','Wrong V9 packet')
    for name, expected in seal['files'].items():
        path=ROOT/name
        require(path.is_file() and not path.is_symlink() and sha(path)==expected,'Sealed V9 file changed: '+name)
    check_inputs(read(BASE/'input-bindings.json'))
    controls=read(BASE/'host-controls.json')
    require(controls['passed'] and all(sha(ROOT/name)==expected for name,expected in controls['sourceFiles'].items()),'Host controls changed/incomplete')
    old = read(V7/'packet-seal.json')
    return dict(schema='mixer.apple-toggle.keyboard-v9-host-preflight.1', sealSHA256=sha(BASE/'packet-seal.json'),
                candidateSourceClosureSHA256=old['candidateSourceClosureSHA256'], candidateArchiveSHA256=old['candidateArchiveSHA256'],
                testRunnerSourceTreeSHA256=old['testRunnerSourceTreeSHA256'], testRunnerProductTreeSHA256=old['testRunnerProductTreeSHA256'], testRunnerArchiveSHA256=old['testRunnerArchiveSHA256'],
                sourceRevisionContext=old['sourceRevisionContext'],expectedXCTestMethods=1,applicationCasesUnrun=old['applicationCasesUnrun'],
                rootSelectionSHA256=PINS[str(SELECTION.relative_to(ROOT))],status='DIAGNOSTIC_ONLY',nativeExecution=False,nativeInstancesQueried=False,runnerRecompiled=False,physicalPhones='disconnected-deferred',gaAccepted=False)
