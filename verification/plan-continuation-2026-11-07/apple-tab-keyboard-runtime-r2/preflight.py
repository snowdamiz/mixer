#!/usr/bin/env python3
"""Fresh read-only preflight of the unchanged accepted dispatcher."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = HERE.parent
OLD = PARENT / 'apple-settings-runtime-r2'
DEV = '/Applications/Xcode_26.6.app/Contents/Developer'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def put(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')

def identity(path):
    info = path.lstat()
    assert path.resolve() == path and stat.S_ISREG(info.st_mode), str(path)
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=sha(raw), mode=stat.S_IMODE(info.st_mode))

def main():
    assert not (HERE / 'preflight.json').exists(), 'No preflight replay'
    scratch = Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-tab-keyboard-r2-', dir='/private/tmp')).resolve()
    put('scratch-custody.json', dict(path=str(scratch), inode=scratch.stat().st_ino))
    commands = []
    env = {**os.environ, 'DEVELOPER_DIR': DEV, 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(scratch)}
    selected_path = PARENT / 'apple-tab-keyboard-root-selection.json'
    selected = json.loads(selected_path.read_bytes())
    assert selected['rootSelected'] and selected['maximumNativeAttempts'] == 1 and selected['builds'] == 0
    assert selected['originalTwoAttemptBudget'] == dict(previouslyConsumed=1, selectedRemaining=1, automaticRetries=0)
    watched = {str(selected_path): identity(selected_path)}
    for binding in [selected['experiment'], *selected['bindings'].values()]:
        if isinstance(binding, dict) and 'path' in binding:
            p = REPO / binding['path']
            watched[str(p)] = identity(p)
            assert watched[str(p)]['sha256'] == binding['sha256'], str(p)
    for name in ['packet.json', 'dispatch_successor.py', 'run_r2.py', 'materialize.py', 'result.json', 'one-attempt-marker.json', 'raw-artifacts.json', 'relocated-source-custody.json']:
        watched[str(OLD / name)] = identity(OLD / name)
    restored = []
    for group in json.loads((OLD / 'relocated-source-custody.json').read_bytes()):
        original, retained = Path(group['originalPath']), Path(group['retainedPath'])
        for name, row in group['members'].items():
            before, kept = identity(original / name), identity(retained / name)
            assert before == kept and all(before[k] == row[k] for k in ['bytes', 'sha256']), name
            watched[str(original / name)] = before
            watched[str(retained / name)] = kept
        restored.append(dict(original=str(original), retained=str(retained), files=len(group['members']), exactBytesAndModes=True))
    manifest = json.loads((OLD / 'raw-artifacts.json').read_bytes())
    for name, row in manifest['members'].items():
        p = Path(manifest['root']) / name
        actual = identity(p)
        assert all(actual[k] == row[k] for k in ['bytes', 'sha256']), name
        watched[str(p)] = actual
    def command(label, argv, timeout=45, frontend=False):
        start = time.monotonic()
        p = subprocess.run(argv, env=env, cwd=REPO, capture_output=True, timeout=timeout)
        out = p.stdout
        if frontend:
            executable = DEV + '/Applications/Simulator.app/Contents/MacOS/Simulator'
            out = ('\n'.join(line.strip() for line in out.decode().splitlines() if line.strip().endswith(executable)) + '\n').encode()
        (HERE / (label + '.stdout')).write_bytes(out)
        (HERE / (label + '.stderr')).write_bytes(p.stderr)
        commands.append(dict(argv=argv, cwd=str(REPO), at=datetime.datetime.now(datetime.timezone.utc).isoformat(), exitCode=p.returncode, seconds=time.monotonic()-start, stdoutSHA256=sha(out), stderrSHA256=sha(p.stderr), retainedStdoutScope='Pinned Simulator frontend identities only' if frontend else 'complete'))
        assert p.returncode == 0, label
        return out.decode()
    environment = dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), python=sys.version, developerDirectory=DEV, scratch=str(scratch))
    for label, argv in [('os',['/usr/bin/sw_vers']),('xcode',[DEV+'/usr/bin/xcodebuild','-version']),('sdk',['/usr/bin/xcrun','--sdk','iphonesimulator','--show-sdk-version']),('revision',['/usr/bin/git','rev-parse','HEAD']),('runtimes',['/usr/bin/xcrun','simctl','list','runtimes','--json']),('simulators-before',['/usr/bin/xcrun','simctl','list','devices','--json'])]:
        environment[label] = command(label, argv)
    frontends = command('frontends-before',['/bin/ps','-axo','pid=,lstart=,comm='],frontend=True).splitlines()
    put('external-baseline.json',dict(devices=json.loads(environment['simulators-before']),frontends=frontends))
    runtime = next(r for r in json.loads(environment['runtimes'])['runtimes'] if r['identifier'] == 'com.apple.CoreSimulator.SimRuntime.iOS-26-5')
    assert runtime['buildversion'] == '23F77' and runtime['isAvailable']
    put('environment.json', environment)
    spec = importlib.util.spec_from_file_location('_unchanged_accepted_dispatcher', OLD / 'dispatch_successor.py')
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)
    markers = {str(p):identity(p) for p in (dispatcher.BASE/'dispatch-attempts').glob('*.json')}
    phase = dict(verifier=True)
    denied = []
    def audit(event,args):
        if phase['verifier'] and (event in ['subprocess.Popen','os.system','os.kill','os.killpg','os.posix_spawn','os.exec'] or event.startswith('socket.')):
            denied.append(event)
            raise RuntimeError('Read-only verifier forbids: '+event)
    sys.addaudithook(audit)
    try:
        verified = dispatcher.verify()
    finally:
        phase['verifier'] = False
    assert verified['nativeExecuted'] is False
    assert markers == {str(p):identity(p) for p in (dispatcher.BASE/'dispatch-attempts').glob('*.json')}
    assert watched == {p:identity(Path(p)) for p in watched}
    put('input-identities.json', watched)
    put('commands-preflight.json', commands)
    put('preflight.json',dict(verified=verified,unchangedDispatcherSHA256=identity(OLD/'dispatch_successor.py')['sha256'],restoration=restored,blockedNativeOperations=denied,dispatchCalled=False,markersUnchanged=True,selectedEnvironmentExperimentSHA256=identity(selected_path)['sha256'],checkedInputFiles=len(watched),nativeAttempts=0,builds=0))
    print(json.dumps(dict(preflight='passed',verified=verified,externalFrontends=frontends,scratch=str(scratch))))

if __name__ == '__main__':
    main()
