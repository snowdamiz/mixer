#!/usr/bin/env python3
"""Host-only immutable-source product parity; no live source edits or native UI."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / 'results' / STAMP
BUILD = HERE / 'build' / STAMP
OUT.mkdir(parents=True)
BUILD.mkdir(parents=True)
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
ENV.pop('RUSTC_BOOTSTRAP', None)
COMMANDS, BINARIES, VARIANTS, PARITY = [], [], [], []
STATUS = 'failed-implementation-verification'
TESTS = ['shared_control_' + suffix for suffix in ['branch_targets_and_frame_boundary', 'cancellation_and_limits', 'close_partial_effects', 'public_parity_trace', 'warm_dispatch_allocation_free', 'work_and_fuel_prefixes']]
REGRESSIONS = ['span_execution', 'span_execution_allocations', 'span_numeric_extraction']

def encoded(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def manifest(path): return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
def save(name, obj): (OUT/name).write_bytes(encoded(obj))
def freeze(label, files):
    path = BUILD / label / 'vm'; path.mkdir(parents=True)
    for name, data in files.items():
        dest = path/name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
    closure = manifest(path); save(label+'-manifest.json', closure)
    archive = OUT/(label+'-source.tar.gz')
    with tarfile.open(archive, 'w:gz') as tar:
        for name in closure: tar.add(path/name, arcname='vm/'+name, recursive=False)
    VARIANTS.append(dict(name=label, path=str(path), manifest=label+'-manifest.json', treeSHA256=hashlib.sha256(encoded(closure)).hexdigest(), files=len(closure), archive=archive.name, archiveSHA256=sha(archive)))
    return path, closure

def command(name, argv, path=ROOT, target=None, closure=None):
    if closure: assert manifest(path)==closure, 'before '+name
    env = dict(ENV)
    if target: env['CARGO_TARGET_DIR'] = str(target)
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=path, env=env, capture_output=True, timeout=1200)
    for stream, data in [('stdout',result.stdout),('stderr',result.stderr)]: (OUT/(name+'.'+stream)).write_bytes(data)
    if closure: assert manifest(path)==closure, 'after '+name
    entry = dict(name=name, argv=argv, cwd=str(path), target=str(target) if target else None, exitCode=result.returncode, startedUTC=start, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), sourceBeforeAfterVerified=bool(closure), diagnosticBootstrap=False)
    for stream in ['stdout','stderr']: entry[stream]=name+'.'+stream; entry[stream+'SHA256']=sha(OUT/entry[stream])
    COMMANDS.append(entry); print(name, result.returncode, flush=True)
    assert result.returncode==0, name
    return result.stdout.decode()

def build_tests(label, variant, feature, release, targets, lib=False):
    path, closure = variant; target=BUILD/'targets'/label
    argv=['cargo','test','--locked','--offline','--no-run','--message-format=json']+feature+(['--release'] if release else [])
    if lib: argv+=['--lib']
    else:
        for name in targets: argv+=['--test',name]
    output=command(label+'-build',argv,path,target,closure)
    binaries={}
    for line in output.splitlines():
        try: item=json.loads(line)
        except ValueError: continue
        if item.get('reason')=='compiler-artifact' and item.get('executable') and item.get('profile',{}).get('test'):
            binaries[item['target']['name']]=Path(item['executable'])
    assert len(binaries)==(1 if lib else len(targets)), (label,list(binaries))
    results={}
    for name,binary in binaries.items():
        listing=command(label+'-'+name+'-list',[str(binary),'--list'],path,closure=closure)
        identities=[line[:-6] for line in listing.splitlines() if line.endswith(': test')]
        assert identities and len(identities)==len(set(identities)), label
        if name=='span_control_extraction': assert identities==TESTS,(label,identities)
        if lib:
            selected=[test for test in identities if ('control_probe_' in test if 'probe' in label else 'swift_values_' in test)]
            assert len(selected)==(2 if 'probe' in label else 9), (label,selected)
            filter_name='control_probe_' if 'probe' in label else 'swift_values_'
            args=[str(binary),filter_name,'--nocapture','--test-threads=1']
        else: selected=identities; args=[str(binary),'--nocapture','--test-threads=1']
        run=command(label+'-'+name+'-run',args,path,closure=closure)
        assert f'test result: ok. {len(selected)} passed; 0 failed; 0 ignored;' in run,label
        # Preserve original test list and independently measured binary identity.
        entry=dict(label=label,name=name,path=str(binary),sha256=sha(binary),bytes=binary.stat().st_size,tests=identities,executedTests=selected,listCommand=label+'-'+name+'-list',runCommand=label+'-'+name+'-run')
        BINARIES.append(entry); results[name]=run
    return results

try:
    tools={name:command('tool-'+name,argv).strip() for name,argv in {'cargo':['cargo','--version'],'rustc':['rustc','-vV'],'python':['python3','--version'],'host':['uname','-a'],'revision':['git','rev-parse','HEAD']}.items()}
    with tarfile.open(HERE/'accepted-baseline.tar.gz') as tar:
        baseline={m.name.removeprefix('vm/'):tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    expected=json.loads((HERE/'accepted-baseline-manifest.json').read_text())
    assert {name:hashlib.sha256(data).hexdigest() for name,data in baseline.items()}==expected
    assert hashlib.sha256(encoded(expected)).hexdigest()=='96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7'
    paths=[ROOT/'vm/Cargo.toml',ROOT/'vm/Cargo.lock']
    for folder in ['src','tests','include']: paths+=sorted(p for p in (ROOT/'vm'/folder).rglob('*') if p.is_file())
    candidate={str(p.relative_to(ROOT/'vm')):p.read_bytes() for p in paths}
    added=set(candidate)-set(baseline); changed={name for name in baseline if baseline[name]!=candidate[name]}
    assert added=={'tests/span_control_extraction.rs'}
    assert changed=={'src/experimental/execution/mod.rs','src/experimental/execution/borrowed.rs'}
    baseline['tests/span_control_extraction.rs']=candidate['tests/span_control_extraction.rs']
    variants={'baseline':freeze('baseline',baseline),'candidate':freeze('candidate',candidate)}
    probe=(HERE/'private_probes.rs').read_bytes()
    probe_variants={}
    for name,files in [('baseline',baseline),('candidate',candidate)]:
        files=dict(files)
        files['src/experimental/execution/control_probe.rs']=probe
        files['src/experimental/execution/mod.rs']+=b'\n#[cfg(all(test,feature="experimental-span-execution"))]\n#[path="control_probe.rs"] mod control_probes;\n'
        files['src/lib.rs']+=b'\n#[cfg(test)] extern crate self as mixer_vm;\n'
        probe_variants[name]=freeze(name+'-probe',files)
    save('tools.json',tools)
    source_outputs={}
    for mode,feature in [('span',['--features','experimental-span-execution']),('all',['--all-features'])]:
        for profile,release in [('debug',False),('release',True)]:
            for name in ['baseline','candidate']:
                label=name+'-'+mode+'-'+profile
                results=build_tests(label,variants[name],feature,release,['span_control_extraction']+REGRESSIONS)
                source_outputs[label]=results
                probe_results=build_tests(label+'-probe',probe_variants[name],feature,release,[],True)
                source_outputs[label+'-probe']=probe_results
            for target in ['span_control_extraction']+REGRESSIONS:
                left=source_outputs['baseline-'+mode+'-'+profile][target]
                right=source_outputs['candidate-'+mode+'-'+profile][target]
                markers=['control_trace ','control_warm ','control_validation_ceiling '] if target=='span_control_extraction' else ['numeric_trace ','numeric_cases '] if target=='span_numeric_extraction' else []
                if markers:
                    def traces(text):
                        rows=[]
                        for line in text.splitlines():
                            for marker in markers:
                                at=line.find(marker)
                                if at>=0: rows.append(line[at:]); break
                        return rows
                    a,b=traces(left),traces(right); assert a==b,(mode,profile,target)
                    PARITY.append(dict(mode=mode,profile=profile,target=target,records=len(a),traceSHA256=hashlib.sha256(encoded(a)).hexdigest()))
            left=source_outputs['baseline-'+mode+'-'+profile+'-probe']['mixer_vm']
            right=source_outputs['candidate-'+mode+'-'+profile+'-probe']['mixer_vm']
            def probe_rows(text): return [line[line.index('control_probe '):] for line in text.splitlines() if 'control_probe ' in line]
            assert probe_rows(left)==probe_rows(right)
            PARITY.append(dict(mode=mode,profile=profile,target='archived-private-probes',records=len(probe_rows(left)),traceSHA256=hashlib.sha256(encoded(probe_rows(left))).hexdigest()))
    # The accepted Swift value route remains a separate regression, with exact
    # runtime identities selected from the real unit binary's complete --list.
    for mode,feature in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for profile,release in [('debug',False),('release',True)]:
            build_tests('candidate-'+mode+'-'+profile+'-values',variants['candidate'],feature,release,[],True)
    for mode,feature in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for profile,release in [('debug',False),('release',True)]:
            path,closure=variants['candidate'];label='candidate-'+mode+'-'+profile+'-check'
            command(label,['cargo','check','--locked','--offline','--lib']+feature+(['--release'] if release else []),path,BUILD/'targets'/label,closure)
    path,closure=variants['candidate']
    command('candidate-format',['cargo','fmt','--all','--','--check'],path,closure=closure)
    command('candidate-clippy',['cargo','clippy','--locked','--offline','--lib','--all-features','--','-D','warnings'],path,BUILD/'targets'/'clippy',closure)
    assert {str(p.relative_to(ROOT/'vm')):sha(p) for p in paths}=={name:hashlib.sha256(data).hexdigest() for name,data in candidate.items()}
    STATUS='host-bounded-executable-parity-complete-root-review-pending'
finally:
    receipt=dict(schema=1,status=STATUS,sourceRevision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),acceptedBaselineTreeSHA256='96b16d4886b9218e132a2a1255c0ce4e66c60879ed7bb5f1ea1185b0ca08b8c7',variants=VARIANTS,commands=COMMANDS,binaries=BINARIES,parity=PARITY,productHooksAdded=False,swiftInvocation=False,nativeRuntime=False,physicalRuntime=False,publication=False,gaAcceptance=False,limitations=['Bounded frozen source extraction, not Swift control execution','Derived malformed-state probes are archived overlays, not valid public paths','Final physical matrix, immutable FieldLog publication, signing/store/customer/operational and GA remain pending'])
    save('receipt.json',receipt)
    print(str(OUT/'receipt.json'),flush=True)
