#!/usr/bin/env python3
"""Audit and seal the completed bounded host qualification; never rerun it."""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
spec = importlib.util.spec_from_file_location('candidate4_qualified_runner', BASE / 'qualify.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def main():
    check = runner.check
    receipt = runner.load(BASE / 'receipt.json')
    check(receipt['status'] == 'passed-exact-candidate4-profile3-host-qualification-awaiting-independent-root-review',
          'qualification did not pass')
    runner.require(BASE / 'qualify.py', receipt['runner'])
    q = runner.Qualification()
    q.commands = runner.load(BASE / 'commands.json')
    q.versions = receipt['tool_versions']
    check(len(q.commands) == 96, 'unexpected initial command count')
    # Resolve the actual selected Xcode tool binaries in addition to the hashed
    # /usr/bin launcher and retained version output used by the completed build.
    compiler = {}
    for name in ('swift', 'swiftc'):
        out, _ = q.run('resolve-host-' + name, ['/usr/bin/xcrun', '--find', name])
        path = Path(out.decode().strip()).resolve()
        compiler[name] = {'path': str(path), **runner.identity(path.read_bytes())}
    out, err = q.run('resolved-host-swiftc-version', [compiler['swiftc']['path'], '--version'])
    version = (out + err).decode().strip()
    check(version.splitlines()[0] == receipt['tool_versions']['host-swift'].splitlines()[0],
          'resolved compiler version differs from build version')
    q.run('final-owned-diff-check', ['/usr/bin/git', 'diff', '--check', '--', *runner.OWNED,
                                    'docs/android-private-owner-profile3-integration.md'])
    for command in q.commands:
        folder = BASE / 'commands' / command['label']
        check(command['exit'] == command['expected_exit'] and not command['timed_out'] and command['child_reaped'],
              'nonpassing command: ' + command['label'])
        runner.require(folder / 'stdout', command['stdout'])
        runner.require(folder / 'stderr', command['stderr'])
        check(runner.load(folder / 'result.json') == command, 'command result mismatch')
        check(command['pid'] == command['pgid'] and command['timeout_seconds'] > 0, 'unbounded or unowned command')
    source = runner.load(BASE / 'source-binding.json')
    for name, expected in source['files'].items():
        runner.require(BASE / 'source' / name, expected)
        runner.require(ROOT / name, expected)
    final_owned = runner.load(BASE / 'final-owned-sources.json')
    for name in runner.OWNED:
        runner.require(ROOT / name, final_owned[name])
    history = {p.relative_to(BASE.parent).as_posix(): runner.identity(p.read_bytes())
               for p in sorted(BASE.parent.rglob('*')) if p.is_file() and BASE not in p.parents}
    check(history == runner.load(BASE / 'historical-inputs-before.json') ==
          runner.load(BASE / 'historical-inputs-after.json'), 'historical inputs changed')
    candidate_manifest = runner.load(runner.CANDIDATE / 'manifest.json')
    runner.pin(runner.CANDIDATE / 'manifest.json', runner.PINS['candidate_manifest'])
    for name, expected in candidate_manifest['files'].items():
        runner.require(runner.CANDIDATE / name, expected)
    canonical = runner.load(runner.CANDIDATE / 'source-map.json')
    for name, expected in canonical.items():
        runner.require(ROOT / name, expected)
    bindings = runner.load(BASE / 'consumer-source-binding.json')
    for folder, key in [('Profile3Consumer', 'created'), ('CopiedConsumer', 'copied_and_customized')]:
        check(runner.regular_files(BASE / folder) == bindings[key], 'consumer source drift')
    for removed in receipt['cleanup']['owned_scratch_removed']:
        check(not (BASE / removed).exists(), 'owned build scratch remains')
    products = runner.load(BASE / 'compiled-products-before-cleanup.json')
    for label, product in receipt['compiled_products'].items():
        relative = str(Path(product['path']).relative_to(BASE))
        check(products[relative] == {k: product[k] for k in ('bytes', 'sha256')}, 'CLI precleanup hash mismatch')
    check(len(products) == 39, 'host product inventory changed')
    doc = ROOT / 'docs/android-private-owner-profile3-integration.md'
    (BASE / 'documentation.md').write_bytes(doc.read_bytes())
    runner.save(BASE / 'seal-receipt.json', {
        'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv': [sys.executable, *sys.argv], 'cwd': str(ROOT), 'pid': os.getpid(), 'pgid': os.getpgrp(),
        'python_version': sys.version, 'python_executable': receipt['python_executable'],
        'script': runner.identity(Path(__file__).read_bytes()), 'limits': receipt['limits'],
        'status': 'closed-host-qualification-packet-awaiting-independent-root-review',
        'candidate_manifest': runner.PINS['candidate_manifest'], 'selection': runner.PINS['selection'],
        'profile_proposal': runner.PINS['profile'], 'final_five': final_owned,
        'source_members': len(source['files']), 'source_projection_sha256': source['projection_sha256'],
        'candidate_members_reverified': len(candidate_manifest['files']), 'canonical_members_reverified': len(canonical),
        'commands_passed_with_expected_disposition': len(q.commands),
        'actual_negative_CLI_driver_commands': sum(c['expected_exit'] != 0 for c in q.commands),
        'Swift_methods_per_Debug_Release': 13, 'Python_methods_per_normal_optimized': [10, 9, 11],
        'copied_host_shared_methods': 4, 'copied_host_session_methods': 3, 'copied_custom_factory_reducer_methods': 1,
        'actual_host_compiler_provenance': compiler, 'resolved_host_swiftc_version': version,
        'documentation': {'path': str(doc.relative_to(ROOT)), **runner.identity(doc.read_bytes())},
        'compiled_products_hashed_before_cleanup': len(products), 'historical_profile_inputs_unchanged': True,
        'native_runtime_capture_UI_or_process_discovery': False, 'native_compilation_credit': 'producer provenance reuse only',
        'implementation_accepted': False, 'GA_qualified': False,
    })
    files = {}
    for path in sorted(BASE.rglob('*')):
        if not path.is_file() or path.name == 'manifest.json':
            continue
        check(not path.is_symlink(), 'packet symlink')
        files[path.relative_to(BASE).as_posix()] = runner.identity(path.read_bytes())
    runner.save(BASE / 'manifest.json', {'schema': 1, 'members': len(files),
                                        'bytes': sum(x['bytes'] for x in files.values()), 'files': files})
    print(json.dumps({'members': len(files), 'bytes': sum(x['bytes'] for x in files.values()),
                      'manifest': runner.identity((BASE / 'manifest.json').read_bytes()),
                      'seal_receipt': runner.identity((BASE / 'seal-receipt.json').read_bytes())}, indent=2))


if __name__ == '__main__':
    main()
