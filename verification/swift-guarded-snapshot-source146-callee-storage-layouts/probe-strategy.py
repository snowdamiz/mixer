"""One bounded compile-only technique probe; never executes emitted code."""
import hashlib, json, os, signal, subprocess, time
from pathlib import Path
D = Path(__file__).resolve().parent
C = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
assert not (D / 'strategy-receipt.json').exists()
assert hashlib.sha256(C.read_bytes()).hexdigest() == 'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
args = [str(C), '--crate-name', 'closure_layout_strategy', '--edition=2021', '--crate-type=lib', '--emit=metadata', '--error-format=json', str(D/'strategy-probe.rs'), '-o', str(D/'strategy.rmeta')]
env = {'PATH':'/usr/bin:/bin', 'RUSTC_BOOTSTRAP':'1'}
start = time.monotonic()
p = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timed_out = False
try:
    stdout, stderr = p.communicate(timeout=10)
except subprocess.TimeoutExpired:
    timed_out = True
    os.killpg(p.pid, signal.SIGKILL)
    stdout, stderr = p.communicate()
try:
    os.killpg(p.pid, 0)
    absent = False
except ProcessLookupError:
    absent = True
for name, data in [('stdout', stdout), ('stderr', stderr)]:
    (D / ('strategy.'+name)).write_bytes(data)
rec = dict(argv=args, environment=env, exit_code=p.returncode, timed_out=timed_out, elapsed_seconds=time.monotonic()-start, direct_child_waited=True, owned_group_absent=absent, source_sha256=hashlib.sha256((D/'strategy-probe.rs').read_bytes()).hexdigest(), script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), product_source=False, runtime=False, global_process_inventory=False, outputs={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in [('stdout',stdout),('stderr',stderr)]})
(D/'strategy-receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
assert not timed_out and absent and not (D/'strategy.rmeta').exists()
print(json.dumps(rec))
for line in stderr.splitlines():
    obj=json.loads(line)
    if obj.get('level')=='error': print(obj.get('rendered', obj['message']))
