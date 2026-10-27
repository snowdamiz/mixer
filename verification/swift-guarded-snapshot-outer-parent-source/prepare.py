#!/usr/bin/env python3
"""Compose source data only; no compiler, fixture, product or process calls."""
import difflib
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / 'verification/swift-guarded-snapshot-host-composition'
BASE = ROOT / 'verification/swift-guarded-snapshot-funding-implementation/source/vm'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
BASE_TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def row(path, data): return dict(path=path, bytes=len(data), sha256=sha(data))
def write(path, obj):
    (HERE/path).write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')
def source_data():
    manifest = json.loads((FROZEN/'source-manifest.json').read_bytes())
    assert len(manifest['members']) == 146
    assert sha(canonical(manifest['members'])) == BASE_TREE
    source, custody = {}, []
    for member in manifest['members']:
        name = member['path']
        overlay = FROZEN/'overlay/vm'/name
        origin = overlay if overlay.is_file() else BASE/name
        data = origin.read_bytes()
        assert row(name, data) == member, origin
        source[name] = data
        custody.append(dict(origin=str(origin.relative_to(ROOT)), **member))
    old = source[PROFILE]
    assert old.endswith(b'\n}\n')
    snippet = (HERE/'outer-parent.inc.rs').read_bytes()
    assert snippet.startswith(b'// Source candidate only.')
    added = b'\n\n    // Private outer caller candidate; all prior bodies remain exact.\n'+snippet
    source[PROFILE] = old[:-2]+added+b'}\n'
    assert source[PROFILE].removesuffix(added+b'}\n')+b'}\n' == old
    members = [row(n, source[n]) for n in sorted(source, key=Path)]
    new = dict(schema=1, member_count=len(members), members=members,
               tree_sha256=sha(canonical(members)))
    return source, new, custody, old

def main():
    source, manifest, custody, old = source_data()
    target = HERE/'overlay/vm'/PROFILE
    patch = ''.join(difflib.unified_diff(old.decode().splitlines(True),
        source[PROFILE].decode().splitlines(True),
        fromfile='frozen146/vm/'+PROFILE, tofile='outer-candidate146/vm/'+PROFILE))
    receipt_path = HERE/'commands/compiler-only-query/receipt.json'
    compiler_receipt = json.loads(receipt_path.read_bytes()) if receipt_path.exists() else None
    candidate = dict(schema=1, status='private-outer-source-candidate-pending-terminal-compiler-status-and-independent-review',
        source_members=146, old_source_tree_sha256=BASE_TREE,
        new_source_tree_sha256=manifest['tree_sha256'],
        changed_source_members=[dict(path=PROFILE, old=row(PROFILE, old), new=row(PROFILE, source[PROFILE]))],
        exact_unchanged_source_members=145, existing_body_bytes_preserved=True,
        delta='inline private outer module only; no old declaration/body bytes changed',
        source_work_occurrences=dict(I_max=1, U_max=3, binding_pending_I=0,
            binding_pending_U=0, account_refusal_I=0, account_refusal_U=0,
            entry_refusal_I=0, entry_refusal_U=2,
            returned_I=1, returned_U=3),
        inherited_P0_account_surface_max=2628088+194231+1039*3,
        inherited_component_only=True, new_outer_work_and_storage_priced=False,
        complete_whole_host_quote=False,
        compiler_invocations=compiler_receipt['compiler_invocations'] if compiler_receipt else 0,
        compiler_terminal_success_claim=False,
        compiler_evidence='emitted MIR/metadata and layout observations; receipt-writer failure lost exit/PID/elapsed' if compiler_receipt else 'pending',
        rust_unit_tests='written-not-compiled-or-run under production-only query',
        actual_binding_or_build_session_executable_identity=False,
        policy_quote_binding_selectors_pending=True,
        fixture_runtime=False, healthy_file_close_or_cleanup=False,
        native_UI_capture=False, OTA_FieldLog_GA=False)
    if '--check-only' in sys.argv:
        assert target.read_bytes() == source[PROFILE]
        assert (HERE/'source-delta.patch').read_text() == patch
        assert json.loads((HERE/'source-manifest.json').read_bytes()) == manifest
        assert json.loads((HERE/'source-custody.json').read_bytes()) == custody
        assert json.loads((HERE/'candidate.json').read_bytes()) == candidate
    else:
        assert not (HERE/'seal.json').exists(), 'sealed candidate is immutable'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source[PROFILE])
        (HERE/'source-delta.patch').write_text(patch)
        write('source-manifest.json', manifest)
        write('source-custody.json', custody)
        write('candidate.json', candidate)
    print(json.dumps(dict(passed=True, source_members=146, old_tree=BASE_TREE,
        new_tree=manifest['tree_sha256'], inherited_account_component_only=2825436,
        compiler_invocations=candidate['compiler_invocations'], actual_runtime=False)))

if __name__ == '__main__': main()
