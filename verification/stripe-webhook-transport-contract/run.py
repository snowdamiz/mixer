"""Isolated pinned API probe. No production app startup or repository/Git actions."""
import hashlib, json, os, platform, shutil, signal, socket, subprocess, sys, tarfile, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')

def main():
    number = 1
    while (HERE / f'run-{number}').exists():
        number += 1
    result = HERE / f'run-{number}'
    result.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix='mixer-transport-contract-'))
    identity = [scratch.stat().st_dev, scratch.stat().st_ino]
    (scratch / 'owned.json').write_text(json.dumps({'pid': os.getpid(), 'identity': identity}))
    commands = []
    failure = None

    def run(label, argv, env=None, timeout=30):
        started = time.monotonic()
        proc = subprocess.Popen(argv, cwd=scratch, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        expired = False
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate(timeout=5)
        path = result / f'{label}.log'
        path.write_bytes(output)
        executable = Path(shutil.which(argv[0])).resolve()
        commands.append({'command': argv, 'cwd': str(scratch), 'environmentOverrides': {k: v for k, v in (env or {}).items() if k.startswith('TRANSPORT_')}, 'resolvedExecutable': str(executable), 'executableSHA256': sha(executable), 'pid': proc.pid, 'processGroup': proc.pid, 'exitCode': proc.returncode, 'timedOut': expired, 'elapsedSeconds': round(time.monotonic() - started, 3), 'output': path.name, 'outputSHA256': sha(path)})
        write(result / 'commands.json', commands)
        if proc.returncode or expired:
            raise RuntimeError(f'{label} failed; retained unmodified attempt')
        return output.decode().strip()

    try:
        pins = json.loads((REPO / 'verification/stripe-raw-body-capture/pinned-dependency-identity.json').read_text())
        assert sha(REPO / 'hosted/mix.lock') == pins['lockSHA256']
        for name, digest in pins['source'].items():
            assert sha(REPO / 'hosted/deps' / name) == digest, name
        for name, digest in pins['beams'].items():
            assert sha(REPO / 'hosted/_build/test/lib' / name) == digest, name
        for name, value in pins['toolchain'].items():
            assert sha(Path(name)) == value['sha256'], name
        integration = json.loads((REPO / 'verification/stripe-raw-body-integration/acceptance.json').read_text())
        for name, digest in integration['sourceInputs'].items():
            assert sha(REPO / name) == digest, name
        names = ['AGENTS.md', 'PLAN.md', 'mixer-product-plan.md', 'THIRD_PARTY.yml', 'docs/stripe-raw-body-direction.md', 'docs/stripe-raw-body-contract.md', 'docs/stripe-raw-body-capture.md', 'docs/stripe-raw-body-capture-review.md', 'verification/stripe-raw-body-integration/acceptance.json', 'verification/stripe-raw-body-capture/pinned-dependency-identity.json', 'verification/stripe-raw-body-capture/seal.json', 'verification/stripe-raw-body-capture/run-9/seal.json', 'verification/stripe-raw-body-capture/transport-observations.json', 'verification/stripe-raw-body-capture-review/seal.json', 'verification/stripe-raw-body-capture-review/review.json', 'verification/stripe-raw-body-capture-review/run-1/seal.json'] + list(integration['sourceInputs'])
        frozen = scratch / 'source'
        for name in sorted(set(names)):
            dest = frozen / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, dest)
        shutil.copyfile(HERE / 'probe.exs', frozen / 'probe.exs')
        shutil.copyfile(HERE / 'run.py', frozen / 'run.py')
        source_inputs = {str(p.relative_to(frozen)): sha(p) for p in sorted(frozen.rglob('*')) if p.is_file()}
        write(result / 'source-inputs.json', source_inputs)
        with tarfile.open(result / 'source-closure.tar.gz', 'w:gz') as archive:
            for p in sorted(frozen.rglob('*')):
                if p.is_file():
                    archive.add(p, arcname=str(p.relative_to(frozen)), recursive=False)
        write(result / 'dependency-source-inputs.json', pins['source'])
        write(result / 'dependency-beam-inputs.json', pins['beams'])
        shutil.copyfile(REPO / 'verification/stripe-raw-body-capture/run-9/dependency-source-closure.tar.gz', result / 'dependency-source-closure.tar.gz')
        cache = scratch / 'dependency-cache'
        for app in sorted((REPO / 'hosted/_build/test/lib').iterdir()):
            if app.name != 'mixer_hosted' and (app / 'ebin').is_dir():
                shutil.copytree(app / 'ebin', cache / app.name / 'ebin')
        run('elixir-version', ['elixir', '--version'])
        run('python-version', ['python3', '--version'])
        run('os-version', ['uname', '-a'])
        otp_root = run('otp-root', ['elixir', '-e', 'IO.puts(:code.root_dir())'])
        binaries = [Path(sys.executable).resolve(), Path(shutil.which('elixir')).resolve(), Path(shutil.which('erl')).resolve()] + sorted(Path(otp_root).glob('erts-*/bin/beam.smp'))
        write(result / 'toolchain-executables.json', {str(p): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in binaries})
        args = ['elixir']
        for path in sorted(cache.glob('*/ebin')):
            args += ['-pa', str(path)]
        args += [str(frozen / 'probe.exs')]
        env = dict(os.environ, TRANSPORT_CAPTURE_SOURCE=str(frozen / 'hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex'), TRANSPORT_RESULT_DIR=str(result))
        run('probe', args, env, timeout=30)
    except BaseException as exc:
        failure = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        groups = {c['processGroup'] for c in commands}
        inventory = subprocess.run(['ps', '-axo', 'pid=,pgid=,command='], capture_output=True, text=True, timeout=10)
        remaining = [line for line in inventory.stdout.splitlines() if len(parts := line.split(None, 2)) >= 2 and parts[1].isdigit() and int(parts[1]) in groups]
        write(result / 'owned-process-groups.json', {'groups': sorted(groups), 'remaining': remaining, 'command': ['ps', '-axo', 'pid=,pgid=,command='], 'exitCode': inventory.returncode})
        ports = []
        if (result / 'listener.json').exists():
            port = json.loads((result / 'listener.json').read_text())['port']
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.2):
                    refused = False
            except ConnectionRefusedError:
                refused = True
            except OSError:
                refused = False
            ports.append({'port': port, 'connectionRefused': refused})
        holders = subprocess.run(['lsof', '-nP', '+D', str(scratch)], capture_output=True, text=True, timeout=20)
        (result / 'scratch-holders.log').write_text(holders.stdout + holders.stderr)
        same = identity == [scratch.stat().st_dev, scratch.stat().st_ino] and json.loads((scratch / 'owned.json').read_text())['pid'] == os.getpid()
        cleanup = {'scratch': str(scratch), 'identity': identity, 'identityMatched': same, 'lsofCommand': ['lsof', '-nP', '+D', str(scratch)], 'lsofExitCode': holders.returncode, 'openHolders': bool(holders.stdout.strip()), 'ownedProcessGroupsEmpty': not remaining, 'ports': ports}
        if same and not remaining and holders.returncode == 1 and not holders.stdout.strip() and all(v['connectionRefused'] for v in ports):
            shutil.rmtree(scratch)
        cleanup['scratchRemoved'] = not scratch.exists()
        if not cleanup['scratchRemoved']:
            failure = failure or {'type': 'CleanupFailure', 'message': 'Owned scratch retained'}
        write(result / 'receipt.json', {'schema': 1, 'observedUTC': datetime.now(timezone.utc).isoformat(), 'host': platform.platform(), 'sourceDigest': integration.get('sourceDigest') if 'integration' in locals() else None, 'sourceRevisionFromAcceptance': integration.get('sourceParent') if 'integration' in locals() else None, 'dependencySourcesChecked': len(pins['source']) if 'pins' in locals() else None, 'dependencyBeamsChecked': len(pins['beams']) if 'pins' in locals() else None, 'freshCaptureCompilation': True, 'freshDependencyCompilation': False, 'failure': failure, 'cleanup': cleanup, 'commands': commands, 'productionChanged': False, 'publicAdmissionAccepted': False, 'providerContacted': False, 'nativeStarted': False})
        write(result / 'seal.json', {str(p.relative_to(result)): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(result.rglob('*')) if p.is_file() and p.name != 'seal.json'})
    print(json.dumps({'run': result.name, 'failure': failure, 'cleanup': cleanup}, sort_keys=True))
    if failure:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
