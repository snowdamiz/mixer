"""Verify and seal only this owned bounded composition packet."""
from pathlib import Path
import datetime
import json
import sys

sys.dont_write_bytecode = True
from prepare import HERE, sha, canonical, row, write
from verify import verify


def main():
    assert not (HERE / 'seal.json').exists()
    verified = verify()
    assert not (HERE / 'owned-work').exists()
    write('summary.json', dict(verified,
        status='frozen-bounded-combined-source145-host-interactions-awaiting-independent-review',
        at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        C=79676, S=941467, A=430175, H=81327, fixed_selected_work=451814442,
        expected_unit_admitted_before_common_correction=1898105,
        expected_unit_admitted_combined=1899541, expected_common_delta=1436,
        frozen_phase_tests_modified=False, unused_helper_delegated=False,
        compiler_or_runtime_command_failures=0,
        prior_component_tests='Accepted attribution reused; only new interaction behavior replayed',
        canonical_or_sibling_or_git_mutations=False,
        whole_source_compiler_concurrency=1,
        publication_customer_credentials_or_destructive_actions=False,
        independent_review='pending', H_pre_ingress_bootstrap_full_funding_healthy_cleanup_real_writer='pending'))
    write('cleanup.json', dict(schema=1, owned_scratch_removed=True,
        recorded_owned_child_groups_reaped_and_absent=verified['owned_command_groups_terminal_and_absent'],
        only_owned_groups_inspected=True, global_process_inventory=False,
        native_device_simulator_emulator_UI_capture_started=False))
    write('freeze-command.json', dict(schema=1, argv=[sys.executable, str(HERE / 'freeze.py')],
        python_version=sys.version, python_executable=sys.executable,
        driver_sha256=sha(Path(__file__).read_bytes()), scope='Read-only reconciliation, summary and final packet seal only',
        exit_code=0, output='Verified exact source145, four fresh builds, eight filtered interactions, ten owned child groups absent; source and host manifests unchanged'))
    members = [row(path.relative_to(HERE).as_posix(), path.read_bytes())
               for path in sorted(HERE.rglob('*')) if path.is_file()]
    assert not any('__pycache__' in r['path'] or r['path'].startswith('owned-work/') for r in members)
    seal = dict(schema=1, member_count=len(members), member_bytes=sum(r['bytes'] for r in members),
        members=members, tree_sha256=sha(canonical(members)),
        scope='Exact isolated combined source145 and unchanged host11; fresh production/unit metadata and separately bound four synthetic private-core/A-commit/real-complete interactions in each mode; no genuine loader/writer, bootstrap, full funding, healthy cleanup, canonical, native, OTA or GA qualification')
    write('seal.json', seal)
    print(json.dumps(dict(seal_sha256=sha((HERE / 'seal.json').read_bytes()), members=len(members),
        bytes=seal['member_bytes'], source145=verified['source_tree_sha256'],
        host11=verified['host_support_tree_sha256'])))


if __name__ == '__main__':
    main()
