#!/usr/bin/env python3
"""Fresh product source snapshots and independent public-contract regression."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / STAMP
LOCAL = HERE / 'local' / STAMP
OUT.mkdir()
LOCAL.mkdir(parents=True)
sha = lambda b: hashlib.sha256(b).hexdigest()
jsonbytes = lambda x: (json.dumps(x, sort_keys=True, indent=2) + '\n').encode()
manifest = lambda root: {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
paths = [ROOT/'vm/Cargo.toml', ROOT/'vm/Cargo.lock'] + sorted((ROOT/'vm/src').rglob('*')) + sorted((ROOT/'vm/tests').rglob('*')) + sorted((ROOT/'vm/include').rglob('*'))
paths = [p for p in paths if p.is_file()]
product = {str(p.relative_to(ROOT/'vm')): sha(p.read_bytes()) for p in paths}
(OUT/'product-source-manifest.json').write_bytes(jsonbytes(product))
archive = OUT/'product-source.tar.gz'
with tarfile.open(archive, 'w:gz') as tf:
    for p in paths: tf.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
with tarfile.open(archive) as tf: tf.extractall(LOCAL, filter='data')
VM = LOCAL/'vm'
assert manifest(VM) == product
(VM/'tests/independent_numeric.rs').write_bytes((HERE/'independent_numeric.rs').read_bytes())
closure = manifest(VM)
(OUT/'derived-test-manifest.json').write_bytes(jsonbytes(closure))
commands = []
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
def command(name, argv, cwd, target=None, check_source=False):
    if check_source: assert manifest(VM) == closure
    runenv = dict(env)
    if target: runenv['CARGO_TARGET_DIR'] = str(target)
    p = subprocess.run(argv, cwd=cwd, env=runenv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    (OUT/(name+'.log')).write_bytes(p.stdout)
    if check_source: assert manifest(VM) == closure
    commands.append(dict(name=name, argv=argv, cwd=str(cwd), target=str(target) if target else None,
        sourceBeforeAfterVerified=check_source, exit=p.returncode, log=name+'.log', logSHA256=sha(p.stdout)))
    print(name, p.returncode, flush=True)
    assert p.returncode == 0, p.stdout.decode(errors='replace')[-6000:]
    return p.stdout.decode()
status = 'failed'
try:
    command('rustc-version', ['rustc', '-vV'], ROOT)
    command('cargo-version', ['cargo', '-V'], ROOT)
    for profile in ['debug', 'release']:
        flags = ['--release'] if profile == 'release' else []
        text = command(profile, ['cargo', 'test', '--locked', '--offline', '--features', 'experimental-span-execution', *flags,
            '--test', 'independent_numeric', '--', '--nocapture', '--test-threads=1'], VM, LOCAL/profile/'target', True)
        assert text.count('independent_numeric ') == 10
        assert '1 passed; 0 failed; 0 ignored' in text
    assert all(sha((ROOT/'vm'/p).read_bytes()) == h for p,h in product.items())
    status = 'passed-independent-host-numeric-contract-only'
finally:
    (OUT/'receipt.json').write_bytes(jsonbytes(dict(schema=1, status=status, revision=revision,
        observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Uninstrumented current product library with one independent injected integration test. Ten direct numeric expectations, four numeric work boundary/exact-credit pairs, trap cursor/fuel/instruction/cleanup/sticky-failure checks, cold no-reallocation and warm zero-allocation checks in Debug and Release. No Swift execution, device, release, published consumer, full suite or GA qualification.',
        productArchiveSHA256=sha(archive.read_bytes()), productSourceTreeSHA256=sha(jsonbytes(product)),
        independentTestSHA256=sha((HERE/'independent_numeric.rs').read_bytes()),
        productVMUnchangedDuringVerification=all(sha((ROOT/'vm'/p).read_bytes()) == h for p,h in product.items()),
        commands=commands)))
    print(OUT, flush=True)
