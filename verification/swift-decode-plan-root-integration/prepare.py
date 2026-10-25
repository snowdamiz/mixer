#!/usr/bin/env python3
"""Integrate the reviewed source; normalize only newly introduced test formatting."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
INPUT = ROOT / 'verification/swift-decode-plan-full-regression'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (BASE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


assert not (BASE / 'selection.json').exists(), 'Preserve earlier selection'
seal_hash = sha((INPUT / 'seal.json').read_bytes())
assert seal_hash == 'dd75be634be6b4fbd955accb5b4265aecccfee26c62bed1e7dab5e526e2a0a22'
old = json.loads((INPUT / 'live-input-manifest.json').read_text())
candidate = json.loads((INPUT / 'final-source-manifest.json').read_text())
for name, value in old.items():
    assert sha((ROOT / 'vm' / name).read_bytes()) == value, name
for name, value in candidate.items():
    assert sha((INPUT / 'source' / name).read_bytes()) == value, name
changed = [name for name in old if old[name] != candidate[name]]
assert changed == [f'src/experimental_swift_reactor/{name}' for name in
                   ['cache.rs', 'cache_tests.rs', 'execution_tests.rs', 'lifecycle_tests.rs']]
save('selection.json', {
    'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevision': '9102ad3ee1247187c01ea5f55c42caaac882961b',
    'regressionSealSHA256': seal_hash,
    'verifiedBeforeMutation': {
        'command': ['python3', '-B', 'verification/swift-decode-plan-full-regression/verify.py'],
        'toolResultChunk': 'cd3ffc', 'exitCode': 0, 'verifiedFiles': 560,
        'externalBindings': 5, 'finalNamedPasses': 2314, 'ignoredPerContext': 9,
        'swiftDebugReleasePassedEach': 519, 'fullDebugReleasePassedEach': 638,
        'ClippyPass': True, 'fullFormattingPass': False,
        'liveUnchanged': True, 'scratchAbsent': True,
    },
    'rootReview': 'Production cache matches accepted finite accounting review; test updates follow actual measured allocations/work, expand all fifteen allocation failures, and preserve full validation, failure precedence and consuming cleanup. No production limits change.',
    'changedPaths': changed,
    'originalSourceClosure': sha((INPUT / 'live-input-manifest.json').read_bytes()),
    'testedSourceClosure': sha((INPUT / 'final-source-manifest.json').read_bytes()),
    'selected': 'Four-file live integration plus formatting-only derivative of new test additions, followed by a fresh live private Swift library suite.',
    'fullReactorSelected': False, 'nativeAccepted': False, 'gaAccepted': False,
    'historicalVerifierAfterIntegration': 'The isolated verifier binds the old live tree and is expected to reject later live source drift; this is the pre-mutation acceptance record.',
})
for name in changed:
    before = BASE / 'before' / name
    before.parent.mkdir(parents=True, exist_ok=True)
    before.write_bytes((ROOT / 'vm' / name).read_bytes())
    (ROOT / 'vm' / name).write_bytes((INPUT / 'source' / name).read_bytes())

tools = json.loads((INPUT / 'tools.json').read_text())
rustfmt = tools['rustfmt']['path']
assert sha(Path(rustfmt).read_bytes()) == tools['rustfmt']['sha256']
test_dir = ROOT / 'vm/src/experimental_swift_reactor'
cache = test_dir / 'cache_tests.rs'
text = cache.read_text()
start = text.index('fn plan_reuse_cached_deadline_and_precedence()')
end = text.index('\n#[test]', start)
original = text[start:end].rstrip() + '\n'
argv = [rustfmt, '--edition', '2021', '--emit', 'stdout']
formatted = subprocess.run(argv, input=original, text=True, capture_output=True, check=True)
(BASE / 'format-fragment-before.rs').write_text(original)
(BASE / 'format-fragment-after.rs').write_text(formatted.stdout)
(BASE / 'format-fragment.stderr').write_text(formatted.stderr)
cache.write_text(text[:start] + formatted.stdout.rstrip() + '\n' + text[end:])
for name in ['cache_tests.rs', 'execution_tests.rs', 'lifecycle_tests.rs']:
    path = test_dir / name
    text = path.read_text()
    marker = '\n\n\n#[test]\nfn full_regression_observe_'
    assert text.count(marker) == 1, name
    path.write_text(text.replace(marker, '\n\n#[test]\nfn full_regression_observe_'))
path = test_dir / 'execution_tests.rs'
text = path.read_text()
before = '        println!("REGRESSION_ADMISSION kind={kind:?} attempts={} expected={attempts}", stats.attempts);'
after = '''        println!(
            "REGRESSION_ADMISSION kind={kind:?} attempts={} expected={attempts}",
            stats.attempts
        );'''
assert text.count(before) == 1
path.write_text(text.replace(before, after))
patch = ''
for name in changed:
    patch += ''.join(difflib.unified_diff(
        (INPUT / 'source' / name).read_text().splitlines(True),
        (ROOT / 'vm' / name).read_text().splitlines(True),
        fromfile='tested/' + name, tofile='integrated/' + name))
(BASE / 'format-only.patch').write_text(patch)
live = {name: sha((ROOT / 'vm' / name).read_bytes()) for name in candidate}
assert live['src/experimental_swift_reactor/cache.rs'] == candidate['src/experimental_swift_reactor/cache.rs']
assert [name for name in candidate if candidate[name] != live[name]] == changed[1:]
save('live-source-manifest.json', live)
save('format-derivative.json', {
    'command': argv, 'rustfmt': tools['rustfmt'], 'exitCode': formatted.returncode,
    'changes': ['Format one new cached-deadline test using pinned rustfmt.',
                'Remove one extra blank boundary before each of three new observation tests.',
                'Wrap one new diagnostic print; preserve literal string and expression.'],
    'productionBytesIdentical': True,
    'testedSourceClosure': sha((INPUT / 'final-source-manifest.json').read_bytes()),
    'integratedSourceClosure': sha((BASE / 'live-source-manifest.json').read_bytes()),
    'patchSHA256': sha(patch.encode()),
})
print(json.dumps({'changedFiles': changed, 'liveSourceClosure': sha((BASE / 'live-source-manifest.json').read_bytes())}))
