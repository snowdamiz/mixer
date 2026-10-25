#!/usr/bin/env python3
"""Isolated credit attribution preparation. Target requires fresh exact root selection."""
import argparse, datetime, difflib, hashlib, json, os
from pathlib import Path
import platform, resource, shutil, signal, subprocess, sys, time
from transform import transform

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = HERE / 'source'
SCRATCH = HERE / 'owned-scratch'
TARGET = SCRATCH / 'target'
BINARY = HERE / 'bin/attribution-tests'
CLOSURE = 'b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11'
PREPARATION = ROOT / 'verification/swift-cache-work-attribution-root-selection/preparation.json'
PREPARATION_HASH = '0f6538d299958465f47fb87e2041f33cdb9d433305e92abeb20ee63c68a8596c'
PROPOSAL = ROOT / 'verification/swift-cache-remaining-work-diagnosis/instrumentation-proposal.json'
PROPOSAL_HASH = '40f76f897aee8aa113755afe37fbfcade7f93ff919d620d5f7a40370774d95ba'
REACTOR = ROOT / 'compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm'
REACTOR_HASH = '24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
PREFIX = 'experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::tests::work_attribution_diagnostic::'
CONTROL_PREFIX = 'experimental_swift_reactor::cache_tests::'
CHANGED = ['src/experimental/cache/borrowed.rs', 'src/experimental_swift_reactor/cache.rs', 'src/experimental_swift_reactor/cache_tests.rs', 'src/experimental_swift_reactor/lifecycle_tests.rs']
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def save(path, value):
    path = HERE / path; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def identity(path):
    path = Path(path)
    return {'path': str(path), 'resolvedPath': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': sha(path)}
def source_manifest(directory):
    paths = [directory / 'Cargo.toml', directory / 'Cargo.lock']
    paths += [p for top in ('include', 'src', 'tests') for p in (directory / top).rglob('*') if p.is_file()]
    return {str(p.relative_to(directory)): sha(p) for p in sorted(paths)}
def closure(value): return hashlib.sha256((json.dumps(value, indent=2, sort_keys=True)+'\n').encode()).hexdigest()
def environment():
    env = {k: os.environ[k] for k in ('HOME', 'USER', 'LOGNAME') if k in os.environ}
    env.update(PATH='/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
               CARGO_NET_OFFLINE='true', CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='2',
               CARGO_TARGET_DIR=str(TARGET), TMPDIR=str(SCRATCH/'tmp'), RUST_TEST_THREADS='1')
    return env
def tools():
    result = {'python': identity(sys.executable), 'pythonVersion': sys.version, 'system': platform.platform(), 'machine': platform.machine()}
    for name, flags in [('rustc', ['-vV']), ('cargo', ['-V'])]:
        tool = Path(shutil.which(name, path=environment()['PATH']))
        result[name] = identity(tool) | {'version': subprocess.check_output([str(tool), *flags], env=environment(), text=True, stderr=subprocess.PIPE).strip()}
    return result
def assert_baseline():
    baseline = read(HERE/'baseline-manifest.json')
    assert len(baseline) == 132 and closure(baseline) == CLOSURE
    assert source_manifest(ROOT/'vm') == baseline, 'live 132-file baseline drift'
    current = source_manifest(SOURCE)
    assert [n for n in baseline if baseline[n] != current[n]] == CHANGED
    assert all((SOURCE/n).read_bytes() == transform(n, (ROOT/'vm'/n).read_bytes()) for n in baseline)
    assert current == read(HERE/'copied-source-manifest.json')
    return current
def assert_inputs():
    binding = read(HERE/'binding.json')
    for info in binding['inputs']: assert identity(info['path']) == info, info['path']
    assert identity(REACTOR) == binding['target']
    assert sha(PREPARATION) == PREPARATION_HASH and sha(PROPOSAL) == PROPOSAL_HASH
    assert REACTOR.stat().st_size == 53_777_114 and sha(REACTOR) == REACTOR_HASH
    for name, digest in binding['authoredInputs'].items(): assert sha(HERE/name) == digest, name
def prepare():
    assert not (HERE/'binding.json').exists() and not SOURCE.exists() and not SCRATCH.exists()
    assert sha(PREPARATION) == PREPARATION_HASH and sha(PROPOSAL) == PROPOSAL_HASH
    baseline = read(ROOT/'verification/swift-exact-reactor-after-cache/baseline-manifest.json')
    assert len(baseline) == 132 and closure(baseline) == CLOSURE and source_manifest(ROOT/'vm') == baseline
    save('baseline-manifest.json', baseline)
    for name in baseline:
        destination = SOURCE/name; destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(transform(name, (ROOT/'vm'/name).read_bytes()))
    save('copied-source-manifest.json', source_manifest(SOURCE))
    (HERE/'instrumentation.patch').write_text(''.join(''.join(difflib.unified_diff((ROOT/'vm'/name).read_text().splitlines(True), (SOURCE/name).read_text().splitlines(True), fromfile='vm/'+name, tofile='isolated/'+name)) for name in CHANGED))
    (SCRATCH/'tmp').mkdir(parents=True, mode=0o700)
    refs = [ROOT/'AGENTS.md', PREPARATION, PROPOSAL,
            ROOT/'verification/swift-cache-remaining-work-diagnosis/seal.json',
            ROOT/'verification/swift-cache-remaining-work-diagnosis/verify.py',
            ROOT/'verification/swift-exact-reactor-after-cache/binding.json',
            ROOT/'verification/swift-exact-reactor-after-cache/harness.rs',
            ROOT/'verification/swift-exact-reactor-after-cache/diagnostic.py',
            ROOT/'verification/swift-exact-reactor-after-cache/result-seal.json']
    # Prior packet paths are immutable data references only; no prior driver import/run.
    binding = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sourceRevisionContext': read(ROOT/'verification/swift-cache-remaining-work-diagnosis/receipt.json')['sourceRevisionAtFixture'],
        'sourceRevisionScope': 'historical diagnosis context only; exact current 132-file baseline digest is authoritative; no Git operation',
        'baselineClosure': CLOSURE, 'inputs': [identity(p) for p in refs], 'target': identity(REACTOR),
        'authoredInputs': {n: sha(HERE/n) for n in ('observer.rs','controls.rs','transform.py','harness.rs','driver.py','test_driver.py')},
        'tools': tools(), 'fullTargetSelected': False, 'targetExecuted': False,
        'selectedScope': 'isolated preparation and finite actual-cache controls only',
        'priorAfterCachePacket': 'immutable method/data; no rerun', 'forbiddenLanesReadOrExecuted': False}
    save('binding.json', binding); assert_baseline(); assert_inputs()
    record_command('diagnosis-verify', [sys.executable, '-B', str(ROOT/'verification/swift-cache-remaining-work-diagnosis/verify.py')], 30, cwd=ROOT)
    print(json.dumps({'prepared': True, 'targetExecuted': False, 'liveClosure': CLOSURE}))

def observe_group(pgid, ps_deadline=None):
    """EPERM is unknown unless a complete exact-PGID ps observation proves state."""
    observation = {"processGroup": pgid, "state": "unknown", "method": "killpg-zero"}
    try:
        os.killpg(pgid, 0)
        observation["state"] = "present"
        return observation
    except ProcessLookupError:
        observation["state"] = "absent"
        return observation
    except OSError as error:
        observation["killpgError"] = {"errno": error.errno, "type": type(error).__name__, "message": str(error)}
    ps_timeout = 2 if ps_deadline is None else min(2, max(0, ps_deadline - time.monotonic()))
    if ps_timeout <= 0:
        observation["psError"] = {"type": "ObservationDeadlineExpired", "message": "fixed cleanup envelope exhausted; group remains unknown"}
        return observation
    try:
        query = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat=,comm="],
                               capture_output=True, text=True, timeout=ps_timeout)
        observation.update(method="killpg-zero+exact-pgid-ps", psExitCode=query.returncode,
                           psStderr=query.stderr)
        rows = []
        valid = query.returncode == 0 and not query.stderr
        for line in query.stdout.splitlines():
            if not line.strip():
                continue
            fields = line.split(None, 4)
            if len(fields) != 5 or not all(value.isdecimal() for value in fields[:3]):
                valid = False
                continue
            if int(fields[2]) == pgid:
                rows.append(line)
        observation.update(exactGroupRows=rows, psCompleteParse=valid)
        if valid:
            observation["state"] = "present" if rows else "absent"
    except (OSError, subprocess.TimeoutExpired) as error:
        observation["psError"] = {"type": type(error).__name__, "message": str(error)}
    return observation


def record_command(name, argv, timeout, env=None, cwd=None):
    directory = HERE / "commands" / name
    assert not directory.exists(), name
    directory.mkdir(parents=True)
    bound = assert_baseline()
    assert_inputs()
    snapshot = directory / "harness.rs"
    shutil.copyfile(HERE / "harness.rs", snapshot)
    shutil.copyfile(HERE / "driver.py", directory / "driver.py")
    save(directory / "source-manifest.json", bound)
    before_tools = tools()
    binding = read(HERE / "binding.json")
    assert before_tools == binding["tools"], "tool drift"
    env = environment() if env is None else env
    argv_files = [identity(arg) for arg in argv if Path(arg).is_absolute() and Path(arg).is_file()]
    receipt = {"argv": argv, "argvFileIdentities": argv_files, "cwd": str(cwd or SOURCE), "environment": env,
        "timeoutSeconds": timeout, "terminationGraceSeconds": 5, "killWaitSeconds": 5,
        "UTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sourceClosure": closure(bound),
        "baselineClosure": CLOSURE, "harnessSHA256": sha(snapshot),
        "driverSHA256": sha(directory / "driver.py"), "toolsBefore": before_tools,
        "started": False, "timedOut": False, "signalSent": [], "commandFailurePreserved": True}
    started = time.monotonic()
    stdout = directory / "stdout"
    stderr = directory / "stderr"
    before_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen(argv, cwd=cwd or SOURCE, env=env, stdout=out, stderr=err, start_new_session=True)
        receipt.update(pid=child.pid, processGroup=child.pid, started=True)
        save(directory / "started.json", receipt)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            receipt["timedOut"] = True
        cleanup_started = time.monotonic()
        cleanup_deadlines = [cleanup_started + 5, cleanup_started + 10]
        observation = observe_group(child.pid, cleanup_deadlines[0])
        receipt["cleanupEnvelopeSeconds"] = 10
        receipt["groupBeforeCleanup"] = observation
        receipt["ownedGroupSurvivedDirectChild"] = child.returncode is not None and observation["state"] == "present"
        # Capture first failure and partial raw streams before any host cleanup signal.
        if receipt["timedOut"] or child.returncode != 0 or observation["state"] != "absent":
            save(directory / "before-process-cleanup.json", {
                "exitCode": child.returncode, "timedOut": receipt["timedOut"],
                "durationSeconds": time.monotonic() - started, "group": observation,
                "stdout": identity(stdout), "stderr": identity(stderr),
                "failureEvidencePrecedesHostCleanup": True})
        receipt["cleanupObservations"] = []
        if observation["state"] != "absent":
            for sig, grace_ends in zip((signal.SIGTERM, signal.SIGKILL), cleanup_deadlines):
                try:
                    os.killpg(child.pid, sig)
                    receipt["signalSent"].append(sig.name)
                except ProcessLookupError:
                    receipt["cleanupObservations"].append(observe_group(child.pid, grace_ends))
                    break
                except OSError as error:
                    receipt["cleanupObservations"].append({"signal": sig.name, "error": str(error), "errno": error.errno})
                while time.monotonic() < grace_ends:
                    child.poll()
                    observation = observe_group(child.pid, grace_ends)
                    if observation["state"] == "absent":
                        break
                    time.sleep(min(0.05, max(0, grace_ends - time.monotonic())))
                receipt["cleanupObservations"].append(observe_group(child.pid, grace_ends))
                if receipt["cleanupObservations"][-1]["state"] == "absent":
                    break
            child.poll()

    after_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt.update(exitCode=child.returncode, durationSeconds=time.monotonic() - started,
        stdout=identity(stdout), stderr=identity(stderr),
        childUserSeconds=after_usage.ru_utime-before_usage.ru_utime,
        childSystemSeconds=after_usage.ru_stime-before_usage.ru_stime,
        cumulativeChildrenMaxRSS=after_usage.ru_maxrss, maxRSSUnit="bytes on Darwin; cumulative child high water, not per-phase runtime reservations",
        sourceUnchanged=assert_baseline() == bound, toolsUnchanged=tools() == before_tools)
    assert_inputs()
    receipt["argvFilesUnchanged"] = all(identity(info["path"]) == info for info in argv_files)
    receipt["allBoundInputsUnchanged"] = True
    receipt["harnessUnchanged"] = sha(HERE / "harness.rs") == sha(snapshot)
    receipt["driverUnchanged"] = sha(HERE / "driver.py") == sha(directory / "driver.py")
    receipt["finalGroupObservation"] = observe_group(child.pid, cleanup_deadlines[-1])
    receipt["processGroupEmpty"] = receipt["finalGroupObservation"]["state"] == "absent"
    receipt["rawStreamEOFConfirmed"] = receipt["processGroupEmpty"]
    receipt["rawStreamEOFScope"] = "regular output handles closed; complete hash reads reached EOF after owned PGID absence"
    receipt["passed"] = child.returncode == 0 and not receipt["timedOut"] and receipt["sourceUnchanged"] and receipt["toolsUnchanged"] and receipt["processGroupEmpty"] and receipt["harnessUnchanged"] and receipt["driverUnchanged"] and receipt["argvFilesUnchanged"]
    save(directory / "receipt.json", receipt)
    return receipt, stdout, stderr



def build():
    count = len(list((HERE/'commands').glob('build-*'))) + 1
    argv = [str(Path(environment()['PATH'].split(':')[0])/'cargo'), 'test', '--lib', '--no-run', '--release', '--locked', '--offline', '--no-default-features', '--features', 'experimental-swift-reactor', '--message-format=json']
    receipt, stdout, _ = record_command(f'build-{count:03}', argv, 180)
    if not receipt['passed']: return 1
    artifacts = [json.loads(line) for line in stdout.read_text().splitlines() if line.startswith('{')]
    executables = [a['executable'] for a in artifacts if a.get('reason') == 'compiler-artifact' and a.get('executable') and a.get('profile',{}).get('test')]
    assert len(executables) == 1
    BINARY.parent.mkdir(exist_ok=True); shutil.copyfile(executables[0], BINARY); BINARY.chmod(0o700)
    save('binary.json', {'retained': identity(BINARY), 'buildReceipt': f'commands/build-{count:03}/receipt.json', 'sourceManifestSHA256': sha(HERE/'copied-source-manifest.json')})
    receipt, stdout, _ = record_command(f'list-{count:03}', [str(BINARY), '--list'], 30)
    assert receipt['passed']
    selected = [line.removesuffix(': test') for line in stdout.read_text().splitlines() if line.endswith(': test') and ('work_attribution_diagnostic::' in line or 'cache_tests::attribution_' in line)]
    assert len(selected) == 4, selected
    save('selected-tests.json', selected)
    return 0
def control():
    tests = [CONTROL_PREFIX+'attribution_actual_cache_controls', CONTROL_PREFIX+'attribution_finite_failure_prefixes_and_invalidity_are_observational', PREFIX+'attribution_reactor_harness_control']
    outcomes = []
    for index, test in enumerate(tests, 1):
        receipt, stdout, _ = record_command(f'control-{index:03}', [str(BINARY), test, '--exact', '--nocapture', '--test-threads=1'], 60)
        outcomes.append(receipt['passed'])
        rows = []
        for line in stdout.read_text().splitlines():
            for prefix in ('MIXER_ATTRIBUTION ', 'MIXER_EXACT '):
                if prefix in line: rows.append(json.loads(line.split(prefix,1)[1]))
        save(f'control-{index:03}-events.json', rows)
    return 0 if all(outcomes) else 1
def host_controls():
    receipt, _, _ = record_command('driver-controls', [sys.executable, '-B', str(HERE/'test_driver.py')], 30)
    return 0 if receipt['passed'] else 1
def proposed_command():
    return {'schema': 1, 'argv': [str(BINARY), PREFIX+'attribution_reactor_target_once', '--exact', '--nocapture', '--test-threads=1'],
        'outerCommand': ['python3','-B', str((HERE/'driver.py').relative_to(ROOT)), 'target'],
        'cwd': str(ROOT), 'childCwd': str(SOURCE),
        'childEnvironment': environment() | {'MIXER_EXACT_REACTOR_INPUT': str(SCRATCH/'fieldlog-reactor.wasm')},
        'outerDeadlineSeconds': 170, 'terminationGraceSeconds': 5, 'killWaitSeconds': 5,
        'validationDeadlineMs': 120000, 'cumulativeRuntimeDeadlineMs': 30000, 'cumulativeWasiDeadlineMs': 30000,
        'maxTargetAttempts': 1, 'allOtherBudgetsAndGuestInput': 'unchanged from sealed after-cache harness',
        'observerScope': 'credit-site counts and exact distinct/repeated completed decodes; external cfg(test) overhead, no CPU profile'}
def propose():
    assert not (HERE/'root-selection.json').exists() and not (HERE/'target-attempt-started.json').exists()
    assert_baseline(); assert_inputs(); assert identity(BINARY) == read(HERE/'binary.json')['retained']
    commands = ['diagnosis-verify', 'control-001', 'control-002', 'control-003', 'driver-controls']
    for name in commands:
        receipt = read(HERE/'commands'/name/'receipt.json')
        assert receipt['passed'] and receipt['rawStreamEOFConfirmed'] and receipt['processGroupEmpty']
    command = proposed_command(); save('proposed-command.json', command)
    files = ['baseline-manifest.json','copied-source-manifest.json','instrumentation.patch','binding.json','binary.json','selected-tests.json','observer.rs','controls.rs','transform.py','harness.rs','driver.py','test_driver.py','proposed-command.json']
    files += [str(p.relative_to(HERE)) for p in sorted((HERE/'commands').glob('*/receipt.json'))]
    files += [f'control-{i:03}-events.json' for i in range(1,4)]
    save('prepared-selection.json', {'schema':1, 'status':'prepared-awaiting-fresh-exact-root-selection',
        'targetAttempted': False, 'baselineClosure': CLOSURE, 'binary': identity(BINARY),
        'target': identity(REACTOR), 'argv':command['argv'], 'outerCommand':command['outerCommand'],
        'maxTargetAttempts':1, 'rootMustCreateSelectionBeforeTarget':True,
        'boundEvidence': {n:sha(HERE/n) for n in files}, 'gaAccepted':False})
    print(json.dumps({'preparedSelectionSHA256':sha(HERE/'prepared-selection.json'), 'targetExecuted':False}))
def target():
    # No implicit authority flows from preparation, a previous selection, or expected failure.
    selection = read(HERE/'root-selection.json')
    prepared = read(HERE/'prepared-selection.json')
    assert selection['exactCommandSelected'] is True
    assert selection['preparedSelectionSHA256'] == sha(HERE/'prepared-selection.json')
    assert selection['selectedBy'] == 'root' and selection['maxTargetAttempts'] == 1
    assert selection['argv'] == prepared['argv'] == proposed_command()['argv']
    assert selection['outerCommand'] == prepared['outerCommand'] == proposed_command()['outerCommand']
    assert all(sha(HERE/name) == digest for name,digest in prepared['boundEvidence'].items())
    assert_baseline(); assert_inputs(); assert identity(BINARY) == prepared['binary']; assert identity(REACTOR) == prepared['target']
    marker = HERE/'target-attempt-started.json'
    (SCRATCH/'tmp').mkdir(parents=True, exist_ok=True)
    with marker.open('x') as stream:
        stream.write(json.dumps({'selection':identity(HERE/'root-selection.json'), 'prepared':identity(HERE/'prepared-selection.json'), 'target':identity(REACTOR), 'binary':identity(BINARY), 'proposedCommand':proposed_command()}, indent=2, sort_keys=True)+'\n')
    target_copy = SCRATCH/'fieldlog-reactor.wasm'; shutil.copyfile(REACTOR,target_copy)
    assert target_copy.stat().st_size == 53_777_114 and sha(target_copy) == REACTOR_HASH
    receipt, stdout, _ = record_command('target-once', prepared['argv'], 170, env=proposed_command()['childEnvironment'])
    assert sha(target_copy) == REACTOR_HASH and identity(REACTOR) == prepared['target']
    events = [json.loads(line.split('MIXER_EXACT ',1)[1]) for line in stdout.read_text().splitlines() if 'MIXER_EXACT ' in line]
    save('target-events.json',events)
    save('target-result.json',{'commandPassed':receipt['passed'], 'firstFailure':next((e for e in events if e['event'] in ('validation_failure','adoption_failure','construction_failure','runtime_failure','guest_output_failure')),None), 'targetAttempted':True, 'gaAccepted':False})
    return 0 if receipt['passed'] else 1
def cleanup():
    groups=[]
    for path in sorted((HERE/'commands').glob('*/receipt.json')):
        receipt=read(path); observed=observe_group(receipt['processGroup'])
        assert observed['state']=='absent', str(path); groups.append(observed)
    assert_baseline(); assert_inputs()
    result={'processGroups':groups,'retainedForRootSelection':['source','bin/attribution-tests'],'removed':False}
    if SCRATCH.exists():
        assert not SCRATCH.is_symlink()
        before=SCRATCH.stat()
        holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],capture_output=True,timeout=30)
        result.update(lsofArgv=holders.args,lsofExitCode=holders.returncode,lsofStdout=holders.stdout.decode(),lsofStderr=holders.stderr.decode())
        assert holders.returncode==1 and not holders.stdout and not holders.stderr
        assert (SCRATCH.stat().st_dev,SCRATCH.stat().st_ino)==(before.st_dev,before.st_ino)
        result['removedLogicalBytes']=sum(p.stat().st_size for p in SCRATCH.rglob('*') if p.is_file())
        shutil.rmtree(SCRATCH)
    result.update(removed=not SCRATCH.exists(),live132SourceHashesUnchanged=True)
    save('cleanup.json',result); save('live-source-after.json',source_manifest(ROOT/'vm'))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','build','control','host-controls','propose','target','cleanup'))
    return {'prepare':prepare,'build':build,'control':control,'host-controls':host_controls,'propose':propose,'target':target,'cleanup':cleanup}[parser.parse_args().action]() or 0
if __name__=='__main__': sys.exit(main())
