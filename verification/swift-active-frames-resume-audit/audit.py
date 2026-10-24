#!/usr/bin/env python3
"""Bounded offline audit. Does not compile, run retained binaries, or use native UI."""
from pathlib import Path
from datetime import datetime, timezone
import collections
import hashlib
import json
import shutil
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-active-frames-implementation'
REVIEW = ROOT / 'verification/swift-active-frames-implementation-review'
FINAL = '4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
BASELINE = '4df46815f8a9b30db00dda35ed97603da229ac3be957d3f27df38ed2ac56a7c9'
HISTORICAL = 'f10e1fef4a86baf8a0406e925622d7ac48a36aca276f3baa4a6e858d806b257b'


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    out = HERE / 'results' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    receipt = dict(schema=1, startedUTC=now(), scope='Saved private host packet integrity, exact source, lineage and bounded ownership review; root acceptance remains separate.',
                   commands=[], findings=[], remainingBlockingFindings=[],
                   activity=dict(compilation=False, retainedBinaryExecution=False, computerUse=False,
                                 screenCapture=False, nativeRuntime=False, physicalDevice=False,
                                 commits=False, pushes=False, productEdits=False, originalEvidenceEdits=False),
                   pending=['Root source acceptance and coherent delivery', 'Public invocation, dispatcher and initialized lifecycle',
                            'Native and physical device matrix under current pause', 'Published separate-repository FieldLog, signing, store/customer and GA evidence'])

    def command(name, argv):
        started = now()
        result = subprocess.run(argv, cwd=ROOT, capture_output=True)
        stdout, stderr = out / (name + '.stdout'), out / (name + '.stderr')
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        receipt['commands'].append(dict(name=name, argv=argv, cwd=str(ROOT), startedUTC=started,
            completedUTC=now(), exitCode=result.returncode, stdout=stdout.name, stderr=stderr.name,
            stdoutSHA256=sha(stdout), stderrSHA256=sha(stderr)))
        assert result.returncode == 0, (name, result.stderr.decode(errors='replace'))
        return result.stdout.decode()

    inputs = [ROOT / 'AGENTS.md', ROOT / 'docs/implementation-pause-2026-10-24.md',
              ROOT / 'docs/swift-active-frames-implementation.md', ROOT / 'docs/swift-active-frames-implementation-review.md',
              PRODUCER / 'final-receipt.json', PRODUCER / 'seal.json', PRODUCER / 'verify.py',
              REVIEW / 'decision.json', REVIEW / 'review-seal.json', REVIEW / 'verify_review.py', REVIEW / 'verify.py',
              REVIEW / 'source-review.json', HERE / 'audit.py', HERE / 'measure_delivery.py', ROOT / 'docs/swift-active-frames-resume-audit.md']
    try:
        receipt['inputFiles'] = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
        receipt['currentHEAD'] = command('head', ['git', 'rev-parse', 'HEAD']).strip()
        command('status', ['git', 'status', '--short'])
        receipt['tools'] = dict(python=command('python-version', [sys.executable, '--version']).strip(),
            git=command('git-version', ['git', '--version']).strip(),
            currentRustc=shutil.which('rustc'), currentCargo=shutil.which('cargo'),
            rustcUse='No compiler invoked by this audit; saved version is evidence, not a current compile claim',
            savedRustc=(PRODUCER / 'results/20261024T050444826239Z/rustc-version.stdout').read_text().strip(),
            savedCargo=(PRODUCER / 'results/20261024T050444826239Z/cargo-version.stdout').read_text().strip())
        receipt['providedVerifierResults'] = [
            json.loads(command('producer-verifier', [sys.executable, str(PRODUCER / 'verify.py'), '--check-worktree'])),
            json.loads(command('independent-review-verifier', [sys.executable, str(REVIEW / 'verify_review.py')]))]
        final = read(PRODUCER / 'final-receipt.json')
        decision = read(REVIEW / 'decision.json')
        seal = read(PRODUCER / 'seal.json')
        review_seal = read(REVIEW / 'review-seal.json')
        assert final['finalSource']['sourceTreeSHA256'] == decision['sourceTreeSHA256'] == FINAL
        assert seal['finalCandidateTree'] == review_seal['sourceTreeSHA256'] == FINAL
        assert sha(PRODUCER / 'final-receipt.json') == seal['finalReceiptSHA256']
        assert sha(ROOT / 'docs/swift-active-frames-implementation.md') == seal['implementationDocumentSHA256']
        assert sha(ROOT / 'docs/swift-active-frames-implementation-review.md') == decision['reviewDocumentSHA256'] == review_seal['reviewDocument']['sha256']
        for key, path in [('decision', REVIEW / 'decision.json'), ('seal', REVIEW / 'review-seal.json')]:
            ref = final['independentReview'][key]
            assert sha(PRODUCER / ref['path']) == ref['sha256'] == sha(path)
        assert not decision['remainingBlockingReviewFindings']
        assert not any(final['scope'].values())
        manifest = read(PRODUCER / final['finalSource']['manifest']['path'])
        baseline = read(PRODUCER / final['baselineSource']['manifest']['path'])
        source_paths = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock'] + [p for d in ['src', 'tests', 'include'] for p in sorted((ROOT / 'vm' / d).rglob('*')) if p.is_file()]
        actual = {str(p.relative_to(ROOT / 'vm')): sha(p) for p in source_paths}
        assert actual == manifest and len(actual) == 119
        assert hashlib.sha256(encoded(actual)).hexdigest() == FINAL
        changed = {name: digest for name, digest in actual.items() if baseline.get(name) != digest}
        assert len(changed) == 8 and not set(baseline) - set(actual)
        receipt['source'] = dict(treeSHA256=FINAL, baselineSHA256=BASELINE, files=119,
                                exactCurrentClosure=True, changedOrAdded=changed)
        commands = final['commands']
        assert len(commands) == 229 and sum(c['reused'] for c in commands) == 204
        origins = collections.Counter()
        for item in commands:
            assert item['sourceTreeSHA256'] in [None, FINAL, BASELINE]
            assert item['executionOrigin'] == item['importChain'][-1]
            previous = None
            for link in item['importChain']:
                origin = PRODUCER / link['receipt']['path']
                assert sha(origin) == link['receipt']['sha256']
                entry = next(c for c in read(origin)['commands'] if c['name'] == item['name'])
                assert entry['sourceTreeSHA256'] == link['sourceTreeSHA256'] == item['sourceTreeSHA256']
                for stream in ['stdout', 'stderr']:
                    assert sha(origin.parent / entry[stream]) == entry[stream + 'SHA256'] == item[stream]['sha256']
                if previous:
                    assert Path(previous['reusedFromReceipt']).parts[-2:] == origin.parts[-2:]
                    for key in ['argv', 'startedUTC', 'completedUTC', 'exitCode', 'sourceTreeSHA256', 'stdoutSHA256', 'stderrSHA256']:
                        assert previous[key] == entry[key]
                previous = entry
            assert not previous.get('reusedFromReceipt')
            assert item['reused'] == (len(item['importChain']) > 1)
            if item['name'].endswith('-run'):
                expected = '20261024T050048420640Z' if item['name'].startswith('candidate-') else '20261024T045149763486Z'
                assert expected in item['executionOrigin']['receipt']['path']
                assert item['executionOrigin']['sourceTreeSHA256'] == (FINAL if expected.endswith('050048420640Z') else BASELINE)
                origins[expected] += 1
        assert HISTORICAL not in json.dumps(commands)
        receipt['lineage'] = dict(commandRecords=229, reused=204, fresh=25, runtimeOrigins=dict(origins), historicalCandidateCounted=False)
        host = read(PRODUCER / final['hostReceipt']['path'])
        lint = read(PRODUCER / Path(final['hostReceipt']['path']).parent / 'broad-clippy-identities.json')
        assert lint['baseline'] == lint['candidate'] and len(lint['candidate']) == 26
        for c in host['commands']:
            if 'clippy-broad' in c['name']:
                assert c['exitCode'] == 101
        receipt['baselineClippy'] = dict(priorIdentities=26, exactSourceAssociatedIdentityParity=True, broadLintPassed=False)
        expected = {'production': dict(permanent=1086648, executionHeader=1378536, active=929872, frame=1049448, originalValue=119576, state=424),
                    'unit': dict(permanent=1945656, executionHeader=2238504, active=1505296, frame=1624872, originalValue=119576, state=424)}
        for layout in final['accounting']['layouts']:
            mode = 'unit' if layout['label'].endswith('-unit') else 'production'
            assert all(layout['bytes'][key] == value for key, value in expected[mode].items())
            assert layout['fieldCount'] == (17865 if mode == 'unit' else 9345)
        assert len(final['accounting']['layouts']) == 8
        receipt['accounting'] = dict(bounds=expected, productionFields=9345, unitFields=17865,
                                    frozenFields=1061, supplementalFields=16804, metadataLayouts=8,
                                    logicalOwnershipOnly=True, optimizerStackBoundClaim=False)
        receipt['portability'] = dict(producerRuntimeArtifacts=100, producerMetadataArtifacts=8,
                                     independentRuntimeArtifacts=20, independentMetadataArtifacts=2,
                                     originalCargoTargetsRequired=False, retainedBinariesExecuted=False,
                                     bothFullSealsVerified=True, producerSealedPaths=len(seal['files']), reviewerSealedPaths=len(review_seal['files']))
        receipt['review'] = dict(status=decision['status'], correctedFindings=decision['correctedFindings'],
                                independentlySavedProbeExecutions=40, independentlySavedCandidateUnitExecutions=682,
                                blockerFoundInBoundedOwnershipRecheck=False,
                                af15CapacityCase='Derived defensive-boundary injection; not naturally reachable from a valid returned owner')
        receipt['delivery'] = json.loads(command('delivery-measurements', [sys.executable, str(HERE / 'measure_delivery.py')]))
        assert receipt['inputFiles'] == {str(p.relative_to(ROOT)): sha(p) for p in inputs}
        assert {str(p.relative_to(ROOT / 'vm')): sha(p) for p in source_paths} == actual
        receipt['status'] = 'passed-bounded-offline-resume-audit-root-acceptance-pending'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['remainingBlockingFindings'].append(repr(error))
        receipt['traceback'] = traceback.format_exc()
    receipt['completedUTC'] = now()
    (out / 'receipt.json').write_bytes(encoded(receipt))
    print(json.dumps(dict(status=receipt['status'], receipt=str((out / 'receipt.json').relative_to(ROOT)),
                          remainingBlockingFindings=receipt['remainingBlockingFindings']), sort_keys=True, indent=2))
    return 0 if receipt['status'].startswith('passed-') else 1


if __name__ == '__main__':
    sys.exit(main())
