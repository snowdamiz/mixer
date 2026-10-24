"""Supplement the historical candidate4 with uninstrumented, isolated full tests."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-executor-construction/candidate-4'
OUT = HERE / 'candidate4-clean'
BUILD = HERE / 'build/candidate4-clean'
OUT.mkdir(exist_ok=False)
BUILD.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt = json.loads((PRODUCER / 'receipt.json').read_text())
manifest = json.loads((PRODUCER / 'source-manifest.json').read_text())
archive = PRODUCER / receipt['archive']['path']
assert sha(archive) == receipt['archive']['sha256']
with tarfile.open(archive) as t:
    t.extractall(BUILD / 'source', filter='data')
SOURCE = BUILD / 'source/vm'
TARGET = BUILD / 'product-only-target'
assert not TARGET.exists()
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'],
           CARGO_TARGET_DIR=str(TARGET))
commands = []
counts = {}
binaries = {}
status = 'failed'

def verify_source():
    for name, digest in manifest.items():
        assert sha(SOURCE / name) == digest, name

def run(name, argv):
    verify_source()
    p = subprocess.run(argv, cwd=SOURCE, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=1200)
    log = OUT / (name + '.log')
    log.write_bytes(p.stdout)
    verify_source()
    commands.append(dict(name=name, argv=argv, cwd=str(SOURCE),
                         cargoTargetDirectory=str(TARGET), exit=p.returncode,
                         log=str(log.relative_to(ROOT)), sha256=sha(log),
                         sourceBeforeAfterVerified=True))
    print(name, p.returncode, flush=True)
    if p.returncode:
        raise RuntimeError(p.stdout.decode(errors='replace')[-5000:])
    return p.stdout.decode()

try:
    verify_source()
    run('rustc-version', ['rustc', '-Vv'])
    run('cargo-version', ['cargo', '-V'])
    for profile in ['debug', 'release']:
        argv = ['cargo', 'test', '--locked', '--offline', '--all-features',
                '--manifest-path', str(SOURCE / 'Cargo.toml'),
                '--target-dir', str(TARGET)]
        if profile == 'release':
            argv.append('--release')
        output = run('full-' + profile, argv)
        assert 'frozen_construction_metadata' not in output
        results = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', output)
        assert results and int(results[0][0]) == 151, results[:1]
        counts[profile] = dict(passed=sum(int(x[0]) for x in results),
                               failed=sum(int(x[1]) for x in results),
                               ignored=sum(int(x[2]) for x in results),
                               suites=len(results), uninstrumentedLibraryPassed=151)
        match = re.search(r'Running unittests src/lib.rs \(([^\n]+)\)', output)
        assert match
        binary = Path(match.group(1))
        if not binary.is_absolute():
            binary = SOURCE / binary
        binary = binary.resolve()
        assert binary.is_relative_to(TARGET.resolve())
        listing = run('unit-list-' + profile, [str(binary), '--list'])
        assert 'frozen_construction_metadata' not in listing
        assert len(re.findall(r': test$', listing, re.M)) == 151
        binaries[profile] = dict(path=str(binary), sha256=sha(binary), testCount=151,
                                 metadataProbeAbsent=True)
    status = 'passed-uninstrumented-full-host-regression'
finally:
    result = dict(schema=1, status=status,
                  observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  sourceRevision=receipt['revision'],
                  producerReceiptSHA256=sha(PRODUCER / 'receipt.json'),
                  archiveSHA256=sha(archive), sourceTreeSHA256=receipt['source_tree_digest'],
                  sourceManifestSHA256=sha(PRODUCER / 'source-manifest.json'),
                  sourceFileCount=len(manifest), commands=commands, counts=counts,
                  unitBinaries=binaries, collectorSHA256=sha(Path(__file__)),
                  targetIsolation='Fresh target used only for this exact archived unmodified source; no metadata or review overlays.',
                  supersedes='Only the contaminated candidate4 full-test claims; historical files are preserved.',
                  scope='Full host all-features library, binary, integration and doc suites. Ignored tests remain ignored. No full Swift target initialize/invoke, devices, publication or GA qualification.')
    (OUT / 'qualification.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print('PASS', counts, flush=True)
