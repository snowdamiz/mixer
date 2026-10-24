#!/usr/bin/env python3
"""Exercise the future collector on tiny independent Cargo fixtures only."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

from target_isolation import SnapshotBuildIsolation

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / 'target-isolation-correction/synthetic'
if OUT.exists():
    raise RuntimeError('Preserve prior proof; choose a new output directory.')
SOURCE = OUT / 'source/vm'
META = OUT / 'metadata/vm'
SOURCE.mkdir(parents=True)
(SOURCE / 'src').mkdir()
(SOURCE / 'Cargo.toml').write_text('[package]\nname = "mixer-collector-target-fixture"\nversion = "0.0.0"\nedition = "2021"\n')
(SOURCE / 'src/lib.rs').write_text('#[test]\nfn product_marker() { assert_eq!(2 + 2, 4); }\n')
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
locked = subprocess.run(['cargo', 'generate-lockfile', '--offline'], cwd=SOURCE,
                        env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
assert locked.returncode == 0, locked.stdout
shutil.copytree(SOURCE, META)
with (META / 'src/lib.rs').open('a') as target:
    target.write('''
#[cfg(test)]
mod experimental_swift_reactor {
    pub mod execution {
        #[test]
        fn frozen_construction_metadata() { assert_eq!(3 + 3, 6); }
    }
}
''')
isolation = SnapshotBuildIsolation(OUT, SOURCE, META)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
receipt = {'schema': 'mixer.collector-target-isolation.synthetic.v1',
           'scope': 'Tiny independently authored Cargo tooling fixtures only; no VM regression, engine, Wasm target or device execution.',
           'commands': [], 'negative_checks': [],
           'target_dirs': {kind: str(path) for kind, path in isolation.targets.items()},
           'implementation_hashes': {path.name: sha(path) for path in [BASE / 'target_isolation.py', BASE / 'collect_candidate5.py', Path(__file__)]}}
for tool, args in [('rustc', ['-Vv']), ('cargo', ['-V'])]:
    result = subprocess.run([tool] + args, cwd=SOURCE, env=ENV, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode == 0
    (OUT / (tool + '-version.log')).write_text(result.stdout)
receipt['lockfile'] = {'argv': ['cargo', 'generate-lockfile', '--offline'],
                       'cwd': str(SOURCE), 'exit_code': locked.returncode,
                       'output': locked.stdout, 'sha256': sha(SOURCE / 'Cargo.lock')}
for profile, flags in [('debug', []), ('release', ['--release'])]:
    witnesses = {}
    for stage, cwd in [('product-before', SOURCE), ('metadata', META), ('product-after', SOURCE)]:
        name = stage + '-' + profile
        argv = ['cargo', 'test', '--locked', '--offline'] + flags + ['--lib']
        env = isolation.environment(ENV, cwd)
        command = isolation.arguments(argv, cwd)
        result = subprocess.run(command, cwd=cwd, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (OUT / 'logs').mkdir(exist_ok=True)
        log = OUT / 'logs' / (name + '.log')
        log.write_text(result.stdout)
        assert result.returncode == 0, result.stdout
        witness = isolation.test_binary_witnesses(name, argv, result.stdout, cwd, env)[0]
        assert witness['runtime_test_count'] == (2 if stage == 'metadata' else 1)
        witnesses[stage] = witness
        receipt['commands'].append({'name': name, 'argv': command, 'cwd': str(cwd),
                                    'cargo_target_dir': env['CARGO_TARGET_DIR'],
                                    'exit_code': result.returncode, 'log': str(log),
                                    'log_sha256': sha(log), 'test_binary_witness': witness})
    assert witnesses['product-before']['executable'] == witnesses['product-after']['executable']
    assert witnesses['product-before']['sha256'] == witnesses['product-after']['sha256']
    assert witnesses['product-after']['target_dir'] != witnesses['metadata']['target_dir']
    # Explicitly copy only the tiny synthetic metadata binary into a product
    # target after normal runs, to prove runtime test-list validation rejects it.
    contaminated = isolation.targets['source'] / profile / 'intentionally-contaminated-fixture'
    shutil.copy2(witnesses['metadata']['executable'], contaminated)
    rejected = False
    try:
        isolation.test_binary_witnesses('negative-derived-probe-' + profile,
                                       ['cargo', 'test'],
                                       f'Running unittests src/lib.rs ({contaminated})\n',
                                       SOURCE, isolation.environment(ENV, SOURCE))
    except AssertionError:
        rejected = True
    assert rejected
    receipt['negative_checks'].append({'profile': profile, 'metadata_probe_in_product_target_rejected': True,
                                       'copied_fixture_sha256': sha(contaminated)})
try:
    SnapshotBuildIsolation(OUT, SOURCE, META)
except RuntimeError:
    receipt['negative_checks'].append({'reused_target_roots_rejected': True})
else:
    raise AssertionError('Reused target roots were accepted')
receipt['fixture_inputs'] = {str(path.relative_to(OUT)): sha(path)
                              for snapshot in (SOURCE, META)
                              for path in sorted(snapshot.rglob('*')) if path.is_file()}
receipt['status'] = 'passed: distinct target roots preserved product binary hashes and excluded metadata probes in both profiles; injected probe and reused targets rejected'
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'scope': receipt['scope'], 'commands': len(receipt['commands']),
                  'negative_checks': receipt['negative_checks'], 'status': receipt['status']}, indent=2))
