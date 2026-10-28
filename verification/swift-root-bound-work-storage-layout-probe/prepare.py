#!/usr/bin/env python3
"""One source/offline preparation; never invokes a compiler or another child."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import os
import sys

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-root-bound-work-storage-delta'
I = R / 'verification/swift-root-bound-work-storage-delta-independent'
C = R / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation'
TREE = '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def row(path, base=R):
    assert not path.is_symlink(), path
    raw = path.read_bytes()
    return {'path': str(path.relative_to(base)) if path.is_relative_to(base) else str(path), 'bytes': len(raw), 'sha256': sha(raw)}
def put(name, obj):
    with (D / name).open('x') as handle: json.dump(obj, handle, indent=2, sort_keys=True); handle.write('\n')
def once(raw, needle):
    assert raw.count(needle) == 1, needle
    return raw.index(needle)
def loc(raw, start, end):
    def at(n):
        text = raw[:n].decode('utf-8')
        return text.count('\n') + 1, len(text.rsplit('\n', 1)[-1]) + 1
    sl, sc = at(start); el, ec = at(end)
    return {'byte_start': start, 'byte_end': end, 'line_start': sl, 'column_start': sc, 'line_end': el, 'column_end': ec,
            'source_sha256': sha(raw[start:end]), 'source_text': raw[start:end].decode()}


def main():
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    assert not (D / 'plan.json').exists() and not (D / 'source').exists()
    inputs = []
    for directory, expected in [(P, '1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29'),
                                (I, 'addd2beb80ae25174c210563bffc9122cbe655f69420170ad16305eaeef544ec')]:
        assert row(directory / 'seal.json')['sha256'] == expected
        seal = json.loads((directory / 'seal.json').read_text())
        for member in seal['members']:
            assert {k: row(directory / member['path'], directory)[k] for k in ['path', 'bytes', 'sha256']} == member
        inputs.append(row(directory / 'seal.json'))
    acceptance = R / 'verification/swift-semantic-adapter-root-review/root-bound-work-storage-delta-acceptance.json'
    accepted = json.loads(acceptance.read_text())
    assert accepted['candidate_source146_tree'] == TREE and accepted['work_storage_prices_or_layouts_accepted'] is False
    assert row(C / 'seal.json')['sha256'] == '7efe39286257be85d0e91f4bdd80b6098d24d7d2f446dcdc2e8dd7adb0159fa4'
    inputs += [row(acceptance), row(C / 'seal.json'), row(C / 'source-manifest.json'), row(C / 'toolchain.json'), row(P / 'layout-probe-proposal.json')]
    proposal = json.loads((P / 'layout-probe-proposal.json').read_text())
    assert proposal['source_tree'] == TREE and proposal['future_scratch_only'] == str(D)
    manifest = json.loads((C / 'source-manifest.json').read_text())
    assert manifest['member_count'] == len(manifest['members']) == 146
    assert sha(canonical(manifest['members'])) == manifest['tree_sha256'] == TREE
    original = {}
    for member in manifest['members']:
        path = C / 'source/vm' / member['path']
        assert row(path, C / 'source/vm') == member
        original[member['path']] = path.read_bytes()
    scratch = dict(original)
    fragments = []
    for member in proposal['fragments']:
        path = R / member['path']; assert row(path) == member
        fragments.append(path.read_bytes())
        (D / path.name).write_bytes(fragments[-1])
        inputs.append(row(path))
    loader = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    cache = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    markers = [b'    // OWNER_PROBE_INSERTION', b'    // Private outer caller candidate; all prior bodies remain exact.']
    replacement = b'        Ok(reservation.dispatch_v1(|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)))'
    edits = []
    for name, marker, fragment in [(loader, markers[0], fragments[0]), (cache, markers[1], fragments[1])]:
        offset = once(scratch[name], marker)
        inserted = fragment + b'\n'
        edits.append({'file': name, 'kind': 'insert', 'original_byte_start': offset, 'original_byte_end': offset,
                      'before_sha256': sha(b''), 'after_bytes': len(inserted), 'after_sha256': sha(inserted), 'anchor': marker.decode()})
        scratch[name] = scratch[name][:offset] + inserted + scratch[name][offset:]
    offset = once(scratch[cache], replacement)
    new = fragments[2].rstrip(b'\n')
    edits.append({'file': cache, 'kind': 'replace', 'original_byte_start': once(original[cache], replacement),
                  'original_byte_end': once(original[cache], replacement) + len(replacement), 'before_bytes': len(replacement),
                  'before_sha256': sha(replacement), 'after_bytes': len(new), 'after_sha256': sha(new)})
    scratch[cache] = scratch[cache][:offset] + new + scratch[cache][offset+len(replacement):]
    # A reverse replay proves the delta is exactly these three edits.
    reverse = dict(scratch)
    reverse[cache] = reverse[cache].replace(new, replacement, 1)
    for name, fragment in [(loader, fragments[0]), (cache, fragments[1])]:
        reverse[name] = reverse[name].replace(fragment + b'\n', b'', 1)
    assert reverse == original
    assert sorted(name for name in original if original[name] != scratch[name]) == sorted([loader, cache])
    for name, raw in scratch.items():
        dest = D / 'source/vm' / name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
    members = [{'path': item['path'], 'bytes': len(scratch[item['path']]), 'sha256': sha(scratch[item['path']])} for item in manifest['members']]
    # Preserve the accepted manifest's path ordering for its authoritative tree.
    assert [r['path'] for r in members] == [r['path'] for r in manifest['members']]
    diagnostic = {'member_count': 146, 'members': members, 'tree_sha256': sha(canonical(members))}
    put('original-source-manifest.json', manifest)
    put('diagnostic-source-manifest.json', diagnostic)
    put('exact-three-edit-delta.json', {'schema': 1, 'edits': edits, 'edit_count': 3, 'changed_source_members': [loader, cache],
                                      'original_tree': TREE, 'diagnostic_tree': diagnostic['tree_sha256'], 'reverse_replay_exact146': True})
    patch = ''.join(''.join(difflib.unified_diff(original[name].decode().splitlines(True), scratch[name].decode().splitlines(True),
                    fromfile='original/' + name, tofile='diagnostic/' + name)) for name in [loader, cache])
    (D / 'exact-three-edit-delta.patch').write_text(patch)
    queries = []
    for index, query in enumerate(proposal['named_queries']):
        name = loader if query['fragment'].startswith('proposed-owner') else cache
        raw = scratch[name]
        call = ('pair!(' + query['type'] + ')').encode()
        call_start = once(raw, call)
        expressions = {}
        for kind, function in [('size', 'size'), ('alignment', 'align')]:
            needle = ('[0u8; std::mem::' + function + '_of::<$type>()]').encode()
            at = once(raw, needle); expressions[kind] = loc(raw, at, at + len(needle))
        queries.append({'index': index, 'type': query['type'], 'file': str(D / 'source/vm' / name),
                        'invocation': loc(raw, call_start, call_start + len(call)), 'macro_expressions': expressions})
    raw = scratch[cache]
    expression = b'|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)'
    at = once(raw, expression)
    closure = {'file': str(D / 'source/vm' / cache), 'expression': loc(raw, at, at+len(expression)),
               'identity_span': loc(raw, at, at+2), 'queries': {}}
    for kind, needle in [('size', b'std::mem::transmute(uninitialized_shape_v1(&action))'),
                         ('alignment_wrapper', b'std::mem::transmute(ClosureAlignmentProbeV1 {\n                leading: 0u8, actual: uninitialized_shape_v1(&action),\n            })')]:
        at = once(raw, needle); closure['queries'][kind] = loc(raw, at, at+len(needle))
    compiler = Path(proposal['future_compiler']['path'])
    assert row(compiler) == proposal['future_compiler']
    toolroot = compiler.parents[1]
    toolfiles = [compiler] + sorted((toolroot / 'lib').glob('*.dylib')) + sorted((toolroot / 'lib/rustlib/aarch64-apple-darwin/lib').iterdir())
    assert all(p.is_file() and not p.is_symlink() for p in toolfiles)
    toolmanifest = {'root': str(toolroot), 'members': [row(path, toolroot) for path in toolfiles],
                    'scope': 'rustc executable, compiler lib dylibs, and complete direct target sysroot lib directory; no compiler invocation'}
    toolmanifest['tree_sha256'] = sha(canonical(toolmanifest['members']))
    put('toolchain-manifest.json', toolmanifest)
    sdk = Path(proposal['environment']['SDKROOT'])
    sdkfiles = [p for p in [sdk / 'SDKSettings.json', sdk / 'SDKSettings.plist'] if p.is_file()]
    sdkmanifest = {'requested': str(sdk), 'resolved': str(sdk.resolve()), 'settings': [row(p.resolve()) for p in sdkfiles],
                   'scope': 'SDK path/settings only; compiler metadata diagnostic query does not claim SDK implementation qualification'}
    put('sdk-path-settings.json', sdkmanifest)
    toolchain = json.loads((C / 'toolchain.json').read_text())
    assert toolchain['tool'] == proposal['future_compiler'] and toolchain['SDKROOT'] == str(sdk)
    put('toolchain-version-provenance.json', {'retained': toolchain, 'provenance': row(C / 'toolchain.json'),
                                           'version_command_executed_here': False, 'fresh_binary_and_toolchain_hashes': True})
    python = Path(sys.executable).resolve()
    plan = {'schema': 1, 'status': 'PREPARED_FROZEN_AWAITING_ROOT_INTERNAL_COMPILER_RELEASE', 'prepared_at': start,
            'argv': proposal['argv'], 'cwd': proposal['cwd'], 'environment': proposal['environment'],
            'original_source': {'directory': str(C / 'source/vm'), 'manifest': row(D / 'original-source-manifest.json', D), 'tree_sha256': TREE, 'members': manifest['members']},
            'diagnostic_source': diagnostic, 'delta': row(D / 'exact-three-edit-delta.json', D),
            'inputs': inputs, 'compiler': proposal['future_compiler'], 'toolchain_manifest': row(D / 'toolchain-manifest.json', D),
            'sdk_path_settings': row(D / 'sdk-path-settings.json', D), 'toolchain_version': toolchain['version'],
            'python': {'tool': row(python), 'version': sys.version},
            'scripts': [row(D / name, D) for name in ['prepare.py', 'diagnostics.py', 'run.py', 'check.py', 'controls.py']],
            'bounds': {**proposal['bounds'], 'work_seconds': 44, 'cleanup_deadline_seconds': 49, 'posthash_deadline_seconds': 53.5,
                       'maximum_build_artifact_bytes': 16777216, 'maximum_build_members': 64, 'automatic_retries': 0},
            'diagnostics': {'named_queries': queries, 'actual_closure': closure, 'expected_primary_errors': {'E0308': 56, 'E0512': 2},
                            'allowed_summary_messages': [['error', 'aborting due to 58 previous errors'],
                                ['failure-note', 'Some errors have detailed explanations: E0308, E0512.'],
                                ['failure-note', 'For more information about an error, try `rustc --explain E0308`.']],
                            'unexpected_warning_policy': 'retain and reject; no inferred warning allowlist',
                            'strategy_qualified': False, 'concrete_observations': False},
            'root_release_required': {'path': 'verification/swift-semantic-adapter-root-review/root-bound-work-storage-layout-release.json',
                'required_fields': {'plan_sha256': 'exact SHA256 of this plan.json', 'compiler_lane_released': True, 'compiler_invocations': 1}},
            'execution': {'compiler_started': False, 'runtime_started': False, 'version_commands_started': 0},
            'pending': proposal['still_pending'] + ['actual target layouts including closure diagnostic behavior', 'complete ownership and final native/phone/FieldLog/OTA/GA acceptance'],
            'all_price_layout_backing_peak_funding_ownership_GA_authority': False}
    assert len(queries) == len({q['type'] for q in queries}) == 28
    put('plan.json', plan)
    put('preparation-receipt.json', {'schema': 1, 'status': 'source-and-offline-preparation-only', 'python': sys.version,
        'command': [str(python), '-B', str(D / 'prepare.py')], 'plan_sha256': sha((D / 'plan.json').read_bytes()),
        'original_source146_tree': TREE, 'diagnostic_source146_tree': diagnostic['tree_sha256'], 'exact_source_edits': 3,
        'compiler_runtime_native_capture_network_process_inventory_started': False, 'owned_generated_build_artifacts': 0,
        'cleanup': 'No compiler child or build directory started; frozen diagnostic scratch retained for review.'})
    print(json.dumps({'status': 'prepared-not-executed', 'plan_sha256': sha((D / 'plan.json').read_bytes()),
                      'diagnostic_source146_tree': diagnostic['tree_sha256'], 'argv': plan['argv']}))


if __name__ == '__main__': main()
