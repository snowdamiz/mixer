#!/usr/bin/env python3
"""Offline byte/source audit. Does not execute compiler, runtime, child or socket."""
import hashlib
import json
import ast
from pathlib import Path
import re
import struct
import sys
from datetime import datetime, timezone

def deny(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.spawn',
                 'socket.__new__', 'socket.connect', 'os.kill', 'os.killpg'}:
        raise RuntimeError('Offline investigation forbids ' + event)

sys.addaudithook(deny)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'verification/github-delivery-source-pair-and-rebar/ci-review'
BASE = PACKET / 'swift-cache-state-fixture'
CURRENT = BASE / 'runs/ci-40766689541-1'
HISTORICAL = BASE / 'runs/host-resource-ci-repair-root-1'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    return json.loads(path.read_bytes())

def bind(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}

def output(name, data):
    (HERE / name).write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')

current = read_json(CURRENT / 'receipt.json')
old = read_json(HISTORICAL / 'receipt.json')
assert current['source_revision'] == '8888d8e2c8431ee311c68e94a1abbb280f84802a'
assert current['source_tree'] == '4afcac3a7354d7685fa9ebc55292b9871197e24e'
command = read_json(CURRENT / 'commands/producer-debug-root-03.json')
assert command['timed_out'] and command['exit'] == -9
assert command['child_returned'] and command['owned_group_gone'] and not command['custody_hold']
assert command['effective_timeout_seconds'] == 60
sources = []
for relative, expected in [
    ('source/regression/independent_tests.rs', '7c9c3006e1e7fd6a927fc7c3ca472c33abe3084f50a1f5aea0d31c6d9d75c411'),
    ('source/library/analyzer.rs', 'ad039daac5de9ea811da70261ae6591dfe6846e23bea1a87fc013755b502af6e'),
]:
    paths = [BASE / 'pack' / relative, CURRENT / 'pack' / relative, HISTORICAL / 'pack' / relative]
    assert all(sha(path.read_bytes()) == expected for path in paths)
    sources.extend(bind(path) for path in paths)

# Independently encode only the context baseline from the bound Fixture::new.
maximum = (1 << 64) - 1
context = bytearray(8192)
values = [int.from_bytes(b'MIXFIX01', 'little'), 1, 8192, 1, 32, 33, 1000, 3,
          2, 3, 1, 100, 1000, 500, 0, 0]
for i, value in enumerate(values):
    struct.pack_into('<Q', context, i * 8, value)
for digest in range(8):
    context[128 + digest * 32:160 + digest * 32] = bytes([17 + digest]) * 32
scalar = [(1,2),(2,8191),(3,0),(3,2),(4,0),(4,4194305),(5,32),(5,64),
          (6,maximum),(7,0),(7,4294967296),(8,0),(8,65),(9,0),(9,65),
          (10,0),(10,2),(11,maximum),(12,99),(13,0),(13,1001),(14,1),(15,1)]
vectors = []
for word, value in scalar:
    data = bytearray(context)
    struct.pack_into('<Q', data, word * 8, value)
    vectors.append((f'context-{word}-{value}', bytes(data)))
for word in range(48, 1024):
    data = bytearray(context)
    struct.pack_into('<Q', data, word * 8, 1)
    vectors.append((f'context-reserved-{word}', bytes(data)))
for length in [0, 1, 8191, 8193]:
    vectors.append((f'context-length-{length}', bytes(context[:length]) + bytes(max(0, length - len(context)))))
assert len(vectors) == 1003 and len({name for name, _ in vectors}) == 1003

retention = read_json(CURRENT / 'retention.json')
remnants = [row for row in retention['files'] if row['path'].startswith('producer-debug-root-03/')]
expected_dir = 'producer-debug-root-03/986-context-reserved-1011/'
assert sorted(row['path'] for row in remnants) == [expected_dir + name for name in ['context','profile','report','stream']]
raw = {}
for row in remnants:
    data = (CURRENT / row['content']).read_bytes()
    assert row['encoding'] == 'identity' and len(data) == row['bytes'] and sha(data) == row['sha256']
    raw[Path(row['path']).name] = data
assert raw['context'] == vectors[986][1]
assert len(raw['profile']) == 2560512 and len(raw['stream']) == 2688 and raw['report'] == b''
vector_inventory = [{'ordinal': i, 'label': label, 'stream_sha256': sha(raw['stream']),
                     'profile_sha256': sha(raw['profile']), 'context_bytes': len(data),
                     'context_sha256': sha(data)} for i, (label, data) in enumerate(vectors)]
output('ordered-context-vector-inventory.json', vector_inventory)

# This is a source/vector equivalence check, never a compiled/runtime pass.
original_source = (BASE/'pack/source/regression/independent_tests.rs').read_text()
candidate_path = HERE/'candidate/source/regression/independent_tests.rs'
candidate_source = candidate_path.read_text()
def method(text):
    return text.split('fn context_schema_scalar_reserved_and_lengths() {',1)[1].split('\n#[test]',1)[0]
old_method, new_method = method(original_source), method(candidate_source)
def extracted_vectors(body):
    scalar_text = re.search(r'for \(word,value\) in (\[.*?\]) \{',body).group(1)
    scalars = ast.literal_eval(scalar_text.replace('M',str(maximum)))
    reserved = re.search(r'for word in (\d+)\.\.(\d+) \{',body)
    lengths = ast.literal_eval(re.search(r'for len in (\[.*?\]) \{',body).group(1).replace('usize',''))
    observed=[]
    for word,value in scalars:
        data=bytearray(context);struct.pack_into('<Q',data,word*8,value)
        observed.append((f'context-{word}-{value}',bytes(data)))
    for word in range(int(reserved.group(1)),int(reserved.group(2))):
        data=bytearray(context);struct.pack_into('<Q',data,word*8,1)
        observed.append((f'context-reserved-{word}',bytes(data)))
    for length in lengths:
        observed.append((f'context-length-{length}',bytes(context[:length])+bytes(max(0,length-len(context)))))
    return observed
assert extracted_vectors(old_method) == vectors == extracted_vectors(new_method)
old_run = original_source.split('fn run(f: &Fixture, framing: bool, label: &str) {',1)[1].split('\n#[test]',1)[0]
assert 'fn run(f: &Fixture, framing: bool, label: &str) {'+old_run in candidate_source
old_assertions = old_run.split('    match &result {',1)[1].split('    drop((stream,profile,context,output));',1)[0]
candidate_assertions = candidate_source.split('fn run_context_opened(',1)[1].split('    match &result {',1)[1].split('    let report_assert=report_start.elapsed();',1)[0]
assert old_assertions == candidate_assertions
assert 'baseline.clone()' not in new_method
assert 'permissions.set_readonly(true);' in new_method
assert new_method.count('assert_shared_context_inputs(&shared,&baseline);') == 2
assert 'File::open(shared.join("stream"))' in candidate_source
assert 'File::open(shared.join("profile"))' in candidate_source
assert 'assert_eq!(file.stream_position().unwrap(),0' in candidate_source
assert new_method.index('assert_eq!(completed,1003') < new_method.rindex('assert_shared_context_inputs') < new_method.index('fs::remove_dir_all(&shared)')
candidate_audit = {
    'schema':1,'status':'offline-source-vector-equivalence-passed-no-compiled-claim',
    'source_sha256':sha(original_source.encode()),'candidate_sha256':sha(candidate_source.encode()),
    'ordered_vectors_compared_byte_for_byte':1003,'original_run_function_unchanged':True,
    'context_assertion_block_identical_sha256':sha(old_assertions.encode()),
    'inputs':{'stream_sha256':sha(raw['stream']),'profile_sha256':sha(raw['profile'])},
    'read_only_and_fresh_handles':'Candidate writes shared inputs once, marks them read-only, uses fresh File::open for each input and asserts all four cursors zero before each call. This is source evidence pending a real compiled test.',
    'success_cleanup':'Final completed=1003 and exact shared content/read-only checks precede shared directory removal.',
    'failure_retention':'Existing runner recursively retains every non-product scratch file; shared paths are not compiler products. No RAII deletion removes shared input files during unwinding.',
    'limitations':['Not compiled','No runtime or speedup claim','Source vector extraction supports test equivalence only; it grants no release or semantic authority'],
}
output('candidate-source-audit.json',candidate_audit)

historical_times = {row['name']: row['elapsed_seconds'] for row in old['commands']
                    if row['name'] in ['host-debug-all','producer-debug-root-01','producer-debug-root-02','producer-debug-root-03']}
current_times = {row['name']: row['elapsed_seconds'] for row in current['commands']
                if row['name'] in historical_times}
source_bindings = {
    'scope': 'Read-only Git object observations from the investigation; no Git mutation.',
    'tool_version_command':'git --version','tool_version_stdout':'git version 2.56.0\n',
    'revisions': ['56ff14c925168284761c5aca4f0bd4129cf3c995', current['source_revision']],
    'command_template': 'git ls-tree REV verification/swift-cache-state-ci .github/workflows/verify.yml',
    'identical_for_both_revisions': {
        '.github/workflows/verify.yml': {'type':'blob','object':'c739fa726fd8f6a67390654eb76262b42b9ed73d'},
        'verification/swift-cache-state-ci': {'type':'tree','object':'ccf670a18d2d28ccb67220c8a1cae414476ef8f5'},
    },
    'additional_read_only_command': 'git diff --name-status 56ff14c925168284761c5aca4f0bd4129cf3c995 8888d8e2c8431ee311c68e94a1abbb280f84802a -- .github/workflows verification/swift-cache-state-ci scripts/ci',
    'additional_command_exit': 0, 'additional_command_stdout': '',
}
output('git-source-bindings.json', source_bindings)
report = {
    'schema': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
    'command': ['python3','-B','verification/cache-fixture-debug-timeout-investigation/audit.py'],
    'python': sys.version, 'platform': sys.platform, 'scope':'offline source/artifact analysis only',
    'source_revision': current['source_revision'], 'source_tree': current['source_tree'],
    'run':40766689541, 'job':123092607744, 'artifact':12851075835,
    'method':'context_schema_scalar_reserved_and_lengths',
    'case_counts': {'scalar':23,'reserved':976,'length':4,'total':1003},
    'retained_active_case': {'ordinal':986,'label':'context-reserved-1011','files':remnants,
                             'completed_prior_cases':986,'cases_after_active':16},
    'progress_reasoning':'Exact single Rust test; NEXT begins zero, increments once at run entry, and run removes its directory only after analyze/report/assertions/handle closure. Existing ordinal 986 with only its four files supports prior cases 0..985 completed. It does not prove speed during the final case or identify the blocking phase.',
    'pre_report_phase_bound':'All input writes and report creation occurred; zero report bytes means no report bytes were retained. Exact remaining instruction/IO phase cannot be recovered.',
    'finite_cost': {'arena_bytes_per_case':8388608,'arena_debug_budgeted_extensions_per_case':1048576,
                    'full_method_arena_extensions':1003*1048576,'full_method_arena_bytes_initialized':1003*8388608,
                    'profile_clone_bytes':1003*2560512,'profile_file_write_bytes':1003*2560512},
    'diagnosis': {'supported':'Finite expensive debug method reached case 986 before a fixed 60-second wall deadline. The deadline failure is consistent with throughput exhaustion; saved evidence does not establish a deterministic unbounded loop.',
                  'unresolved':['CPU scheduling/optimization cost versus filesystem preparation cost','Exact phase within active case','Any OS-level stalled file operation at the final case','Exact prior 56ff method timing/compiler identity; only job success is locally retained'],
                  'not_supported':['Local SDK tree size as proof of remote contention','Treating historical compiler timing as current benchmark','Accepting later producer/optimized scopes']},
    'historical_comparison': {'scope':'c4d04e embedded history only; no current acceptance',
                              'source_revision':old['source_revision'],'pack_tree_identical':old['pack_tree_sha256']==current['pack_tree_sha256'],
                              'current_rustc':current['rustc'],'historical_rustc':old['rustc'],
                              'current_runner_sha256':current['runner']['sha256'],'historical_runner_sha256':old['runner']['sha256'],
                              'current_times_seconds':current_times,'historical_times_seconds':historical_times,
                              'limitation':'Compiler 1.98.1 versus 1.99.0 and runner hashes differ; ratios cannot attribute causal environmental slowdown.'},
    'minimum_harness_proposal': {'product_source_change':False,'all_1003_vectors_and_assertions_preserved':True,
                                'change':'Within this context-only method, store unchanged stream/profile once; clone only context per vector; reopen immutable baseline stream/profile with fresh offset-zero File handles; retain fresh distinct context/report per vector and all existing assertions/closure checks.',
                                'profile_clone_bytes_avoided':1003*2560512,
                                'profile_file_write_bytes_avoided':1002*2560512,
                                'limitation':'All debug arena initialization remains. No runtime speedup or 60-second pass is asserted.'},
    'bounded_next_diagnostic': {'selected_or_run':False,'bound_seconds_per_child':60,'active_bound_seconds':600,
                              'preserve':['Original failed command and sealed packets','Unchanged analyzer allocation/budget/capability/security semantics','Existing group ownership and cleanup checks','Complete case coverage and order'],
                              'instrumentation':['One prepared candidate with unchanged product sources and shared immutable input files','Progress every 64 cases and at completion, with cumulative prepare/open, analyze, report/assert, and cleanup wall durations','Record per-owned-child CPU user/system rusage and faults, with exact compiler hash','Assert baseline input content hashes before and after and emit the complete ordered vector hash inventory'],
                              'decision':'One same-compiler remote diagnostic may distinguish throughput cost and preparation savings. If analysis dominates, do not increase timeout blindly: review finite subcase partition preserving every original vector and total 600-second active bound. A pass requires the complete fixture closure, not this single method.'},
    'executed_runtime_compiler_native_capture_socket_process_probe':False,
    'canonical_or_frozen_files_changed':False,
    'candidate_source_audit':candidate_audit,
    'bindings': sources + [bind(CURRENT/'receipt.json'), bind(CURRENT/'retention.json'),
                           bind(CURRENT/'commands/producer-debug-root-03.json'),
                           bind(CURRENT/'commands/producer-debug-root-03.stdout'),
                           bind(CURRENT/'commands/producer-debug-root-03.stderr'),
                           bind(HISTORICAL/'receipt.json'), bind(ROOT/'.github/workflows/verify.yml'),
                           bind(ROOT/'verification/github-delivery-binary-export-and-ui/ci-jobs-1.stdout')],
}
output('report.json', report)
members = [bind(path) for path in sorted(HERE.rglob('*')) if path.is_file() and path.name != 'seal.json']
output('seal.json', {'schema':1,'scope':'Owned offline investigation and sibling source proposal only',
                     'member_count':len(members),'members':members,
                     'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())})
print(json.dumps({'status':'offline-audit-passed','vectors':len(vectors),'completed_prior_cases':986,
                  'active_case':vectors[986][0],'report_bytes':len(raw['report']),
                  'output':'verification/cache-fixture-debug-timeout-investigation/report.json'}, sort_keys=True))
