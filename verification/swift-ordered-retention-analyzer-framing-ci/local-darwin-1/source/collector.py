#!/usr/bin/env python3
"""Replay the accepted fixture framing test closure; never grant replay authority."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = 'verification/swift-ordered-retention-analyzer-library'
REVIEW = 'verification/swift-ordered-retention-analyzer-library-review'
FROZEN = {
    PRODUCER: ('777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63', 270),
    REVIEW: ('a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e', 624),
}
SELECTED = {
    PRODUCER + '/src/analyzer.rs': 'source/original/analyzer.rs',
    PRODUCER + '/tests/fixture_tests.rs': 'source/tests/fixture_tests.rs',
    REVIEW + '/independent_tests.rs': 'source/executed-independent-tests.rs',
    REVIEW + '/private_io_tests.rs': 'source/original/private_io_tests.rs',
}
EXPECTED_METHODS = tuple('''all_phase_masks_and_empty_scalar_domain_are_admitted_as_fixtures_only
cap_and_terminal_scalar_forms_are_framing_only
context_schema_scalar_reserved_and_lengths
coordinated_positive_scalar_boundaries_and_unavailable_getters
exact_stream_length_and_coordinates
failure_record_closed_payload_and_bounds
footer_closed_scalar_reserved_flags_and_digest
independently_encoded_all_kind_baseline
output_alias_stale_length_and_cursor_fail_before_mutation
output_clone_hardlink_and_input_aliases_refuse_without_input_mutation
oversized_sparse_stream_is_refused_before_reading_the_envelope
product::independent_transport_review::independent_actual_budget_boundary_and_malformed_tail_override
product::independent_transport_review::independent_allocation_results_and_inventory_value_layouts
product::independent_transport_review::independent_each_input_eof_and_error_paths_refuse_observation
product::independent_transport_review::independent_eof_exact_limit_trailing_and_transport_failures
product::independent_transport_review::independent_exact_32_read_attempts_short_and_interrupted
product::independent_transport_review::independent_input_and_output_metadata_drift_refuse_authority
product::independent_transport_review::independent_output_exact_limit_and_retained_partial_failures
product::tests::allocation_refusal_capacity_mismatch_and_initialization_budget
product::tests::arena_checked_regions_fields_overflow_and_sentinels
product::tests::block_boundaries_footer_straddle_and_bounded_drain
product::tests::concrete_layouts_and_named_role_caps
product::tests::context_closed_fields_reserved_lengths_and_no_real_binding
product::tests::coordinate_negative_sequences_work_instructions_phases_operations
product::tests::empty_profile_zero_scalars_and_defined_zero_length_at_extent_are_finite_only
product::tests::eof_long_short_and_error_never_invent_complete_framing
product::tests::footer_all_scalars_ranges_opaque_ledger_and_cap_shape
product::tests::header_every_scalar_reserved_word_and_digest_echo_mutations
product::tests::immutable_captured_footer_observations_never_reclassify_sidecars
product::tests::io_short_interrupted_zero_error_overreported_and_exact_32_attempts
product::tests::metadata_offset_type_length_and_drift_refusals
product::tests::no_fixture_can_grant_acceptance_or_populate_semantic_metrics
product::tests::pairwise_file_aliases_and_output_freshness_refuse_before_any_write
product::tests::profile_headers_rows_boundaries_and_reserved_words
product::tests::public_file_borrows_report_scope_and_initial_offset
product::tests::record_all_kinds_closed_fields_and_immutable_identity
product::tests::report_short_zero_interrupted_error_overreport_nonempty_and_metadata_failure
product::tests::steps_preflight_exact_boundary_tail_drain_and_bad_footer_override
profile_schema_reserved_digest_and_row_boundaries
readonly_output_and_nonregular_descriptor_refuse
record_all_kind_unused_payloads_and_selected_limits
report_source_digest_echoes_are_observations
stream_header_every_closed_scalar_reserved_and_digest
unknown_context_magic_refuses_real_binding_without_framing'''.splitlines())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def member_path(value):
    path = PurePosixPath(value)
    require(isinstance(value, str) and value == str(path) and not path.is_absolute()
            and '..' not in path.parts and '.git' not in path.parts,
            'Unsafe member path: ' + str(value))
    return Path(value)


def no_symlinks(path):
    """Validate lexical ancestors before any resolve or mutation."""
    require(path.is_absolute(), 'Expected absolute path')
    for part in [*reversed(path.parents), path]:
        require(not part.is_symlink(), 'Symlink path is forbidden: ' + str(part))


def regular_file(path):
    no_symlinks(path)
    require(stat.S_ISREG(path.stat().st_mode), 'Expected regular file: ' + str(path))
    return path


def fresh_output(path, root=ROOT):
    require('..' not in path.parts and '.git' not in path.parts,
            'Output cannot traverse parent or .git components')
    out = Path(os.path.abspath(path))
    no_symlinks(out)
    require(out.parent.is_dir(), 'Output parent must already exist')
    require(not out.exists(), 'Output must be fresh: ' + str(out))
    for packet in (*FROZEN, 'verification/swift-ordered-retention-analyzer-library-root-review'):
        require(not out.is_relative_to(root / packet), 'Output cannot mutate a frozen packet')
    out.mkdir(exist_ok=False)
    return out


def frozen_state(root=ROOT):
    """Hash sealed history, but neither execute nor copy any old packet runner."""
    manifests, all_members = {}, {}
    for packet, (expected, count) in FROZEN.items():
        seal = regular_file(root / packet / 'seal.json')
        require(sha(seal) == expected, 'Frozen seal digest differs: ' + packet)
        sidecar = regular_file(seal.with_suffix('.sha256'))
        require(sidecar.read_text().split()[0] == expected, 'Frozen seal sidecar differs')
        rows = json.loads(seal.read_bytes())['members']
        require(len(rows) == count, 'Frozen member count differs: ' + packet)
        members = {}
        for row in rows:
            relative = member_path(row['path'])
            require(row['path'] not in members, 'Duplicate sealed member')
            source = regular_file(root / relative)
            require(source.stat().st_size == row['bytes'] and sha(source) == row['sha256'],
                    'Frozen member differs: ' + str(relative))
            members[row['path']] = {'bytes': row['bytes'], 'sha256': row['sha256']}
        manifests[packet] = {'seal_sha256': expected, 'members': members,
                             'seal_sidecar_sha256': sha(sidecar)}
        for name, entry in members.items():
            require(name not in all_members or all_members[name] == entry, 'Conflicting frozen member')
            all_members[name] = entry
    return manifests, all_members


def tree_digest(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def snapshot_selection(out, members, root=ROOT):
    selection = dict(SELECTED)
    prefix = PRODUCER + '/inputs/historical/'
    historical = sorted(name for name in members if name.startswith(prefix))
    require(len(historical) == 34, 'Expected exactly 17 historical stream/sidecar pairs')
    binaries = {Path(name).name[:-4] for name in historical if name.endswith('.bin')}
    sidecars = {Path(name).name[:-13] for name in historical if name.endswith('.sidecar.json')}
    require(len(binaries) == 17 and binaries == sidecars, 'Historical pair inventory differs')
    for name in historical:
        selection[name] = 'inputs/historical/' + Path(name).name
    copied = {}
    for name, destination in sorted(selection.items()):
        require(name in members, 'Selected source is not frozen: ' + name)
        source = regular_file(root / member_path(name))
        target = out / member_path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as stream, target.open('xb') as sink:
            shutil.copyfileobj(stream, sink, length=65536)
        require(target.stat().st_size == members[name]['bytes'] and sha(target) == members[name]['sha256'],
                'Snapshot differs: ' + name)
        target.chmod(0o444)
        copied[name] = {**members[name], 'snapshot': destination}
    history = []
    for name in sorted(sidecars):
        relative = 'inputs/historical/' + name + '.sidecar.json'
        sidecar = json.loads((out / relative).read_bytes())
        require(sidecar['status'] == 'invalid' and sidecar['failure'] == 15,
                'Historical classification differs: ' + name)
        binary = out / 'inputs/historical' / (name + '.bin')
        require(sidecar['stream_sha256'] == sha(binary)
                and sidecar['stream_bytes'] == binary.stat().st_size,
                'Historical stream/sidecar join differs: ' + name)
        history.append({'name': name, 'historical_sidecar': {'status': 'invalid', 'failure': 15},
                        'new_framing_observation': 'not a historical reclassification'})
    product = out / 'source/inputs/framing.rs'
    product.parent.mkdir()
    product.write_bytes((out / 'source/original/analyzer.rs').read_bytes() + b'\n'
                        + (out / 'source/original/private_io_tests.rs').read_bytes())
    product.chmod(0o444)
    return copied, history, {'path': 'source/inputs/framing.rs', 'sha256': sha(product),
                             'construction': 'unchanged analyzer.rs + one LF + unchanged private_io_tests.rs; test-only'}


class Commands:
    def __init__(self, out, receipt):
        self.out, self.receipt = out, receipt
        (out / 'commands').mkdir()
        self.active = None

    def save(self):
        write_json(self.out / 'receipt.json', self.receipt)

    def run(self, name, argv, *, cwd, env=None, timeout=15):
        require(self.active is None, 'Only one synchronous child is permitted')
        argv = list(map(str, argv))
        row = {'name': name, 'argv': argv, 'cwd': str(cwd), 'started_utc': now(),
               'timeout_seconds': timeout, 'environment_overrides': env or {},
               'exit': None, 'timed_out': False, 'child_returned': False}
        self.receipt['commands'].append(row)
        self.save()
        start = time.monotonic()
        stdout, stderr = [self.out / 'commands' / (name + suffix) for suffix in ('.stdout', '.stderr')]
        try:
            with stdout.open('xb') as output, stderr.open('xb') as error:
                command_env = dict(os.environ)
                # Caller test filters/options cannot silently alter this fixed closure.
                for key in ('RUST_TEST_THREADS', 'RUST_TEST_NOCAPTURE', 'RUST_TEST_TIME_UNIT',
                            'RUST_TEST_TIME_INTEGRATION', 'RUST_TEST_TIME_DOCTEST'):
                    command_env.pop(key, None)
                command_env.update(env or {})
                self.active = subprocess.Popen(argv, cwd=cwd, env=command_env,
                                               stdout=output, stderr=error, start_new_session=True)
                row['pid'] = self.active.pid
                try:
                    self.active.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    row['timed_out'] = True
                    try:
                        os.killpg(self.active.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    self.active.wait()
                row['exit'] = self.active.returncode
                row['child_returned'] = True
        except OSError as error:
            row['spawn_error'] = str(error)
        finally:
            if self.active is not None and not row['child_returned']:
                # An interrupted collector must return its own child before cleanup, too.
                try:
                    os.killpg(self.active.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.active.wait()
                row['exit'] = self.active.returncode
                row['child_returned'] = True
            self.active = None
            row['finished_utc'] = now()
            row['elapsed_seconds'] = round(time.monotonic() - start, 6)
            for label, path in [('stdout', stdout), ('stderr', stderr)]:
                if path.exists():
                    row[label] = {'path': str(path.relative_to(self.out)), 'bytes': path.stat().st_size,
                                  'sha256': sha(path)}
            write_json(self.out / 'commands' / (name + '.json'), row)
            self.save()
        require(row['child_returned'] and row['exit'] == 0 and not row['timed_out'],
                'Command failed: ' + name + '; see retained command receipt')
        return stdout.read_text()


def verify_methods(output):
    names = [line[:-6] for line in output.splitlines() if line.endswith(': test')]
    require(len(names) == 44 and len(set(names)) == 44 and set(names) == set(EXPECTED_METHODS),
            'Frozen 44-method inventory differs')
    return sorted(names)


def preserve_and_cleanup(out, scratch, identity, marker):
    """Retain test-created files, then remove only this exact owned scratch inode."""
    no_symlinks(scratch)
    current = scratch.stat()
    require((current.st_dev, current.st_ino) == identity, 'Owned scratch identity changed; retained')
    require(json.loads((scratch / 'ownership.json').read_text()) == marker,
            'Owned scratch marker changed; retained')
    retained = out / 'retained'
    retained.mkdir()
    inventory = {}
    for source in sorted(scratch.rglob('*')):
        require(not source.is_symlink(), 'Symlink in scratch; preserve for inspection')
        if source.is_dir():
            continue
        require(stat.S_ISREG(source.stat().st_mode), 'Special scratch member; preserve for inspection')
        relative = source.relative_to(scratch)
        # Compiler products are identified by hashes; retain test-created input/output bytes.
        if str(relative) in ('foundation.rlib', 'framing-tests', 'ownership.json'):
            continue
        target = retained / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        uncompressed_bytes = source.stat().st_size
        # A failed oversized-stream control can leave a 536,871,937-byte sparse
        # fixture. Preserve its exact bytes with bounded streaming compression.
        if uncompressed_bytes > 16 * 1024 * 1024:
            target = target.with_name(target.name + '.gz')
            with source.open('rb') as stream, gzip.open(target, 'xb') as sink:
                shutil.copyfileobj(stream, sink, length=65536)
            encoding = 'gzip'
        else:
            shutil.copyfile(source, target)
            encoding = 'identity'
        inventory[str(relative)] = {'path': str(target.relative_to(out)), 'encoding': encoding,
                                    'bytes': target.stat().st_size, 'sha256': sha(target),
                                    'uncompressed_bytes': uncompressed_bytes,
                                    'uncompressed_sha256': sha(source)}
    # No running child can still own these files; the caller checks that separately.
    shutil.rmtree(scratch)
    require(not scratch.exists(), 'Owned scratch cleanup did not finish')
    return {'path': str(scratch), 'identity': list(identity), 'marker': marker,
            'removed': True, 'children_returned_before_cleanup': True,
            'retained_test_files': inventory, 'other_processes_or_instances_queried': False}


def execute(out, rustc, root=ROOT):
    receipt = {'schema': 1, 'started_utc': now(), 'invocation': sys.argv,
               'collector_sha256': sha(Path(__file__)), 'python': platform.python_version(),
               'python_executable': str(Path(sys.executable).resolve()),
               'platform': platform.platform(), 'machine': platform.machine(), 'system': platform.system(),
               'scope': 'Accepted standalone fixture framing foundation, 20 producer plus 24 independent host methods. CI evidence preparer only; no real analyzer source authority adapter.',
               'storedPrefixValidated': False, 'fullReplayAccepted': False,
               'native_capture_or_device_execution': False, 'linux_qualification': 'unqualified',
               'commands': [], 'result': 'failed', 'errors': []}
    commands = Commands(out, receipt)
    marker = {'owner': 'scripts/ci/check-analyzer-framing.py', 'output': str(out), 'nonce': str(uuid.uuid4())}
    write_json(out / 'ownership.json', marker)
    (out / 'source').mkdir()
    shutil.copyfile(Path(__file__), out / 'source/collector.py')
    scratch, identity, before = None, None, None
    try:
        receipt['revision_before'] = commands.run('revision-before', ['git', 'rev-parse', 'HEAD'], cwd=root).strip()
        before, members = frozen_state(root)
        receipt['frozen_before'] = before
        receipt['frozen_tree_sha256'] = tree_digest(before)
        selected, history, appended = snapshot_selection(out, members, root)
        receipt.update(selected_closure=selected, selected_tree_sha256=tree_digest(selected),
                       historical_sidecars=history, test_only_appended_source=appended)
        resolved = shutil.which(str(rustc))
        require(resolved is not None, 'rustc executable was not found: ' + str(rustc))
        launcher = Path(resolved).absolute()
        compiler = launcher.resolve(strict=True)
        receipt['rustc_launcher'] = {'path': str(launcher), 'resolved_path': str(compiler),
                                     'sha256': sha(compiler)}
        if compiler.name == 'rustup':
            selected = commands.run('rustc-resolve', [compiler, 'which', 'rustc'], cwd=root).strip()
            require('\n' not in selected and Path(selected).is_absolute(), 'Invalid rustup compiler selection')
            compiler = Path(selected).resolve(strict=True)
        require(compiler.is_file(), 'rustc is not a file')
        receipt['rustc'] = {'requested': str(rustc), 'path': str(compiler), 'sha256': sha(compiler)}
        receipt['rustc']['version_verbose'] = commands.run('rust-version', [compiler, '--version', '--verbose'], cwd=out)
        receipt['python_version_output'] = commands.run('python-version', [sys.executable, '--version'], cwd=out)
        scratch = out / 'scratch'
        scratch.mkdir()
        write_json(scratch / 'ownership.json', marker)
        stamp = scratch.stat()
        identity = stamp.st_dev, stamp.st_ino
        (scratch / 'producer').mkdir()
        commands.run('library-compile', [compiler, '--edition=2021', '--crate-type=lib', '-Dwarnings',
                                       out / 'source/original/analyzer.rs', '-o', scratch / 'foundation.rlib'],
                     cwd=out, timeout=60)
        receipt.setdefault('compiled_artifacts', {})['unchanged_library'] = sha(scratch / 'foundation.rlib')
        commands.run('test-compile', [compiler, '--edition=2021', '--test', '-Dwarnings', '-O',
                                    out / 'source/executed-independent-tests.rs', '-o', scratch / 'framing-tests'],
                     cwd=out, timeout=60)
        receipt['compiled_artifacts']['combined_test_binary'] = sha(scratch / 'framing-tests')
        listing = commands.run('test-list', [scratch / 'framing-tests', '--list'], cwd=out)
        receipt['methods'] = verify_methods(listing)
        output = commands.run('test-execute', [scratch / 'framing-tests', '--test-threads=1', '--nocapture'],
                              cwd=out, timeout=120,
                              env={'MIXER_REVIEW_SCRATCH': str(scratch),
                                   'MIXER_ANALYZER_LIBRARY_TEST_SCRATCH': str(scratch / 'producer'),
                                   'MIXER_ANALYZER_LIBRARY_HISTORICAL': str(out / 'inputs/historical')})
        require('test result: ok. 44 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in output,
                'Exact 44-method pass summary is absent')
        passed = [line[5:].split(' ... ')[0] for line in output.splitlines()
                  if line.startswith('test ') and ' ... ' in line]
        require(len(passed) == 44 and set(passed) == set(EXPECTED_METHODS), 'Executed method names differ')
        require('HISTORICAL_SIDECARS_INVALID=17 FOOTER_GRAMMAR_REFUSED=7 FOOTER_ONLY_OBSERVED=10' in output,
                'Historical observation receipt differs')
        receipt['passed_methods'] = 44
        receipt['result'] = 'passed'
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        receipt['errors'].append(str(error))
    finally:
        if sha(Path(__file__)) != receipt['collector_sha256'] or sha(out / 'source/collector.py') != receipt['collector_sha256']:
            receipt['errors'].append('Collector source changed during execution')
        if before is not None:
            try:
                after, _ = frozen_state(root)
                receipt['frozen_after_tree_sha256'] = tree_digest(after)
                require(after == before, 'Original frozen packets changed during execution')
                for source, row in receipt.get('selected_closure', {}).items():
                    require(sha(regular_file(root / source)) == row['sha256']
                            and sha(regular_file(out / row['snapshot'])) == row['sha256'],
                            'Selected source or snapshot changed: ' + source)
                if 'test_only_appended_source' in receipt:
                    appended = receipt['test_only_appended_source']
                    require(sha(regular_file(out / appended['path'])) == appended['sha256'],
                            'Test-only appended source changed')
                receipt['frozen_packets_unchanged'] = True
            except (OSError, RuntimeError, ValueError, KeyError) as error:
                receipt['errors'].append('Postflight: ' + str(error))
        try:
            receipt['revision_after'] = commands.run('revision-after', ['git', 'rev-parse', 'HEAD'], cwd=root).strip()
        except (OSError, RuntimeError) as error:
            receipt['errors'].append('Revision postflight: ' + str(error))
        if scratch is not None and identity is not None:
            try:
                require(commands.active is None and all(row['child_returned'] or 'spawn_error' in row
                                                       for row in receipt['commands']),
                        'Cannot clean scratch before children return')
                receipt['cleanup'] = preserve_and_cleanup(out, scratch, identity, marker)
            except (OSError, RuntimeError, ValueError) as error:
                receipt['errors'].append('Cleanup: ' + str(error))
        else:
            receipt['cleanup'] = {'created': False, 'removed': False, 'reason': 'No scratch was created'}
        if receipt['errors']:
            receipt['result'] = 'failed'
        receipt['finished_utc'] = now()
        commands.save()
    print(json.dumps({'result': receipt['result'], 'receipt': str(out / 'receipt.json'),
                      'passed_methods': receipt.get('passed_methods', 0), 'errors': receipt['errors']}))
    return 0 if receipt['result'] == 'passed' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='Fresh output; existing parent, no symlink ancestors')
    parser.add_argument('--rustc', default='rustc', help='Compiler path or command; resolved and recorded before use')
    args = parser.parse_args(argv)
    try:
        out = fresh_output(args.output)
    except (OSError, RuntimeError) as error:
        parser.exit(2, str(error) + '\n')
    return execute(out, args.rustc)


if __name__ == '__main__':
    raise SystemExit(main())
