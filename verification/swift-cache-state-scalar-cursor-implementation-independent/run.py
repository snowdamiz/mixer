#!/usr/bin/env python3
"""Independent, serial Rust controls; each owned child has a 60s deadline."""
import datetime, hashlib, json, os, pathlib, platform, selectors, signal, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[1]
RUST = pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SELECTED = REPO / 'verification/swift-cache-state-scalar-cursor-proposal/source/cache_state.rs.txt'
SOURCE_HASH = 'f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b'
SUFFIX = b'\n#[cfg(test)]\n#[path = "../scalar_cursor_independent.rs"]\nmod scalar_cursor_independent;\n'
CAP = 8 * 1024 * 1024
DEADLINE = 60

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(label, command):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clock = time.monotonic()
    command = [str(part) for part in command]
    proc = subprocess.Popen(command, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    selectors_ = selectors.DefaultSelector()
    selectors_.register(proc.stdout, selectors.EVENT_READ, 'stdout')
    selectors_.register(proc.stderr, selectors.EVENT_READ, 'stderr')
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    failed = None
    killed = False
    initial = {'argv': command, 'cwd': str(REPO), 'pid': proc.pid, 'pgid': proc.pid,
        'started_at': started, 'new_session': True, 'deadline_seconds': DEADLINE, 'per_stream_byte_cap': CAP,
        'source_revision_context': 'a24011487bfc368512fa52125241d9c46e7cdd3f',
        'actual_library_sha256': {p.name: sha(p) for p in sorted((ROOT / 'source/library').glob('*.rs'))},
        'independent_controls_sha256': sha(ROOT / 'source/scalar_cursor_independent.rs'),
        'runner_sha256': sha(pathlib.Path(__file__))}
    (ROOT / f'evidence/{label}.start.json').write_text(json.dumps(initial, indent=2) + '\n')
    while selectors_.get_map() or proc.poll() is None:
        if time.monotonic() - clock >= DEADLINE and failed is None:
            failed = 'timeout'
        if failed and not killed:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            killed = True
        for key, _ in selectors_.select(0.025):
            data = os.read(key.fileobj.fileno(), 65536)
            if not data:
                selectors_.unregister(key.fileobj)
                key.fileobj.close()
                continue
            available = CAP - len(buffers[key.data])
            buffers[key.data].extend(data[:available])
            if len(data) > available and failed is None:
                failed = 'output-cap'
    proc.wait(timeout=5)
    selectors_.close()
    for stream, data in buffers.items():
        (ROOT / f'evidence/{label}.{stream}').write_bytes(data)
    result = dict(initial, exit=proc.returncode, failure=failed, group_termination_requested=killed,
        parent_exit_observed=True, elapsed_seconds=time.monotonic() - clock,
        output_sha256={name: hashlib.sha256(value).hexdigest() for name, value in buffers.items()})
    (ROOT / f'evidence/{label}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(label, result['exit'], result['failure'], f"{result['elapsed_seconds']:.3f}s", flush=True)
    return result

def cleanup(product, rows):
    if product.exists():
        row = {'path': str(product.relative_to(ROOT)), 'bytes': product.stat().st_size,
            'sha256_before_removal': sha(product)}
        product.unlink()
        row['absent_after_removal'] = not product.exists()
        rows.append(row)
        (ROOT / 'evidence/owned-product-cleanup.json').write_text(json.dumps(rows, indent=2) + '\n')

def main():
    began = time.monotonic()
    assert sha(SELECTED) == SOURCE_HASH
    source = ROOT / 'source/library/cache_state.rs'
    if source.read_bytes() == SELECTED.read_bytes():
        source.write_bytes(SELECTED.read_bytes() + SUFFIX)
    assert source.read_bytes() == SELECTED.read_bytes() + SUFFIX
    before = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'source').rglob('*')) if p.is_file()}
    (ROOT / 'evidence/compiled-source-identity.json').write_text(json.dumps({
        'selected_sha256': SOURCE_HASH, 'selected_bytes': SELECTED.stat().st_size,
        'append_only_cfg_test_suffix': SUFFIX.decode(), 'derivative_sha256': sha(source),
        'exact_prefix_verified': True, 'library_sources_and_test_oracles_before': before,
        'copied_original_private_tests_adapted': False, 'only_test_filter_executed': 'scalar_cursor_independent',
        'copied_original_test_modules_compiled_but_not_executed': True,
    }, indent=2) + '\n')
    rows = []
    results = [run('rust-version', [RUST, '--version', '--verbose'])]
    for mode, flags in [('debug', []), ('optimized', ['-O'])]:
        product = ROOT / f'evidence/independent-{mode}'
        try:
            compilation = run(f'compile-{mode}', [RUST, '--edition=2021', '--test', *flags,
                ROOT / 'source/library/analyzer.rs', '-o', product])
            results.append(compilation)
            if compilation['exit'] == 0 and compilation['failure'] is None:
                results.append(run(f'tests-{mode}', [product, 'scalar_cursor_independent',
                    '--test-threads=1', '--nocapture']))
        finally:
            cleanup(product, rows)
    assert source.read_bytes() == SELECTED.read_bytes() + SUFFIX
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'source').rglob('*')) if p.is_file()}
    summary = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'python': platform.python_version(), 'platform': platform.platform(),
        'total_wall_seconds': time.monotonic() - began,
        'all_commands_passed': all(row['exit'] == 0 and row['failure'] is None for row in results),
        'commands': [{'argv': row['argv'], 'elapsed_seconds': row['elapsed_seconds'],
            'exit': row['exit'], 'failure': row['failure']} for row in results],
        'owned_children_reaped': all(row['parent_exit_observed'] for row in results),
        'owned_binaries_hashed_then_removed': rows, 'scratch_created': False,
        'native_capture_ui_or_process_inventory_started': False,
        'production_behavior_source_edits': False,
        'source_identity_after_verified': True,
        'scope': 'Independent actual Rust host component controls only. No canonical/native/public-admission/full-target/GA promotion.'}
    (ROOT / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
    if not summary['all_commands_passed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
