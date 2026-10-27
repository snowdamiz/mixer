"""Reconcile recorded commands without recompilation, then freeze owned evidence."""
from pathlib import Path
import datetime
import json
import os
import sys
import time

sys.dont_write_bytecode = True
from audit import HERE, ROOT, P, KEYS, TREE, HOST, digest, canon, read, write, row, roster, unpack, checked_sources, inspect


def main():
    assert not (HERE / 'seal.json').exists(), 'Frozen packet must not be rewritten'
    start = time.monotonic()
    assert inspect() == read(HERE / 'audit-results.json')
    _, source, hosts = checked_sources()
    own_tests = dict(source)
    for name, part in [('src/experimental_swift_reactor/control_tests.rs', HERE / 'interaction-tests.inc.rs'),
                       ('src/experimental_swift_reactor/cache.rs', P / 'cache-tests.inc.rs'),
                       ('src/experimental_swift_reactor/cache/initial_profile_v1.rs', P / 'profile-tests.inc.rs')]:
        own_tests[name] += part.read_bytes()
    for mode in ('interactions-debug', 'interactions-optimized'):
        command = read(P / 'commands' / (mode + '-tests') / 'receipt.json')
        assert command['exit_code'] == 0 and command['child_reaped'] and command['owned_group_absent']
        assert not command['timed_out_or_output_limited']
        for stream in ('stdout', 'stderr'):
            assert digest((P / 'commands' / (mode + '-tests') / stream).read_bytes()) == command[stream + '_sha256']
    result = []
    for mode in ('debug', 'optimized'):
        pre = HERE / 'preimages' / mode
        raw = (pre / 'manifest.json').read_bytes()
        identity = json.loads(raw)
        binding = read(pre / 'binding.json')
        assert raw == canon(identity)
        assert identity['distribution'] == roster(source)
        assert identity['compiled_source'] == roster(own_tests)
        assert identity['host_support'] == roster(hosts)
        assert identity['tools_runner_SDK_outside_host11']
        build = read(HERE / 'commands' / (mode + '-compile') / 'receipt.json')
        assert unpack((pre / 'argv.bin').read_bytes()) == [os.fsencode(v) for v in build['argv']]
        assert '--test' in build['argv'] and '--emit=link' in build['argv']
        bare = {k: v for k, v in build['environment'].items() if k not in KEYS}
        assert unpack((pre / 'environment.bin').read_bytes()) == [os.fsencode(k + '=' + v) for k, v in sorted(bare.items())]
        expected = dict(zip(KEYS, (digest(raw), digest((pre / 'argv.bin').read_bytes()),
            digest((pre / 'environment.bin').read_bytes()), identity['tools']['rustc']['sha256'],
            digest((pre / 'compiler-version.txt').read_bytes()))))
        assert binding['compile_identity_keys'] == expected
        assert {k: build['environment'][k] for k in KEYS} == expected
        assert build['runner_sha256'] == next(i['sha256'] for i in identity['orchestration'] if i['path'].endswith('/run.py'))
        for item in [identity['tools']['rustc'], identity['tools']['python'], identity['tools']['cc'],
                     *identity['tools']['SDK_headers'], identity['root_release'], *identity['orchestration']]:
            path = Path(item['path'])
            if path == HERE / 'run.py' and mode == 'debug':
                path = HERE / 'attempt-history/test-output-format-v1/run.py'
            assert row(item['path'], path.read_bytes()) == item
        for kind in ('rustc-version', 'compile', 'tests'):
            folder = HERE / 'commands' / (mode + '-' + kind)
            rec = read(folder / 'receipt.json')
            assert rec['exit_code'] == 0 and rec['child_reaped'] and rec['owned_group_absent']
            assert not rec['timed_out_or_output_limited']
            for stream in ('stdout', 'stderr'):
                assert digest((folder / stream).read_bytes()) == rec[stream + '_sha256']
        stdout = (HERE / 'commands' / (mode + '-tests') / 'stdout').read_bytes()
        assert b'4 passed; 0 failed; 0 ignored; 0 measured; 468 filtered out' in stdout
        assert sum(s.startswith(b'test experimental_swift_reactor::control::tests::combined_independent_') for s in stdout.splitlines()) == 4
        assert b'retained=1899541 work=451814442 live=5 same_ticket=true provenance=ordinary-synthetic' in stdout
        for ceiling in (0, 451814441):
            assert ('first-work ceiling=%d attempted=451814442 work=0 live=0 peak=0' % ceiling).encode() in stdout
        artifact = read(HERE / 'commands' / (mode + '-compile') / 'artifact.json')
        cleanup = read(HERE / 'commands' / (mode + '-compile') / 'cleanup.json')
        assert artifact == cleanup['removed_artifact'] and not Path(artifact['path']).exists()
        assert cleanup['owned_groups_absent'] and cleanup['scratch_removed']
        assert cleanup['completed'] == (mode == 'optimized')
        result.append(dict(mode=mode, tests_passed=4, tests_failed=0,
            executable_bytes=artifact['bytes'], executable_sha256=artifact['sha256'],
            compiled_tree_sha256=roster(own_tests)['tree_sha256'], manifest_sha256=digest(raw),
            five_identity_keys_reconciled=True, owned_child_groups_terminal=3, scratch_removed=True,
            postcheck='original textual output-count assumption failed after all Rust tests passed; reconciled without rerun' if mode == 'debug' else 'passed'))
    assert not (HERE / 'owned-work').exists()
    audit = read(HERE / 'commands/audit/receipt.json')
    assert audit['exit_code'] == 0 and audit['owned_group_absent'] and audit['child_reaped']
    write('review.json', dict(schema=1,
        status='accepted-bounded-exact-combined-source-and-synthetic-private-interaction-evidence',
        blocking_findings=[], producer_members_verified=97, producer_bytes_verified=622914,
        producer_seal_sha256='2eb3dab82f2b492b491e9f80e1d05fb0f8745e41c452f4f3bc777a33b62e8bdc',
        source_members=145, source_tree_sha256=TREE, host_support_members=11, host_support_tree_sha256=HOST,
        overlay_files=4, overlay_bytes=180134, component_orders_byte_identical=6,
        descriptor_count_and_five_key_bindings_verified=True,
        producer_unit_metadata='successful typechecking only; zero-byte output; no usable loader output record or executable',
        producer_production_metadata_bytes=24482879, producer_tests_passed_each_mode=4,
        independent_builds=result, independent_tests_passed=8, Rust_compile_failures=0, Rust_test_failures=0,
        independent_audit_driver_assumptions=4, independent_audit_timeouts=1,
        independent_post_test_reporting_assumptions=1, producer_preparation_assumptions=2,
        producer_metadata_extent_assumptions=1, failures_preserved=True,
        fixed_execution_work=451814442, selected_construction=1469366, A=430175, retained_unit_floor=1899541,
        accepted_common_delta=1436, same_ticket_held_through_actual_complete=True, first_work_refusal_atomic=True,
        synthetic_private_fixture_has_no_selected_loader_provenance=True, helper_unused=True, WorkAuditPending=True,
        conservative_ConstructionBound_preserved=True,
        actual_loader_guest_cache_scope_construct_writer_or_helper_executed=False,
        bootstrap_H_full_funding_healthy_cleanup_final_production_caller_native_OTA_GA_qualified=False,
        no_active_new_host_account_or_loader_composition=True,
        own_groups_inspected_only=True, producer_old_PIDs_not_reprobed=True,
        native_UI_capture_or_global_inventory=False, owned_scratch_removed=True, canonical_and_git_changed=False))
    write('finalize-command.json', dict(schema=1, argv=['python3',str(Path(__file__).resolve())],
        cwd=str(ROOT), at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        python_version=sys.version, python=row(str(Path(sys.executable).resolve()),Path(sys.executable).resolve().read_bytes()),
        source_tree_sha256=TREE, exit_code=0, elapsed_seconds=time.monotonic()-start,
        result='All recorded identities and 8 independent host tests reconciled; scratch absent; no recompilation or runtime invocation',
        scope='Read-only reconciliation of frozen inputs and owned test receipts; no process inventory'))
    members = [row(str(p.relative_to(HERE)), p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file()]
    assert all('__pycache__' not in r['path'] and not r['path'].startswith('owned-work/') for r in members)
    seal = dict(schema=1, member_count=len(members), member_bytes=sum(r['bytes'] for r in members),
                tree_sha256=digest(canon(members)), members=members,
                scope='Independent exact source145/host11 composition and separately bound synthetic private host interactions; no runtime loader, final funding, native, OTA or GA qualification')
    write('seal.json', seal)
    print(json.dumps(dict(seal_sha256=digest((HERE / 'seal.json').read_bytes()),
        member_count=seal['member_count'], member_bytes=seal['member_bytes'], source_tree_sha256=TREE,
        independent_tests=8, blocking_findings=0, Rust_failures=0, scratch_removed=True), sort_keys=True))


if __name__ == '__main__':
    main()
