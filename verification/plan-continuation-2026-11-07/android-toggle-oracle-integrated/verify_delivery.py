#!/usr/bin/env python3
"""Verify the candidate boundary, preserved matrix, bounded smoke, and oracle-only patch."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CANDIDATE = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-5a390519')
CANDIDATE_EVIDENCE = CANDIDATE / 'verification/plan-continuation-2026-11-07/android-effective-motion'
PATHS = [
    'native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java',
    'native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/widget/Switch.java',
    'native/android/tests/NativeAndroidFixtureHostTests.java',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def git(*arguments, cwd=ROOT):
    return subprocess.check_output(['git', *arguments], cwd=cwd, text=True).strip()


manifest = read(CANDIDATE_EVIDENCE / 'implementation-paths.json')
assert git('rev-parse', 'HEAD') == manifest['sourceRevision']
assert read(OUT / 'candidate-import.json')['all18ManifestPathsMatch']
for relative, identity in manifest['paths'].items():
    assert sha(CANDIDATE / relative) == identity['sha256'], relative
    if relative not in PATHS:
        assert sha(ROOT / relative) == identity['sha256'], relative

before = (CANDIDATE / PATHS[0]).read_text()
after = (ROOT / PATHS[0]).read_text()
assert after == before.replace('check(toggle.performClick(), "actual native click accepted");',
                               'result.putBoolean("togglePerformClickReturn", toggle.performClick());')
assert after.count('awaitPresentation("') == 3
assert 'attempt<100' in after and 'Thread.sleep(20)' in after

native = read(OUT / 'receipt.json')
source_lock = read(OUT / 'source-lock.json')
for relative, expected in source_lock['files'].items():
    assert sha(ROOT / relative) == expected, relative
admission = read(OUT / 'candidate-admission.json')
assert not admission['sourceMismatches'] and not admission['toolMismatches']
reuse = read(OUT / 'native-reuse.json')
assert reuse['all18CandidateNativeLibrariesMatch'] and len(reuse['nativeLibraries']) == 18
assert not reuse['sourceMismatches'] and not reuse['toolMismatches'] and reuse['rebuildCount'] == 0
assert native['status'] == 'passed-smoke' and native['runtime']['passed']
assert native['nativeInstancesStarted'] == 1 and native['elapsedSeconds'] < 1200
assert native['sourceStable'] and native['baselineByteForBytePreserved']
assert 'checks=11' in native['runtime']['instrumentationOutput']
assert 'togglePerformClickReturn=false' in native['runtime']['instrumentationOutput']
assert native['runtime']['environment']['ro.build.version.sdk'] == '37'
assert native['runtime']['environment']['ro.product.cpu.abi'] == 'arm64-v8a'
assert not native['physicalTargetsQueried']
assert native['cleanup']['allOwnedGroupsClosed'] and native['cleanup']['allOwnedLeadersReaped']
cleanup = read(OUT / 'cleanup-port-recheck.json')
assert cleanup['allPortsReleased'] and cleanup['scratchRemoved'] and cleanup['avdRemoved']
assert not Path(native['scratch']).exists() and not Path(native['avd']['path']).exists()
held = {20745,20770,20780,20817,20842,20851,20866,2424,2621}
assert all(row['pid'] not in held and row['pgid'] not in held for row in native['cleanup']['groups'])

host = read(OUT / 'fullB/receipt.json')
assert host['status'] == 'passed-host-only' and host['source_stable']
assert all(host['cleanup'][key] for key in ('scratch_removed', 'children_reaped'))
matrix = read(OUT / 'fullB/barrier-cases.json')
assert matrix == read(CANDIDATE_EVIDENCE / 'fullB/barrier-cases.json')
assert len(matrix['cases']) == 1323 and not matrix['missing']
assert 'checks=14662' in (OUT / 'fullB/host.stdout').read_text()
fixture = read(OUT / 'fixture-control.json')
assert fixture['status'] == 'passed' and fixture['unchangedCandidateLeafRejected']
assert fixture['scratchRemoved']
assert all(row['cleanup']['groupAbsent'] and row['cleanup']['leaderReaped'] for row in fixture['commands'])

allowed = set(manifest['paths']) | set(PATHS)
changed = set(git('diff', '--name-only').splitlines())
untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
unexpected = (changed | untracked) - allowed
unexpected = {path for path in unexpected if not path.startswith(str(OUT.relative_to(ROOT)) + '/')}
assert not unexpected, sorted(unexpected)

patch = ''.join(''.join(difflib.unified_diff(
    (CANDIDATE / relative).read_text().splitlines(keepends=True),
    (ROOT / relative).read_text().splitlines(keepends=True),
    fromfile='a/' + relative, tofile='b/' + relative)) for relative in PATHS)
(OUT / 'oracle.patch').write_text(patch)
with tempfile.TemporaryDirectory(prefix='mixer-oracle-patch-check-', dir='/tmp') as temporary:
    scratch = Path(temporary)
    for relative in PATHS:
        target = scratch / relative; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((CANDIDATE / relative).read_bytes())
    git('apply', '--check', str(OUT / 'oracle.patch'), cwd=scratch)
    git('apply', str(OUT / 'oracle.patch'), cwd=scratch)
    assert all((scratch / relative).read_bytes() == (ROOT / relative).read_bytes() for relative in PATHS)

result = {
    'status': 'PASS narrow oracle correction; independent candidate review remains separate',
    'verificationCommand': 'python3 verification/plan-continuation-2026-11-07/android-toggle-oracle/verify_delivery.py',
    'python': sys.version, 'git': git('--version'),
    'baseRevision': manifest['sourceRevision'], 'baseTree': native['sourceTree'],
    'candidateImportManifestPathsVerified': 18,
    'oraclePatchSHA256': sha(OUT / 'oracle.patch'),
    'oraclePatchFiles': {relative: {'candidateSHA256': sha(CANDIDATE / relative),
                                   'correctedSHA256': sha(ROOT / relative)} for relative in PATHS},
    'patchForwardApplicationAndByteComparison': 'passed in disposable scratch',
    'allOtherInstrumentationBytesPreserved': True,
    'productAndPair8ChangesBeyondImportedCandidate': [],
    'sourceClosureSHA256': native['sourceClosureSHA256'],
    'matchingCandidateInputsExceptTwoDiagnosticTests': admission['matchingCandidateInputsExceptTwoTests'],
    'candidateToolsVerified': len(admission['candidateTools']),
    'reusedExactCandidateNativeLibraries': 18, 'swiftRebuilds': 0,
    'native': {'attempts': 1, 'elapsedSeconds': native['elapsedSeconds'], 'api': 37,
               'abi': 'arm64-v8a', 'checks': 11, 'performClickReturn': False,
               'fullSmokePassed': True, 'readiness': 'all three 100 x 20ms checks retained and passed',
               'postconditions': 'input eligibility, exact packet identity/bytes, revision, Swift flag, native checked state/committed presentation, post-toggle pause completion retained and passed'},
    'host': {'fullBRunCount': 1, 'checks': 14662, 'priorChecks': 14655,
             'newFixtureChecks': 7, 'matrixCases': 1323, 'entireMatrixReportIdenticalToCandidate': True,
             'oldUnconditionalTrueLeafRejected': True},
    'cleanup': {'ownedNativeGroupsClosed': len(native['cleanup']['groups']),
                'allLeadersReaped': True, 'ports': cleanup['ports'], 'avdRemoved': True,
                'scratchAndDisposableKeysRemoved': True, 'fullBChildrenReapedAndScratchRemoved': True,
                'fixtureControlChildrenReapedAndScratchRemoved': True,
                'initialImmediatePortObservationRetained': True},
    'parentBaselineByteForBytePreserved': True,
    'heldProcessPolicy': 'no probes or signals targeted historical held identities; only fresh owned groups',
    'publication': 'no commits, push, merges or root metadata edits',
    'limitations': native['limitations'],
}
(OUT / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps(result, indent=2))
