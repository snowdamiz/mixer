#!/usr/bin/env python3
"""Proposed sole candidate host run. No local execution or dispatch authority."""
import argparse, collections, difflib, hashlib, json, os, platform, re, shutil, signal, stat, sys, time, uuid
from pathlib import Path
from bounded_commands import Commands, need, regular, no_symlinks, identity, save, member, json_data, sha, exception_details

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PACKET = ROOT / 'verification/swift-pin-bitmap-match-binding-correction'
SEAL_SHA = '0210ab9c252c6f7a5a3eff077e36c2811c79351d916d78b75b2cda88e2bdf85c'
BASELINE = 'af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b'
CANDIDATE = 'e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1'
PROFILE = 'pin-bitmap-lint-regression-v1'
WORKFLOW_PATH = '.github/workflows/swift-pin-bitmap-lint-regression-admission.yml'
TOOLCHAIN = '1.99.0-x86_64-unknown-linux-gnu'
ACTIVE_SECONDS, CLEANUP_SECONDS = 1800, 60
MAX_FILE_BYTES, MAX_SOURCE_BYTES = 16*1024*1024, 64*1024*1024
REQUIRED_HOST_COMPONENTS = ('rustfmt-preview-x86_64-unknown-linux-gnu', 'clippy-preview-x86_64-unknown-linux-gnu')
TOOLS = ('rustc', 'rustfmt', 'cargo', 'cargo-clippy', 'clippy-driver')
OVERLAYS = (
    'src/experimental/cache/borrowed.rs',
    'src/experimental_swift_reactor/bulk_memory_operations_tests.rs',
    'src/experimental_swift_reactor/cache.rs',
    'src/experimental_swift_reactor/cache_tests.rs',
    'src/experimental_swift_reactor/control_operations_tests.rs',
    'src/experimental_swift_reactor/diagnostic_profile_tests.rs',
    'src/experimental_swift_reactor/diagnostic_result_v1_tests.rs',
    'src/experimental_swift_reactor/execution_tests.rs',
    'src/experimental_swift_reactor/lifecycle_tests.rs',
    'src/experimental_swift_reactor/memory_growth_operations_tests.rs',
    'src/experimental_swift_reactor/memory_operations_tests.rs',
    'src/experimental_swift_reactor/value_operation_tests.rs',
    'src/experimental_wasi/accounted_tests.rs',
    'tests/experimental_guest_ui_allocations.rs',
    'tests/experimental_guest_ui_validation.rs',
)
ORACLES = (
    'every_integer_opcode_matches_node', 'structured_control_and_memory_match_node',
    'accepted_mutations_are_also_valid_webassembly_in_node',
    'node_validation_of_original_supported_subset_fixtures',
    'every_float_arithmetic_comparison_rounding_and_bitwise_opcode',
    'conversions_reinterpret_and_saturating_boundaries',
    'float_memory_calls_and_global_ownership_preserve_bits',
    'copy_fill_overlap_bounds_and_zero_length',
    'indirect_types_arguments_nulls_elements_and_instantiation',
)
NODE_SCRIPT = 'console.log(JSON.stringify({execPath:process.execPath,version:process.version,versions:process.versions,platform:process.platform,arch:process.arch}))'


def inputs():
    need(sha(regular(PACKET/'seal.json')) == SEAL_SHA, 'Frozen lint-correction seal changed')
    sealed = json_data((PACKET/'seal.json').read_bytes())
    need(len(sealed['files']) == 24, 'Exact 24 sealed input members')
    for n, row in sealed['files'].items():
        bound(PACKET/member(n), row)
    m = json_data((PACKET/'manifest.json').read_bytes())
    need(len(m['baselineFiles']) == len(m['candidateFiles']) == 136, 'Complete 136-member closures')
    need(set(m['candidateFiles']) == set(m['baselineFiles']) == set(m['materializationPaths']), 'Complete source roster')
    need(closure(m['baselineFiles']) == BASELINE and closure(m['candidateFiles']) == CANDIDATE, 'Source closure digests')
    need(m['overlayPaths'] == list(OVERLAYS), 'Exactly 15 selected overlays')
    need({n for n in m['baselineFiles'] if m['baselineFiles'][n] != m['candidateFiles'][n]} == set(OVERLAYS), 'Overlay difference set')
    data = {}; total = 0
    for n in m['candidateFiles']:
        original = bound(ROOT/'vm'/member(n), m['baselineFiles'][n])
        path = ('verification/swift-pin-bitmap-match-binding-correction/candidate/vm/' if n in OVERLAYS else 'vm/') + n
        need(m['materializationPaths'][n] == path, 'Exact materialization path')
        raw = bound(ROOT/member(path), m['candidateFiles'][n]) if n in OVERLAYS else original
        data[n] = raw; total += len(raw)
        need(total <= MAX_SOURCE_BYTES, 'Aggregate source bound')
    # This reads only lean sealed source/metadata, never the local raw CI paths
    # recorded as historical bindings in actual-bindings.json.
    return m, data


def bound(path, expected):
    regular(path)
    need(type(expected['bytes']) is int and 0 <= expected['bytes'] <= MAX_FILE_BYTES, 'Input file byte bound')
    need(path.stat().st_size == expected['bytes'], 'Input size changed')
    raw = path.read_bytes(); need(file_row(raw) == expected, 'Input digest changed: '+str(path))
    return raw


def binary_row(path):
    regular(path); need(os.access(path, os.X_OK), 'Executable required')
    s = path.stat()
    return {'path': str(path), 'sha256': sha(path), 'bytes': s.st_size, 'device': s.st_dev, 'inode': s.st_ino, 'mode': stat.S_IMODE(s.st_mode)}


def choose_node(temp):
    # Resolve exactly one existing image executable. No execution, install,
    # fallback binary, package manager or second discovery pass occurs here.
    requested = shutil.which('node', path=os.environ.get('PATH', ''))
    need(requested is not None and Path(requested).is_absolute(), 'Existing absolute Node executable required')
    resolved = Path(requested).resolve(strict=True)
    need(not resolved.is_relative_to(ROOT) and not resolved.is_relative_to(temp), 'Node must be outside checkout and all owned runner scratch')
    row = binary_row(resolved); row['requested'] = requested
    row['qualification'] = 'This observed hosted binary only; no external Node release qualification'
    return row


def check_binaries(tools, node, paths=None):
    for expected in [*tools.values(), node]:
        actual = binary_row(Path(expected['path']))
        need(all(actual[k] == expected[k] for k in actual), 'Bound tool identity changed')
    if paths is not None:
        identity(paths['nodebin'])
        link = paths['nodebin']/'node'
        need(link.is_symlink() and os.readlink(link) == node['path'] and link.resolve(strict=True) == Path(node['path']), 'Private Node link identity changed')
        need(set(p.name for p in paths['nodebin'].iterdir()) == {'node'}, 'Private Node directory changed')
    return {'verified': True, 'count': 6, 'nodeSHA256': node['sha256']}


def arm_environment(paths, toolbin, node):
    return {'HOME': str(paths['home']), 'CARGO_HOME': str(paths['cargo']), 'CARGO_TARGET_DIR': str(paths['target']),
            'CARGO_NET_OFFLINE': 'true', 'CARGO_INCREMENTAL': '0', 'RUSTUP_TOOLCHAIN': TOOLCHAIN,
            'RUSTC': str(toolbin/'rustc'), 'CLIPPY_CONF_DIR': str(paths['home']),
            'MIXER_NODE': node['path'], 'PATH': str(paths['nodebin'])+':'+str(toolbin)+':/usr/bin:/bin',
            'LANG': 'C', 'LC_ALL': 'C'}


def command_plan(paths, toolbin, config, node):
    cargo = [str(toolbin/'cargo')]
    manifest = str(paths['source']/'Cargo.toml')
    tests = ['test', '--manifest-path', manifest, '--locked', '--offline', '--all-features']
    tail = ['--', '--include-ignored', '--test-threads=1', '--show-output']
    return [
        {'name': 'compiler-identity', 'argv': [str(toolbin/'rustc'), '-vV'], 'seconds': 30, 'accepted_exits': (0,)},
        {'name': 'node-identity', 'argv': [node['path'], '-e', NODE_SCRIPT], 'seconds': 30, 'accepted_exits': (0,)},
        {'name': 'format-candidate', 'argv': [str(toolbin/'rustfmt'), '--edition', '2021', '--emit', 'files', '--config-path', str(config), *[str(paths['source']/n) for n in OVERLAYS]], 'seconds': 60, 'accepted_exits': (0,)},
        {'name': 'clippy-candidate', 'argv': cargo+['clippy', '--manifest-path', manifest, '--locked', '--offline', '--all-features', '--all-targets', '--message-format=json', '--', '-D', 'warnings'], 'seconds': 300, 'accepted_exits': (0,101)},
        {'name': 'debug-regression', 'argv': cargo+tests+tail, 'seconds': 600, 'accepted_exits': (0,)},
        {'name': 'release-regression', 'argv': cargo+tests+['--release']+tail, 'seconds': 600, 'accepted_exits': (0,)},
    ]


def test_evidence(text):
    # libtest writes ordinary terminals on one line, but direct stdout writes
    # can separate a serialized test header from its standalone terminal. Bind
    # both forms to running groups; captured --show-output text is never a test.
    need(type(text) is str and len(text.encode('utf-8')) <= 8*1024*1024, 'Test evidence text bound')
    need(not re.search(r'[\x00-\x08\x0b-\x1f\x7f]', text), 'Control characters in test evidence')
    summary_pattern = r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;(?: finished in \d+(?:\.\d+)?s)?'
    split_names = {
        'shared_control_branch_targets_and_frame_boundary',
        'shared_control_cancellation_and_limits',
        'shared_control_close_partial_effects',
        'shared_control_public_parity_trace',
        'shared_control_warm_dispatch_allocation_free',
        'shared_control_work_and_fuel_prefixes',
    }
    allocation = r'\(\d+, \d+, \d+\)'
    usage = r'ExecutionUsage \{ [^{}\n]* \}'
    cache = r'CacheUsage \{ [^{}\n]* \}'
    config = r'Limits \{ [^{}\n]* \}/ExecutionBudget \{ [^{}\n]* \}/CacheBudget \{ [^{}\n]* \}/(?:true|false)/\d+/\d+'
    trace_pattern = r'control_trace [a-z][a-z0-9-]* config=' + config + r' (?:constructor=[^\n]+ allocations=' + allocation + r'|initial=' + usage + r' first=[^\n]+ final=' + usage + r' cache=' + cache + r' allocations=' + allocation + '/' + allocation + ')'
    warm_pattern = r'control_warm [a-z][a-z0-9-]* usage=' + usage + r' cache=' + cache + r' allocations=' + allocation
    ceiling_pattern = r'control_validation_ceiling (operand|control) failure=Failure \{ kind: ResourceExhausted, code: "profile_\1_limit", [^\n]+ \}'
    identifier = r'[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*'
    doctest = r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.rs - ' + identifier + r' \(line [1-9]\d*\)(?: - compile fail)?'
    rows, terminals, names = [], [], set()
    group = None
    pending = None
    traces = 0
    for line in text.split('\n'):
        stripped = line.lstrip()
        if stripped.startswith('running '):
            match = re.fullmatch(r'running (0|[1-9]\d*) (test|tests)', line)
            need(match is not None and group is None and pending is None, 'Malformed or overlapping running group')
            count = int(match[1])
            need(count <= 699 and match[2] == ('test' if count == 1 else 'tests') and len(rows) < 700, 'Running group count or grammar')
            group = {'running': count, 'terminals': 0, 'output': False}
        elif stripped.startswith('test result'):
            match = re.fullmatch(summary_pattern, line)
            need(match is not None and group is not None and pending is None, 'Malformed, orphan or unfinished test summary')
            need(match[1] == 'ok', 'Non-ok test summary')
            row = dict(zip(('passed', 'failed', 'ignored', 'measured', 'filtered'), map(int, match.groups()[1:])))
            need(all(row[k] == 0 for k in ('failed', 'ignored', 'measured', 'filtered')), 'No failed, ignored, measured or filtered tests')
            need(group['running'] == group['terminals'] == row['passed'], 'Running, terminal and summary counts disagree')
            rows.append(row)
            group = None
        elif stripped.startswith('test ') and (group is None or not group['output'] or ' ... ' in line):
            need(group is not None and not group['output'] and pending is None, 'Orphan, captured or overlapping test header')
            need(line.startswith('test ') and line.count(' ... ') == 1, 'Malformed test header')
            name, status = line[5:].split(' ... ', 1)
            need(re.fullmatch(identifier, name) or re.fullmatch(doctest, name), 'Malformed test identity')
            need(name not in names, 'Duplicate test identity')
            need(group['terminals'] < group['running'] and len(terminals) < 699, 'Too many test headers')
            names.add(name)
            if status == 'control_observer serialized lane':
                need(name in split_names, 'Unrecognized split test identity')
                pending, traces = name, 0
            else:
                need(status == 'ok', 'Non-ok or malformed terminal test status')
                terminals.append((name, status))
                group['terminals'] += 1
        elif pending is not None:
            if line == 'ok':
                need(traces > 0, 'Split terminal requires serialized trace output')
                terminals.append((pending, 'ok'))
                group['terminals'] += 1
                pending = None
            else:
                trace = re.fullmatch(trace_pattern, line)
                warm = pending == 'shared_control_warm_dispatch_allocation_free' and re.fullmatch(warm_pattern, line)
                ceiling = pending == 'shared_control_cancellation_and_limits' and re.fullmatch(ceiling_pattern, line)
                need(trace is not None or warm or ceiling, 'Malformed split trace or terminal transition')
                traces += int(trace is not None)
        elif stripped.startswith(('control_trace', 'control_warm', 'control_observer', 'control_validation_ceiling')):
            need(False, 'Orphan serialized control output')
        elif stripped == 'ok' or stripped.startswith(('FAILED', 'ignored')):
            need(False, 'Orphan or non-ok standalone test result')
        elif stripped == 'successes:':
            need(line == stripped and group is not None and group['terminals'] == group['running'], 'Premature or orphan captured output')
            group['output'] = True
        else:
            need(not line or (group is not None and group['output']), 'Unexpected output outside captured test output')
    need(group is None and pending is None and rows, 'Missing summary or unfinished running group')
    need(sum(r['passed'] for r in rows) == 699, 'Exactly 699 passed tests required')
    need(len(terminals) == 699, 'Exactly 699 terminal ok lines required')
    oracle_names = collections.Counter(name for name, _ in terminals)
    need(all(oracle_names[n] == 1 for n in ORACLES), 'All nine exact Node oracles must pass once')
    return {'summaries': rows, 'terminals': terminals, 'passed': 699, 'ignored': 0, 'nodeOracles': list(ORACLES),
            'scope': 'Full all-feature host Debug or Release, including explicit development Node oracles; no production Node interpreter'}


def checked_command(c, spec, paths, toolbin, tools, node, expected, out, raw_before, config):
    source = paths['source']; primary = None; row = None; result = None
    try:
        exact_source(source, expected)
        check_binaries(tools, node, paths)
        need(config.read_text() == 'edition = "2021"\n', 'Formatter config changed')
        cargo_configs_absent(source); cargo_configs_absent(paths['home'])
        text, err, row = c.run(spec['name'], spec['argv'], source, arm_environment(paths, toolbin, node), seconds=spec['seconds'], accepted_exits=spec['accepted_exits'])
        if spec['name'] == 'compiler-identity':
            need(re.search(r'^release: 1\.99\.0$', text, re.M) and re.search(r'^host: x86_64-unknown-linux-gnu$', text, re.M), 'Exact Rust release and host required')
            result = {'compilerIdentity': text}
        elif spec['name'] == 'node-identity':
            result = json_data(text)
            need(result['execPath'] == node['path'] and result['platform'] == 'linux' and result['arch'] == 'x64' and re.fullmatch(r'v\d+\.\d+\.\d+', result['version']), 'Node identity child mismatch')
            need(result['versions']['node'] == result['version'][1:], 'Node version identities disagree')
            save(out/'node-identity.json', {**node, 'runtime': result})
        elif spec['name'] == 'clippy-candidate':
            result = lint_evidence(text, row['exit'], source)
            save(out/'clippy-candidate.json', result)
            need(result['lintPassed'], 'Clippy findings: regression not admitted')
        elif spec['name'].endswith('-regression'):
            result = test_evidence(text); save(out/(spec['name']+'.json'), result)
    except BaseException as e:
        primary = e
    finally:
        if row is None and c.receipt['commands'] and c.receipt['commands'][-1]['name'] == spec['name']:
            row = c.receipt['commands'][-1]
        if row is None:
            row = {'name': spec['name']}; c.receipt.setdefault('unregisteredPostflights', []).append(row)
        # Keep source and tool postflights independent: a source failure cannot
        # prevent recording the binary check, or erase the primary exception.
        try:
            if spec['name'] == 'format-candidate':
                updated, evidence = format_evidence(out, 'candidate', source, expected, raw_before)
                expected.clear(); expected.update(updated); row['formatEvidence'] = evidence
                save(out/'formatted-source-manifest.json', {'files': updated, 'treeSHA256': closure(updated)})
            row['sourceAfter'] = exact_source(source, expected)
            row['sourcePostflight'] = {'attempted': True, 'verified': True, 'members': 136}
        except BaseException as e:
            row['sourcePostflight'] = {'attempted': True, 'verified': False, 'error': exception_details(e)}; primary = primary or e
        try:
            row['binaryPostflight'] = check_binaries(tools, node, paths)
        except BaseException as e:
            row['binaryPostflight'] = {'verified': False, 'error': exception_details(e)}; primary = primary or e
        try:
            c.save()
        except BaseException as e:
            row['postflightReceiptError'] = exception_details(e); primary = primary or e
    if primary is not None:
        raise primary
    return result


def hosted():
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted', 'GitHub hosted only')
    need(os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and os.environ.get('GITHUB_RUN_ATTEMPT') == '1', 'Manual first attempt only')
    need(os.environ.get('GITHUB_REPOSITORY') == 'snowdamiz/mixer' and re.fullmatch('[0-9a-f]{40}', os.environ.get('GITHUB_SHA','')), 'Bound source revision')
    need(os.environ.get('MIXER_PIN_BITMAP_LINT_SELECTION') == PROFILE, 'Exact profile selection')
    need(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'Linux x86_64 required')
    temp = Path(os.environ['RUNNER_TEMP']); need(temp.is_absolute() and '..' not in temp.parts, 'Canonical runner temp'); identity(temp)
    need(not temp.is_relative_to(ROOT) and not ROOT.is_relative_to(temp), 'Separate checkout and temp')
    rustup = Path(os.environ['RUSTUP_HOME']); need(rustup.is_absolute() and '..' not in rustup.parts, 'Canonical Rust toolchain root'); identity(rustup)
    toolbin = rustup/'toolchains'/TOOLCHAIN/'bin'; identity(toolbin)
    for n in TOOLS: regular(toolbin/n)
    return temp, toolbin


def execute():
    temp, toolbin = hosted(); manifest, data = inputs(); node = choose_node(temp)
    tools = {n: binary_row(toolbin/n) for n in TOOLS}
    out = temp/(PROFILE+'-evidence'); no_symlinks(out); need(not out.exists(), 'Fresh evidence only'); out.mkdir()
    receipt = {'schema': 1, 'status': 'running', 'sourceRevision': os.environ['GITHUB_SHA'], 'runID': os.environ.get('GITHUB_RUN_ID'), 'runAttempt': 1,
               'profile': PROFILE, 'baselineTreeSHA256': BASELINE, 'candidateTreeSHA256': CANDIDATE, 'pythonVersion': sys.version,
               'activeSeconds': ACTIVE_SECONDS, 'cleanupSeconds': CLEANUP_SECONDS, 'maxChildren': 6, 'perStreamOutputCapBytes': 8*1024*1024, 'aggregateOutputCapBytes': 32*1024*1024,
               'commands': [], 'errors': [], 'automaticRetry': False, 'GAQualified': False, 'canonicalInstallationSelected': False,
               'toolchainFiles': tools, 'node': node, 'installerCustodyEvidence': False, 'explicitPipeEOFSinkCloseFlags': False,
               'NodeInternalPipeCaps': False, 'individualNodeGrandchildReapEvidence': False, 'descendantScope': 'same-group trusted source children only; no escaped group or whole-provider disposal proof'}
    marker = {'purpose': PROFILE, 'token': uuid.uuid4().hex}; save(out/'ownership.json', marker); out_id = identity(out)
    save(out/'source-manifest.json', manifest)
    for n in ('admit.py', 'bounded_commands.py'):
        shutil.copyfile(HERE/n, out/('executed-'+n))
    receipt['harnessFiles'] = {n: sha(HERE/n) for n in ('admit.py', 'bounded_commands.py')}
    receipt['components'] = component_evidence(toolbin.parent/'lib/rustlib/components')
    save(out/'receipt.json', receipt)
    c = Commands(out, receipt, time.monotonic()+ACTIVE_SECONDS)
    scratch = out/'scratch'; owned = None; failure = None
    handlers = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM)}
    def alarm(signum, frame): raise TimeoutError('Finite active or cleanup allowance expired')
    def interrupt(signum, frame): raise KeyboardInterrupt('Signal '+str(signum))
    signal.signal(signal.SIGALRM, alarm); signal.signal(signal.SIGINT, interrupt); signal.signal(signal.SIGTERM, interrupt); signal.setitimer(signal.ITIMER_REAL, ACTIVE_SECONDS)
    try:
        no_symlinks(scratch); need(not scratch.exists(), 'Fresh scratch only'); scratch.mkdir(); owned = identity(scratch); c.bind_scratch(scratch)
        paths = {n: scratch/n for n in ('source', 'target', 'cargo', 'home', 'nodebin')}
        for p in paths.values(): p.mkdir()
        (paths['nodebin']/'node').symlink_to(node['path'])
        for n, raw in data.items():
            p = paths['source']/member(n); p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as f: f.write(raw)
        expected = dict(manifest['candidateFiles']); exact_source(paths['source'], expected)
        raw_before = {n: data[n] for n in OVERLAYS}
        config = scratch/'rustfmt.toml'; config.write_text('edition = "2021"\n')
        plan = command_plan(paths, toolbin, config, node); save(out/'command-plan.json', plan)
        for spec in plan:
            result = checked_command(c, spec, paths, toolbin, tools, node, expected, out, raw_before, config)
            if spec['name'] == 'compiler-identity': receipt.update(result)
        need(len(receipt['commands']) == 6, 'Exactly six managed children')
        receipt['formattedSourceClosure'] = closure(expected)
        receipt['status'] = 'host-regression-completed'; receipt['DebugPassed'] = receipt['ReleasePassed'] = 699; receipt['ignored'] = 0
    except BaseException as e:
        failure = e; receipt['status'] = 'failed'; receipt['errors'].append(exception_details(e))
    finally:
        signal.setitimer(signal.ITIMER_REAL, CLEANUP_SECONDS)
        try:
            need(c.active is None and all(r.get('child_returned') and r.get('owned_group_gone') for r in receipt['commands'] if 'pid' in r), 'Unresolved custody: preserve scratch')
            need(identity(out) == out_id and json_data(regular(out/'ownership.json').read_bytes()) == marker, 'Evidence ownership changed')
            if owned is not None:
                need(identity(scratch) == owned, 'Owned scratch identity changed'); shutil.rmtree(scratch); need(not scratch.exists(), 'Scratch cleanup incomplete')
            receipt['cleanup'] = {'ownedScratchRemoved': True, 'childReapAndGroupAbsenceVerified': True, 'processInventory': False, 'otherProjectsTouched': False}
        except BaseException as e:
            receipt['cleanup'] = {'ownedScratchRemoved': False, 'custodyHold': True}; receipt['errors'].append(exception_details(e)); receipt['status'] = 'failed-custody-or-cleanup'; failure = failure or e
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            for s, h in handlers.items(): signal.signal(s, h)
            receipt['finishedUTC'] = time.time(); save(out/'receipt.json', receipt)
    if failure is not None: raise failure
    return receipt


# Generic source/evidence helpers copied from the reviewed prior admission are
# inserted below by the source-only preparation script, before main executes.


def digest(raw):return hashlib.sha256(raw).hexdigest()

def closure(rows):return digest(''.join(n+'\0'+rows[n]['sha256']+'\n'for n in sorted(rows)).encode())

def file_row(raw):return {'bytes':len(raw),'sha256':digest(raw)}

def inventory(source):
 rows={};total=0
 for directory,dirs,files in os.walk(source,followlinks=False):
  for n in dirs:no_symlinks(Path(directory)/n)
  for n in files:
   p=regular(Path(directory)/n);need(p.stat().st_size<=MAX_FILE_BYTES,'Source member byte bound')
   raw=p.read_bytes();total+=len(raw);need(total<=MAX_SOURCE_BYTES,'Source aggregate bound')
   rows[p.relative_to(source).as_posix()]=file_row(raw)
 return rows

def exact_source(source,expected):
 rows=inventory(source);need(rows==expected,'Complete source postflight mismatch');return closure(rows)

def format_roster(source,expected):
 # Traverse only the expected directory skeleton. Unexpected directories and
 # every symlink are recorded as metadata, never followed or read as source.
 directories={'.'}
 for name in expected:
  directories.update(str(p) for p in member(name).parents if str(p)!='.')
 regular_files=set();unexpected=[];unsafe=[];errors=[]
 def visit(directory,relative):
  try:
   no_symlinks(directory)
   with os.scandir(directory)as entries:
    for entry in entries:
     name=entry.name if relative=='.'else relative+'/'+entry.name
     if entry.is_symlink():
      if name in expected or name in directories:unsafe.append(name)
      else:unexpected.append(name)
     elif name in directories:
      if entry.is_dir(follow_symlinks=False):visit(Path(entry.path),name)
      else:unsafe.append(name)
     elif name in expected:
      if entry.is_file(follow_symlinks=False):regular_files.add(name)
      else:unsafe.append(name)
     else:unexpected.append(name)
  except OSError as e:errors.append({'path':relative,**exception_details(e)})
  except RuntimeError as e:errors.append({'path':relative,**exception_details(e)})
 visit(source,'.')
 return {'regularFiles':sorted(regular_files),'missingPaths':sorted(set(expected)-regular_files),
         'unexpectedPaths':sorted(unexpected),'unsafePaths':sorted(unsafe),'errors':errors}

def format_evidence(out,arm,source,before,raw_before):
 dest=out/'format'/arm;dest.mkdir(parents=True,exist_ok=True);diff=[]
 result={'beforeTreeSHA256':closure(before),'afterTreeSHA256':None,'changedPaths':[],
         'outsideOverlayChanges':[],'files':{},'verified':False}
 # The trusted original before bytes survive even if the source root, roster,
 # or an expected after file is now absent, linked, oversized or unreadable.
 for n in OVERLAYS:
  p=dest/'before'/member(n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw_before[n])
  result['files'][n]={'before':before[n],'after':None,'afterAvailable':False}
 roster=format_roster(source,before);result['roster']=roster
 after={};raw_after={};read_errors=[];total=0
 for n in roster['regularFiles']:
  try:
   p=regular(source/member(n));size=p.stat().st_size
   need(size<=MAX_FILE_BYTES,'Source member byte bound')
   need(total+size<=MAX_SOURCE_BYTES,'Source aggregate bound')
   raw=p.read_bytes();need(len(raw)==size,'Source member size changed while reading')
   total+=len(raw);after[n]=file_row(raw)
   if n in OVERLAYS:raw_after[n]=raw
  except (OSError,RuntimeError)as e:read_errors.append({'path':n,**exception_details(e)})
 result['expectedReadErrors']=read_errors
 result['changedPaths']=sorted(n for n in after if after[n]!=before[n])
 result['outsideOverlayChanges']=sorted(set(result['changedPaths'])-set(OVERLAYS))
 roster_ok=not any(roster[k]for k in ('missingPaths','unexpectedPaths','unsafePaths','errors'))
 complete=roster_ok and not read_errors and set(after)==set(before)
 result['availableExpectedTreeSHA256']=closure(after);result['availableExpectedMembers']=len(after)
 if complete:result['afterTreeSHA256']=closure(after)
 decoding_errors=[]
 for n,raw in raw_after.items():
  p=dest/'after'/member(n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  result['files'][n].update(after=after[n],afterAvailable=True)
  try:after_text=raw.decode()
  except UnicodeDecodeError as e:
   decoding_errors.append({'path':n,**exception_details(e)});after_text=raw.decode(errors='replace')
  diff.extend(difflib.unified_diff(raw_before[n].decode().splitlines(keepends=True),after_text.splitlines(keepends=True),fromfile='before/'+n,tofile='after/'+n))
 (dest/'format.diff').write_text(''.join(diff));result['diffSHA256']=sha(dest/'format.diff')
 result['diffScope']='Available expected overlay files only; exact bytes retained separately; replacement decoding used for invalid UTF-8'
 result['diffDecodingErrors']=decoding_errors
 result['verified']=complete and not result['outsideOverlayChanges'] and not decoding_errors;save(dest/'receipt.json',result)
 need(roster_ok,'Formatter source roster changed; retained explicit roster failure')
 need(complete,'Formatter expected source unavailable; retained available expected files')
 need(not decoding_errors,'Formatter after source is not UTF-8; retained exact bytes and replacement-decoded diff')
 need(result['verified'],'Formatter changed outside the fifteen overlays')
 return after,result


def cargo_configs_absent(source):
 for directory in (source,*source.parents):
  for n in ('config','config.toml'):need(not(directory/'.cargo'/n).exists(),'Inherited Cargo configuration forbidden')
  for n in ('clippy.toml','.clippy.toml'):need(not(directory/n).exists(),'Inherited Clippy configuration forbidden')

def lint_evidence(text,exit_code,source):
 messages=[];finished=[];reasons=collections.Counter()
 for line in text.splitlines():
  if not line.strip():continue
  value=json_data(line);need(isinstance(value,dict)and isinstance(value.get('reason'),str),'Malformed Cargo JSON record')
  reasons[value['reason']]+=1
  if value['reason']=='build-finished':need(type(value.get('success'))is bool,'Malformed build completion');finished.append(value['success'])
  if value['reason']=='compiler-message':
   msg=value['message'];need(isinstance(msg,dict)and isinstance(msg.get('message'),str)and isinstance(msg.get('level'),str),'Malformed compiler diagnostic')
   messages.append(msg)
 need(len(finished)==1 and finished[0]==(exit_code==0),'Cargo completion/exit mismatch')
 if exit_code==101:need(any(x['level']=='error'for x in messages),'Nonzero Cargo result has no error diagnostic')
 return {'exit':exit_code,'lintPassed':exit_code==0,'buildFinished':finished[0],'recordReasons':dict(reasons),
         'diagnostics':messages,'sourceRoot':str(source),'scope':'compile/lint only; no Rust tests or product execution'}

def component_evidence(component):
 raw=regular(component).read_bytes();text=raw.decode()
 need(set(REQUIRED_HOST_COMPONENTS)<=set(text.splitlines()),'Required pinned host components absent')
 return {'sha256':digest(raw),'text':text,'requiredHostComponents':list(REQUIRED_HOST_COMPONENTS),
         'sha256Scope':'raw manifest observation; ordering is not a reproducibility identity'}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=('check', 'run')); args = parser.parse_args()
    if args.mode == 'check':
        m, data = inputs(); print(json.dumps({'sourceMembers': len(data), 'candidateTreeSHA256': CANDIDATE, 'overlays': len(OVERLAYS), 'plannedChildren': 6, 'runtimeRuns': 0})); return
    print(json.dumps(execute()))


if __name__ == '__main__': main()
