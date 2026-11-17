"""R5098: one instrumented pass through the pinned distribution-tree owner."""
import ast
import collections
import copy
import cProfile
import hashlib
import json
import os
import pathlib
import platform
import pstats
import resource
import signal
import stat
import sys
import time
import types

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[2]
OWNER = None
PIN = '2c61ce4c118d3af3978f7ac047c7ac8b7ba4f226283484038baec47363766cd5'
TOOLCHAIN = None
REFERENCE = '0d79dcd75ec7e2e8467f6572f049f25adde933d6d1a35b64a222079f61752051'
COUNTERS = ('read_bytes', 'read_calls', 'file_open_calls', 'files_completed',
            'directories', 'entries_completed', 'stat_calls', 'fstat_calls',
            'cache_lookups', 'cache_hits')


def profile_save(name, data):
    with (BASE / name).open('x') as output:
        json.dump(data, output, indent=2, sort_keys=True)
        output.write('\n')


def usage():
    value = resource.getrusage(resource.RUSAGE_SELF)
    return {key: getattr(value, key) for key in (
        'ru_utime', 'ru_stime', 'ru_maxrss', 'ru_minflt', 'ru_majflt',
        'ru_inblock', 'ru_oublock', 'ru_nvcsw', 'ru_nivcsw')}


def environment():
    return {'uname': list(os.uname()), 'mac_ver': platform.mac_ver(),
            'python': sys.version, 'executable': sys.executable,
            'cpu_count': os.cpu_count(), 'load_average': os.getloadavg(),
            'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


TIMES = collections.defaultdict(lambda: {'calls': 0, 'wall_ns': 0, 'cpu_ns': 0})


def observe(label, function, *args, **kwargs):
    start_wall = time.monotonic_ns()
    start_cpu = time.process_time_ns()
    try:
        return function(*args, **kwargs)
    finally:
        cpu = time.process_time_ns() - start_cpu
        wall = time.monotonic_ns() - start_wall
        row = TIMES[label]
        row['calls'] += 1
        row['wall_ns'] += wall
        row['cpu_ns'] += cpu


def observed_walk(*args, **kwargs):
    iterator = os.walk(*args, **kwargs)
    while True:
        try:
            row = observe('tree.walk_next', next, iterator)
        except StopIteration:
            return
        yield row


class Instrument(ast.NodeTransformer):
    def __init__(self):
        self.scope = ''

    def visit_FunctionDef(self, node):
        old = self.scope
        self.scope = node.name
        self.generic_visit(node)
        self.scope = old
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if not isinstance(node.func, ast.Attribute):
            return node
        owner = ast.unparse(node.func.value)
        name = node.func.attr
        if owner == 'os' and name == 'walk':
            return ast.copy_location(ast.Call(ast.Name('observed_walk', ast.Load()), node.args, node.keywords), node)
        selected = ((owner == 'stream' and name == 'read') or
                    (owner == 'h' and name == 'update') or
                    (owner == 'os' and name in ('open', 'fstat', 'close', 'readlink')) or
                    (owner in ('path', 'item') and name in ('stat', 'is_file', 'is_dir', 'is_symlink', 'resolve')))
        if selected:
            label = self.scope + ':' + owner + '.' + name
            return ast.copy_location(ast.Call(ast.Name('observe', ast.Load()),
                [ast.Constant(label), node.func, *node.args], node.keywords), node)
        return node


class InventoryCache(dict):
    def __init__(self):
        super().__init__()
        self.declared_file_bytes = 0
        self.declared_unique_bytes = 0
        self.file_paths = 0

    def __setitem__(self, key, value):
        size = value[0][4]
        self.file_paths += 1
        self.declared_file_bytes += size
        if key not in self:
            self.declared_unique_bytes += size
        super().__setitem__(key, value)


def profile_once(owner, toolchain, output, reference=REFERENCE):
    global BASE, OWNER, TOOLCHAIN, REFERENCE
    BASE, OWNER, TOOLCHAIN, REFERENCE = pathlib.Path(output), pathlib.Path(owner), pathlib.Path(toolchain), reference
    TIMES.clear()
    source = OWNER.read_bytes()
    require(len(source) == 56337 and hashlib.sha256(source).hexdigest() == PIN, 'Pinned resource changed; Root rebase required')
    (BASE / 'android-build.py').write_bytes(source)
    parsed = ast.parse(source)
    nodes = [n for n in parsed.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))
             and n.name in ('InspectionDigests', 'tree')]
    require(len(nodes) == 2, 'Selected owner changed')
    original_ast = ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False)
    instrumented = ast.fix_missing_locations(Instrument().visit(ast.Module(body=nodes, type_ignores=[])))
    class RemoveTiming(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id == 'observe':
                return ast.Call(node.args[1], node.args[2:], node.keywords)
            if isinstance(node.func, ast.Name) and node.func.id == 'observed_walk':
                return ast.Call(ast.Attribute(ast.Name('os', ast.Load()), 'walk', ast.Load()), node.args, node.keywords)
            return node
    restored = RemoveTiming().visit(copy.deepcopy(instrumented))
    require(ast.dump(restored, include_attributes=False) == original_ast, 'Selected AST changed')
    (BASE / 'instrumented-owner.py').write_text(ast.unparse(instrumented) + '\n')
    namespace = {'hashlib': hashlib, 'os': os, 'pathlib': pathlib, 'stat': stat,
                 'observe': observe, 'observed_walk': observed_walk}
    exec(compile(instrumented, str(OWNER), 'exec'), namespace)
    cache = InventoryCache()
    digests = namespace['InspectionDigests']()
    digests._files = cache
    progress = types.SimpleNamespace(counts=dict.fromkeys(COUNTERS, 0), operation='start')
    digests._progress = progress
    root_identity = tuple(TOOLCHAIN.stat())
    before_environment = environment()
    profile_save('decision.json', {
        'decision': 'Locate actual tree cost in read, hashing CPU, metadata/walk, or unresolved off-CPU time. Never infer hosted cause or a speedup from this single local profiled pass.',
        'algorithm': 'Original sorted os.walk tree and InspectionDigests; transparent call timing only; no digest, size, identity, alias, FIFO or symlink guard changes.',
        'source_path': str(OWNER), 'source_sha256': PIN, 'source_bytes': len(source),
        'original_selected_ast_sha256': hashlib.sha256(original_ast.encode()).hexdigest(),
        'removing_timing_restores_exact_original_ast': True,
        'distribution': str(TOOLCHAIN), 'reference_digest': REFERENCE,
        'reference': 'verification/receipts/fieldlog-current-android-build-r5054.json:toolchain.distributions.swift_toolchain',
        'cache': 'one new in-memory cache, initially empty; no product or OS cache reset',
        'payload_limit_seconds': 180, 'run_count': 1,
        'profile': 'cProfile wall-clock + transparent wall/process-CPU call timings + SIGALRM Python stack samples at 250 ms, max 720',
        'noise_floor': 'unmeasured; no repeats or comparison; concurrent ready lanes may run',
        'metadata_paths_pinned': [], 'environment': before_environment,
        'root_identity': root_identity,
    })
    samples = []
    sampled_functions = collections.Counter()
    def sample(signum, frame):
        if len(samples) >= 720:
            return
        frames = []
        current = frame
        for _ in range(8):
            if current is None:
                break
            frames.append({'file': current.f_code.co_filename, 'function': current.f_code.co_name, 'line': current.f_lineno})
            current = current.f_back
        sampled_functions[str(progress.operation)] += 1
        samples.append({'wall_ns': time.monotonic_ns() - wall_start,
            'cpu_ns': time.process_time_ns() - cpu_start, 'operation': progress.operation,
            'read_bytes': progress.counts['read_bytes'], 'load_average': os.getloadavg(),
            'usage': usage(), 'stack': frames})
    sampler = AlarmSampler(sample)
    require(sys.getprofile() is None, 'Foreign profiler')
    profiler = cProfile.Profile()
    before_usage = usage()
    wall_start = time.monotonic_ns()
    cpu_start = time.process_time_ns()
    sampler.__enter__()
    result = None
    failure = None
    primary_error = None
    try:
        profiler.enable()
        result = namespace['tree'](TOOLCHAIN, digests)
    except BaseException as error:
        primary_error = error
        failure = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        profiler.disable()
        sampler.__exit__(None, None, None)
        try:
            cpu_ns = time.process_time_ns() - cpu_start
            wall_ns = time.monotonic_ns() - wall_start
            after_usage = usage()
            after_environment = environment()
            profiler.dump_stats(str(BASE / 'profile.pstats'))
            stats = pstats.Stats(profiler)
            functions = [{'file': key[0], 'line': key[1], 'function': key[2],
                'primitive_calls': value[0], 'calls': value[1], 'self_wall_s': value[2],
                'cumulative_wall_s': value[3]} for key, value in stats.stats.items()]
            functions.sort(key=lambda row: row['cumulative_wall_s'], reverse=True)
            profile_save('profile-functions.json', functions)
            profile_save('samples.json', samples)
            metrics = {
                'status': 'completed' if failure is None else 'failed', 'failure': failure,
                'run_count': 1, 'digest': result, 'reference_digest': REFERENCE,
                'digest_matches_existing_reference': result == REFERENCE,
                'wall_ns': wall_ns, 'process_cpu_ns': cpu_ns,
                'resource_before': before_usage, 'resource_after': after_usage,
                'resource_delta': {key: after_usage[key] - before_usage[key] for key in before_usage},
                'source_counters': progress.counts,
                'inventory': {'file_paths': cache.file_paths, 'unique_inodes': len(cache),
                    'declared_file_bytes': cache.declared_file_bytes,
                    'declared_unique_file_bytes': cache.declared_unique_bytes,
                    'symlink_readlinks': TIMES['tree:os.readlink']['calls']},
                'call_timings': dict(TIMES), 'samples': len(samples),
                'sampled_operation_labels': sampled_functions,
                'environment_before': before_environment, 'environment_after': after_environment,
                'source_sha256_at_payload_end': hashlib.sha256(OWNER.read_bytes()).hexdigest(),
                'distribution_root_identity_unchanged': tuple(TOOLCHAIN.stat()) == root_identity,
                'timing_limitations': ['Instrumented single pass, unmeasured OS cache state and host load; no speedup or repeatability claim.',
                    'Python-returned bytes and logical stream reads are not physical disk traffic/syscall counts.',
                    'Python signal frames are delayed to interpreter handling and are not kernel stacks.',
                    'Wall minus process CPU does not distinguish filesystem wait, vCPU descheduling or other waits.',
                    'Fresh worker is not the original failed physical host; admission.json records exact image/Python matches.',
                    'Root directory identity plus original per-file identity guards are not a global immutable snapshot.'],
            }
            profile_save('metrics.json', metrics)
            print(json.dumps({'digest': result, 'reference_match': result == REFERENCE,
                'wall_seconds': wall_ns / 1e9, 'cpu_seconds': cpu_ns / 1e9,
                'counters': progress.counts, 'samples': len(samples)}), flush=True)
        except BaseException as publication_error:
            if primary_error is None:
                raise
            errno = publication_error.errno if isinstance(publication_error, OSError) else None
            primary_error.add_note(
                f"Profile artifact publication failed separately: type={type(publication_error).__name__[:80]}; "
                f"errno={errno if isinstance(errno, int) and -9999 <= errno <= 9999 else None}")
    require(result == REFERENCE, 'Distribution digest mismatch; no second payload')
    require(metrics['source_sha256_at_payload_end'] == PIN, 'Resource changed')
    require(metrics['distribution_root_identity_unchanged'], 'Root identity changed')


import subprocess
def read(p):return json.loads(p.read_bytes())

def save(n,v):(OUT/n).write_text(json.dumps(v,indent=2)+'\n')

def row(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

class InertPopen(subprocess.Popen):
 def __del__(self):pass

def run(label,argv,cwd=ROOT,timeout=60):
 gate='import os,sys; assert os.read(0,1)==b"G"; os.execvpe(sys.argv[1],sys.argv[1:],os.environ)'
 started=time.monotonic()
 child=InertPopen([sys.executable,'-c',gate,*map(str,argv)],cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 rec={'label':label,'argv':list(map(str,argv)),'cwd':str(cwd),'pid':child.pid,'pgid':child.pid,'state':'gated'}
 records.append(rec);save('commands.json',records)
 try:stdout,stderr=child.communicate(b'G',timeout=timeout)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:stdout,stderr=child.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   rec['state']='UNKNOWN';save('commands.json',records);save('HOLD.json',rec);raise
 for stream in [child.stdin,child.stdout,child.stderr]:
  if stream:stream.close()
 rec.update(state='direct_reaped',exitCode=child.returncode,bothEOF=True,closedFDs=True,seconds=time.monotonic()-started)
 try:os.killpg(child.pid,0)
 except ProcessLookupError:rec['ownedGroupAbsentESRCH']=True
 except BaseException as exc:
  rec.update(state='UNKNOWN',observation=type(exc).__name__);save('commands.json',records);save('HOLD.json',rec);raise
 else:
  rec['state']='UNKNOWN';save('commands.json',records);save('HOLD.json',rec);raise RuntimeError('owned group remains')
 save('commands.json',records)
 (OUT/(label+'.stdout')).write_bytes(stdout);(OUT/(label+'.stderr')).write_bytes(stderr)
 assert max(len(stdout),len(stderr))<=8*1024*1024,'bounded output exceeded'
 assert child.returncode==0,label
 return stdout

# R986 custodian copied verbatim above: inert finalizer, bounded output,
# TERM grace, terminal-fact checks and sticky UNKNOWN retention.
import argparse
import runpy
import shutil
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[3]
BOOTSTRAP = 'verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py'
BOOTSTRAP_SHA = '800f76c4139ae7bb3ca692df438a4f162406a120e6c0d26173d9dbf8abb23a6e'
HOST_SHA = 'ee82e57774d6650f94aa06302435d6f44a055b9411698db8ecb85d9a3bcc91d0'
ORIGINAL_IMAGE = '20260824.0517.1'
ADMISSIONS = ('exact-original-image', 'same-class-current-image')
OUT = None
records = []
ROOT = REPO

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

class AlarmSampler:
    def __init__(self, callback):
        self.callback = callback

    def __enter__(self):
        require(signal.getsignal(signal.SIGALRM) == signal.SIG_DFL, 'Foreign SIGALRM handler')
        require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'Foreign timer')
        require(signal.SIGALRM not in signal.sigpending(), 'Pending SIGALRM')
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        require(signal.SIGALRM not in mask, 'Foreign blocked SIGALRM')
        try:
            signal.signal(signal.SIGALRM, self.callback)
            signal.setitimer(signal.ITIMER_REAL, 0.25, 0.25)
        except BaseException:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            raise
        return self

    def __exit__(self, *_):
        old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if signal.SIGALRM in signal.sigpending():
                signal.sigwait({signal.SIGALRM})
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, old)

def admission(policy, env=None, system=None, machine=None, version=None):
    env = os.environ if env is None else env
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    version = platform.python_version() if version is None else version
    same_class = (env.get('GITHUB_ACTIONS') == 'true' and
        env.get('RUNNER_OS') == 'macOS' and env.get('RUNNER_ARCH') == 'X64' and
        env.get('ImageOS') == 'macos26' and system == 'Darwin' and
        machine == 'x86_64' and version.startswith('3.14.') and bool(env.get('ImageVersion')))
    exact_image = env.get('ImageVersion') == ORIGINAL_IMAGE
    exact_python = version == '3.14.7'
    admitted = policy in ADMISSIONS and same_class and (
        policy == 'same-class-current-image' or (exact_image and exact_python))
    return dict(policy=policy, admitted=admitted, same_runner_class=same_class,
        exact_image_match=exact_image, exact_python_match=exact_python,
        original_image=ORIGINAL_IMAGE, original_python='3.14.7',
        actual={k:env.get(k) for k in ('ImageOS','ImageVersion','RUNNER_OS','RUNNER_ARCH')},
        system=system, machine=machine, python=version,
        scope='fresh current-runner diagnostic; original hosted causality unproven',
        original_physical_host_match=False, automatic_retries=0, profile_limit_seconds=180)

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def check_inputs():
    owner = REPO / 'cli/Sources/MixerBuild/Resources/android-build.py'
    bootstrap = REPO / BOOTSTRAP
    data = owner.read_bytes()
    require(len(data) == 56337 and hashlib.sha256(data).hexdigest() == PIN, 'Pinned resource changed; Root rebase required')
    require(hashlib.sha256(bootstrap.read_bytes()).hexdigest() == BOOTSTRAP_SHA, 'Bootstrap changed')
    return owner, bootstrap

def experiment(output, policy):
    global OUT, records
    facts = admission(policy)
    write_json(output / 'admission.json', facts)
    require(facts['admitted'], 'Runner mismatch before download')
    owner, bootstrap = check_inputs()
    packet = runpy.run_path(str(bootstrap), run_name='inert_official_bootstrap')
    OUT = output / 'inner'
    OUT.mkdir()
    records = []
    work = output / 'work'
    work.mkdir()
    write_json(output / 'environment.json', environment())
    pins = {}
    for path in (owner, bootstrap, pathlib.Path(__file__), REPO / '.github/workflows/manual-swift-tree-profile.yml'):
        data = path.read_bytes()
        pins[str(path.relative_to(REPO))] = row(data)
    write_json(output / 'source-pins.json', pins)

    def command(label, argv, diagnostics=False):
        result = run(label, argv, cwd=REPO, timeout=360 if label == 'download-swift-host' else 180).decode()
        return result + (OUT / (label + '.stderr')).read_text() if diagnostics else result

    def identity(path):
        size = 0
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                size += len(block)
                h.update(block)
        return dict(bytes=size, sha256=h.hexdigest())

    completed = False
    try:
        download = packet['download'](command, identity, 'download-swift-host',
            packet['HOST_URL'], work / 'swift.pkg', packet['HOST_BYTES'], HOST_SHA)
        write_json(output / 'download.json', download)
        swift = packet['extract_host'](command, work / 'swift.pkg', work / 'expanded', work / 'swift.xctoolchain')
        version = command('swift-version', [swift, '--version'])
        write_json(output / 'toolchain.json', {'version':version, 'tag':packet['TAG'], 'host_archive_sha256':HOST_SHA})
        require('Swift version 6.3.3 ' in version, 'Swift version changed')
        profile_output = output / 'profile'
        profile_output.mkdir()
        run('profile-once', [sys.executable, '-I', '-B', '-S', __file__,
            '_profile', '--owner', owner, '--tree', swift.parents[2],
            '--output', profile_output], cwd=REPO, timeout=180)
        completed = True
    finally:
        write_json(output / 'experiment-terminal.json', {
            'completed':completed, 'profile_attempts':sum(r['label']=='profile-once' for r in records),
            'commands':records, 'historical_holds_released':False,
            'retained_work':not completed, 'no_retry':True})
        if completed:
            shutil.rmtree(work)

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Manual one-pass Swift tree diagnostic; no compiler or SDK hash')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('launch','_experiment'):
        item = commands.add_parser(name)
        item.add_argument('--admission', choices=ADMISSIONS, required=True)
        item.add_argument('--output', type=pathlib.Path, required=True)
    item = commands.add_parser('_profile')
    for name in ('owner','tree','output'):
        item.add_argument('--' + name, type=pathlib.Path, required=True)
    return parser.parse_args(argv)

def cli(argv=None):
    global OUT, records
    args = parse_args(argv)
    if args.command == '_profile':
        require(args.output.is_dir() and not any(args.output.iterdir()), 'Profile output must be fresh')
        def deadline(signum, frame):
            raise TimeoutError('Existing 180-second parent deadline sent SIGTERM; no retry')
        require(signal.getsignal(signal.SIGTERM) == signal.SIG_DFL, 'Foreign SIGTERM handler')
        signal.signal(signal.SIGTERM, deadline)
        try:
            profile_once(args.owner, args.tree, args.output)
        finally:
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
        return
    if args.command == '_experiment':
        experiment(args.output, args.admission)
        return
    args.output.mkdir(parents=True, exist_ok=False)
    facts = admission(args.admission)
    write_json(args.output / 'runner-admission.json', facts)
    require(facts['admitted'], 'Runner mismatch before work/download; no profile consumed')
    check_inputs()
    OUT = args.output / 'outer'
    OUT.mkdir()
    records = []
    try:
        run('experiment', [sys.executable, '-I', '-B', '-S', __file__, '_experiment',
            '--admission', args.admission, '--output', args.output], cwd=REPO, timeout=1000)
    finally:
        write_json(args.output / 'outer-terminal.json', {'commands':records,
            'scope':'outer facts do not override inner HOLD or missing terminal evidence',
            'historical_holds_released':False})

if __name__ == '__main__':
    cli()
