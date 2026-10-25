#!/usr/bin/env python3
"""One bounded synthetic actual-cache run; no target path or target execution."""
from pathlib import Path
import datetime, difflib, hashlib, json, os, platform, shutil, signal, subprocess, sys, time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASELINE = ROOT / 'verification/swift-exact-reactor-after-cache/baseline-manifest.json'
CLOSURE = 'b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11'
SCRATCH = HERE / 'scratch'
BUILD = HERE / 'target'
TMP = HERE / 'tmp'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def manifest(directory):
    paths = [directory / 'Cargo.toml', directory / 'Cargo.lock']
    paths += [p for top in ('include', 'src', 'tests') for p in (directory / top).rglob('*') if p.is_file()]
    return {str(p.relative_to(directory)): sha(p) for p in sorted(paths)}
def process_group(pgid):
    p = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid=,command='], capture_output=True, text=True, check=True, timeout=10)
    return [line.strip() for line in p.stdout.splitlines() if len(line.split(None, 2)) >= 2 and int(line.split(None, 2)[1]) == pgid]

assert not (HERE / 'fixture-command.json').exists(), 'finite synthetic run already recorded'
assert not any(p.exists() for p in (SCRATCH, BUILD, TMP))
bound = json.loads(BASELINE.read_text())
assert sha(BASELINE) == CLOSURE and len(bound) == 132
assert manifest(ROOT / 'vm') == bound
save('live-source-before.json', bound)
refs = ['AGENTS.md', 'docs/swift-cache-reset-elision-checkpoint.md',
        'docs/swift-exact-reactor-after-cache-result.md',
        'verification/swift-exact-reactor-after-cache-root-selection/result-binding.json',
        'verification/swift-exact-reactor-after-cache/phase-counters.json',
        'verification/swift-exact-reactor-after-cache/result-seal.json',
        'verification/swift-exact-reactor-after-cache/harness.rs',
        'verification/swift-exact-reactor-after-cache/diagnostic.py',
        'verification/swift-exact-reactor-after-cache/baseline-manifest.json']
save('input-bindings.json', {name: sha(ROOT / name) for name in refs})
revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10).stdout.strip()
save('preparation.json', {'sourceRevision': revision, 'liveClosureSHA256': CLOSURE,
                        'scope': 'small synthetic actual-cache fixture only', 'targetExecuted': False})
for name in bound:
    path = SCRATCH / name
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'vm' / name, path)
source = SCRATCH / 'src/experimental_swift_reactor/cache.rs'
old = '''        self.control
            .work_with_wasi(Work::Cache, n, self.cursor, self.observation())'''
new = '''        let result = self.control
            .work_with_wasi(Work::Cache, n, self.cursor, self.observation());
        #[cfg(test)]
        if result.is_ok() { super::cache_tests::remaining_note_work(n); }
        result'''
text = source.read_text()
assert text.count(old) == 1
source.write_text(text.replace(old, new))
tests = SCRATCH / 'src/experimental_swift_reactor/cache_tests.rs'
tests.write_bytes(tests.read_bytes() + b'\n' + (HERE / 'fixture-hook.rs').read_bytes())
modified = manifest(SCRATCH)
changed = [name for name in bound if bound[name] != modified[name]]
assert changed == ['src/experimental_swift_reactor/cache.rs', 'src/experimental_swift_reactor/cache_tests.rs']
save('copied-source-manifest.json', modified)
patch = ''.join(''.join(difflib.unified_diff((ROOT/'vm'/name).read_text().splitlines(True), (SCRATCH/name).read_text().splitlines(True), fromfile='vm/'+name, tofile='isolated/'+name)) for name in changed)
(HERE / 'instrumentation.patch').write_text(patch)
TMP.mkdir()
toolchain = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env = {key: os.environ[key] for key in ('HOME', 'USER', 'LOGNAME') if key in os.environ}
env.update(PATH=str(toolchain)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
           CARGO_TARGET_DIR=str(BUILD), CARGO_BUILD_JOBS='2', CARGO_NET_OFFLINE='true',
           CARGO_INCREMENTAL='0', RUST_TEST_THREADS='1', TMPDIR=str(TMP))
versions = {'python': {'path': sys.executable, 'sha256': sha(Path(sys.executable).resolve()), 'version': sys.version}, 'platform': platform.platform()}
for name, flags in [('rustc', ['-vV']), ('cargo', ['-V'])]:
    tool = toolchain / name
    p = subprocess.run([str(tool), *flags], env=env, capture_output=True, text=True, check=True, timeout=10)
    versions[name] = {'path': str(tool), 'sha256': sha(tool), 'stdout': p.stdout, 'stderr': p.stderr}
save('tool-versions.json', versions)
argv = [str(toolchain/'cargo'), 'test', '--lib', '--locked', '--offline', '--no-default-features', '--features', 'experimental-swift-reactor', '--release', 'experimental_swift_reactor::cache_tests::remaining_work_actual_cache_fixture', '--', '--exact', '--nocapture', '--test-threads=1']
began = datetime.datetime.now(datetime.timezone.utc).isoformat()
start = time.monotonic()
signals = []
with (HERE/'fixture.stdout').open('wb') as stdout, (HERE/'fixture.stderr').open('wb') as stderr:
    p = subprocess.Popen(argv, cwd=SCRATCH, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
    timed_out = False
    try: code = p.wait(timeout=120)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, signal.SIGTERM); signals.append('SIGTERM')
        try: code = p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL); signals.append('SIGKILL'); code = p.wait(timeout=3)
record = {'argv': argv, 'cwd': str(SCRATCH), 'environment': env, 'beganUTC': began,
          'elapsedSeconds': time.monotonic()-start, 'exitCode': code, 'timeoutSeconds': 120,
          'timedOut': timed_out, 'pid': p.pid, 'pgid': p.pid, 'signalsSent': signals,
          'sourceManifestSHA256': sha(HERE/'copied-source-manifest.json'),
          'stdoutSHA256': sha(HERE/'fixture.stdout'), 'stderrSHA256': sha(HERE/'fixture.stderr')}
save('fixture-command.json', record)
rows = [json.loads(line.split('REMAINING ', 1)[1]) for line in (HERE/'fixture.stdout').read_text().splitlines() if 'REMAINING ' in line]
save('fixture-observations.json', {'observations': rows})
group = process_group(p.pid)
holders = subprocess.run(['/usr/sbin/lsof', '-nP', '-t', '+D', str(HERE)], capture_output=True, text=True, timeout=20)
save('cleanup-preflight.json', {'processGroupMembers': group, 'lsofArgv': holders.args,
                              'lsofExitCode': holders.returncode, 'lsofStdout': holders.stdout,
                              'lsofStderr': holders.stderr})
assert group == [] and holders.returncode == 1 and not holders.stdout and not holders.stderr
assert manifest(ROOT/'vm') == bound and manifest(SCRATCH) == modified
assert all(sha(ROOT/name) == value for name,value in json.loads((HERE/'input-bindings.json').read_text()).items())
scratch_bytes = sum(p.stat().st_size for d in (SCRATCH, BUILD, TMP) for p in d.rglob('*') if p.is_file())
for path in (SCRATCH, BUILD, TMP): shutil.rmtree(path)
save('live-source-after.json', manifest(ROOT/'vm'))
save('cleanup.json', {'ownedPathsAbsent': all(not p.exists() for p in (SCRATCH, BUILD, TMP)),
                     'live132SourceHashesUnchanged': True, 'inputHashesUnchanged': True,
                     'processGroupMembers': group, 'signalsSent': signals, 'removedLogicalBytes': scratch_bytes})
print(json.dumps({'exitCode': code, 'observations': rows, 'cleanupComplete': True}))
raise SystemExit(code)
