#!/usr/bin/env python3
"""Independent source/packet review; no Cargo/compiler/test or process probes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/vm-cancellation-ci-correction'
started = time.monotonic()
inputs, paths = {}, {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def read(path, expected=None):
    assert time.monotonic() - started < 55 and path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    if expected is not None:
        assert sha(raw) == expected, path
    name = str(path.relative_to(R))
    row = {'bytes': len(raw), 'sha256': sha(raw)}
    assert name not in inputs or inputs[name] == row
    inputs[name], paths[name] = row, path
    return raw


def load(path):
    return json.loads(read(path), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


for path in sorted(P.iterdir()):
    assert path.is_file() and not path.is_symlink()
    read(path)
receipt = load(P / 'receipt.json')
manifest = read(P / 'source-manifest.sha256', receipt['source_manifest_sha256'])
manifest_rows = []
for line in manifest.decode().splitlines():
    digest, name = line.split('  ', 1)
    assert re.fullmatch(r'[0-9a-f]{64}', digest) and not Path(name).is_absolute() and '..' not in Path(name).parts
    read(R / name, digest)
    manifest_rows.append(name)
assert len(manifest_rows) == len(set(manifest_rows)) == 15
assert receipt['source_revision'] == (P / 'head.stdout').read_text().strip() == 'd87ce0a1b05a9ad42cd2118bbf2ccc5491499663'
assert receipt['changed_product_sources'] == [] and receipt['changed_test_sources'] == ['vm/tests/span_execution.rs']
before_raw = read(D / 'before.rs.txt', receipt['test_before_sha256'])
after_raw = read(R / 'vm/tests/span_execution.rs', '8412a9914c6d4698fd9e0d9f71506101aafe80d218e56c389d1a95047d377321')
assert sha(after_raw) == receipt['test_after_sha256']
assert read(D / 'actual-test.diff') == read(P / 'proposed-change.stdout')
assert read(D / 'product-and-observer.diff') == b''
before, after = before_raw.decode(), after_raw.decode()
names = re.findall(r'#\[test\]\s*fn (\w+)\(', after)
old_names = re.findall(r'#\[test\]\s*fn (\w+)\(', before)
new_name = 'cancellation_during_guest_memory_growth_is_terminal_and_cleans_frames'
assert len(names) == len(set(names)) == 17 and len(old_names) == 16
assert set(names) == set(old_names) | {new_name}
admission = 'fn invocation_admission_is_terminal_and_cancellation_before_construct_or_dispatch() {'
old_admission = before[before.index(admission):]
old_admission = old_admission[:old_admission.index('\n#[test]')]
new_admission = after[after.index(admission):]
new_admission = new_admission[:new_admission.index('\n#[test]')]
assert new_admission == old_admission[:old_admission.index('    // Cancellation arrives after a long-running invocation has begun.')] + '}\n'
body = after[after.index('fn ' + new_name + '() {'):]
body = body[:body.index('\n#[test]')]
assert after.count('allocation_observer::Ownership::new()') == after.count('allocation_observer::begin(') == 1
assert body.index('functions.pin(0, &token).unwrap()') < body.index('functions.release(pin).unwrap()') < body.index('SpanInstance::new(') < body.index('allocation_observer::begin(0, 1, &token)') < body.index('span.invoke("run", &[])') < body.index('operation.finish()')
for token in ('vec![0x41, 0, 0x41, 7, 0x36, 2, 0, 0x41, 1, 0x40, 0, 0x1a, 0x0b]',
    'spec.memory = Some((1, 2));', 'assert!(!token.is_cancelled());',
    'assert_eq!(error.kind, ExecutionFailureKind::Cancelled, "{error:?}");',
    'assert_eq!(error.code, "cancelled", "{error:?}");', 'assert_eq!(error.cache_failure, None, "{error:?}");',
    'assert_eq!(error.usage.instructions, 5, "{error:?}");', '&span.memory()[..4], &[7, 0, 0, 0]',
    'assert_eq!(span.memory().len(), 65536);', 'assert_eq!(error.usage.memory_pages, 1);',
    'assert_eq!(error.usage.state_reserved, initial_state);', 'assert_eq!(span.invoke("run", &[]), Err(error));', 'clean(&span);'):
    assert token in body, token
assert 'std::thread::sleep' not in after and 'std::thread::spawn' not in body
observer = read(R / 'vm/tests/common/allocation_observer.rs').decode()
assert 'if !active() {\n        return true;\n    }' in observer
assert observer.index('if !active()') < observer.index('CALLS.fetch_add(1')
assert 'static ACTIVE: Cell<bool>' in observer and 'static CANCEL_AT: Cell<usize>' in observer
assert 'static OWNED: Cell<bool>' in observer and 'static CANCEL: RefCell<Option<Cancellation>>' in observer
assert '#[test]' not in observer
assert 'ACTIVE.with(|value| value.set(false));' in observer and 'impl Drop for Operation' in observer
assert 'LedgerGuard::acquire().ledger().remove(pointer as usize);' in observer
execute = read(R / 'vm/src/execute.rs').decode()
assert 'pub struct Cancellation(Arc<AtomicBool>);' in execute
assert 'self.0.store(true, Ordering::Relaxed);' in execute
execution = read(R / 'vm/src/experimental/execution/mod.rs').decode()
growth = read(R / 'vm/src/experimental/execution/borrowed.rs').decode()
assert 'self.values = self.allocation(self.budget.live_values)?;' in execution
assert 'self.controls = self.allocation(self.budget.live_controls)?;' in execution
assert 'self.frames = self.allocation(self.cache.spans().limits().call_depth)?;' in execution
assert 'let mut memory = $leaf!(allocation $this, bytes)?;' in growth
assert growth.index('let mut memory = $leaf!(allocation $this, bytes)?;') < growth.index('$leaf!(zero_check $this, memory)?;')
assert '(rollback $s:ident,$memory:ident,$bytes:ident) => {drop($memory);$s.usage.state_reserved -= $bytes;};' in growth
assert 'if let Some(error) = self.failure {\n            return Err(error);\n        }' in execution
assert 'self.failure = Some(error);' in execution and 'error.usage = self.usage;' in execution
ci = read(R / 'verification/github-delivery-dependency-model/job-122629888437-tail.log').decode()
assert 'left: Cache' in ci and 'right: Cancelled' in ci and 'tests/span_execution.rs:685:5' in ci
assert 'cache_failure:' not in ci

plan = load(P / 'validation-plan.json')
commands = [row['argv'] for row in plan['commands']]
expected = [['cargo', '--version'], ['rustc', '--version'],
    ['rustfmt', '--check', '--edition', '2021', 'vm/tests/span_execution.rs'],
    ['cargo', 'test', '--locked', '--offline', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-span-execution', '--test', 'span_execution', '--', '--nocapture'],
    ['cargo', 'test', '--locked', '--offline', '--release', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-span-execution', '--test', 'span_execution', '--', '--nocapture'],
    ['cargo', 'clippy', '--locked', '--offline', '--manifest-path', 'vm/Cargo.toml', '--features', 'experimental-span-execution', '--test', 'span_execution', '--', '-D', 'warnings']]
assert commands == expected
assert [row['timeout_seconds'] for row in plan['commands']] == [1, 1, 3, 20, 20, 10]
assert sum(row['timeout_seconds'] for row in plan['commands']) == plan['maximum_cumulative_command_seconds'] == 55
assert plan['cwd'] == str(R) and all('--test-threads=1' not in command for command in commands)
assert 'ordinary remote VM CI' in plan['external_validation']
after_inputs = {name: {'bytes': len(path.read_bytes()), 'sha256': sha(path.read_bytes())} for name, path in paths.items()}
assert after_inputs == inputs
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_TEST_ONLY_CANCELLATION_CORRECTION_SOURCE_REVIEW_BOUNDED_VALIDATION_RECOMMENDED',
    'source_revision': receipt['source_revision'], 'source_tree': receipt['source_tree'],
    'test_before_sha256': sha(before_raw), 'test_after_sha256': sha(after_raw),
    'source_manifest_sha256': sha(manifest), 'validation_plan_sha256': inputs[str((P / 'validation-plan.json').relative_to(R))]['sha256'],
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R), 'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()), 'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'review_script_sha256': sha(Path(__file__).read_bytes()), 'checked_input_members': len(inputs),
    'before_after_input_tree_sha256': sha(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode()),
    'before_after_custody_equal': True,
    'findings': [], 'bounded_validation_recommended': True,
    'declared_test_methods': 17, 'old_admission_assertions_preserved': True,
    'scope': 'Test-only deterministic real guest memory.grow cancellation after committed store;not product error remapping or a proven remote root-cause fix.',
    'meaningful_coverage': ['Warm decoded entry removes decode allocation from armed interval;constructor preallocates execution stacks.',
        'Guest const0,const7,store,const1,memory.grow are the5dispatched instructions;prior store and5count reject early cancellation.',
        'FAIL0 disables allocator denial;CANCEL_AT1 cancels the existing same-instance Arc token synchronously at real allocation.',
        'Strict Cancelled/code/no-cache rejects a cache wrapper or noncancellation failure;memory/page/state checks reject committed growth or reservation leak.',
        'Identical terminal error on repeated invoke and clean frames/values/controls/cache pins remain asserted.',
        'Observer ACTIVE/OWNED/CANCEL_AT/CANCEL areTLS;only one test arms this module;other harness threads do not increment CALLS or cancel this token.'],
    'limitations': ['No exact nested cause of remote Cache was printed;do not infer cancellation,exhaustion or a diagnosed product bug.',
        'This5instruction test covers a cooperative bulk-growth checkpoint,not external-thread latency or compute-bound long-loop instruction cancellation. The broader long-execution matrix is not newly qualified by this fixture.',
        'Global allocator wrapper affects this test binary;Debug+Release with default concurrency and lint must actually pass before acceptance.',
        'The55s sum is a cumulative subprocess ceiling;root should enforce remaining budget,stop on failure/timeout,record resolved tool versions/environment/source/output and preserve incomplete stages.',
        'Ordinary remote VM CI after integration/delivery remains required. Local host tests are not native/device/OTA/GA evidence.'],
    'read_only_git_evidence_commands': [
        ['git', 'show', receipt['source_revision'] + ':vm/tests/span_execution.rs'],
        ['git', 'diff', '--', 'vm/tests/span_execution.rs'],
        ['git', 'diff', '--exit-code', '--', 'vm/src', 'vm/tests/common/allocation_observer.rs']],
    'read_only_git_evidence_exits': [0, 0, 0],
    'cargo_compiler_rustfmt_clippy_test_native_UI_capture_device_process_inventory_commands': 0,
    'product_source_dependency_budget_or_canonical_metadata_edits': 0,
    'commit_push': 0, 'remote_nested_cause_diagnosed': False, 'test_pass_claimed': False,
    'cleanup': 'No test/runtime/native child or build artifact created;no cleanup owed.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
for name, value in [('review-result.json', report), ('checked-inputs.json', inputs)]:
    with (D / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'checked_input_members', 'declared_test_methods', 'bounded_validation_recommended', 'elapsed_seconds')}))
