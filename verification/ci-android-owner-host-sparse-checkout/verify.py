#!/usr/bin/env python3
"""Offline checkout coverage only; never imports or executes product/test runners."""
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
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REV = 'ee9f6dc77f88259e2b143fc81dc1085b34a4a943'
WORKFLOW = '.github/workflows/verify.yml'
BASE_WORKFLOW_SHA256 = '80d09b839d91a8be0a50bb19fc84b63b421193af26e1b2a95aa668f98b7a4680'
ROSTER = 'verification/android-private-owner-effect-roster-amendment/required-host-roster.json'
BARRIERS = 'verification/android-private-owner-integration-implementation/barrier-map.json'
DESCRIPTOR = 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
SELECTION = 'verification/android-environment-platform-root-review/selection.json'
PRIVATE = 'native/android/tests/run-private-owner-host.py'
ENVIRONMENT = 'native/android/tests/run-environment-platform-host.py'
PLATFORM = 'native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'
DATA = (ROSTER, BARRIERS, DESCRIPTOR, SELECTION)
PATTERNS = ('/native/android/',) + tuple('/' + p for p in DATA)
LIMIT = 40_000_000
COMMANDS = []
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')


def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def git(*args, stdin=None):
    argv = ['git', *args]
    result = subprocess.run(argv, input=stdin, cwd=ROOT, env=ENV,
                            capture_output=True, timeout=60, check=False)
    COMMANDS.append({'argv': argv, 'cwd': str(ROOT), 'environment_overrides':
                     {'GIT_OPTIONAL_LOCKS': '0', 'GIT_NO_LAZY_FETCH': '1'},
                     'stdin': ident(stdin) if stdin is not None else None,
                     'exit': result.returncode, 'stdout': ident(result.stdout),
                     'stderr': ident(result.stderr),
                     'stderr_text': result.stderr.decode(errors='replace')})
    if result.returncode:
        raise RuntimeError(str(argv) + ': ' + result.stderr.decode(errors='replace'))
    return result.stdout


def blob(path):
    return git('show', REV + ':' + path)


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    git_version = git('--version').decode().strip()
    tree = git('rev-parse', REV + '^{tree}').decode().strip()
    before = blob(WORKFLOW)
    assert ident(before)['sha256'] == BASE_WORKFLOW_SHA256
    addition = ('        with:\n'
                '          # Host closures use Android sources and these four canonical data inputs.\n'
                '          sparse-checkout-cone-mode: false\n'
                '          sparse-checkout: |\n' +
                ''.join('            ' + p + '\n' for p in PATTERNS)).encode()
    marker = (b'  android-owner-host:\n    runs-on: ubuntu-24.04\n'
              b'    timeout-minutes: 15\n    steps:\n'
              b'      - uses: actions/checkout@v4\n')
    assert before.count(marker) == 1
    expected = before.replace(marker, marker + addition, 1)
    after = (ROOT / WORKFLOW).read_bytes()
    assert after == expected, 'Change exceeds the owned checkout with block'
    assert b'fetch-depth' not in addition
    diff = ''.join(difflib.unified_diff(before.decode().splitlines(True),
                   after.decode().splitlines(True), fromfile='a/' + WORKFLOW,
                   tofile='b/' + WORKFLOW))
    (OUT / 'workflow.diff').write_text(diff)
    (OUT / 'patterns.txt').write_text('\n'.join(PATTERNS) + '\n')

    # Metadata inventory reads no excluded file contents. Git itself evaluates
    # every canonical tracked path against the exact non-cone patterns.
    listing = git('ls-tree', '-r', '-l', '-z', REV)
    entries = {}
    for row in listing.split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        mode, kind, oid, size = meta.decode().split()
        entries[path.decode()] = {'mode': mode, 'type': kind, 'git_blob': oid,
                                 'bytes': int(size) if size != '-' else 0}
    path_input = b''.join(p.encode() + b'\0' for p in entries)
    selected_raw = git('sparse-checkout', 'check-rules', '--no-cone',
                       '--rules-file', str(OUT / 'patterns.txt'), '-z', stdin=path_input)
    selected = sorted(p.decode() for p in selected_raw.split(b'\0') if p)
    wanted = sorted(p for p in entries if p.startswith('native/android/') or p in DATA)
    assert selected == wanted
    assert set(DATA) <= set(selected)
    assert all(entries[p]['type'] == 'blob' and entries[p]['mode'] in
               ('100644', '100755') for p in selected)
    retained_bytes = sum(entries[p]['bytes'] for p in selected)
    assert retained_bytes < LIMIT, 'Refuse oversized canonical materialization'

    # Only selected local blobs are read. No checkout/worktree/index mutation,
    # repository config change, history fetch or execution of their contents.
    batch = git('cat-file', '--batch', stdin=''.join(entries[p]['git_blob'] + '\n'
                                                  for p in selected).encode())
    content = {}
    cursor = 0
    for p in selected:
        end = batch.index(b'\n', cursor)
        oid, kind, size = batch[cursor:end].decode().split()
        cursor = end + 1
        data = batch[cursor:cursor + int(size)]
        cursor += int(size)
        assert batch[cursor:cursor + 1] == b'\n'
        cursor += 1
        assert oid == entries[p]['git_blob'] and kind == 'blob'
        assert len(data) == entries[p]['bytes']
        content[p] = data
    assert cursor == len(batch)
    manifest = {p: dict(entries[p], sha256=ident(content[p])['sha256']) for p in selected}
    save('retained-files.json', manifest)

    roster = json.loads(content[ROSTER])
    closures = {}
    for name, closure in roster['closures'].items():
        sources = (closure['actual_production_sources'] + [PLATFORM] +
                   [s['source'] for s in closure['substitutes']] +
                   closure['test_support_sources'] + [closure['test_source']])
        assert len(sources) == len(set(sources))
        closures[name] = sources
    env_tree = ast.parse(content[ENVIRONMENT])
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in env_tree.body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id in ('ENV', 'PLATFORM', 'LEAF', 'LEAVES')}
    env_sources = ([constants['ENV'], constants['PLATFORM']] +
                   ['native/android/app/src/dev/mixer/android/' + n + '.java' for n in
                    ('AppearanceDescriptorV2', 'AppearanceResolverV2', 'AppearanceGeometryV2', 'Json', 'UiPacket')] +
                   [constants['LEAF'] + s for s in constants['LEAVES']] +
                   ['native/android/tests/NativeEnvironmentV2ObserverHostTests.java',
                    'native/android/tests/NativeEnvironmentPlatformV2HostTests.java'])
    closures['environment-default'] = env_sources
    java_sources = sorted(set(p for sources in closures.values() for p in sources))
    required = sorted(set(java_sources + [PRIVATE, ENVIRONMENT] + list(DATA)))
    assert set(required) <= set(selected)
    assert all(p.startswith('native/android/') for p in java_sources)
    save('required-closure.json', {'source_revision': REV, 'java_sources_by_invocation': closures,
          'unique_java_sources': len(java_sources), 'required_files': required,
          'required_file_count': len(required), 'missing_from_git_selected_paths': []})

    # Reviewed file I/O sites: A reads argv[0]; B reads argv[0] and argv[2].
    # Both write only supplied evidence paths. Environment tests read no files.
    # InstalledAppearanceV2's asset stream is supplied by in-memory host leaves.
    needles = ('Files.', 'Path.of', 'Paths.', 'java.io.', 'FileInputStream',
               'FileOutputStream', 'new File(', 'ProcessBuilder', 'Runtime.getRuntime',
               'getResourceAsStream', 'System.getProperty', 'System.getenv')
    java_io = {p: [{'line': i, 'text': line} for i, line in
                   enumerate(content[p].decode().splitlines(), 1)
                   if any(token in line for token in needles)] for p in java_sources}
    java_io = {p: lines for p, lines in java_io.items() if lines}
    runner_reads = {}
    for p in (PRIVATE, ENVIRONMENT):
        syntax = ast.parse(content[p])
        lines = content[p].decode().splitlines()
        runner_reads[p] = [{'line': n.lineno, 'text': lines[n.lineno - 1]}
                           for n in ast.walk(syntax) if isinstance(n, ast.Call)
                           and isinstance(n.func, ast.Attribute)
                           and n.func.attr in ('read_bytes', 'read_text')]
    selection = json.loads(content[SELECTION])
    save('input-review.json', {'runner_read_sites': runner_reads, 'java_io_sites': java_io,
          'reviewed_java_sources': java_sources,
          'canonical_data_inputs': {p: manifest[p] for p in DATA},
          'selection_context_revision': selection['context_revision'],
          'selection_is_data_only': 'Environment runner reads context_revision only; historical packet paths are not opened or traversed.',
          'roster_selection': 'Private runner A and B select only closures.A-orchestration or closures.B-concrete-renderer-views; source arrays and substitutes are all retained.',
          'barrier_selection': 'B test loadBarriers reads records/candidates/boundary values from the supplied barrier JSON; source references are data, not additional file reads. A ignores extra barrier arguments.',
          'descriptor_selection': 'A/B read the supplied canonical descriptor; tests seed in-memory AssetManager maps used by InstalledAppearanceV2.capture. No packaged asset file is opened.',
          'environment_selection': 'Default environment closure is 34 explicit Java files; no Java test filesystem inputs. Runner freezes its five auxiliary paths, including itself and all four JSON files.',
          'git_use_by_ci_runners': 'Only private runner git rev-parse HEAD; environment runner inherits selection context and does not invoke Git. Default shallow fetch is sufficient.',
          'review_scope': 'Checkout input coverage only. Source inspection authorizes no OTA, compiler, JVM, native, device, store or GA claim.'})

    scratch_path = None
    with tempfile.TemporaryDirectory(prefix='mixer-android-ci-closure-') as scratch:
        scratch_path = Path(scratch)
        for p in selected:
            target = scratch_path / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content[p])
        files = sorted(str(p.relative_to(scratch_path)) for p in scratch_path.rglob('*') if p.is_file())
        assert files == selected
        assert sum((scratch_path / p).stat().st_size for p in files) == retained_bytes
        assert all(ident((scratch_path / p).read_bytes())['sha256'] == manifest[p]['sha256'] for p in selected)
        assert all((scratch_path / p).is_file() for p in required)
    assert scratch_path is not None and not scratch_path.exists()

    save('commands.json', COMMANDS)
    receipt = {'schema': 1, 'at': started, 'status': 'passed-offline-checkout-coverage-only',
               'command': 'python3 -B verification/ci-android-owner-host-sparse-checkout/verify.py',
               'source_revision': REV, 'source_git_tree': tree,
               'canonical_ls_tree': ident(listing),
               'tools': {'git': git_version, 'python': sys.version, 'platform': platform.platform()},
               'verifier': ident(Path(__file__).read_bytes()),
               'workflow_before': ident(before), 'workflow_after': ident(after),
               'workflow_delta': ident(diff.encode()), 'workflow_checkout_only_exact_byte_check': True,
               'default_fetch_depth_preserved': True, 'patterns': list(PATTERNS),
               'canonical_tracked_files': len(entries),
               'canonical_tracked_blob_bytes': sum(e['bytes'] for e in entries.values()),
               'git_selected_files': len(selected), 'materialized_bytes': retained_bytes,
               'materialization_limit_bytes': LIMIT, 'required_files_covered': len(required),
               'closure_java_counts': {k: len(v) for k, v in closures.items()},
               'retained_manifest': ident((OUT / 'retained-files.json').read_bytes()),
               'input_source': 'Canonical Git blobs at source_revision only; dirty active lanes excluded.',
               'cleanup': {'owned_scratch_path': str(scratch_path), 'owned_scratch_removed': True,
                           'worktrees_or_indexes_or_config_created_or_changed': False,
                           'native_or_capture_processes_started_or_queried': False},
               'not_run': ['compiler/JVM/native/UI/capture/network/product tests',
                           'stopped Android v5 or callback/PG16/broad hosted/catalog harnesses',
                           'global process inventory'],
               'pending': ['GitHub checkout action integration and existing JVM job result after root delivery'],
               'qualification': 'No Android runtime, physical phone, immutable FieldLog, OTA/signing/store/operations or GA evidence.'}
    save('receipt.json', receipt)
    output = (f'PASS offline Git non-cone rules: {len(selected)} files, {retained_bytes} '
              f'bytes; all {len(required)} runner inputs covered; owned scratch removed\n'
              f"workflow SHA256 {receipt['workflow_after']['sha256']}\n"
              f"workflow delta SHA256 {receipt['workflow_delta']['sha256']}\n")
    (OUT / 'stdout.txt').write_text(output)
    print(output, end='')


if __name__ == '__main__':
    main()
