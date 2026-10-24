#!/usr/bin/env python3
"""Bounded original-owner declaration/borrow probe; never edits live VM."""
from pathlib import Path
import datetime, hashlib, json, os, re, shutil, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
encoded = lambda x: (json.dumps(x, sort_keys=True, indent=2) + '\n').encode()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda x: hashlib.sha256(encoded(x)).hexdigest()

def source_files(vm):
    files = [vm/'Cargo.toml', vm/'Cargo.lock']
    for name in ['src', 'tests', 'include']:
        files += sorted(p for p in (vm/name).rglob('*') if p.is_file())
    return {str(p.relative_to(vm)): sha(p) for p in files}

def generalized_macro(source):
    prefix = 'macro_rules! frozen_control_methods {\n    () => {\n'
    start = source.index(prefix) + len(prefix)
    end = source.index('\n    };\n}', start)
    body = source[start:end]
    frame = 'let frame = self.frames.last().ok_or_else(|| self.invariant())?;'
    assert frame in body
    body = body.replace(frame, '$leaf!(frame $this, frame);')
    body = body.replace('self.frames.last_mut().ok_or_else(unreachable_failure)?.pc = pc;', '$leaf!(set_pc $this, pc);')
    body = body.replace('self.values.truncate(control.height);', '$leaf!(truncate_values $this, $leaf!(height $control));')
    body = body.replace('self.controls.truncate(if control.kind == Kind::Loop {\n                index + 1\n            } else {\n                index\n            });', '$leaf!(truncate_controls $this, if $leaf!(loop $control) {\n                index + 1\n            } else {\n                index\n            });')
    body = body.replace('control.result = false;', '$leaf!(clear $control);')
    body = body.replace('control.kind == Kind::Loop', '$leaf!(loop $control)')
    body = body.replace('control.kind == Kind::Function', '$leaf!(function $control)')
    body = body.replace('control.end + 1', '$leaf!(after_end $control)')
    body = body.replace('control.start', '$leaf!(start $control)')
    body = body.replace('control.height', '$leaf!(height $control)')
    body = body.replace('control.result', '$leaf!(result $control)')
    body = body.replace('frame.controls', '$leaf!(floor frame)')
    body = body.replace('self.pop()', '$leaf!(pop $this)')
    body = body.replace('self.push(value)', '$leaf!(push $this, value)')
    body = body.replace('self.observe()', '$leaf!(observe $this)')
    body = body.replace('self.invariant()', '$leaf!(invariant $this)')
    body = body.replace('self.values', '$leaf!(values $this)')
    body = body.replace('self.controls', '$leaf!(controls $this)')
    body = body.replace('self\n                .controls', '$leaf!(controls $this)')
    body = re.sub(r'\bself\b', '$this', body)
    body = re.sub(r'(?<!\$)\bcontrol\b', '$control', body)
    # The only configured close prelude is empty for Frozen and a frame-floor
    # declaration for Swift. Its receiver/parameter tokens are invocation-bound.
    marker = 'fn close_control(&mut $this, $control: Control) -> Result<(), ExecutionFailure> {\n'
    assert marker in body
    body = body.replace(marker, marker + '            $($close_prelude)*\n')
    body = body.replace('ExecutionFailure', '$failure')
    return '''// Derived only from the actual accepted literal macro; never run here.
#[allow(unused_macros)]
macro_rules! contract_control_methods {
    ($this:ident, $failure:ty, $leaf:ident, $control:ident, {$($close_prelude:tt)*}) => {
''' + body + '''
    };
}
pub(crate) use contract_control_methods;
'''

ACCESSORS = '''
// Additive isolated scalar visibility witness; Kind and fields stay private.
#[cfg(test)]
impl Control {
    pub(crate) fn contract_result(self) -> bool { self.result }
    pub(crate) fn contract_height(self) -> usize { self.height }
    pub(crate) fn contract_start(self) -> usize { self.start }
    pub(crate) fn contract_end(self) -> usize { self.end }
    pub(crate) fn contract_is_loop(self) -> bool { self.kind == Kind::Loop }
    pub(crate) fn contract_is_function(self) -> bool { self.kind == Kind::Function }
    pub(crate) fn contract_clear_result(&mut self) { self.result = false; }
    pub(crate) fn contract_decoded(kind: ControlKind, start: usize, end: usize,
        height: usize, result: bool) -> Self {
        Self { kind: match kind { ControlKind::Block => Kind::Block,
            ControlKind::Loop => Kind::Loop, ControlKind::If => Kind::If },
            start, end, height, result }
    }
}
'''

def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out, build = HERE/'results'/stamp, HERE/'build'/stamp
    out.mkdir(parents=True); build.mkdir(parents=True)
    vm = build/'vm'
    baseline = source_files(ROOT/'vm')
    (out/'source-manifest.json').write_bytes(encoded(baseline))
    with tarfile.open(out/'source.tar.gz','w:gz') as archive:
        for name in baseline: archive.add(ROOT/'vm'/name, arcname='vm/'+name, recursive=False)
    for name in baseline:
        dest = vm/name; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'vm'/name,dest)
    borrowed = vm/'src/experimental/execution/borrowed.rs'
    macro = generalized_macro(borrowed.read_text())
    (out/'generalized-methods.rs').write_text(macro)
    borrowed.write_text(borrowed.read_text()+'\n'+macro)
    owner = vm/'src/experimental/execution/mod.rs'
    owner.write_text(owner.read_text()+ACCESSORS)
    frame = vm/'src/experimental_swift_reactor/frame_operations.rs'
    frame.write_text(frame.read_text()+'\n#[cfg(test)]\n#[path = "contract_probe.rs"]\nmod contract_probe;\n')
    shutil.copyfile(HERE/'probe.rs',vm/'src/experimental_swift_reactor/contract_probe.rs')
    (out/'probe.rs').write_bytes((HERE/'probe.rs').read_bytes())
    (out/'collect.py').write_bytes(Path(__file__).read_bytes())
    overlay = source_files(vm)
    (out/'overlay-manifest.json').write_bytes(encoded(overlay))
    commands, layouts = [], {}
    environment = dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
    environment.pop('RUSTC_BOOTSTRAP',None)
    status='failed'
    def run(name, argv, cwd=ROOT, target=None):
        assert source_files(ROOT/'vm') == baseline, 'live VM changed'
        assert source_files(vm) == overlay, 'overlay changed'
        env=dict(environment)
        if target: env['CARGO_TARGET_DIR']=str(target)
        started=datetime.datetime.now(datetime.timezone.utc).isoformat()
        result=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=180)
        for stream in ['stdout','stderr']: (out/(name+'.'+stream)).write_bytes(getattr(result,stream))
        commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,
            startedUTC=started,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            exitCode=result.returncode,baselineSHA256=digest(baseline),overlaySHA256=digest(overlay),
            stdout=name+'.stdout',stdoutSHA256=sha(out/(name+'.stdout')),
            stderr=name+'.stderr',stderrSHA256=sha(out/(name+'.stderr'))))
        assert source_files(ROOT/'vm') == baseline and source_files(vm) == overlay
        print(name,result.returncode,flush=True)
        if result.returncode: raise RuntimeError(result.stderr.decode(errors='replace')[-9000:])
        return result.stdout.decode()
    try:
        run('revision',['git','rev-parse','HEAD'])
        run('rustc-version',['rustc','-vV'])
        run('cargo-version',['cargo','-V'])
        run('python-version',['python3','--version'])
        run('host',['uname','-a'])
        for feature in ['swift','all']:
            for profile in ['debug','release']:
                name=feature+'-'+profile
                flags=['--all-features'] if feature=='all' else ['--features','experimental-swift-reactor']
                if profile=='release': flags += ['--release']
                output=run(name,['cargo','test','--lib',*flags,'control_invocation_contract_metadata_only','--','--nocapture','--test-threads=1'],vm,build/(name+'-target'))
                rows={kind:int(size) for kind,size in re.findall(r'^contract_size\|([^|]+)\|(\d+)$',output,re.M)}
                assert len(rows)==17, rows
                layouts[name]=rows
        assert all(value==layouts['swift-debug'] for value in layouts.values())
        status='passed-declaration-borrow-layout-only'
    finally:
        receipt=dict(status=status,sourceTreeSHA256=digest(baseline),sourceFiles=len(baseline),overlayTreeSHA256=digest(overlay),
            commands=commands,layouts=layouts,liveVMUnchanged=source_files(ROOT/'vm')==baseline,
            scope='Uncalled generalized helper declarations on the actual FrameOperationPhase and actual leaf borrow APIs. One host metadata test per configuration. No control opcode, guest, native runtime or public invocation executed.',
            implementationAccepted=False,accountingAccepted=False,nativeRuntime=False,physicalRuntime=False,gaAcceptance=False)
        (out/'receipt.json').write_bytes(encoded(receipt))
        shutil.rmtree(build)
        (out/'cleanup.json').write_bytes(encoded(dict(removed=str(build),buildRemoved=not build.exists(),nativeInstancesStarted=False)))
        print(out/'receipt.json',flush=True)

if __name__ == '__main__': main()
