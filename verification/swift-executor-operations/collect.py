#!/usr/bin/env python3
"""Original/candidate immutable product runs, disjoint derived layout targets."""
from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = '25c5e03833e04608f6626dc384f330008990fa4c'
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE/'results'/STAMP
BUILD = HERE/'build'/STAMP
OUT.mkdir(parents=True, exist_ok=False)
BUILD.mkdir(parents=True, exist_ok=False)
env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
encoded = lambda obj: (json.dumps(obj, sort_keys=True, indent=2)+'\n').encode()
digest = lambda obj: hashlib.sha256(encoded(obj)).hexdigest()
def manifest(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}

commands=[]; binaries=[]; layouts=[]; comparisons=[]; statuses={}
revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
files=[ROOT/'vm/Cargo.toml', ROOT/'vm/Cargo.lock']
for directory in ['src','tests','include']:
    files += sorted(p for p in (ROOT/'vm'/directory).rglob('*') if p.is_file())
source={str(p.relative_to(ROOT/'vm')):sha(p) for p in files}
(OUT/'candidate-manifest.json').write_bytes(encoded(source))
with tarfile.open(OUT/'candidate-source.tar.gz','w:gz') as archive:
    for p in files: archive.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
with (OUT/'baseline-source.tar').open('wb') as output:
    subprocess.run(['git','archive',BASE,'vm'],cwd=ROOT,stdout=output,check=True)
(OUT/'inputs').mkdir()
for name in ['collect.py','operation-layout-probe.rs','owner-layout-probe.rs']:
    (OUT/'inputs'/name).write_bytes((HERE/name).read_bytes())

def command(name, argv, cwd, target=None, closure=None, allow_failure=False):
    if closure is not None: assert manifest(cwd)==closure, 'changed before '+name
    actual_env=dict(env)
    if target is not None: actual_env['CARGO_TARGET_DIR']=str(target)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(argv,cwd=cwd,env=actual_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1200)
    log=OUT/(name+'.log'); log.write_bytes(p.stdout)
    if closure is not None: assert manifest(cwd)==closure, 'changed after '+name
    commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,
        startedUTC=started,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        exit=p.returncode,log=log.name,logSHA256=sha(log),sourceBeforeAfterVerified=closure is not None))
    print(name,p.returncode,flush=True)
    if p.returncode and not allow_failure: raise RuntimeError(p.stdout.decode(errors='replace')[-8000:])
    return p.stdout.decode(errors='replace')

def extract(label, archive):
    dest=BUILD/label
    with tarfile.open(archive) as tf: tf.extractall(dest,filter='data')
    return dest/'vm'

def build_and_run(name,dest,flags,profile,targets,closure):
    target=BUILD/(name+'-target')
    args=['cargo','test','--locked','--offline','--no-run','--message-format=json',*flags]
    if profile=='release': args+=['--release']
    args+=['--lib']
    for t in targets: args+=['--test',t]
    output=command(name+'-build',args,dest,target,closure)
    artifacts=[]
    for line in output.splitlines():
        try: obj=json.loads(line)
        except ValueError: continue
        if obj.get('reason')=='compiler-artifact' and obj.get('executable') and obj.get('profile',{}).get('test'):
            artifacts.append((obj['target']['name'],Path(obj['executable'])))
    assert len(artifacts)==1+len(targets)
    all_tests=[]; traces=[]; counts=[]
    for t,path in sorted(artifacts):
        listed=command(name+'-'+t+'-list',[str(path),'--list'],dest,target,closure)
        runtime=command(name+'-'+t+'-run',[str(path),'--nocapture','--test-threads=1'],dest,target,closure)
        tests=[line for line in listed.splitlines() if line.endswith(': test')]
        all_tests+=tests
        traces += [line[line.index('numeric_trace '):] for line in runtime.splitlines() if 'numeric_trace ' in line]
        summaries=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',runtime)
        assert len(summaries)==1 and summaries[0][0]=='ok' and summaries[0][2]=='0'
        counts.append(dict(target=t,passed=int(summaries[0][1]),ignored=int(summaries[0][3])))
        binaries.append(dict(configuration=name,target=t,path=str(path),sha256=sha(path),runtimeTests=tests,
            listCommand=name+'-'+t+'-list',runCommand=name+'-'+t+'-run'))
    statuses[name]=dict(tests=all_tests,traces=traces,counts=counts)

try:
    command('rustc-version',['rustc','-vV'],ROOT)
    command('cargo-version',['cargo','-V'],ROOT)
    command('python-version',['python3','--version'],ROOT)
    sources={label:extract(label+'-product',OUT/archive) for label,archive in
        [('baseline','baseline-source.tar'),('candidate','candidate-source.tar.gz')]}
    for label,dest in sources.items():
        closure=manifest(dest)
        (OUT/(label+'-product-closure.json')).write_bytes(encoded(closure))
        if label=='candidate':
            assert closure==source
            command('candidate-format',['cargo','fmt','--all','--','--check'],dest,closure=closure)
            command('candidate-clippy-lib',['cargo','clippy','--locked','--offline','--lib','--all-features','--','-D','warnings'],dest,BUILD/'candidate-clippy-lib-target',closure)
            command('candidate-clippy-broad',['cargo','clippy','--locked','--offline','--all-targets','--all-features','--','-D','warnings'],dest,BUILD/'candidate-clippy-broad-target',closure,True)
            for config,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
                command('candidate-check-'+config,['cargo','check','--locked','--offline','--lib',*flags],dest,BUILD/('candidate-check-'+config+'-target'),closure)
        else:
            command('baseline-clippy-broad',['cargo','clippy','--locked','--offline','--all-targets','--all-features','--','-D','warnings'],dest,BUILD/'baseline-clippy-broad-target',closure,True)
        for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
            targets=['differential','float_differential','float']
            if config=='all': targets+=['span_numeric_extraction','span_execution','span_execution_allocations','span_execution_oracle']
            for profile in ['debug','release']:
                build_and_run(label+'-'+config+'-'+profile,dest,flags,profile,targets,closure)
    for config in ['swift','all']:
        for profile in ['debug','release']:
            before=statuses['baseline-'+config+'-'+profile]
            after=statuses['candidate-'+config+'-'+profile]
            added=sorted(set(after['tests'])-set(before['tests']))
            assert len(added)==12 and all('swift_values_' in name for name in added)
            assert not (set(before['tests'])-set(after['tests']))
            assert before['traces']==after['traces']
            comparisons.append(dict(configuration=config,profile=profile,addedTests=added,
                frozenTraceRecords=len(before['traces']),frozenTraceEqual=True,
                frozenTraceSHA256=digest(before['traces']),baselineCounts=before['counts'],candidateCounts=after['counts']))
    # Derived metadata closure and targets are disjoint from every product build.
    for label,archive in [('baseline','baseline-source.tar'),('candidate','candidate-source.tar.gz')]:
        dest=extract(label+'-layout',OUT/archive)
        execution=dest/'src/experimental_swift_reactor/execution.rs'
        execution.write_text(execution.read_text()+'\n'+(OUT/'inputs/owner-layout-probe.rs').read_text())
        calls='execution::operations_owner_layout_probe();'
        if label=='candidate':
            op=dest/'src/experimental_swift_reactor/value_operations.rs'
            op.write_text(op.read_text()+'\n'+(OUT/'inputs/operation-layout-probe.rs').read_text())
            calls+=' execution::value_operations::operations_layout_probe();'
        module=dest/'src/experimental_swift_reactor/mod.rs'
        module.write_text(module.read_text()+'\npub(crate) fn value_layout_probe(){'+calls+'}\n')
        lib=dest/'src/lib.rs'
        lib.write_text(lib.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn value_layout_probe(){experimental_swift_reactor::value_layout_probe();}\n')
        (dest/'examples').mkdir(exist_ok=True)
        (dest/'examples/value-layout.rs').write_text('fn main(){mixer_vm::value_layout_probe();}\n')
        execution.write_text(execution.read_text()+'\n#[cfg(test)] #[test] fn value_layout_only(){super::value_layout_probe();}\n')
        closure=manifest(dest)
        (OUT/(label+'-layout-closure.json')).write_bytes(encoded(closure))
        for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
            for profile in ['debug','release']:
                for cfg in ['production','unit']:
                    name=label+'-'+config+'-'+profile+'-layout-'+cfg
                    target=BUILD/(name+'-target')
                    args=['cargo', 'run' if cfg=='production' else 'test','--locked','--offline',*flags]
                    if profile=='release': args+=['--release']
                    if cfg=='production': args+=['--example','value-layout']
                    else: args+=['--lib','value_layout_only','--','--nocapture','--test-threads=1']
                    result=command(name,args,dest,target,closure)
                    markers=['value_owner|','value_owner_field|','value_bounds|','value_inventory|','value_position|']
                    records=[line[min(line.index(marker) for marker in markers if marker in line):]
                        for line in result.splitlines() if any(marker in line for marker in markers)]
                    assert records and any(line.startswith('value_bounds|header|') for line in records)
                    layouts.append(dict(label=label,configuration=config,profile=profile,cfg=cfg,command=name,records=records))
    for before in [row for row in layouts if row['label']=='baseline']:
        after=next(row for row in layouts if row['label']=='candidate' and all(row[k]==before[k] for k in ['configuration','profile','cfg']))
        assert [v for v in before['records'] if v.startswith('value_owner')]==[v for v in after['records'] if v.startswith('value_owner')]
        b={line.split('|')[1]:int(line.split('|')[2]) for line in before['records'] if line.startswith('value_bounds|')}
        a={line.split('|')[1]:int(line.split('|')[2]) for line in after['records'] if line.startswith('value_bounds|')}
        assert a['header']==b['header']+a['permanent'] and a['construction']==b['construction']
        assert a['phase']==a['declared_operation']+a['active']
    assert all(sha(ROOT/'vm'/path)==value for path,value in source.items())
    status='passed-private-zero-frame-value-operations-host-only-pending-root-accounting-review'
except Exception:
    status='failed'
    raise
finally:
    (OUT/'receipt.json').write_bytes(encoded(dict(schema=1,status=status,baseRevision=BASE,observedRevision=revision,
        scope='Actual original-owner zero-frame value/numeric prepare/complete only. No initialize/invoke/run/host/branch/memory, full target, devices, publication or GA qualification.',
        candidateSourceTreeSHA256=digest(source),candidateSourceArchiveSHA256=sha(OUT/'candidate-source.tar.gz'),
        baselineSourceArchiveSHA256=sha(OUT/'baseline-source.tar'),commands=commands,binaries=binaries,
        comparisons=comparisons,layouts=layouts,sourceCount=len(source),
        candidateSourceUnchanged=all(sha(ROOT/'vm'/path)==value for path,value in source.items()))))
    print(str(OUT),flush=True)
