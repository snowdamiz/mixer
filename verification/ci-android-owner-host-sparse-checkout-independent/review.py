#!/usr/bin/env python3
"""Independent finite, offline source-coverage review; executes only Git reads."""
import ast
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/ci-android-owner-host-sparse-checkout'
REV = 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
TREE = '076842155358f5be57a6f97af73577687a32a6d4'
MANIFEST_SHA = '27c7a3c226cc1b38fa835f59ce4d7ef12753f05bbd416a17463814b9b45a889f'
WORKFLOW_SHA = 'fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88'
DELTA_SHA = 'a475d9cb12c1dd9f230f4075d9afb924596ef86ddd838330326d8a0f827e4f14'
WORKFLOW = '.github/workflows/verify.yml'
PRIVATE = 'native/android/tests/run-private-owner-host.py'
ENVIRONMENT = 'native/android/tests/run-environment-platform-host.py'
DATA = (
    'verification/android-private-owner-effect-roster-amendment/required-host-roster.json',
    'verification/android-private-owner-integration-implementation/barrier-map.json',
    'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
    'verification/android-environment-platform-root-review/selection.json',
)
COMMANDS = []
GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')


def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def git(*args, stdin=None):
    argv = ['git', *args]
    result = subprocess.run(argv, cwd=ROOT, env=GIT_ENV, input=stdin,
                            capture_output=True, timeout=55, check=False)
    COMMANDS.append({'argv': argv, 'cwd': str(ROOT), 'timeout_seconds': 55,
                     'environment_overrides': {'GIT_OPTIONAL_LOCKS': '0', 'GIT_NO_LAZY_FETCH': '1'},
                     'stdin': None if stdin is None else ident(stdin),
                     'stdout': ident(result.stdout), 'stderr': ident(result.stderr),
                     'stderr_text': result.stderr.decode(errors='replace'),
                     'exit': result.returncode})
    if result.returncode:
        raise RuntimeError(str(argv) + ': ' + result.stderr.decode(errors='replace'))
    return result.stdout


def finite(node, scope):
    """Interpret only finite source-list syntax, never runner code or imports."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return scope[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [finite(n, scope) for n in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return finite(node.left, scope) + finite(node.right, scope)
    if isinstance(node, ast.Subscript):
        return finite(node.value, scope)[finite(node.slice, scope)]
    if isinstance(node, ast.ListComp):
        assert len(node.generators) == 1
        generator = node.generators[0]
        assert isinstance(generator.target, ast.Name) and not generator.ifs and not generator.is_async
        return [finite(node.elt, dict(scope, **{generator.target.id: value}))
                for value in finite(generator.iter, scope)]
    raise AssertionError('Unreviewed finite source syntax: ' + ast.dump(node))


def source_assignment(statements):
    nodes = [n for n in statements if isinstance(n, ast.Assign)
             and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id == 'sources']
    assert len(nodes) == 1
    return nodes[0]


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest_data = (PRODUCER / 'manifest.json').read_bytes()
    assert ident(manifest_data)['sha256'] == MANIFEST_SHA
    manifest = json.loads(manifest_data)
    for name, expected in manifest['members'].items():
        assert ident((PRODUCER / name).read_bytes()) == expected, name

    version = git('--version').decode().strip()
    observed_head = git('rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines()
    assert git('rev-parse', REV + '^{tree}').decode().strip() == TREE
    before = git('show', REV + ':' + WORKFLOW)
    after = (ROOT / WORKFLOW).read_bytes()
    assert ident(after)['sha256'] == WORKFLOW_SHA
    pattern_data = ('/native/android/\n' + ''.join('/' + p + '\n' for p in DATA)).encode()
    assert (PRODUCER / 'patterns.txt').read_bytes() == pattern_data
    marker = b'  android-owner-host:\n    runs-on: ubuntu-24.04\n    timeout-minutes: 15\n    steps:\n      - uses: actions/checkout@v4\n'
    addition = (b'        with:\n'
                b'          # Host closures use Android sources and these four canonical data inputs.\n'
                b'          sparse-checkout-cone-mode: false\n'
                b'          sparse-checkout: |\n' +
                b''.join(b'            ' + p + b'\n' for p in pattern_data.splitlines()))
    assert before.count(marker) == 1 and after == before.replace(marker, marker + addition, 1)
    assert b'fetch-depth' not in addition
    delta = ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                       fromfile='a/' + WORKFLOW, tofile='b/' + WORKFLOW)).encode()
    assert delta == (PRODUCER / 'workflow.diff').read_bytes()
    assert ident(delta)['sha256'] == DELTA_SHA

    listing = git('ls-tree', '-r', '-l', '-z', REV, '--', 'native/android', *DATA)
    canonical = {}
    for row in listing.split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, kind, oid, size = meta.decode().split()
        assert kind == 'blob' and mode in ('100644', '100755')
        canonical[name.decode()] = {'mode': mode, 'type': kind, 'git_blob': oid, 'bytes': int(size)}
    selected = sorted(canonical)
    assert len(selected) == 304 and sum(v['bytes'] for v in canonical.values()) == 2_108_263
    assert all(p.startswith('native/android/') or p in DATA for p in selected)
    assert set(DATA) <= set(selected)
    negative_paths = [
        'native/android-other/file.java', 'native/ios/file.swift', '.github/workflows/verify.yml',
        'verification/android-private-owner-effect-roster-amendment/receipt.json',
        'verification/android-private-owner-integration-implementation/receipt.json',
        'verification/ui-measured-appearance-v2-contract/receipt.json',
        'verification/android-environment-platform-root-review/receipt.json',
        'verification/android-environment-platform-root-review/selection.json.bak',
    ]
    checked = git('sparse-checkout', 'check-rules', '--no-cone', '--rules-file',
                  str(PRODUCER / 'patterns.txt'), '-z',
                  stdin=b''.join(p.encode() + b'\0' for p in selected + negative_paths))
    assert sorted(p.decode() for p in checked.split(b'\0') if p) == selected

    batch = git('cat-file', '--batch', stdin=''.join(canonical[p]['git_blob'] + '\n' for p in selected).encode())
    content = {}
    cursor = 0
    for p in selected:
        end = batch.index(b'\n', cursor)
        oid, kind, size = batch[cursor:end].decode().split()
        cursor = end + 1
        value = batch[cursor:cursor + int(size)]
        cursor += int(size)
        assert batch[cursor:cursor + 1] == b'\n'
        cursor += 1
        assert oid == canonical[p]['git_blob'] and kind == 'blob' and len(value) == canonical[p]['bytes']
        assert hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() == oid
        canonical[p]['sha256'] = ident(value)['sha256']
        content[p] = value
    assert cursor == len(batch)
    assert canonical == json.loads((PRODUCER / 'retained-files.json').read_bytes())
    local_mismatches = [p for p in selected if (ROOT / p).is_symlink() or (ROOT / p).read_bytes() != content[p]]
    assert not local_mismatches, local_mismatches

    roster = json.loads(content[DATA[0]])
    private_ast = ast.parse(content[PRIVATE])
    private_main = next(n for n in private_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    private_sources = source_assignment(private_main.body)
    closures = {name: finite(private_sources.value, {'closure': value})
                for name, value in roster['closures'].items()}
    env_ast = ast.parse(content[ENVIRONMENT])
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in env_ast.body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id in ('ENV', 'PLATFORM', 'LEAF', 'LEAVES')}
    env_main = next(n for n in env_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    default_if = next(n for n in env_main.body if isinstance(n, ast.If)
                      and ast.unparse(n.test) == "a.closure == 'environment'")
    environment_sources = source_assignment(default_if.body)
    closures['environment-default'] = finite(environment_sources.value, constants)
    for name, paths in closures.items():
        assert len(paths) == len(set(paths)) and set(paths) <= set(selected)
    assert {k: len(v) for k, v in closures.items()} == {
        'A-orchestration': 87, 'B-concrete-renderer-views': 90, 'environment-default': 34}
    java = sorted(set(p for paths in closures.values() for p in paths))
    required = sorted(set(java + [PRIVATE, ENVIRONMENT] + list(DATA)))
    producer_closure = json.loads((PRODUCER / 'required-closure.json').read_bytes())
    assert closures == producer_closure['java_sources_by_invocation']
    assert required == producer_closure['required_files']
    assert len(java) == 193 and len(required) == 199 and set(required) <= set(selected)

    tokens = ('java.io.', 'java.nio.file.', 'Files.', 'Path.of', 'Paths.', 'FileInputStream',
              'FileOutputStream', 'RandomAccessFile', 'ProcessBuilder', 'Runtime.getRuntime',
              'System.getenv', 'System.getProperty', 'java.net.', 'getResourceAsStream',
              'getAssets()', 'assets.put(', 'Class.forName', 'loadLibrary')
    io_review = {p: [{'line': i, 'text': line} for i, line in enumerate(content[p].decode().splitlines(), 1)
                    if any(token in line for token in tokens)] for p in java}
    io_review = {p: sites for p, sites in io_review.items() if sites}
    save('source-review.json', {
        'derived_source_assignment_lines': {PRIVATE: private_sources.lineno, ENVIRONMENT: environment_sources.lineno},
        'closures': {name: {'count': len(paths), 'paths': paths} for name, paths in closures.items()},
        'required_files': required, 'unique_java_sources': len(java), 'java_io_review_sites': io_review,
        'canonical_inputs': {p: canonical[p] for p in DATA},
        'selected_canonical_manifest': ident(json.dumps(canonical, sort_keys=True).encode()),
        'selected_local_content_matches_canonical': not local_mismatches,
        'negative_sparse_rule_paths_excluded': negative_paths,
    })
    assert (ROOT / WORKFLOW).read_bytes() == after
    assert (PRODUCER / 'manifest.json').read_bytes() == manifest_data
    for name, expected in manifest['members'].items():
        assert ident((PRODUCER / name).read_bytes()) == expected
    save('commands.json', COMMANDS)
    save('receipt.json', {
        'schema': 1, 'at': started, 'status': 'passed-independent-offline-checkout-coverage-only',
        'command': 'python3 -B verification/ci-android-owner-host-sparse-checkout-independent/review.py',
        'tools': {'python': sys.version, 'git': version, 'platform': platform.platform()},
        'source_revision': REV, 'source_git_tree': TREE,
        'observed_head': observed_head[0], 'observed_head_tree': observed_head[1],
        'producer_manifest': ident(manifest_data), 'producer_members_verified': len(manifest['members']),
        'workflow_before': ident(before), 'workflow_after': ident(after), 'workflow_delta': ident(delta),
        'only_change_is_android_owner_checkout_with_block': True,
        'other_workflow_bytes_pins_commands_limits_triggers_and_default_fetch_depth_unchanged': True,
        'finite_canonical_git_listing': ident(listing), 'selected_files': len(selected),
        'selected_bytes': sum(v['bytes'] for v in canonical.values()),
        'closure_counts': {name: len(paths) for name, paths in closures.items()},
        'unique_java_sources': len(java), 'required_files_covered': len(required),
        'producer_packet_and_candidate_unchanged_through_checks': True,
        'verification_script': ident(Path(__file__).read_bytes()),
        'not_run': ['compiler/JVM/CI/product tests', 'native runtime/UI/capture', 'global process inventories',
                    'stopped Android candidate5 replay', 'checkout/materialization/worktree/index/config/network operations'],
        'cleanup': {'scratch_created': False, 'worktrees_indexes_or_config_changed': False,
                    'native_capture_or_other_project_processes_started_or_queried': False},
        'pending': ['GitHub actions/checkout v4 integration with sparse inputs and subsequent existing JVM job result'],
        'qualification': 'Checkout input coverage only; prior base CI does not validate candidate workflow. No runtime, device, OTA, signing, store, operation, immutable FieldLog or GA qualification.',
    })
    output = ('PASS independent offline review: exact checkout-only delta; '
              '304 canonical files / 2108263 bytes; 199 required inputs covered; '
              'no scratch or runtime processes.\n')
    (OUT / 'stdout.txt').write_text(output)
    print(output, end='')


if __name__ == '__main__':
    main()
