"""Independent bounded review replay. Writes only this review lane and owned scratch."""
import difflib, hashlib, json, os, platform, shutil, signal, socket, subprocess, sys, tarfile, tempfile, time, uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCER = REPO / 'verification/stripe-raw-body-capture'
EXPECTED = '7797a09d3a99f5dabafb681bf2e5bda4bb1f01bc3974beb94176965f9f30546e'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, data): p.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
def files(base): return sorted(p for p in base.rglob('*') if p.is_file())
def load(p): return json.loads(p.read_text())

def audit():
    top = load(PRODUCER/'seal.json')
    actual = {str(p.relative_to(REPO)) for p in files(PRODUCER) if p != PRODUCER/'seal.json'} | {'docs/stripe-raw-body-capture.md'}
    assert set(top) == actual and len(top) == 273
    for path, pin in top.items():
        p = REPO/path
        assert p.stat().st_size == pin['bytes'] and sha(p) == pin['sha256'], path
    archive_count = 0
    for run in sorted(PRODUCER.glob('run-*')):
        nested = load(run/'seal.json')
        assert set(nested) == {str(p.relative_to(run)) for p in files(run) if p.name != 'seal.json'}
        for path, pin in nested.items():
            p = run/path
            assert p.stat().st_size == pin['bytes'] and sha(p) == pin['sha256']
        for archive_name, manifest_name in [('candidate-source-closure.tar.gz', 'source-inputs.json'), ('dependency-source-closure.tar.gz', 'dependency-source-inputs.json')]:
            expected = load(run/manifest_name)
            observed = {}
            with tarfile.open(run/archive_name) as archive:
                for entry in archive:
                    path = PurePosixPath(entry.name)
                    assert entry.isfile() and not path.is_absolute() and '..' not in path.parts and entry.name not in observed
                    observed[entry.name] = hashlib.sha256(archive.extractfile(entry).read()).hexdigest()
            assert observed == expected
            archive_count += len(observed)
        receipt = load(run/'receipt.json')
        assert receipt['cleanup']['scratchRemoved'] is True
    attempts = load(PRODUCER/'attempts.json')
    assert [x['run'] for x in attempts] == [f'run-{i}' for i in range(1, 10)]
    for attempt in attempts:
        assert sha(PRODUCER/attempt['receipt']) == attempt['receiptSHA256']
        assert load(PRODUCER/attempt['receipt'])['failure'] == attempt['failure']
    candidate = PRODUCER/'candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex'
    assert sha(candidate) == EXPECTED
    expected_patch = ''.join(difflib.unified_diff([], candidate.read_text().splitlines(True), fromfile='/dev/null', tofile='b/hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex'))
    assert (PRODUCER/'candidate.patch').read_text() == expected_patch
    selection = load(REPO/'verification/stripe-raw-body-root-review/selection.json')
    for path, digest in selection['bindings'].items(): assert sha(REPO/path) == digest, path
    for path, digest in selection['beamInputs'].items(): assert sha(REPO/path) == digest, path
    for path, digest in selection['sourceInputs'].items(): assert sha(REPO/path) == digest, path
    assert len(selection['sourceInputs']) == 69
    pins = load(PRODUCER/'pinned-dependency-identity.json')
    assert sha(REPO/'hosted/mix.lock') == pins['lockSHA256']
    for path, digest in pins['source'].items(): assert sha(REPO/'hosted/deps'/path) == digest, path
    for path, digest in pins['beams'].items(): assert sha(REPO/'hosted/_build/test/lib'/path) == digest, path
    for path, pin in pins['toolchain'].items(): assert sha(Path(path)) == pin['sha256'], path
    latest = PRODUCER/'run-9'
    clients = load(latest/'wire/clients.json')
    events = load(latest/'wire/events.json')
    by_id = {x['id']: x for x in events}
    assert len(by_id) == len(events) == 95
    assert len({x['id'] for x in clients}) == len(clients) == 105
    correlations = [{'id': c['id'], 'transport': c['transport'], 'statuses': c['statuses'], 'classification': by_id.get(c['id'], {}).get('outcome', 'framework-pre-Plug'), 'event': by_id.get(c['id'])} for c in clients]
    assert load(PRODUCER/'wire-correlations.json') == correlations
    assert all(not any(200 <= x <= 299 for x in c['statuses']) for c in clients)
    assert all(x['verifierCalls'] == (1 if x['outcome'] == 'captured' else 0) for x in events)
    matrix = load(PRODUCER/'matrix.json')
    frozen = load(REPO/'verification/stripe-raw-body-contract/test-matrix.json')
    assert [(x['id'], x['cases']) for x in matrix['rows']] == [(x['id'], x['cases']) for x in frozen['rows']]
    assert len(matrix['rows']) == 13 and matrix['allRowsPassed'] is False
    return {'producerFiles': len(top), 'archiveMemberBindings': archive_count, 'attempts': len(attempts), 'candidateSHA256': EXPECTED,
        'selectionSHA256': sha(REPO/'verification/stripe-raw-body-root-review/selection.json'), 'producerSealSHA256': sha(PRODUCER/'seal.json'),
        'hostedInputs': len(selection['sourceInputs']), 'sourceDigest': hashlib.sha256(json.dumps(selection['sourceInputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'dependencySourcePins': len(pins['source']), 'dependencyBeamPins': len(pins['beams']), 'producerClientCounts': dict(Counter(c['transport'] for c in clients)),
        'producerOutcomes': dict(Counter(c['classification'] for c in correlations)), 'producerCorrelationsExact': True, 'originalMatrixRows': 13}

def derive_wire(original):
    text = original.read_text()
    trace = (HERE/'invocation_trace.exs').read_text()
    text = text.replace('ExUnit.start(autorun: false)', 'ExUnit.start(autorun: false)\n' + trace, 1)
    text = text.replace('    original = conn.adapter\n', '    CaptureReview.InvocationTrace.begin()\n    original = conn.adapter\n', 1)
    text = text.replace('  defp record(id, started, result) do\n', '  defp record(id, started, result) do\n    traced = CaptureReview.InvocationTrace.finish()\n', 1)
    text = text.replace('        id: id,\n        verifierCalls:', '        id: id,\n        tracedVerifierCalls: length(traced),\n        tracedVerifierInputs: traced,\n        verifierCalls:', 1)
    text = text.replace('    assert result.event.verifier == verify\n', '    assert result.event.verifier == verify\n    assert result.event.tracedVerifierCalls == 1\n    assert [%{bodySHA256: digest, signatureValues: signatures}] = result.event.tracedVerifierInputs\n    assert digest == result.event.bodySHA256 and signatures == result.event.signatureValues\n', 1)
    text = text.replace('      assert result.event.verifierCalls == 0 and result.event.domainCalls == 0\n', '      assert result.event.verifierCalls == 0 and result.event.domainCalls == 0\n      assert result.event.tracedVerifierCalls == 0\n', 1)
    text = text.replace('try do\n  summary = ExUnit.run()', (HERE/'additional_wire.exs').read_text() + '\ntry do\n  summary = ExUnit.run()', 1)
    text = text.replace('  :telemetry.detach("capture-synthetic-probe")', '  1 = :erlang.trace_pattern({MixerHosted.Billing.WebhookSignature, :verify, 4}, false, [:local])\n  :telemetry.detach("capture-synthetic-probe")', 1)
    assert text.count('tracedVerifierCalls: length(traced)') == 1
    return text

def main():
    number = 1
    while (HERE/f'run-{number}').exists(): number += 1
    result = HERE/f'run-{number}'
    result.mkdir()
    commands, cleanup, failure = [], {}, None
    scratch = Path(tempfile.mkdtemp(prefix='mixer-stripe-raw-review-'))
    identity = (scratch.stat().st_dev, scratch.stat().st_ino)
    token = str(uuid.uuid4())
    write(scratch/'holder.json', {'token': token, 'pid': os.getpid(), 'device': identity[0], 'inode': identity[1]})
    def run(label, argv, env=None, timeout=60, cwd=None):
        began = time.monotonic()
        process = subprocess.Popen(argv, cwd=cwd or scratch, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        expired = False
        try: output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            if os.getpgid(process.pid) == process.pid: os.killpg(process.pid, signal.SIGTERM)
            try: output, _ = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                if os.getpgid(process.pid) == process.pid: os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate(timeout=3)
        (result/f'{label}.log').write_bytes(output)
        record = {'command': argv, 'cwd': str(cwd or scratch), 'pid': process.pid, 'processGroup': process.pid, 'exitCode': process.returncode, 'timedOut': expired,
            'elapsedSeconds': round(time.monotonic()-began, 3), 'environmentOverrides': {k: env[k] for k in ['CAPTURE_SOURCE_DIR', 'CAPTURE_RESULT_DIR', 'CAPTURE_PHASE'] if env and k in env},
            'resolvedExecutable': os.path.realpath(shutil.which(argv[0])), 'executableSHA256': sha(Path(shutil.which(argv[0])).resolve()), 'output': f'{label}.log', 'outputSHA256': sha(result/f'{label}.log')}
        commands.append(record)
        write(result/'commands.json', commands)
        if expired or process.returncode: raise RuntimeError(f'{label} failed; original output retained')
        return output.decode(errors='replace')
    try:
        audit_result = audit()
        write(result/'integrity.json', audit_result)
        run('producer-verifier', ['python3', '-B', str(PRODUCER/'verify.py')], cwd=REPO)
        run('elixir-version', ['elixir', '--version'])
        run('python-version', ['python3', '--version'])
        run('os-version', ['uname', '-a'])
        otp = run('otp-root', ['elixir', '-e', 'IO.puts(:code.root_dir())']).strip()
        binaries = [Path(sys.executable).resolve(), Path(shutil.which('elixir')).resolve(), Path(shutil.which('erl')).resolve()] + sorted(Path(otp).glob('erts-*/bin/beam.smp'))
        write(result/'toolchain-executables.json', {str(p): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in binaries})
        source = scratch/'source'
        source.mkdir()
        # Archive was already verified entry-by-entry, without following links.
        with tarfile.open(PRODUCER/'run-9/candidate-source-closure.tar.gz') as archive:
            for entry in archive:
                target = source/entry.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(entry).read())
        shutil.copyfile(HERE/'independent.exs', source/'tests/independent.exs')
        original_wire = source/'tests/wire.exs'
        wire_text = derive_wire(original_wire)
        (result/'wire-instrumentation.diff').write_text(''.join(difflib.unified_diff(original_wire.read_text().splitlines(True), wire_text.splitlines(True), fromfile='sealed-producer/tests/wire.exs', tofile='review-derived/tests/wire.exs')))
        original_wire.write_text(wire_text)
        write(result/'source-inputs.json', {str(p.relative_to(source)): sha(p) for p in files(source)})
        with tarfile.open(result/'review-source-closure.tar.gz', 'w:gz') as archive:
            for p in files(source): archive.add(p, arcname=str(p.relative_to(source)), recursive=False)
        cache = scratch/'dependency-cache'
        pins = load(PRODUCER/'pinned-dependency-identity.json')
        for path, digest in pins['beams'].items():
            target = cache/path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO/'hosted/_build/test/lib'/path, target)
            assert sha(target) == digest
        write(result/'dependency-beam-inputs.json', {'reuse': 'copied exact producer-pinned dependency BEAMs; no dependency build', 'inputs': pins['beams']})
        args = ['elixir']
        for path in sorted(cache.glob('*/ebin')): args += ['-pa', str(path)]
        args += [str(source/'tests/boot.exs')]
        for phase in ['component', 'independent', 'wire']:
            output = result/phase
            output.mkdir()
            env = dict(os.environ, CAPTURE_SOURCE_DIR=str(source), CAPTURE_RESULT_DIR=str(output), CAPTURE_PHASE=phase)
            run(phase, args, env=env, timeout=60)
        events = load(result/'wire/events.json')
        clients = load(result/'wire/clients.json')
        by_id = {x['id']: x for x in events}
        assert len(by_id) == len(events)
        assert len(clients) == 110 and len({x['id'] for x in clients}) == 110
        assert all(not any(200 <= s <= 299 for s in c['statuses']) for c in clients)
        for event in events:
            assert event['tracedVerifierCalls'] == event['verifierCalls'] == (1 if event['outcome'] == 'captured' else 0), event['id']
            if event['outcome'] == 'captured':
                [args_seen] = event['tracedVerifierInputs']
                assert args_seen['bodySHA256'] == event['bodySHA256'] and args_seen['bodyBytes'] == event['bodyBytes']
                assert args_seen['signatureValues'] == event['signatureValues'] == event['exposedSignatureValues']
        correlations = [{'id': c['id'], 'statuses': c['statuses'], 'transport': c['transport'], 'classification': by_id.get(c['id'], {}).get('outcome', 'framework-pre-Plug'), 'event': by_id.get(c['id'])} for c in clients]
        write(result/'correlations.json', correlations)
        write(result/'summary.json', {'component': load(result/'component/component-summary.json'), 'independent': load(result/'independent/independent-summary.json'),
            'wire': load(result/'wire/wire-summary.json'), 'clients': len(clients), 'plugOutcomes': len(events), 'transports': dict(Counter(c['transport'] for c in clients)),
            'outcomes': dict(Counter(c['classification'] for c in correlations)), 'actualTracedVerifierCalls': sum(x['tracedVerifierCalls'] for x in events),
            'allTracedInputsMatch': True, 'allNon2xx': True, 'lateHTTP2': by_id['h2-late-success'], 'newHTTP2': by_id['review-h2-declared-split']})
        assert audit() == audit_result, 'sealed producer/current pins changed during review'
    except BaseException as exc:
        failure = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        groups = {x['processGroup'] for x in commands}
        ps = subprocess.run(['ps', '-axo', 'pid=,pgid=,command='], capture_output=True, text=True, timeout=10)
        remaining = []
        for line in ps.stdout.splitlines():
            fields = line.strip().split(None, 2)
            if len(fields) >= 2 and fields[1].isdigit() and int(fields[1]) in groups: remaining.append(line)
        write(result/'owned-process-groups.json', {'groups': sorted(groups), 'remaining': remaining, 'psExit': ps.returncode})
        ports = []
        for path in result.glob('*/listener.json'):
            port = load(path)['port']
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.2): refused = False
            except ConnectionRefusedError: refused = True
            except OSError: refused = False
            ports.append({'port': port, 'connectionRefused': refused})
        holders = subprocess.run(['lsof', '-nP', '+D', str(scratch)], capture_output=True, text=True, timeout=30)
        (result/'scratch-holders.log').write_text(holders.stdout+holders.stderr)
        stat = scratch.stat()
        holder = load(scratch/'holder.json')
        identity_match = (stat.st_dev, stat.st_ino) == identity and holder['token'] == token and holder['pid'] == os.getpid()
        cleanup = {'scratch': str(scratch), 'device': identity[0], 'inode': identity[1], 'holderToken': token, 'holderPID': os.getpid(), 'identityMatched': identity_match,
            'ownedProcessGroupsEmpty': not remaining, 'lsofExit': holders.returncode, 'openHolders': bool(holders.stdout.strip()), 'ports': ports,
            'lsofCommand': ['lsof', '-nP', '+D', str(scratch)], 'processInventoryCommand': ['ps', '-axo', 'pid=,pgid=,command=']}
        if identity_match and not remaining and holders.returncode == 1 and not holders.stdout.strip() and all(x['connectionRefused'] for x in ports): shutil.rmtree(scratch)
        cleanup['scratchRemoved'] = not scratch.exists()
        if not cleanup['scratchRemoved']: failure = failure or {'type': 'CleanupFailure', 'message': 'owned scratch retained due to identity/holder/process/port check'}
        write(result/'receipt.json', {'schema': 1, 'observedUTC': datetime.now(timezone.utc).isoformat(), 'host': platform.platform(), 'candidateSHA256': EXPECTED,
            'commands': commands, 'failure': failure, 'cleanup': cleanup, 'freshCandidateAndSignatureCompilation': True, 'freshDependencyCompilation': False,
            'productionChanged': False, 'producerEvidenceChanged': False, 'nativeStarted': False, 'publicAdmissionAccepted': False, 'g23Accepted': False})
        write(result/'seal.json', {str(p.relative_to(result)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files(result) if p.name != 'seal.json'})
    print(json.dumps({'run': result.name, 'failure': failure, 'cleanup': cleanup}, sort_keys=True))
    if failure: raise SystemExit(1)
if __name__ == '__main__': main()
