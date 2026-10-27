#!/usr/bin/env python3
"""Independent, bounded host review. Never executes a producer supervisor."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/swift-canonical-diagnostic-components'
ACCEPTED = ROOT / 'verification/swift-typed-result-codec-implementation'
TOOLS = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin')
SOURCE = OUT / 'source'
SCRATCH = OUT / 'owned'
EXPECTED_TREE = 'a88d7b81ad7618b40951428c28b12b3b6fec3f1acf5e1875e0b02d9727cef16f'
EXPECTED_SEAL = '3dc5fb0f142d214a31e2d9627296081b5540c9d0768942cd671baeff20c2761a'
EXPECTED_RELEASE = '6ee3a84efa18e7c47fb7626537e139b07f434eb6651745e42152ee3fcefead1f'

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')

def member(base, rel):
    p = base / rel
    assert p.is_file() and not p.is_symlink(), p
    data = p.read_bytes()
    return {'path': rel, 'bytes': len(data), 'sha256': sha(data)}

def manifest(base, rows):
    actual = [member(base, r['path']) for r in rows]
    return {'schema': 1, 'members': actual,
            'tree_sha256': sha(json.dumps(actual, sort_keys=True, separators=(',', ':')).encode())}

def setup():
    assert not SOURCE.exists(), 'Refuse to overwrite an existing source freeze'
    release_path = ROOT / 'verification/swift-semantic-adapter-root-review/canonical-diagnostic-components-independent-release.json'
    assert sha(release_path.read_bytes()) == EXPECTED_RELEASE
    seal_bytes = (PRODUCER / 'seal.json').read_bytes()
    assert sha(seal_bytes) == EXPECTED_SEAL
    seal = json.loads(seal_bytes)
    actual_packet = [member(PRODUCER, r['path']) for r in seal['members']]
    assert actual_packet == seal['members']
    assert len(actual_packet) == seal['member_count'] == 92
    assert sum(r['bytes'] for r in actual_packet) == seal['member_bytes'] == 300960
    assert sha(json.dumps(actual_packet, sort_keys=True, separators=(',', ':')).encode()) == seal['tree_sha256']
    input_manifest = json.loads((PRODUCER / 'source-manifest.json').read_bytes())
    before = manifest(ROOT, input_manifest['members'])
    assert before['members'] == input_manifest['members']
    assert before['tree_sha256'] == EXPECTED_TREE
    assert len(before['members']) == 136
    for row in before['members']:
        dest = SOURCE / row['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / row['path']).read_bytes())
        dest.chmod(0o444)
    frozen = manifest(SOURCE, before['members'])
    assert frozen == before
    write(OUT / 'canonical-preimage.json', before)
    write(OUT / 'source-manifest.json', frozen)
    (OUT / 'inputs').mkdir(exist_ok=True)
    for path in [release_path, ROOT / 'AGENTS.md', PRODUCER / 'seal.json',
                 PRODUCER / 'source-attribution.json', PRODUCER / 'clippy-repair.json']:
        (OUT / 'inputs' / path.name).write_bytes(path.read_bytes())
    attribution = json.loads((PRODUCER / 'canonical-owned-source-roster.json').read_bytes())
    deltas = []
    for row in attribution['files']:
        rel = row['path']
        current = (SOURCE / rel).read_bytes()
        assert member(SOURCE, rel) == {k:row[k] for k in ('path','bytes','sha256')}
        assert current == (PRODUCER / 'canonical' / rel).read_bytes()
        if 'accepted_source' in row:
            accepted = row['accepted_source']
            previous = (ROOT / accepted['path']).read_bytes()
            assert len(previous) == accepted['bytes'] and sha(previous) == accepted['sha256']
            diff = ''.join(difflib.unified_diff(previous.decode().splitlines(keepends=True),
                                              current.decode().splitlines(keepends=True),
                                              fromfile=accepted['path'], tofile=rel))
            (OUT / 'deltas' / Path(rel).name).parent.mkdir(exist_ok=True)
            (OUT / 'deltas' / (Path(rel).name + '.patch')).write_text(diff)
            if rel.endswith('/diagnostic_result_v1.rs'):
                assert previous.replace(b'output.chunks_exact_mut(8).zip(words)',
                                        b'output.as_chunks_mut::<8>().0.iter_mut().zip(words)') == current
            if rel.endswith('/diagnostic_result_v1_tests.rs') or rel.endswith('/diagnostic_profile.rs'):
                assert previous == current
            deltas.append({'path':rel, 'accepted':accepted, 'current':member(SOURCE,rel),
                           'identical':previous == current})
        else:
            suffix = b'\n// Private finite diagnostic row helper; no runtime or publication route.\n#[deny(warnings)]\nmod diagnostic_profile;\n\n// Pure unverified typed-result data; no owner authority or public export.\nmod diagnostic_result_v1;\n'
            assert current.endswith(suffix)
            original_module = current[:-len(suffix)]
            assert len(original_module) == 639
            assert sha(original_module) == 'c7a99b4644a9cde508fcaef8a32fd81c825ab5084251e11b7a78bc6a76bd27b3'
            (OUT / 'deltas' / 'mod.rs.before').write_bytes(original_module)
            (OUT / 'deltas' / 'mod.rs.patch').write_text(''.join(difflib.unified_diff(
                original_module.decode().splitlines(keepends=True), current.decode().splitlines(keepends=True),
                fromfile='canonical-base/mod.rs', tofile=rel)))
            deltas.append({'path':rel, 'reconstructed_before_bytes':len(original_module),
                           'reconstructed_before_sha256':sha(original_module), 'current':member(SOURCE,rel)})
    write(OUT / 'source-custody.json', {'schema':1,'at':now(), 'root_release_sha256':EXPECTED_RELEASE,
          'producer_seal_sha256':EXPECTED_SEAL, 'producer_members_verified':92,'producer_bytes_verified':300960,
          'base_revision_attributed_by_root':'5b80a99aca2bee400786a71f033cc0fd928de89d',
          'source_members_verified':136, 'source_tree_sha256':EXPECTED_TREE,
          'immutable_compilation_copy':str(SOURCE), 'accepted_source_comparisons':deltas,
          'git_read_or_write':False, 'producer_runner_replayed':False})
    print(json.dumps({'setup':'pass','source_members':136,'tree':EXPECTED_TREE}), flush=True)

def known_group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False

def run(name, argv, seconds=600, expected=0):
    dest = OUT / 'commands' / name
    assert not dest.exists(), f'Refuse to overwrite command {name}'
    dest.mkdir(parents=True)
    temporary = SCRATCH / 'tmp' / name
    temporary.mkdir(parents=True)
    (SCRATCH / 'cargo-home').mkdir(exist_ok=True)
    env = {'PATH':f'{TOOLS}:/usr/bin:/bin:/usr/sbin:/sbin',
           'CARGO':str(TOOLS/'cargo'), 'RUSTC':str(TOOLS/'rustc'), 'RUSTDOC':str(TOOLS/'rustdoc'),
           'CARGO_HOME':str(SCRATCH/'cargo-home'), 'CARGO_TARGET_DIR':str(SCRATCH/'target'),
           'CARGO_BUILD_JOBS':'2','CARGO_NET_OFFLINE':'true','TMPDIR':str(temporary),
           'LC_ALL':'C','LANG':'C'}
    for key in ('HOME','DEVELOPER_DIR','SDKROOT'):
        if key in os.environ:
            env[key] = os.environ[key]
    pre = {'schema':1,'name':name,'at':now(),'argv':argv,'cwd':str(SOURCE/'vm'),
           'environment':env,'expected_exit':expected, 'deadline_seconds':seconds,
           'source_tree_sha256':EXPECTED_TREE, 'source_manifest':str(OUT/'source-manifest.json'),
           'source_manifest_sha256':sha((OUT/'source-manifest.json').read_bytes()),
           'TMPDIR_initial_entries':list(temporary.iterdir())}
    write(dest/'preimage.json', pre)
    start = time.monotonic()
    timed_out = False
    group_actions = []
    with (dest/'stdout').open('wb') as stdout, (dest/'stderr').open('wb') as stderr:
        child = subprocess.Popen(argv,cwd=SOURCE/'vm',env=env,stdout=stdout,stderr=stderr,start_new_session=True)
        write(dest/'launch.json',{'pid':child.pid, 'pgid':child.pid,'at':now()})
        try:
            status = child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid,signal.SIGTERM)
            group_actions.append('SIGTERM to known owned session group')
            try:
                status = child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL)
                group_actions.append('SIGKILL to known owned session group')
                status = child.wait(timeout=5)
    group_before_cleanup = known_group_exists(child.pid)
    if group_before_cleanup:
        os.killpg(child.pid,signal.SIGTERM)
        group_actions.append('SIGTERM to remaining known owned session group')
        for _ in range(50):
            if not known_group_exists(child.pid):
                break
            time.sleep(0.1)
        if known_group_exists(child.pid):
            os.killpg(child.pid,signal.SIGKILL)
            group_actions.append('SIGKILL to remaining known owned session group')
    group_after_cleanup = known_group_exists(child.pid)
    contents = [member(temporary,str(p.relative_to(temporary))) for p in sorted(temporary.rglob('*')) if p.is_file()]
    entries = [p.name for p in sorted(temporary.iterdir())]
    leftovers = []
    # Existing cache privacy unit method retains this exact temp fixture; remove
    # only this supervised command's owned directory, after its group is absent.
    if not group_after_cleanup:
        for p in sorted(temporary.iterdir()):
            assert not p.is_symlink(), f'Unanticipated TMPDIR symlink: {p}'
            if re.fullmatch(r'mixer-cache-privacy-\d+-(debug|release)',p.name) and p.is_dir():
                leftovers.append(str(p))
                shutil.rmtree(p)
    remaining = [p.name for p in sorted(temporary.iterdir())]
    receipt = {**pre,'finished_at':now(),'pid':child.pid,'pgid':child.pid,'exit_code':status,
               'elapsed_seconds':round(time.monotonic()-start,3),'timed_out':timed_out,
               'expected_exit_observed':status==expected and not timed_out,
               'direct_child_reaped':child.poll() is not None,
               'owned_group_observed_after_direct_child':group_before_cleanup,
               'owned_group_cleanup_actions':group_actions,'owned_group_absent':not group_after_cleanup,
               'TMPDIR_entries_before_supervisor_cleanup':entries,'TMPDIR_file_manifest':contents,
               'known_inherited_privacy_fixture_removed':leftovers,'TMPDIR_final_entries':remaining,
               'stdout':member(dest,'stdout'),'stderr':member(dest,'stderr')}
    write(dest/'receipt.json',receipt)
    print(json.dumps({'command':name,'exit':status,'expected':expected,'elapsed':receipt['elapsed_seconds'],
                      'TMPDIR_initial_leftovers':entries,'TMPDIR_final':remaining,'owned_group_absent':not group_after_cleanup}),flush=True)
    assert status == expected and not timed_out and not group_after_cleanup and not remaining, name
    return receipt

def tests():
    run('rustc-version',[str(TOOLS/'rustc'),'--version','--verbose'],30)
    run('cargo-version',[str(TOOLS/'cargo'),'--version','--verbose'],30)
    run('python-version',[sys.executable,'--version'],30)
    common=[str(TOOLS/'cargo'),'test','--offline','--locked','--manifest-path',str(SOURCE/'vm/Cargo.toml'),
            '--lib','--features','experimental-swift-reactor']
    run('debug-full-reactor-library',common+['--','--test-threads=1'])
    run('release-full-reactor-library',common+['--release','--','--test-threads=1'])

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=['setup','tests'])
    args=parser.parse_args()
    if args.operation=='setup':
        setup()
    elif args.operation=='tests':
        tests()
