#!/usr/bin/env python3
"""Exact frozen-source public File review; no Cargo/native/capture/target use."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
FREEZE = BASE / 'implementation-review-1'
PRODUCER = ROOT / 'verification/swift-ordered-retention-analyzer-envelope'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
SEAL = 'ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(65536): h.update(block)
    return h.hexdigest()

def frozen():
    seal = PRODUCER / 'seal.json'
    assert sha(seal) == SEAL
    value = json.loads(seal.read_text())
    assert len(value['members']) == 796
    for member in value['members']:
        p = ROOT / member['path']
        assert p.stat().st_size == member['bytes'] and sha(p) == member['sha256'], member['path']
    return dict(seal_sha256=SEAL, members=796, bytes=sum(m['bytes'] for m in value['members']))

def main():
    name = sys.argv[1]
    assert name.startswith('run-') and name[4:].isdigit()
    vectors = BASE / 'pre-access-vectors/run-1'
    if len(sys.argv) > 2:
        assert sys.argv[2] == 'profile-correction-1'
        vectors = BASE / 'corrected-vectors' / sys.argv[2]
    run = FREEZE / 'public' / name
    run.mkdir(parents=True)
    scratch = BASE / 'scratch' / ('public-' + name)
    scratch.mkdir(parents=True)
    shutil.copy2(__file__, run / 'executed-runner.py')
    receipt = dict(schema=1, at_unix=time.time(), scope='External33 public safeFile fixture methods against exact frozen source',
                   commands=[], passed=False, native_capture_or_device_execution=False)

    def write():
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')

    def command(label, args, env=None):
        started = time.time()
        child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = child.communicate(timeout=60)
        except subprocess.TimeoutExpired as error:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
            (run / (label + '.stdout')).write_bytes(stdout)
            (run / (label + '.stderr')).write_bytes(stderr)
            receipt['commands'].append(dict(label=label, argv=[str(x) for x in args], timeout_seconds=60, timed_out=True,
                owned_process_group=child.pid,group_killed=True,direct_child_reaped=True,returncode=child.returncode))
            write()
            raise
        result = subprocess.CompletedProcess(args,child.returncode,stdout,stderr)
        (run / (label + '.stdout')).write_bytes(result.stdout)
        (run / (label + '.stderr')).write_bytes(result.stderr)
        receipt['commands'].append(dict(label=label, argv=[str(x) for x in args], cwd=str(ROOT),
            returncode=result.returncode, timeout_seconds=60, elapsed_seconds=time.time()-started,owned_process_group=child.pid,direct_child_reaped=True,
            stdout_sha256=sha(run / (label + '.stdout')), stderr_sha256=sha(run / (label + '.stderr'))))
        write()
        assert result.returncode == 0, label
        return result

    try:
        receipt['producer_before'] = frozen()
        receipt['runtime_vectors'] = str(vectors.relative_to(ROOT))
        receipt['pre_access_manifest_sha256'] = sha(BASE / 'pre-access-vectors/run-1/manifest.json')
        receipt['runtime_profile_sha256'] = sha(vectors / 'profile.bin')
        if (vectors / 'correction.json').exists():
            receipt['fixture_correction'] = json.loads((vectors / 'correction.json').read_text())
        receipt['revision_start'] = command('revision-start', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
        command('python-version', [sys.executable, '--version'])
        command('rust-version', [str(RUSTC), '--version', '--verbose'])
        receipt['tools'] = dict(python=dict(path=sys.executable, sha256=sha(Path(sys.executable)), version=sys.version),
                                rustc=dict(path=str(RUSTC), sha256=sha(RUSTC)))
        harness = BASE / 'public_fixture_harness.rs'
        cases = BASE / 'generated_public_cases.rs'
        assert sha(harness) == '5f25ab8ed4bdacc4b5d6c7e4e8c7ce62bb54f23c0734a893d47e06e9ed54b3e1'
        assert sha(cases) == '15e7e9e20e7ace1c2eb26e5e08fae830118f7bed97005676644babce1492d8d2'
        shutil.copy2(harness, run / 'pre-access-public-harness.rs')
        shutil.copy2(cases, run / 'generated_public_cases.rs')
        # Mechanical getter adapter only: actual enum getters borrow non-Copy
        # enums. All pre-access expected values and fixtures remain unchanged.
        text = harness.read_text()
        text = text.replace('Decision, ReplayOutcome}', 'Decision, ReplayOutcome, FixtureEnvelopeBoundaryV1, FixtureEnvelopeReasonV1}')
        text = text.replace('envelope.boundary() as u64', 'boundary_id(envelope.boundary())')
        text = text.replace('envelope.reason() as u64', 'reason_id(envelope.reason())')
        boundary_names = ['Unavailable', 'ClosedEnvelopeObserved', 'CapCutUnknownTail', 'Refused', 'AnalysisLimited', 'InternalPoisoned']
        reason_names = ['Observed', 'Steps', 'Shape', 'Coordinate', 'TerminalPhase', 'Phase', 'ReleaseOpen', 'TerminalFailure', 'PinFailure', 'ForbiddenResume', 'Acquire', 'Identity', 'Stage', 'PublicationForm', 'CheckedAccess', 'InternalPoisoned', 'FramingUnavailable', 'FramingInvalid', 'FramingLimited', 'EnvelopeUnavailable', 'UnavailableState', 'IncompleteBoundary']
        adapter = ''
        for function, kind, names in [('boundary_id', 'FixtureEnvelopeBoundaryV1', boundary_names), ('reason_id', 'FixtureEnvelopeReasonV1', reason_names)]:
            adapter += f'fn {function}(value: &{kind}) -> u64 {{ match value {{\n'
            adapter += ''.join(f'    {kind}::{name} => {index},\n' for index, name in enumerate(names))
            adapter += '} }\n'
        text = text.replace('struct Expected {', adapter + '\nstruct Expected {')
        adapted = run / 'public-harness.rs'; adapted.write_text(text)
        library = run / 'libmixer_fixture_envelope.rlib'
        source = FREEZE / 'sources/src/analyzer.rs'
        receipt['source_hashes'] = dict(analyzer=sha(source), envelope=sha(source.with_name('envelope.rs')),
            original_harness=sha(harness), adapted_harness=sha(adapted), generated_cases=sha(cases))
        command('compile-library', [str(RUSTC), '--edition=2021', '--crate-name=mixer_fixture_envelope', '--crate-type=lib', '-Dwarnings', str(source), '-o', str(library)])
        binary = run / 'public-tests'
        command('compile-public-tests', [str(RUSTC), '--edition=2021', '--test', '-Dwarnings', str(adapted), '--extern', 'mixer_fixture_envelope=' + str(library), '-o', str(binary)])
        env = dict(os.environ, MIXER_ENVELOPE_REVIEW_VECTORS=str(vectors),
                   MIXER_ENVELOPE_REVIEW_OUTPUT=str(scratch), PYTHONDONTWRITEBYTECODE='1')
        receipt['test_environment'] = {key: env[key] for key in ['MIXER_ENVELOPE_REVIEW_VECTORS', 'MIXER_ENVELOPE_REVIEW_OUTPUT', 'PYTHONDONTWRITEBYTECODE']}
        result = command('public-tests', [str(binary), '--test-threads=1', '--nocapture'], env)
        assert b'33 passed; 0 failed' in result.stdout
        receipt['methods_passed'] = 33
        receipt['passed'] = True
    except BaseException:
        (run / 'exception.stderr').write_text(traceback.format_exc())
        raise
    finally:
        receipt['producer_after'] = frozen()
        assert receipt['producer_before'] == receipt['producer_after']
        receipt['revision_end'] = command('revision-end', ['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
        if any(scratch.iterdir()): shutil.move(str(scratch), str(run / 'retained-public-files'))
        else: scratch.rmdir()
        if not any(scratch.parent.iterdir()): scratch.parent.rmdir()
        receipt['cleanup'] = 'Exact owned scratch archived/removed after synchronous children returned; no process discovery'
        write()
    print(json.dumps(dict(passed=receipt['passed'], methods=receipt.get('methods_passed', 0), receipt=str((run/'receipt.json').relative_to(ROOT)))))

if __name__ == '__main__': main()
