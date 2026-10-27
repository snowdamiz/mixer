"""One compile-only layout query over the frozen source146 tree; no VM run."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
V = R / 'verification'
COMPILER = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
KEYS = ('MIXER_LOADER_MANIFEST_SHA256', 'MIXER_LOADER_COMMAND_SHA256', 'MIXER_LOADER_COMPILE_ENV_SHA256', 'MIXER_LOADER_COMPILER_SHA256', 'MIXER_LOADER_COMPILER_VERSION_SHA256')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def put(name, obj):
    (D / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def counted(values):
    parts = [v.encode() for v in values]
    assert len(parts) <= 64 and all(len(p) < 4096 and b'\0' not in p for p in parts)
    result = struct.pack('<Q', len(parts)) + b''.join(struct.pack('<Q', len(p)) + p for p in parts)
    assert len(result) <= 16384
    return result


def checked_file(row, path):
    assert not path.is_symlink()
    b = path.read_bytes()
    assert len(b) == row['bytes'] and sha(b) == row['sha256'], str(path)
    return b


def run(label, argv, env, seconds):
    start = time.monotonic()
    p = subprocess.Popen(argv, cwd=R, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timeout = False
    actions = []
    try:
        out, err = p.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timeout = True
        os.killpg(p.pid, signal.SIGKILL)
        actions.append('SIGKILL-owned-command-group-after-timeout')
        out, err = p.communicate()
    try:
        os.killpg(p.pid, 0)
        present = True
    except ProcessLookupError:
        present = False
    if present:
        os.killpg(p.pid, signal.SIGKILL)
        actions.append('SIGKILL-residual-owned-command-group')
        for _ in range(20):
            try:
                os.killpg(p.pid, 0)
                time.sleep(.05)
            except ProcessLookupError:
                present = False
                break
    rec = dict(argv=argv, environment=env, cwd=str(R), timeout_seconds=seconds,
               timed_out=timeout, exit_code=p.returncode, elapsed_seconds=time.monotonic()-start,
               direct_child_pid=p.pid, direct_child_waited=True, owned_group_absent=not present,
               cleanup_actions=actions, global_process_inventory=False, product_runtime=False)
    (D / (label + '.stdout')).write_bytes(out)
    (D / (label + '.stderr')).write_bytes(err)
    rec['outputs'] = {name: dict(bytes=len(data), sha256=sha(data)) for name, data in [('stdout', out), ('stderr', err)]}
    put(label + '-receipt.json', rec)
    assert not timeout and not present
    return out, err, rec


def main():
    # Selection is prepared only after both source roster owners freeze.
    selection = json.loads((D / 'selection.json').read_text())
    for packet in selection['packets']:
        directory = R / packet['path']
        data = (directory / 'seal.json').read_bytes()
        assert sha(data) == packet['seal_sha256']
        for row in json.loads(data)['members']:
            checked_file(row, directory / row['path'])
    q = selection['queries']
    assert q and len({x['concrete'] for x in q}) == len(q)
    assert all(x['concrete'] != 'str' for x in q)
    srcbase = V / 'swift-guarded-snapshot-loader-work-source146'
    manifest = json.loads((srcbase / 'source146-manifest.json').read_text())
    assert manifest['tree_sha256'] == TREE and len(manifest['members']) == 146
    assert sha(canonical(manifest['members'])) == TREE
    refs = json.loads((srcbase / 'source-reference-map.json').read_text())['members']
    assert [(r['path'], r['bytes'], r['sha256']) for r in refs] == [(r['path'], r['bytes'], r['sha256']) for r in manifest['members']]
    sources = {r['path']: checked_file(r, R / r['source']) for r in refs}
    hostmanifest = json.loads((srcbase / 'host11-manifest.json').read_text())
    assert len(hostmanifest['members']) == 11
    assert sha(canonical(hostmanifest['members'])) == hostmanifest['tree_sha256']
    for row in hostmanifest['members']:
        checked_file(row, V / 'swift-real-profile-loader-binding/host' / row['path'])
    fragment = '\n#[cfg(mixer_bootstrap_one_fixture_v1)]\nmod source146_leaf_payload_layout_queries_v1 {\nuse super::*;\n'
    for i, row in enumerate(q):
        for kind in ('size', 'align'):
            fragment += f'const LP_{kind.upper()}_{i}: [(); usize::MAX] = [(); std::mem::{kind}_of::<{row["concrete"]}>()];\n'
    fragment += '}\n'
    (D / 'layout-queries.inc.rs').write_text(fragment)
    original = dict(sources)
    sources[selection['append_to']] += fragment.encode()
    compiled = [dict(path=name, bytes=len(data), sha256=sha(data)) for name, data in sorted(sources.items(), key=lambda p: Path(p[0]))]
    work = D / 'owned-work'
    assert not work.exists() and not (D / 'compiler-receipt.json').exists()
    work.mkdir()
    completed = False
    try:
        vm = work / 'vm'
        for name, data in sources.items():
            dest = vm / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        env = dict(PATH='/usr/bin:/bin', TMPDIR=str(work), CARGO_MANIFEST_DIR=str(vm), RUSTC_BOOTSTRAP='1', SDKROOT='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
        ver, _, version_rec = run('compiler-version', [str(COMPILER), '--version', '--verbose'], env, 10)
        assert version_rec['exit_code'] == 0
        assert sha(ver) == '352d6857968e80a6357a926ac685b9b07f77c479aaafde33e73a53945e802909'
        compiler_sha = sha(COMPILER.read_bytes())
        assert compiler_sha == 'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
        argv = [str(COMPILER), '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin', '-C', 'opt-level=0', '-C', 'overflow-checks=yes', '-C', 'panic=unwind', '-Zmir-opt-level=0', '--error-format=json']
        for feature in ('experimental-swift-reactor', 'experimental-swift-wasi', 'experimental-stream-validation', 'experimental-function-cache'):
            argv += ['--cfg', 'feature="' + feature + '"']
        argv += ['--cfg', 'mixer_bootstrap_one_fixture_v1', '--crate-type', 'rlib', str(vm / 'src/lib.rs'), '--emit=metadata=' + str(work / 'output.rmeta')]
        closure = dict(schema=1, source_manifest=manifest, compiled_source_members=compiled, compiled_tree_sha256=sha(canonical(compiled)), host_support=hostmanifest,
                       query_fragment_sha256=sha(fragment.encode()), selection_sha256=sha((D / 'selection.json').read_bytes()), script_sha256=sha(Path(__file__).read_bytes()), compiler_sha256=compiler_sha, compiler_version_sha256=sha(ver),
                       exact146_production_bodies_unchanged=True, product_runtime=False, expected_result='intentional E0308 constant size/align diagnostic for each query')
        preimages = [canonical(closure), counted(argv), counted([k + '=' + v for k, v in sorted(env.items())])]
        for name, data in zip(('compiled-manifest.json', 'argv.bin', 'environment.bin'), preimages):
            (D / name).write_bytes(data)
        keys = dict(zip(KEYS, [sha(x) for x in preimages] + [compiler_sha, sha(ver)]))
        put('binding.json', dict(source_tree_sha256=TREE, source_members=146, compile_identity_keys=keys, target='aarch64-apple-darwin', python_version=sys.version, query_count=len(q), at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        out, err, rec = run('compiler', argv, env | keys, 60)
        assert rec['exit_code'] == 1 and not out, (rec['exit_code'], out[:100])
        observed = {}
        diagnostics = []
        for line in err.decode().splitlines():
            msg = json.loads(line)
            if msg.get('level') != 'error' or not msg.get('code'):
                continue
            assert msg['code']['code'] == 'E0308', msg.get('rendered')
            rendered = msg['rendered']
            ids = set(re.findall(r'LP_(SIZE|ALIGN)_(\d+)', rendered))
            assert len(ids) == 1, rendered
            kind, i = next(iter(ids)); i = int(i)
            key = (i, kind.lower()); assert key not in observed
            value = int(re.search(r'found one with a size of (\d+)', rendered)[1])
            observed[key] = value
            diagnostics.append(dict(index=i, kind=kind.lower(), value=value, concrete=q[i]['concrete']))
        assert set(observed) == {(i, k) for i in range(len(q)) for k in ('size', 'align')}
        rows = [dict(**row, size=observed[(i, 'size')], alignment=observed[(i, 'align')]) for i, row in enumerate(q)]
        assert all(x['alignment'] > 0 and x['alignment'] & (x['alignment']-1) == 0 and x['size'] % x['alignment'] == 0 for x in rows)
        assert all(sources[k] == v + fragment.encode() if k == selection['append_to'] else sources[k] == v for k,v in original.items())
        assert not (work / 'output.rmeta').exists(), 'Intentionally failed query is not a metadata success.'
        put('results.json', dict(schema=1, source_tree_sha256=TREE, target='aarch64-apple-darwin', compiler_sha256=compiler_sha, queries=rows,
                                expected_E0308_only=True, diagnostic_count=len(diagnostics), diagnostics=diagnostics,
                                scope='Actual source146 concrete size and alignment only; no backing/drop/allocator/CPU/runtime/GA evidence', product_executed=False, metadata_produced=False))
        completed = True
    finally:
        items = [p for p in work.rglob('*') if p.is_file()]
        inventory = [dict(path=str(p.relative_to(work)), bytes=p.stat().st_size, sha256=sha(p.read_bytes())) for p in items]
        # Each owned command is waited and its own process group checked by run().
        receipts = [json.loads(p.read_text()) for p in D.glob('*-receipt.json')]
        reaped = all(r.get('direct_child_waited') and r.get('owned_group_absent') for r in receipts)
        if reaped:
            shutil.rmtree(work)
        put('cleanup.json', dict(completed=completed, command_children_waited_and_groups_absent=reaped, owned_scratch_removed=not work.exists(), removed_files=len(inventory) if reaped else 0,
                                 removed_bytes=sum(r['bytes'] for r in inventory) if reaped else 0, scratch_inventory=inventory, native_or_product_processes_started=False))
    print(json.dumps(dict(status='passed', concrete_layouts=len(q), size_alignment_diagnostics=2*len(q), product_executed=False)))


if __name__ == '__main__':
    main()
