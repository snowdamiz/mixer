"""Bounded compiler and standalone scalar controls. Never dispatch the VM/writer."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from prepare import HERE, BASE, RECIPE, AUTHORITY_TREE, CONTROL, PROFILE, canonical, members, sha, write

RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
ACCEPTANCE = HERE.parent / 'swift-semantic-adapter-root-review/guarded-snapshot-owner-storage-host-acceptance.json'
ACCEPTANCE_SHA = '6830f6cf2d889b3df551b0ad1e6e278d340dfa291abf153401f467548d2e2688'

def custody():
    assert sha(ACCEPTANCE.read_bytes()) == ACCEPTANCE_SHA
    source = members(HERE / 'source/vm')
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    assert source == manifest['members'] and len(source) == 144
    assert sha(canonical(members(BASE / 'source/vm'))) == AUTHORITY_TREE
    return dict(source_tree_sha256=sha(canonical(source)), source_members=144,
                owner_recipe_acceptance_sha256=ACCEPTANCE_SHA, runtime_selected=False)

def bounded(argv, env, cwd, timeout=55):
    started = time.monotonic()
    child = subprocess.Popen(argv, env=env, cwd=cwd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    actions = []
    try:
        out, err = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(child.pid, signal.SIGTERM)
            actions.append('SIGTERM owned group')
        except ProcessLookupError:
            pass
        try:
            out, err = child.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
                actions.append('SIGKILL owned group')
            except ProcessLookupError:
                pass
            out, err = child.communicate(timeout=2)
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    return out, err, dict(argv=argv, exit_code=child.returncode,
        elapsed_seconds=time.monotonic()-started, timeout_seconds=timeout,
        timed_out=timed_out, owned_process_group=child.pid, new_session=True,
        child_reaped=True, owned_group_absent=absent, cleanup_actions=actions)

def run(label, unit=False, standalone=False, overflow=False, negative=False):
    binding = custody()
    command = HERE / 'commands' / label
    command.mkdir(parents=True, exist_ok=False)
    scratch = HERE / 'owned-work' / label
    scratch.mkdir(parents=True, exist_ok=False)
    version_out, version_err, version_receipt = bounded([str(RUSTC), '--version', '--verbose'],
        {'PATH': '/usr/bin:/bin'}, HERE, 10)
    assert version_receipt['exit_code'] == 0 and version_receipt['owned_group_absent']
    (command / 'compiler-version-stdout').write_bytes(version_out)
    (command / 'compiler-version-stderr').write_bytes(version_err)
    if standalone:
        source = scratch / 'scalar.rs'
        source.write_text(standalone_source(unit=unit, overflow=overflow, negative=negative))
        (command / 'standalone-source.rs').write_bytes(source.read_bytes())
        preimage = dict(schema=1, standalone_source_sha256=sha(source.read_bytes()),
            exact_recipe_constants_sha256=sha((HERE/'funding-constants.inc.rs').read_bytes()),
            support_driver_sha256=sha(Path(__file__).read_bytes()), source_binding=binding)
        artifact = scratch / 'scalar'
        argv = [str(RUSTC), '--crate-name', 'funding_scalar', '--edition=2021',
                '-C', 'overflow-checks=yes', str(source), '-o', str(artifact)]
        if unit:
            argv += ['--cfg', 'test']
    else:
        vm = scratch / 'vm'
        shutil.copytree(HERE/'source/vm', vm)
        assert members(vm) == json.loads((HERE/'source-manifest.json').read_text())['members']
        source = vm / 'src/lib.rs'
        support = members(HERE.parent/'swift-guarded-snapshot-encoder-implementation/host')
        assert len(support) == 11
        preimage = dict(schema=1, source_members=members(vm), encoder_support_members=support,
                        driver_sha256=sha(Path(__file__).read_bytes()), source_binding=binding)
        artifact = scratch / 'candidate.rmeta'
        mir = scratch / 'candidate.mir'
        argv = [str(RUSTC), '--crate-name', 'mixer_vm', '--edition=2021',
                '--target', 'aarch64-apple-darwin', '-C', 'opt-level=0', '-C',
                'overflow-checks=yes', '-C', 'panic=unwind', '-Zmir-opt-level=0',
                '-Zmir-include-spans=yes']
        for feature in ['experimental-swift-reactor', 'experimental-swift-wasi',
                        'experimental-stream-validation', 'experimental-function-cache']:
            argv += ['--cfg', 'feature="'+feature+'"']
        argv += ['--test'] if unit else ['--crate-type', 'rlib']
        argv += [str(source), '--emit=metadata='+str(artifact)+',mir='+str(mir)]
    (command/'source-preimage.json').write_text(json.dumps(preimage, indent=2, sort_keys=True)+'\n')
    env = {'PATH':'/usr/bin:/bin', 'TMPDIR':str(scratch), 'RUSTC_BOOTSTRAP':'1',
        'CARGO_MANIFEST_DIR':str(source.parent.parent if not standalone else scratch),
        'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),
        'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version_out),
        'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(preimage)),
        'MIXER_LOADER_COMMAND_SHA256':sha(canonical(argv))}
    env['MIXER_LOADER_COMPILE_ENV_SHA256'] = sha(canonical(env))
    try:
        out, err, receipt = bounded(argv, env, HERE.parent.parent)
        (command/'stdout').write_bytes(out)
        (command/'stderr').write_bytes(err)
        receipt.update(schema=1, environment=env, source_binding=binding,
            compiler_sha256=sha(RUSTC.read_bytes()), compiler_version=version_out.decode(),
            compiler_version_command=version_receipt, stdout_sha256=sha(out), stderr_sha256=sha(err),
            expected_result='checked-overflow E0080' if negative else 'success',
            mode='cfg(test)' if unit else 'production',
            scope='Standalone scalar arithmetic only' if standalone else 'Exact candidate metadata and MIR only; no engine/VM/writer invocation')
        receipt['expectation_met'] = (receipt['exit_code'] != 0 and b'E0080' in err) if negative else receipt['exit_code'] == 0
        if artifact.exists():
            receipt['removed_artifact'] = dict(bytes=artifact.stat().st_size, sha256=sha(artifact.read_bytes()))
        if not standalone and mir.exists():
            text = mir.read_text()
            receipt['removed_full_mir'] = dict(bytes=mir.stat().st_size, sha256=sha(mir.read_bytes()))
            selected = extract_bodies(text)
            (command/'funding-functions.mir').write_text('\n\n'.join(selected.values())+'\n')
            receipt['funding_function_summary'] = summarize_bodies(selected)
        (command/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        assert receipt['child_reaped'] and receipt['owned_group_absent'] and not receipt['timed_out']
        assert receipt['expectation_met'], err.decode()[-3000:]
        if standalone and not negative:
            out, err, scalar = bounded([str(artifact)], {'PATH':'/usr/bin:/bin'}, scratch, 10)
            (command/'scalar-stdout').write_bytes(out)
            (command/'scalar-stderr').write_bytes(err)
            scalar.update(schema=1, executable_sha256=sha(artifact.read_bytes()),
                source_sha256=sha(source.read_bytes()), stdout_sha256=sha(out), stderr_sha256=sha(err),
                scope='Pure integer arithmetic with synthetic F0; no Mixer crate/VM/native application/writer dependency')
            (command/'scalar-receipt.json').write_text(json.dumps(scalar,indent=2,sort_keys=True)+'\n')
            assert scalar['exit_code'] == 0 and scalar['owned_group_absent'] and not scalar['timed_out']
        print(json.dumps(dict(label=label, exit_code=receipt['exit_code'], expectation_met=True,
                             elapsed_seconds=receipt['elapsed_seconds'])), flush=True)
    finally:
        shutil.rmtree(scratch)
        (command/'cleanup.json').write_text(json.dumps(dict(owned_scratch=str(scratch), removed=not scratch.exists()),indent=2)+'\n')
    custody()

def extract_bodies(text):
    result = {}
    for name in ['foundation_construction_bytes', 'snapshot_scope_candidate_foundation_v1',
                 'begin_snapshot_access_v1', 'proposed_emission_work_v1']:
        matches = list(re.finditer(r'^fn (?:[^\n]*::)?'+name+r'\([^\n]*\) -> [^\n]* \{\n', text, re.M))
        assert len(matches) == 1, (name, len(matches))
        start = matches[0].start()
        end = text.index('\n}\n', matches[0].end()) + 2
        result[name] = text[start:end]
    return result

def summarize_bodies(bodies):
    result = {}
    for name, body in bodies.items():
        locals_ = re.findall(r'^\s+let (?:mut )?(_\d+): ([^\n]+?);', body, re.M)
        result[name] = dict(mir_sha256=sha(body.encode()), declared_locals=[dict(name=a, type=b) for a,b in locals_])
    for name in ['foundation_construction_bytes','snapshot_scope_candidate_foundation_v1']:
        assert [r['name'] for r in result[name]['declared_locals']] == ['_0'], result[name]
        assert 'checked_add(' not in bodies[name] and ' -> [return:' not in bodies[name]
    return result

def standalone_source(unit=False, overflow=False, negative=False):
    constants = (HERE/'funding-constants.inc.rs').read_text()
    original = 'usize::MAX' if overflow else '366_896'
    code = '''// Standalone scalar harness. The synthetic F0 is not a measured Mixer floor.
mod recipe {
const FOUNDATION_CONSTRUCTION_BYTES:Option<usize>=Some('''+original+''');
'''+constants+'''
pub fn check() {
'''
    if overflow:
        code += '''assert!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1.is_none());
assert!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1.is_none());
assert!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.is_none());
'''
    else:
        code += '''assert_eq!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1,Some(445_136));
assert_eq!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1,Some(1_386_603));
assert_eq!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1,Some(if cfg!(test){1_467_930}else{1_386_603}));
assert_eq!(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1,430_175);
'''
    code += '''}
'''
    if negative:
        code += '''const _:usize=COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1.expect("checked source funding overflow refusal");
'''
    code += '''}
fn main(){
 recipe::check();
 let mut checks=0u64;
 for bits in [32u32,64u32] {
  let limit=(1u128<<bits)-1;
  for base in [0u128,1,300_000,400_000,366_896,limit-78_240,limit-78_239,limit] {
   for host in [false,true] {
    let common=base.checked_add(78_240).filter(|n|*n<=limit);
    let selected=common.and_then(|n|n.checked_add(941_467)).filter(|n|*n<=limit);
    let selected=if host{selected.and_then(|n|n.checked_add(81_327)).filter(|n|*n<=limit)}else{selected};
    let admitted=selected.and_then(|n|n.checked_add(430_175)).filter(|n|*n<=limit);
    let expected=base.checked_add(78_240+941_467+430_175+if host{81_327}else{0}).filter(|n|*n<=limit);
    assert_eq!(admitted,expected);checks+=1;
    if let Some(current)=selected {
     for grant in [0u128,300_000,400_000,current,current+430_174,current+430_175,limit] {
      let before=current;
      let preflight=current.checked_add(430_175).filter(|n|*n<=limit && *n<=grant);
      let after=preflight.unwrap_or(before);
      assert_eq!(after,if current+430_175<=limit && current+430_175<=grant {current+430_175}else{before});
      checks+=1;
     }
    }
   }
  }
 }
 assert!(usize::MAX.checked_add(1).is_none());
 assert!(u64::MAX.checked_add(1).is_none());
 println!("PASS {} scalar phase/overflow/refusal controls; no VM/writer",checks+2);
}
'''
    return code

def main():
    assert len(sys.argv) == 2
    case = sys.argv[1]
    if case == 'metadata-production': run(case)
    elif case == 'metadata-unit': run(case, unit=True)
    elif case == 'scalar-production': run(case, standalone=True)
    elif case == 'scalar-unit': run(case, standalone=True, unit=True)
    elif case == 'scalar-overflow': run(case, standalone=True, overflow=True)
    elif case == 'scalar-overflow-negative': run(case, standalone=True, overflow=True, negative=True)
    else: raise ValueError(case)

if __name__ == '__main__':
    main()
