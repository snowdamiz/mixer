#!/usr/bin/env python3
"""Bounded qualification of a fixture-only proposal; never edits the frozen pack."""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import struct
import sys
import time
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / 'verification/swift-cache-state-ci'
INCIDENT = ROOT / 'verification/swift-host-resource-ci-cache-state/artifact-cache-state.stdout'
ORIGINAL_SHA = '140833c2d18655b77769d3f4c1346aee4b0f43aed25dae8e7160860adcd5033f'
INCIDENT_SHA = '2dd78d33633fca8c05ba8eed1c2551b6fd023541d0648becacb0456346a39c9c'
TARGET = 'context_schema_scalar_reserved_and_lengths'
NEGATIVE = 'fixture_repair_oracle::altered_input_label_and_framing_negative_controls'
spec = importlib.util.spec_from_file_location('frozen_cache_runner', FROZEN / 'check_cache_state.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def need(value, message):
    if not value:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def proposal(original):
    need(digest(original) == ORIGINAL_SHA, 'Original fixture source identity differs')
    start = original.index(b'fn context_schema_scalar_reserved_and_lengths() {')
    end = original.index(b'\n#[test]', start)
    old = original[start:end]
    need(old.count(b'Fixture::new()') == 3, 'Expected three fixture constructions')
    new = old.replace(b'Fixture::new()', b'baseline.clone()')
    new = new.replace(b'() {\n', b'() {\n    let baseline=Fixture::new();\n', 1)
    result = original[:start] + new + original[end:]
    need(result.count(b'let baseline=Fixture::new();') == 1, 'One baseline required')
    return result


def word(buffer, offset, value):
    struct.pack_into('<Q', buffer, offset * 8, value)


def independent_reference():
    """Independent Python byte encoder; no parsing/calling Rust fixture helpers."""
    maximum = (1 << 64) - 1
    context = bytearray(8192)
    context[:128] = struct.pack('<16Q', int.from_bytes(b'MIXFIX01', 'little'), 1, 8192,
                               1, 32, 33, 1000, 3, 2, 3, 1, 100, 1000, 500, 0, 0)
    context[128:384] = b''.join(bytes([17 + i]) * 32 for i in range(8))
    profile = bytearray(512)
    profile[:128] = struct.pack('<16Q', int.from_bytes(b'MIXPRF01', 'little'), 1, 512,
                               32, 80000, 1000, 3, 2, 3, 1, 100, 1000, 500, 0, 0, 0)
    profile[128:192] = context[320:384]
    profile[224:256] = context[160:192]
    profile.extend(struct.pack('<IIQQQ', 0, 0xffffffff, maximum, 0, 0) * 80000)
    for row, ty, offset, length in [(40, 2, 10, 20), (41, 1, 100, 50)]:
        struct.pack_into('<IIQQQ', profile, 512 + row * 32, 1, ty, offset, length, 0)
    header = bytearray(512)
    header[:80] = struct.pack('<10Q', int.from_bytes(b'MIXORDR1', 'little'), 1, 512,
                              128, 512, 32, 80000, 64, 512, 33)
    header[128:192] = context[128:192]
    header[192:256] = context[320:384]
    stream = bytearray(header)
    # Payloads are independently enumerated by record kind, then packed together.
    payloads = [
        [maximum, maximum, maximum, maximum, maximum, 0, 0, 0, 0],
        [10, 20, 2, maximum, maximum, 0, 0, 0, 0],
        [10, 20, 2, maximum, maximum, 0, 0, 0, 40],
        [10, 20, 2, maximum, maximum, 0, 0, maximum, 40],
        [10, 20, 2, maximum, maximum, 0, 60, 100, 1000],
        *[[10, 20, 2, 0, maximum, 0, 60, 0, 0] for _ in range(3)],
        *[[10, 20, 2, maximum, maximum, 0, 60, 0, 0] for _ in range(2)],
        [10, 20, 2, 0, 0, 1, 1, 60, 1],
        [10, maximum, 2, 0, 0, 1, 60, 0, 0],
        [maximum, maximum, maximum, maximum, maximum, 0, 5, 0, 0],
    ]
    for kind, payload in enumerate(payloads, 1):
        prefix = [kind, kind, 5 if kind == 13 else 0,
                  0 if kind in (12, 13) else 1, kind * 10, kind * 2,
                  maximum if kind == 13 else 40]
        stream.extend(struct.pack('<16Q', *(prefix + payload)))
    footer = bytearray(512)
    for offset, value in {0: int.from_bytes(b'MIXOEND1', 'little'), 1: 1, 2: 13, 3: 13,
                         5: 13, 6: 130, 7: 26, 8: 1, 10: 130, 11: 26, 14: maximum,
                         15: 33, 33: 5, 34: 2, 35: 32}.items():
        word(footer, offset, value)
    footer[288:352] = context[128:192]
    stream.extend(footer)
    cases = []
    scalars = [(1, 2), (2, 8191), (3, 0), (3, 2), (4, 0), (4, 4194305),
               (5, 32), (5, 64), (6, maximum), (7, 0), (7, 4294967296),
               (8, 0), (8, 65), (9, 0), (9, 65), (10, 0), (10, 2),
               (11, maximum), (12, 99), (13, 0), (13, 1001), (14, 1), (15, 1)]
    for offset, value in scalars:
        changed = bytearray(context)
        word(changed, offset, value)
        cases.append((f'context-{offset}-{value}', bytes(changed)))
    for offset in range(48, 1024):
        changed = bytearray(context)
        word(changed, offset, 1)
        cases.append((f'context-reserved-{offset}', bytes(changed)))
    for length in [0, 1, 8191, 8193]:
        cases.append((f'context-length-{length}', bytes(context[:length]).ljust(length, b'\0')))
    need(len(cases) == len(set(label for label, _ in cases)) == 1003, 'Independent case closure')
    return dict(stream=bytes(stream), profile=bytes(profile), context=bytes(context)), cases


def bind_original_incident(reference, cases):
    need(runner.sha(INCIDENT) == INCIDENT_SHA, 'Original incident artifact identity differs')
    with zipfile.ZipFile(INCIDENT) as archive:
        receipt = json.loads(archive.read('runs/ci-40507305688-1/receipt.json'))
        retention = json.loads(archive.read('runs/ci-40507305688-1/retention.json'))
        rows = [row for row in retention['files'] if 'producer-debug-root-03/' in row['path']]
        need(len(rows) == 4, 'Original terminal case retention differs')
        verified = []
        for row in rows:
            name = Path(row['path']).name
            expected = cases[-1][1] if name == 'context' else b'' if name == 'report' else reference[name]
            observed = archive.read('runs/ci-40507305688-1/' + row['content'])
            need(row['encoding'] == 'identity' and observed == expected and digest(observed) == row['sha256'],
                 'Independent reference differs from original CI retained ' + name)
            verified.append(dict(path=row['path'], bytes=len(observed), sha256=digest(observed)))
        command = next(row for row in receipt['commands'] if row['name'] == 'producer-debug-root-03')
        need(receipt['status'] == 'failed' and command['timed_out'] and command['exit'] == -9
             and command['owned_group_gone'] and receipt['cleanup']['removed'], 'Original failure disposition differs')
        return dict(artifact_sha256=INCIDENT_SHA, source_revision=receipt['source_revision'],
                    command=command, cleanup=receipt['cleanup'], verified_terminal_case=verified,
                    prior_case_cleanup_inference='Only case 1002 remains; run removes each prior case after assertions.')


def prepare():
    runner.verify_pack(FROZEN / 'pack')
    original = (FROZEN / 'pack/source/regression/independent_tests.rs').read_bytes()
    proposed = proposal(original)
    dest = HERE / 'proposal'
    dest.mkdir(exist_ok=True)
    (dest / 'independent_tests.rs').write_bytes(proposed)
    diff = ''.join(difflib.unified_diff(original.decode().splitlines(True), proposed.decode().splitlines(True),
                                      fromfile='pack/source/regression/independent_tests.rs',
                                      tofile='pack/source/regression/independent_tests.rs'))
    (dest / 'fixture-baseline-clone.patch').write_text(diff)
    reference, cases = independent_reference()
    binding = bind_original_incident(reference, cases)
    summary = dict(original_sha256=digest(original), proposed_sha256=digest(proposed),
                   frozen_pack_unchanged=True, target=TARGET, cases=len(cases),
                   scalar_cases=23, reserved_cases=976, length_cases=4,
                   independent_reference={name: dict(bytes=len(data), sha256=digest(data)) for name, data in reference.items()},
                   original_incident=binding, performance_equivalence_claimed=False,
                   repetitive_row_initializations_before=1003 * 80000,
                   repetitive_row_initializations_after=80000,
                   fresh_per_case_files_and_original_analyzer_assertions=True)
    runner.save(HERE / 'proposal.json', summary)
    return proposed, reference, cases, summary


def execute(requested, name):
    proposed, reference, cases, summary = prepare()
    out = HERE / 'runs' / name
    out.parent.mkdir(exist_ok=True)
    need(not out.exists() and out.parent == HERE / 'runs' and name.replace('-', '').isalnum(), 'Fresh owned run required')
    out.mkdir()
    start = time.monotonic()
    receipt = dict(schema=1, status='running', started_utc=runner.now(), argv=sys.argv,
                   active_deadline_seconds=600, cleanup_allowance_seconds=60, per_child_seconds=60,
                   scope='Isolated fixture proposal host compilation and focused tests only',
                   python=dict(version=sys.version, executable=sys.executable, sha256=runner.sha(Path(sys.executable).resolve())),
                   os=platform.platform(), machine=platform.machine(), runner_sha256=runner.sha(Path(__file__)),
                   imported_runner_sha256=runner.sha(FROZEN / 'check_cache_state.py'), proposal=summary,
                   commands=[], errors=[], performance_equivalence_claimed=False,
                   original_ci_failure_remains_failed=True, native_runtime_started=False,
                   global_process_inventory=False, frozen_pack_modified=False, **runner.FLAGS)
    commands = runner.Commands(out, receipt, start + 600)
    scratch = out / 'scratch'
    scratch.mkdir()
    marker = dict(purpose='cache-state-fixture-repair-focused-scratch', token=uuid.uuid4().hex)
    runner.save(scratch / 'ownership.json', marker)
    scratch_id = runner.identity(scratch)
    commands.bind_scratch(scratch)
    products = set()
    handlers = {sig: signal.getsignal(sig) for sig in [signal.SIGALRM, signal.SIGINT, signal.SIGTERM]}

    def alarm(_signum, _frame):
        raise TimeoutError('Fixed active deadline exhausted')

    def interrupted(signum, _frame):
        raise KeyboardInterrupt('Signal ' + str(signum))

    signal.signal(signal.SIGALRM, alarm)
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    signal.setitimer(signal.ITIMER_REAL, 600)
    try:
        revision = commands.run('source-revision', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}'], ROOT)[0].splitlines()
        receipt.update(source_revision=revision[0], source_tree=revision[1])
        launcher = Path(shutil.which(requested)).absolute()
        sysroot = commands.run('compiler-sysroot', [launcher, '--print', 'sysroot'], out)[0].strip()
        compiler = (Path(sysroot) / 'bin/rustc').resolve(strict=True)
        verbose = commands.run('compiler-identity', [compiler, '--version', '--verbose'], out)[0]
        receipt['rustc'] = dict(launcher=str(launcher), path=str(compiler), sha256=runner.sha(compiler),
                                verbose=verbose, identity=runner.rust_identity(verbose))
        receipt['rustc']['distinct_from_failed_ci_1_98_1'] = receipt['rustc']['identity']['release'] != '1.98.1'
        source = scratch / 'source'
        shutil.copytree(FROZEN / 'pack/source', source)
        (source / 'regression/independent_tests.rs').write_bytes(proposed)
        reference_dir = scratch / 'reference'
        reference_dir.mkdir()
        for key, data in reference.items():
            (reference_dir / (key + '.bin')).write_bytes(data)
        packed = bytearray()
        for label, context in cases:
            raw_label = label.encode()
            packed.extend(struct.pack('<II', len(raw_label), len(context)))
            packed.extend(raw_label)
            packed.extend(context)
        (reference_dir / 'cases.bin').write_bytes(packed)
        runner.save(out / 'independent-case-hashes.json', [dict(index=i, label=label, bytes=len(context), sha256=digest(context))
                                                        for i, (label, context) in enumerate(cases)])
        original_methods = json.loads((FROZEN / 'pack/inventories/methods.json').read_bytes())['producer']
        exact = scratch / 'proposal-debug'
        products.add(exact.name)
        commands.run('proposal-debug-compile', [compiler, '--edition=2021', '--test', '--cfg', 'inherited_transport',
                                               'regression/independent_tests.rs', '-o', exact], source)
        listing = commands.run('proposal-debug-list', [exact, '--list'], source)[0]
        runner.verify_methods(listing, original_methods)
        work = scratch / 'exact-test'
        work.mkdir()
        env = dict(MIXER_REVIEW_SCRATCH=str(work))
        text = commands.run('proposal-debug-context', [exact, TARGET, '--exact', '--test-threads=1', '--nocapture'], source, env)[0]
        runner.verify_methods(text, [TARGET], True, len(original_methods) - 1)
        need(not list(work.iterdir()), 'Exact focused test left case scratch')
        receipt['exact_proposal'] = dict(methods_preserved=len(original_methods), focused_method_passed=TARGET,
                                          focused_context_cases=1003, test_case_scratch_empty=True)
        instrumented = source / 'regression/independent_tests.rs'
        control = (HERE / 'oracle_controls.rs').read_bytes()
        instrumented_bytes = proposed.replace(b'fn run(f: &Fixture, framing: bool, label: &str) {\n',
                                              b'fn run(f: &Fixture, framing: bool, label: &str) {\n    fixture_repair_oracle::check(f, framing, label);\n', 1)
        instrumented_bytes = instrumented_bytes.replace(b'let (mut stream,mut profile,mut context,mut output)=open_inputs(f,&path);',
                                                        b'let (mut stream,mut profile,mut context,mut output)=open_inputs(f,&path);\n    fixture_repair_oracle::fresh(&mut stream,&mut profile,&mut context,&mut output);', 1)
        instrumented_bytes = instrumented_bytes.replace(b'fs::remove_dir_all(&path).unwrap();\n}',
                                                        b'fs::remove_dir_all(&path).unwrap();\n    fixture_repair_oracle::completed(&path);\n}', 1) + control
        need(instrumented_bytes != proposed and proposed.count(b'fn run(f: &Fixture, framing: bool, label: &str) {\n') == 1,
             'Control insertion did not bind exact run helper')
        instrumented.write_bytes(instrumented_bytes)
        receipt['instrumented_source_sha256'] = digest(instrumented_bytes)
        receipt['instrumentation'] = ['check exact bytes, labels and framing before original run helper',
                                      'assert all four newly opened cursors at zero and report empty',
                                      'assert each original case cleanup completed', 'append independent negative controls']
        controls = scratch / 'oracle-debug'
        products.add(controls.name)
        commands.run('oracle-debug-compile', [compiler, '--edition=2021', '--test', '--cfg', 'inherited_transport',
                                             'regression/independent_tests.rs', '-o', controls], source)
        listing = commands.run('oracle-debug-list', [controls, '--list'], source)[0]
        runner.verify_methods(listing, original_methods + [NEGATIVE])
        env['MIXER_REPAIR_ORACLE'] = str(reference_dir)
        text = commands.run('oracle-debug-negative', [controls, NEGATIVE, '--exact', '--test-threads=1', '--nocapture'], source, env)[0]
        runner.verify_methods(text, [NEGATIVE], True, len(original_methods))
        text = commands.run('oracle-debug-context', [controls, TARGET, '--exact', '--test-threads=1', '--nocapture'], source, env)[0]
        runner.verify_methods(text, [TARGET], True, len(original_methods))
        need('REPAIR_ORACLE exact_input_cases=1003 fresh_file_cases=1003 completed_case_cleanups=1003' in text,
             'Independent oracle complete case closure missing')
        need(not list(work.iterdir()), 'Instrumented focused test left case scratch')
        receipt['independent_equivalence'] = dict(cases=1003, exact_stream_profile_context_bytes=True,
                                                 labels_and_order=True, original_analyzer_assertions_executed=True,
                                                 all_input_and_output_cursors_fresh=True,
                                                 all_outputs_initially_empty=True, per_case_cleanups=1003,
                                                 negative_controls_passed=NEGATIVE,
                                                 baseline_clone_has_independent_allocations=True)
        need(runner.sha(FROZEN / 'pack/source/regression/independent_tests.rs') == ORIGINAL_SHA, 'Frozen fixture changed')
        runner.verify_pack(FROZEN / 'pack')
        need((HERE / 'proposal/independent_tests.rs').read_bytes() == proposed, 'Proposed source changed')
        receipt['active_checks_completed'] = True
    except BaseException as error:
        receipt['errors'].append(dict(phase='active', type=type(error).__name__, message=str(error)))
    finally:
        receipt['active_elapsed_seconds'] = round(time.monotonic() - start, 6)

        def cleanup_alarm(_signum, _frame):
            raise runner.CleanupDeadlineExpired('Fixed cleanup deadline exhausted')

        signal.signal(signal.SIGALRM, cleanup_alarm)
        signal.setitimer(signal.ITIMER_REAL, 60)
        cleanup_start = time.monotonic()
        try:
            receipt['cleanup'] = runner.cleanup(out, scratch, scratch_id, marker, products, commands)
        except BaseException as error:
            receipt['errors'].append(dict(phase='cleanup', type=type(error).__name__, message=str(error)))
            receipt['cleanup'] = dict(removed=not scratch.exists(), recoverable_scratch=str(scratch) if scratch.exists() else None)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
            receipt['cleanup_elapsed_seconds'] = round(time.monotonic() - cleanup_start, 6)
        receipt.update(finished_utc=runner.now(), elapsed_seconds=round(time.monotonic() - start, 6),
                       status='passed-focused-fixture-proposal' if receipt.get('active_checks_completed') and not receipt['errors'] else 'failed')
        commands.save()
    print(json.dumps(dict(status=receipt['status'], receipt=str(out / 'receipt.json'), errors=receipt['errors'])))
    return 0 if receipt['status'] == 'passed-focused-fixture-proposal' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--rustc', default='rustc')
    parser.add_argument('--run-name', default='focused-1')
    args = parser.parse_args()
    if args.prepare_only:
        _, _, _, summary = prepare()
        print(json.dumps(summary, sort_keys=True))
    else:
        sys.exit(execute(args.rustc, args.run_name))
