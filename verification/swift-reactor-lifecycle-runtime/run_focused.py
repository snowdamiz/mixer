#!/usr/bin/env python3
"""Run only root-selected exact lifecycle tests, retaining all outcomes."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, shutil, signal, subprocess, sys, tarfile, tempfile, time, traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ACCOUNTING = ROOT / 'verification/swift-reactor-lifecycle-accounting'
SELECTION = ROOT / 'verification/swift-reactor-lifecycle-accounting-root-review/runtime-selection.json'
SELECTION_SHA = 'e6ad507b8484d1f34cef67113022927c5d55a459dd9d9caa9a224088ad7e3287'
SOURCE = '0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f'
NODE = Path('/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin/node')
EXPLICIT_PATH = '/opt/homebrew/opt/rustup/bin:' + str(NODE.parent) + ':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'

def enc(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(8 * 1024 * 1024): h.update(chunk)
    return h.hexdigest()
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else enc(value))
def read(path): return json.loads(path.read_bytes())
def manifest(tree): return {str(p.relative_to(tree)): digest(p) for p in sorted(tree.rglob('*')) if p.is_file()}
def members(group):
    rows = subprocess.check_output(['/bin/ps', '-axo', 'pid=,pgid=,command='], text=True)
    return [r for r in rows.splitlines() if len(r.split(None, 2)) >= 2 and r.split(None, 2)[1] == str(group)]

def source_check():
    actual = manifest(HERE / 'candidate')
    assert actual == read(ACCOUNTING / 'candidate-final-manifest.json')
    assert sha(enc(actual)) == SOURCE
    assert digest(SELECTION) == SELECTION_SHA
    return actual

def tool_check(env):
    query = read(ACCOUNTING / 'exact-query-swift-debug-production.json')
    expected = read(ACCOUNTING / query['attempt'] / 'tools.json')
    actual = expected['actualCompiler']
    for tool in ['rustc', 'cargo', 'rustfmt']:
        pin = expected[tool]
        assert shutil.which(tool, path=env['PATH']) == pin['executable']
        assert digest(pin['executable']) == pin['executableSHA256']
    sysroot = Path(actual['sysroot'])
    files = {str(p.relative_to(sysroot)): digest(p) for group in ['bin', 'lib'] for p in sorted((sysroot / group).rglob('*')) if p.is_file()}
    assert files == actual['sysrootCompilerFiles']
    assert digest(actual['path']) == actual['sha256']
    assert not {k:v for k,v in env.items() if v and (k.startswith('NODE_') or 'DYLD_' in k or k in ['LD_PRELOAD','LD_LIBRARY_PATH'])}
    node = read(ROOT / 'verification/swift-calls-dispatch-node-oracle-qualification/node-provenance.json')
    assert Path(shutil.which('node', path=env['PATH'])).resolve() == NODE
    assert digest(NODE) == node['executableSHA256']
    assert digest(node['systemVersion']['path']) == node['systemVersion']['sha256']
    return {'compiler': expected, 'node': {k:node[k] for k in ['actualPath','executableSHA256','version','systemVersion']}, 'python': {'path':sys.executable,'sha256':digest(sys.executable),'version':sys.version}, 'explicitPATH':EXPLICIT_PATH}

def command(folder, name, argv, env, executable=None, timeout=900):
    before = source_check()
    tools = tool_check(env)
    save(folder / (name + '-tools.json'), tools)
    row = {'argv':argv, 'cwd':str(HERE/'candidate'), 'PATH':env['PATH'], 'environment':{k:env[k] for k in ['CARGO_TARGET_DIR','CARGO_INCREMENTAL']}, 'sourceClosure':SOURCE, 'selectionSHA256':SELECTION_SHA, 'sourceBeforeSHA256':sha(enc(before)), 'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'timeoutSeconds':timeout, 'launched':False}
    if executable:
        assert Path(argv[0]) == executable
        row.update(executableSHA256=digest(executable), executableBytes=executable.stat().st_size)
    destination = folder / (name + '.json')
    save(destination,row)
    child = None
    start = time.monotonic()
    out = err = b''
    try:
        child = subprocess.Popen(argv,cwd=HERE/'candidate',env=env,start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        row.update(launched=True, processGroup=child.pid)
        save(destination,row)
        try: out,err = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            row['timedOut'] = True
            assert child.poll() is None and os.getpgid(child.pid) == child.pid
            os.killpg(child.pid,signal.SIGKILL)
            out,err = child.communicate()
        row['exitCode'] = child.returncode
    except BaseException:
        row['collectionFailure'] = traceback.format_exc()
        raise
    finally:
        if child is not None and child.poll() is None:
            assert os.getpgid(child.pid) == child.pid
            os.killpg(child.pid,signal.SIGKILL)
            moreout,moreerr = child.communicate()
            out += moreout; err += moreerr
        save(folder/(name+'-stdout.gz'),gzip.compress(out,mtime=0))
        save(folder/(name+'-stderr.gz'),gzip.compress(err,mtime=0))
        row.update(stdoutSHA256=sha(out),stderrSHA256=sha(err),durationSeconds=time.monotonic()-start,finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceUnchanged=before==manifest(HERE/'candidate'),remainingGroup=members(child.pid) if child is not None else [])
        save(destination,row)
    assert row['sourceUnchanged'] and not row['remainingGroup']
    return row,out,err

def cleanup(scratch, folder):
    artifacts = []
    try:
        for p in sorted(scratch.rglob('*')):
            if p.is_file() and p.parent.name == 'deps' and p.stat().st_mode & 0o111 and p.suffix == '':
                data = p.read_bytes(); name = 'artifacts/' + str(p.relative_to(scratch)) + '.gz'
                save(folder/name,gzip.compress(data,mtime=0))
                artifacts.append({'path':name,'sha256':sha(data),'bytes':len(data)})
    finally: save(folder/'artifacts.json',artifacts)
    scan = subprocess.run(['/usr/sbin/lsof','-nP','+D',str(scratch)],capture_output=True)
    save(folder/'cleanup-holders.stdout',scan.stdout); save(folder/'cleanup-holders.stderr',scan.stderr)
    row = {'scratch':str(scratch),'lsofExitCode':scan.returncode,'holderCheckEmpty':scan.returncode==1 and not scan.stdout and not scan.stderr,'removed':False,'nativeInstancesCreated':0}
    save(folder/'cleanup.json',row)
    assert row['holderCheckEmpty'], 'holder or scan error; preserve scratch'
    row.update(filesRemoved=sum(p.is_file() for p in scratch.rglob('*')),logicalBytesRemoved=sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file()))
    shutil.rmtree(scratch)
    row['removed'] = not scratch.exists()
    save(folder/'cleanup.json',row)

def main():
    assert digest(SELECTION) == SELECTION_SHA
    selected = read(SELECTION)
    assert selected['runtimeSelected'] and selected['sourceAndLogicalAccountingAccepted'] and not selected['full53MBTargetSelected']
    assert not (HERE/'candidate').exists(), 'fresh runtime packet required'
    shutil.copytree(ACCOUNTING/'candidate',HERE/'candidate')
    before = source_check()
    save(HERE/'candidate-manifest.json',before)
    for name in ['authored-coverage.json','planned-matrix-unchanged.json']:
        save(HERE/name,(ACCOUNTING/name).read_bytes())
    save(HERE/'runtime-selection.json',SELECTION.read_bytes())
    save(HERE/'accounting-seal.json',(ACCOUNTING/'seal.json').read_bytes())
    with tarfile.open(HERE/'source.tar.gz','w:gz') as archive:
        for name in before: archive.add(HERE/'candidate'/name,arcname=name,recursive=False)
    inventory = read(ACCOUNTING/'test-inventories.json')
    results = []
    save(HERE/'results.json',results)
    for features in ['swift','all']:
        for profile in ['debug','release']:
            context = features+'-'+profile
            folder = HERE/'attempts'/context
            folder.mkdir(parents=True)
            scratch = Path(tempfile.mkdtemp(prefix='mixer-lifecycle-runtime-'))
            env = dict(os.environ,PATH=EXPLICIT_PATH,CARGO_TARGET_DIR=str(scratch/'target'),CARGO_INCREMENTAL='0')
            for key in ['RUSTFLAGS','RUSTC_BOOTSTRAP','RUSTC','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS']: env.pop(key,None)
            flags = ['--no-default-features'] + (['--features','experimental-swift-reactor'] if features=='swift' else ['--all-features']) + (['--release'] if profile=='release' else [])
            result = {'context':context,'sourceClosure':SOURCE,'passed':False}
            results.append(result); save(HERE/'results.json',results)
            try:
                row,out,err = command(folder,'build',['cargo','test','--lib','--no-run','--locked','--offline',*flags,'--message-format=json-render-diagnostics'],env)
                result['buildExitCode'] = row['exitCode']
                assert row['exitCode']==0, 'build failed'
                records = [json.loads(line) for line in out.decode().splitlines() if line.startswith('{')]
                artifacts = [r for r in records if r.get('reason')=='compiler-artifact' and r.get('executable') and r['target']['name']=='mixer_vm']
                assert len(artifacts)==1 and not artifacts[0]['fresh'] and artifacts[0]['profile']['test']
                artifact = artifacts[0]; exe = Path(artifact['executable']); assert exe.is_relative_to(scratch/'target')
                save(folder/'cargo-artifact.json',artifact)
                row,out,err = command(folder,'list',[str(exe),'swift_lifecycle_','--list'],env,exe)
                names = [line[:-6] for line in out.decode().splitlines() if line.endswith(': test')]
                expected = next(r['lifecycleTests'] for r in inventory if r['context']==context)
                assert row['exitCode']==0 and names==expected and len(names)==23
                save(folder/'exact-tests.json',names)
                row,out,err = command(folder,'execute',[str(exe),'swift_lifecycle_','--nocapture','--test-threads=1'],env,exe)
                text = out.decode(errors='replace')
                observed = {name:('test '+name+' ... ok') in text for name in names}
                result.update(executionExitCode=row['exitCode'],testIdentities=observed,passed=row['exitCode']==0 and all(observed.values()) and '23 passed; 0 failed; 0 ignored;' in text,executableSHA256=row['executableSHA256'])
                save(HERE/'results.json',results)
                print(json.dumps(result,sort_keys=True),flush=True)
                assert result['passed'], 'focused runtime failed; no unchanged rerun or broader regression allowed'
            except BaseException:
                result['failure'] = traceback.format_exc()
                save(HERE/'results.json',results)
                raise
            finally: cleanup(scratch,folder)
    save(HERE/'focused-complete.json',{'sourceClosure':SOURCE,'contexts':4,'testsPerContext':23,'allAuthoredSubcasesComplete':False,'fullPlannedRowsPassed':False,'broaderRegressionsSelectedNext':True})

if __name__ == '__main__': main()
