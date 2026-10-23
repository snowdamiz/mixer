#!/usr/bin/env python3
"""Independent host review; creates only a temporary detached source clone."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = '4ca99c581a0cdbf4a69e15623ae676ca73403262'
SOURCE_DIGEST = '11e74f195e051317d8097953d8dd9193e29d3a0d66011fe00f29a36f34d5b8fe'
FROZEN = '64123c509e861ddd522631b293eadebdaca11341'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', required=True)
    p.add_argument('--reuse-export', type=pathlib.Path,
                   help='continue the already independently run detached export; verifies pin and baseline digest')
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.name):
        p.error('invalid evidence directory name')
    out = HERE / args.name
    out.mkdir(exist_ok=False)
    env = dict(os.environ)
    env['PATH'] = '/opt/homebrew/opt/rustup/bin:' + env.get('PATH', '')
    commands = []

    def run(name, argv, cwd, timeout=180):
        start = time.monotonic()
        r = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        log = out / (name + '.log')
        log.write_bytes(r.stdout)
        commands.append({'name': name, 'argv': argv, 'cwd': str(cwd), 'exit_code': r.returncode,
                         'elapsed_seconds': round(time.monotonic()-start, 6),
                         'output': log.relative_to(HERE).as_posix(), 'output_sha256': sha(r.stdout)})
        print(f'{name}: exit {r.returncode}', flush=True)
        if r.returncode:
            (out / 'interrupted-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
            raise RuntimeError(f'{name}: see {log}')
        return r.stdout.decode()

    if args.reuse_export:
        export = args.reuse_export.resolve()
    else:
        export = pathlib.Path(tempfile.mkdtemp(prefix='mixer-stream-independent-')) / 'source'
        run('clone', ['git', 'clone', '--shared', '--no-checkout', '--quiet', str(ROOT), str(export)], ROOT)
        run('checkout', ['git', 'checkout', '--quiet', '--detach', PIN], export)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=export, text=True).strip() == PIN
    # Verify every original committed VM file against the immutable tree, including
    # tests/receipts, rather than trusting a caller-provided reuse directory.
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', PIN, '--', 'vm',
                                    'contracts/vm-profile-v1.json', 'contracts/vm-session-v1.json'],
                                   cwd=export, text=True).splitlines()
    hashes = {}
    for name in names:
        expected = subprocess.check_output(['git', 'show', PIN+':'+name], cwd=export)
        actual = (export/name).read_bytes()
        assert actual == expected, name
        hashes[name] = sha(actual)
    source_manifest = ''.join(f'{h}  {name}\n' for name, h in hashes.items())
    (out/'committed-source.sha256').write_text(source_manifest)
    if not args.reuse_export:
        run('immutable-baseline', ['python3', '-B', 'vm/verify-stream-validation.py', '--name', 'independent-baseline'], export, 300)
    baseline = export/'vm/verification/stream-validation/independent-baseline'
    b = json.loads((baseline/'receipt.json').read_text())
    assert b['host_revision_at_start'] == PIN
    assert b['source_tree_digest'] == SOURCE_DIGEST
    assert b['source_tree_digest'] == sha((baseline/'source-manifest.sha256').read_bytes())
    # Preserve independently reproduced output, not the implementer's earlier logs.
    shutil.copytree(baseline, out/'baseline')
    for command in b['commands']:
        original = export/command['output']
        assert sha(original.read_bytes()) == command['output_sha256']
    # All subsequent probes are independent originals and exist only in this export.
    for name in ['review_semantics.rs', 'review_allocations.rs']:
        shutil.copy2(HERE/name, export/'vm/tests'/name)
    env['CARGO_TARGET_DIR'] = str(export/'vm/target/independent-review')
    rustfmt = ['rustfmt', '--edition', '2021']
    run('format-review-probes', rustfmt + ['--check', str(HERE/'review_semantics.rs'), str(HERE/'review_allocations.rs')], export)
    cargo = ['cargo', 'test', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-stream-validation']
    outputs = {}
    for mode, flag in [('debug', []), ('release', ['--release'])]:
        outputs[mode] = run(mode+'-independent-semantics', cargo+flag+['--test', 'review_semantics', '--', '--nocapture'], export)
        outputs[mode+'-allocation'] = run(mode+'-independent-allocation', cargo+flag+['--test', 'review_allocations', '--', '--test-threads=1', '--nocapture'], export)
    run('clippy-review-probes', ['cargo', 'clippy', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-stream-validation', '--test', 'review_semantics', '--test', 'review_allocations', '--', '-D', 'warnings'], export)
    for name in hashes:
        assert sha((export/name).read_bytes()) == hashes[name], name
    cases = {}
    observations = {}
    for mode in ['debug', 'release']:
        cases[mode] = {m[0]: {'cases': int(m[1]), 'accepted': int(m[2]), 'rejected': int(m[3])}
                       for m in re.findall(r'independent Node ([\w-]+): cases=(\d+) accepted=(\d+) rejected=(\d+)', outputs[mode])}
        assert len(cases[mode]) == 5
        m = re.search(r'calls=(\d+) failed_ordinals=(\d+) cancellation_gates=(\d+) measured_peak=(\d+) reserved_peak=(\d+)', outputs[mode+'-allocation'])
        assert m
        observations[mode] = dict(zip(['allocation_calls', 'allocation_failure_ordinals', 'cancellation_gates', 'measured_requested_heap_peak', 'total_peak_reserved'], map(int, m.groups())))
    assert cases['debug'] == cases['release']
    assert observations['debug'] == observations['release']
    probes = {name: sha((HERE/name).read_bytes()) for name in ['run.py', 'review_semantics.rs', 'review_allocations.rs']}
    receipt = {
        'schema_version': 1, 'independent_review': True,
        'reviewer': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewed_revision': PIN,
        'reviewed_tree': subprocess.check_output(['git','rev-parse',PIN+'^{tree}'],cwd=export,text=True).strip(),
        'scoped_vm_source_digest': SOURCE_DIGEST,
        'all_committed_vm_and_contract_files_manifest_sha256': sha(source_manifest.encode()),
        'frozen_production_reference': FROZEN,
        'temporary_export': str(export), 'baseline_receipt': (out/'baseline/receipt.json').relative_to(HERE).as_posix(),
        'environment': {'PATH_prefix': '/opt/homebrew/opt/rustup/bin', 'CARGO_TARGET_DIR': env['CARGO_TARGET_DIR']},
        'versions': b['versions'], 'baseline_counts': b['test_counts'], 'commands': commands,
        'probes': probes, 'node_comparisons_each_build': cases,
        'work_prefix_rejections_each_build': int(re.search(r'work-prefix rejections: (\d+)', outputs['debug'])[1]),
        'independent_allocation_observations': observations,
        'production_findings': [],
        'scope': 'macOS arm64 host; immutable nondefault Rust experiment; independent targeted semantic/resource review; no production route',
        'remaining_requirements': ['full standards suite', 'coverage-guided fuzzing', 'external security audit', 'physical experimental validation (phones disconnected)', 'full Swift/FieldLog admission', 'cache/executable integration design and qualification', 'OTA/GA acceptance'],
        'full_swift_qualified': False, 'ga_qualified': False,
    }
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'receipt': str(out/'receipt.json'), 'node_cases_each_build': sum(v['cases'] for v in cases['debug'].values()), 'production_findings': []}, indent=2))


if __name__ == '__main__':
    main()
