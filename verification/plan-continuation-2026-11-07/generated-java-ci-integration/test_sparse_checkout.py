#!/usr/bin/env python3
"""Bounded pure/read-only-Git controls for the proposed non-cone checkout."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('sparse_bootstrap', HERE / 'bootstrap.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
PATTERNS = ('/cli/', '/sdk/', '/updates/', '/native/android/', '/scripts/ci/',
            '/verification/plan-continuation-2026-11-07/generated-java-ci-integration/',
            '/verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/binding.json')
CURRENT_BINDING = B.ROOT.joinpath('cli/build-tests/current_android_profile.py')
current_spec = importlib.util.spec_from_file_location('sparse_current_profile', CURRENT_BINDING)
current_module = importlib.util.module_from_spec(current_spec)
current_spec.loader.exec_module(current_module)
SOURCE_BINDING = B.SOURCE_AUTHORITY.relative_to(B.ROOT).with_name("binding.json")
HISTORICAL_SOURCE_BINDING = Path('verification/sdk-feature-ui-source141-v1/binding.json')
GIT_COMMANDS = []


def checkout_patterns(text):
    # Deliberately accept only this proposal's narrow checkout stanza. Unknown
    # settings (including filter overrides), duplicates and altered actions fail.
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if 'uses: actions/checkout' in line]
    B.require(len(starts) == 1, 'Expected one official checkout v4 step')
    start = starts[0]
    stop = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('      - ')), len(lines))
    block = [line for line in lines[start:stop] if line.strip() and not line.lstrip().startswith('#')]
    B.require(block[:5] == [
        '      - uses: actions/checkout@v4', '        with:',
        '          persist-credentials: false', '          sparse-checkout-cone-mode: false',
        '          sparse-checkout: |'], 'Unadmitted checkout settings; preserve implicit blob:none')
    B.require(all(line.startswith('            /') for line in block[5:]), 'Invalid non-cone pattern block')
    patterns = tuple(line.strip() for line in block[5:])
    B.require(patterns and len(set(patterns)) == len(patterns), 'Missing or duplicate sparse patterns')
    B.require(all(p.startswith('/') and all(part and part not in ('.', '..') and
                  all(c.isalnum() or c in '-_.' for c in part)
                  for part in p.strip('/').split('/')) for p in patterns),
              'Only explicit rooted checkout paths are admitted')
    return patterns


def proposal_patterns(text):
    patterns = checkout_patterns(text)
    B.require(patterns == PATTERNS, 'Sparse selection differs from reviewed checkout closure')
    return patterns


def owning_patterns(text):
    # Finite extraction of this one known job, not a general workflow parser.
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line == '  android-generated-java:']
    B.require(len(starts) == 1, 'Missing or ambiguous owning Android job')
    start = starts[0]
    stop = next((i for i in range(start + 1, len(lines))
                 if lines[i].strip() and not lines[i].lstrip().startswith('#') and
                 not lines[i].startswith('    ')), len(lines))
    return checkout_patterns('\n'.join(lines[start:stop]))


def admission_paths(root=None, binding=None):
    """Read the complete selected admission declaration, including raw history."""
    import hashlib
    root = ROOT if root is None else Path(root)
    binding = SOURCE_BINDING if binding is None else Path(binding)
    def relative(name):
        p = Path(name)
        B.require(type(name) is str and name and not p.is_absolute() and
                  p.as_posix() == name and all(x not in ('.', '..', '.git') for x in p.parts),
                  'Invalid admission witness path')
        return p
    def read_json(path):
        return json.loads(path.read_bytes(), object_pairs_hook=current_module.unique_object)
    base = root / relative(binding.as_posix()).parent
    seal = read_json(base / 'seal.json')
    members = seal['members']
    B.require(type(members) is dict and 0 < len(members) <= 2048,
              'Invalid selected admission roster')
    for name, expected in members.items():
        raw = (base / relative(name)).read_bytes()
        B.require(expected == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                  'Selected admission seal differs: ' + name)
    digest = hashlib.sha256(''.join(n + '\0' + v['sha256'] + '\n'
                                   for n, v in sorted(members.items())).encode()).hexdigest()
    B.require(seal['tree_sha256'] == digest and binding.name in members,
              'Selected admission seal or binding differs')
    declaration = read_json(root / binding)
    manifests = (declaration['source']['manifest'],)
    if 'predecessor_binding' in declaration:
        previous = relative(declaration['predecessor_binding'])
        B.require(previous == HISTORICAL_SOURCE_BINDING and previous != binding,
                  'Invalid archive predecessor binding')
        dependencies = admission_paths(root, previous)
        dependencies.update(relative(path).as_posix() for path in declaration['changes'])
        for key in ('capability_transition', 'upgrade_transition', 'pair24_transition',
                    'cancel_cli_transition', 'local_store_transition',
                    'release_inspector_transition', 'icu_notice_transition', 'halt_cli_transition',
                    'release_rest_v3_transition', 'stock_promotion_transition',
                    'hosted_v71_transition', 'hosted_v72_transition', 'hosted_v73_transition',
                    'android_inspection_deadline_transition'):
            if key in declaration:
                dependencies.update(relative(path).as_posix() for path in declaration[key]['changes'])
    else:
        manifests += ('caller-inputs.json', 'owning-closure.json', 'historical-inputs.json')
        dependencies = set()
    paths = {binding.parent.joinpath(name).as_posix() for name in (*members, 'seal.json')}
    for name in manifests:
        B.require(name in members, 'Unsealed admission manifest: ' + name)
        rows = read_json(base / relative(name))
        B.require(type(rows) is dict and len(rows) <= 2048, 'Invalid admission input map')
        paths.update(relative(path).as_posix() for path in rows)
    return paths | dependencies


def owning_paths(patterns):
    authority = B.canonical()
    paths = set(B.admit_source_inputs(authority, authority.load_profile()))
    paths.update(admission_paths())
    paths.update(('cli/Package.swift', 'sdk/Package.swift', 'updates/Package.swift',
                  'native/android/engine/Package.swift', 'scripts/ci/check-android-binding.py',
                  HERE.relative_to(ROOT).as_posix() + '/test_bootstrap.py',
                  PATTERNS[-1].lstrip('/'), current_module.BINDING.as_posix(),
                  '.github/workflows/verify.yml'))
    paths.update(p.lstrip('/') + 'binding.json' for p in patterns
                 if p.startswith(('/verification/native-output-', '/verification/native-report-')) and p.endswith('/'))
    return sorted(paths)



def git_selected(paths, patterns=PATTERNS):
    B.require(len(paths) <= 10000 and sum(len(p) for p in paths) <= 1_000_000,
              'Sparse matching input budget exceeded')
    with tempfile.TemporaryDirectory(prefix='sparse-rules-', dir=HERE) as td:
        rules = Path(td) / 'rules'
        rules.write_text('\n'.join(patterns) + '\n')
        argv = ['git', '-C', str(ROOT), 'sparse-checkout', 'check-rules', '--no-cone',
                '--rules-file', str(rules), '-z']
        GIT_COMMANDS.append({'argv': argv, 'timeout_seconds': 15, 'paths': len(paths),
                             'patterns': list(patterns)})
        result = subprocess.run(argv, input=('\0'.join(paths) + '\0').encode(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=True)
        B.require(len(result.stdout) <= 1_100_000 and len(result.stderr) <= 65536,
                  'Sparse matching output budget exceeded')
        return set(result.stdout.decode().rstrip('\0').split('\0')) if result.stdout else set()


def require_coverage(paths, selected):
    B.require(set(paths) <= selected, 'Sparse checkout omits required inputs: ' + repr(sorted(set(paths) - selected)))


class SparseControls(unittest.TestCase):
    def assert_current_source(self, authority, inputs, root=None, binding=SOURCE_BINDING):
        root = B.ROOT if root is None else root
        source = json.loads((root / binding).read_bytes(),
                            object_pairs_hook=current_module.unique_object)['source']
        self.assertEqual(source['manifest'], 'current-source-inputs.json')
        self.assertEqual((len(inputs), authority.source_digest(inputs)),
                         (source['count'], source['sha256']))

    def test_current_source_count_and_digest_are_independent_of_runtime_pins(self):
        from unittest.mock import patch
        authority = B.canonical()
        profile = authority.load_profile()
        inputs = authority.source_inputs(profile)
        self.assert_current_source(authority, inputs)
        binding = json.loads((B.ROOT / SOURCE_BINDING).read_bytes())
        with tempfile.TemporaryDirectory(dir=HERE) as td:
            root = Path(td)
            path = root / SOURCE_BINDING
            path.parent.mkdir(parents=True)
            # The historical stale count is a negative case, never CURRENT.
            stale = dict(binding['source'], count=116)
            path.write_text(json.dumps({'source': stale}))
            with self.assertRaises(AssertionError):
                self.assert_current_source(authority, inputs, root)
            for extra in (1, 3):
                future = dict(inputs)
                for index in range(extra):
                    future['sdk/Sources/MixerGuest/FutureControl%d.swift' % index] = {
                        'bytes': 1, 'sha256': ('%064x' % (index + 1))}
                expected = dict(binding['source'], count=len(future),
                                sha256=authority.source_digest(future))
                path.write_text(json.dumps({'source': expected}))
                # A coherent future binding works without editing a test literal.
                self.assert_current_source(authority, future, root)
                with patch.object(authority, 'source_inputs', return_value=future):
                    with self.assertRaisesRegex(RuntimeError, 'owning inputs'):
                        B.admit_source_inputs(authority, profile)
                    with patch.object(B, 'SOURCE_INPUT_COUNT', len(future), create=True), \
                         patch.object(B, 'SOURCE_INPUT_SHA256', expected['sha256'], create=True):
                        # Matching runtime constants cannot bless a foreign map.
                        with self.assertRaisesRegex(RuntimeError, 'owning inputs'):
                            B.admit_source_inputs(authority, profile)
                        path.write_text(json.dumps({'source': binding['source']}))
                        with self.assertRaises(AssertionError):
                            self.assert_current_source(authority, future, root)
                path.write_text(json.dumps({'source': dict(expected, sha256='0' * 64)}))
                with self.assertRaises(AssertionError):
                    self.assert_current_source(authority, future, root)

    def test_actual_proposal_selects_every_canonical_owning_input(self):
        # The seven-pattern proposal predates optional native-sdk inputs. Bind
        # its unchanged assertions to the real declared predecessor bytes.
        import hashlib
        selected_root = ROOT
        spec = importlib.util.spec_from_file_location('proposal_current_adopter',
            B.SOURCE_AUTHORITY)
        adopter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adopter)
        binding, _, prior = adopter.admit()
        predecessor_authority, _ = adopter.load_predecessor()
        history = predecessor_authority.load(
            predecessor_authority.HERE / 'historical-inputs.json')
        with tempfile.TemporaryDirectory(prefix='historical-proposal-', dir=HERE) as td:
            predecessor = Path(td) / 'source127'
            result = adopter.prepare_predecessor(predecessor)
            for name, expected in history.items():
                raw = (predecessor / name).read_bytes()
                self.assertEqual({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, expected)
            self.assertEqual(result['source127'], binding['sdk_transition']['sourceBefore'])
            historical_binding = Path('verification/native-report-source127-v1/binding.json')
            old_spec = importlib.util.spec_from_file_location('proposal_predecessor_adopter',
                predecessor / historical_binding.parent / 'adopt_envelope.py')
            old_adopter = importlib.util.module_from_spec(old_spec)
            old_spec.loader.exec_module(old_adopter)
            self.assertEqual(old_adopter.verify(True)['source_count'], len(prior))
            historical_here = predecessor / HERE.relative_to(selected_root)
            boot_spec = importlib.util.spec_from_file_location('proposal_predecessor_bootstrap',
                historical_here / 'bootstrap.py')
            historical = importlib.util.module_from_spec(boot_spec)
            boot_spec.loader.exec_module(historical)
            subprocess.run(['git', '-C', str(predecessor), 'init', '-q'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=True)
            with patch(__name__ + '.ROOT', predecessor), patch(__name__ + '.HERE', historical_here), \
                 patch.object(B, 'ROOT', predecessor), \
                 patch.object(B, 'canonical', historical.canonical), \
                 patch.object(B, 'admit_source_inputs', historical.admit_source_inputs), \
                 patch.object(current_module, 'BINDING', historical_binding):
                patterns = proposal_patterns((HERE / 'workflow-proposal.yml').read_text())
                a = B.canonical()
                inputs = B.admit_source_inputs(a, a.load_profile())
                self.assert_current_source(a, inputs, predecessor, historical_binding)
                require_coverage(inputs, git_selected(list(inputs), patterns))


    def test_actual_git_excludes_historical_receipts_root_files_and_nearby_names(self):
        rejected = ['verification/android-binding-stage4/receipt.json', 'STATUS.md',
                    '.github/workflows/verify.yml', 'cli-other/Sources/x.swift',
                    'native/android-other/file', 'scripts/ci-other/file',
                    HERE.relative_to(ROOT).as_posix() + '-review/REVIEW.md']
        self.assertEqual(git_selected(rejected), set())

    def test_each_selected_directory_is_necessary_for_complete_dependency_closure(self):
        patterns = owning_patterns((ROOT / '.github/workflows/verify.yml').read_text())
        paths = owning_paths(patterns)
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)
        require_coverage(paths, git_selected(paths, patterns))
        for omitted in patterns:
            with self.subTest(omitted=omitted), self.assertRaisesRegex(RuntimeError, 'omits'):
                require_coverage(paths, git_selected(paths, tuple(p for p in patterns if p != omitted)))

    def test_owning_job_extraction_refuses_missing_ambiguous_or_unsafe_checkout(self):
        text = (ROOT / '.github/workflows/verify.yml').read_text()
        for altered in (text.replace('  android-generated-java:', '  other-android-job:'),
                        text + '\n  android-generated-java:\n',
                        text.replace('      - uses: actions/checkout@v4',
                                     '      - uses: actions/checkout@v3'),
                        text.replace('            /cli/', '            /*'),
                        text.replace('            /cli/', '            /cli/\n            /cli/'),
                        text.replace('          sparse-checkout-cone-mode: false',
                                     '          sparse-checkout-cone-mode: true')):
            with self.subTest(altered=altered), self.assertRaises(RuntimeError):
                owning_patterns(altered)

    def test_owning_selection_tracks_future_binding_and_retained_history(self):
        text = (ROOT / '.github/workflows/verify.yml').read_text()
        patterns = owning_patterns(text)
        future = Path('verification/native-output-future-admission/binding.json')
        future_pattern = '/' + future.parent.as_posix() + '/'
        changed = text.replace('            /cli/\n',
                               '            /cli/\n            ' + future_pattern + '\n')
        selected = owning_patterns(changed)
        self.assertEqual(set(selected), set(patterns) | {future_pattern})
        import shutil
        with tempfile.TemporaryDirectory(dir=HERE) as td:
            fixture = Path(td)
            shutil.copytree(ROOT / current_module.BINDING.parent, fixture / future.parent)
            shutil.copytree(ROOT / HISTORICAL_SOURCE_BINDING.parent,
                            fixture / HISTORICAL_SOURCE_BINDING.parent)
            declared = admission_paths(fixture, future)
            self.assertIn(future.as_posix(), declared)
            self.assertIn(HISTORICAL_SOURCE_BINDING.as_posix(), declared)
            with patch.object(current_module, 'BINDING', future), \
                 patch(__name__ + '.admission_paths', return_value=declared):
                paths = owning_paths(selected)
        self.assertIn(future.as_posix(), paths)
        for pattern in patterns:
            if pattern.startswith('/verification/native-output-') and pattern.endswith('/'):
                self.assertIn(pattern.lstrip('/') + 'binding.json', paths)

    def test_proposal_omission_refused(self):
        text = (HERE / 'workflow-proposal.yml').read_text()
        for pattern in PATTERNS:
            with self.subTest(pattern=pattern), self.assertRaises(RuntimeError):
                proposal_patterns(text.replace('            ' + pattern + '\n', ''))

    def test_cone_filter_and_full_checkout_regressions_refused(self):
        text = (HERE / 'workflow-proposal.yml').read_text()
        variants = [text.replace('sparse-checkout-cone-mode: false', 'sparse-checkout-cone-mode: true'),
                    text.replace('          sparse-checkout: |', '          filter: blob:limit=1m\n          sparse-checkout: |'),
                    text.replace('actions/checkout@v4', 'actions/checkout@v3'),
                    text.replace('          persist-credentials: false', '          persist-credentials: true'),
                    text.replace('            /cli/', '            /*'),
                    text.replace('          sparse-checkout: |', '          sparse-checkout: cli')]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(RuntimeError):
                proposal_patterns(variant)

    def test_git_failure_propagates(self):
        with patch.object(subprocess, 'run', side_effect=subprocess.CalledProcessError(128, ['git'])):
            with self.assertRaises(subprocess.CalledProcessError):
                git_selected(['cli/Package.swift'])

    def test_git_timeout_propagates(self):
        with patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired(['git'], 15)):
            with self.assertRaises(subprocess.TimeoutExpired):
                git_selected(['cli/Package.swift'])

    def test_selection_budget_refuses_before_git(self):
        with patch.object(subprocess, 'run') as run, self.assertRaises(RuntimeError):
            git_selected(['x'] * 10001)
        run.assert_not_called()

    def test_missing_or_changed_owning_input_fails_closed(self):
        a = B.canonical()
        profile = a.load_profile()
        inputs = a.source_inputs(profile)
        for missing in ('cli/Package.swift', 'scripts/ci/check-android-binding.py'):
            altered = dict(inputs)
            del altered[missing]
            with patch.object(a, 'source_inputs', return_value=altered), self.assertRaisesRegex(RuntimeError, 'owning inputs'):
                B.admit_source_inputs(a, profile)
        altered = dict(inputs)
        altered['cli/Package.swift'] = {'bytes': 1, 'sha256': '0' * 64}
        with patch.object(a, 'source_inputs', return_value=altered), self.assertRaisesRegex(RuntimeError, 'owning inputs'):
            B.admit_source_inputs(a, profile)

    def test_missing_file_error_propagates(self):
        authority = B.canonical()
        profile = authority.load_profile()
        with patch.object(authority, 'source_inputs',
                          side_effect=FileNotFoundError('missing owning file')) as collect:
            with self.assertRaisesRegex(FileNotFoundError, 'missing owning file'):
                B.admit_source_inputs(authority, profile)
        collect.assert_called_once_with(profile)

    def test_disk_boundary_observation_survives_refusal(self):
        for free in (B.MINIMUM_FREE_BYTES - 1, B.MINIMUM_FREE_BYTES, B.MINIMUM_FREE_BYTES + 1):
            receipt = {}
            with patch.object(B.shutil, 'disk_usage', return_value=SimpleNamespace(free=free)):
                if free < B.MINIMUM_FREE_BYTES:
                    with self.assertRaisesRegex(RuntimeError, '12GiB'):
                        B.disk_admission(HERE, receipt)
                else:
                    B.disk_admission(HERE, receipt)
            self.assertEqual(receipt['initial_disk_space']['free_bytes'], free)
            self.assertEqual(receipt['initial_disk_space']['admitted'], free >= B.MINIMUM_FREE_BYTES)
            self.assertIn('observed_utc', receipt['initial_disk_space'])

    def test_low_disk_main_persists_receipt_before_native_or_download(self):
        a = B.canonical()
        with tempfile.TemporaryDirectory(dir=HERE) as td:
            output = Path(td) / 'out'
            with patch.object(B, 'canonical', return_value=a), \
                 patch.object(B, 'hosted_environment') as hosted, \
                 patch.object(B, 'download') as download, \
                 patch.object(B.shutil, 'disk_usage', return_value=SimpleNamespace(free=1)), \
                 patch.dict(os.environ, {'RUNNER_TEMP': td}), \
                 patch.object(sys, 'argv', ['bootstrap.py', '--output', str(output), '--execute']):
                self.assertEqual(B.main(), 1)
            receipt = json.loads((output / 'bootstrap-receipt.json').read_text())
            self.assertEqual(receipt['initial_disk_space']['free_bytes'], 1)
            self.assertFalse(receipt['initial_disk_space']['admitted'])
            self.assertEqual(receipt['status'], 'failed')
            hosted.assert_not_called()
            download.assert_not_called()



    def test_materialized_checkout_runs_selected_installed_admission(self):
        import shutil
        patterns = owning_patterns((ROOT / '.github/workflows/verify.yml').read_text())
        paths = owning_paths(patterns)
        without_root_lock = [pattern for pattern in patterns if pattern != '/Package.resolved']
        with tempfile.TemporaryDirectory(prefix='materialized-admission-', dir=HERE) as td:
            base = Path(td)
            repo = base / 'repo'
            repo.mkdir()
            empty = base / 'empty'
            empty.mkdir()
            config = base / 'empty-config'
            config.write_text('')
            env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=str(config),
                       GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
            for name in paths:
                out = repo / name
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / name, out)
            git = ['git', '-C', str(repo), '-c', 'init.templateDir=' + str(empty),
                   '-c', 'core.hooksPath=' + str(empty), '-c', 'core.fsmonitor=false',
                   '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']
            def command(args, **kw):
                return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      timeout=30, env=env, **kw)
            command(git + ['init', '-q'], check=True)
            command(git + ['add', '-f', '--all'], check=True)
            command(git + ['sparse-checkout', 'set', '--no-cone', '--stdin'],
                    input=('\n'.join(without_root_lock) + '\n').encode(), check=True)
            self.assertFalse((repo / 'Package.resolved').exists())
            adopter = repo / B.SOURCE_AUTHORITY.relative_to(ROOT)
            python = [sys.executable, '-I', '-B', '-S'] + (['-O'] if sys.flags.optimize else [])
            failed = command(python + [str(adopter), 'verify', '--workflow-installed'])
            self.assertEqual(failed.returncode, 1)
            self.assertIn(b'Package.resolved', failed.stderr)
            command(git + ['sparse-checkout', 'set', '--no-cone', '--stdin'],
                    input=('\n'.join(patterns) + '\n').encode(), check=True)
            self.assertEqual([n for n in paths if not (repo / n).is_file()], [])
            passed = command(python + [str(adopter), 'verify', '--workflow-installed'], check=True)
            observed = json.loads(passed.stdout)
            self.assertEqual(observed['source_count'], len(B.admit_source_inputs(B.canonical(), B.canonical().load_profile())))
            self.assertFalse(observed['GA'])
            binding = json.loads((repo / SOURCE_BINDING).read_bytes())
            pair24 = binding['pair24_transition']
            self.assertEqual(observed['profile'], binding['profile'])
            self.assertEqual(observed['predecessor_upgraded_pair23_sha256'], pair24['sourceBefore'])
            self.assertEqual(pair24['sourceBefore'], binding['upgrade_transition']['sourceAfter'])
            self.assertEqual(pair24['sourceAfter'], observed['predecessor_pair24_source141_sha256'])
            self.assertEqual(binding['hydration_transition']['sourceAfter'],
                             observed['predecessor_local_store_source141_sha256'])
            inspector = binding['release_inspector_transition']
            self.assertEqual(inspector['sourceBefore'], binding['runtime_notice_witness_transition']['sourceAfter'])
            self.assertEqual(observed['predecessor_release_inspector_sha256'], inspector['sourceBefore'])
            icu = binding['icu_notice_transition']
            self.assertEqual(icu['sourceBefore'], inspector['sourceAfter'])
            self.assertEqual(observed['predecessor_icu_notice_sha256'], icu['sourceBefore'])
            halt = binding['halt_cli_transition']
            self.assertEqual(observed['predecessor_source150_sha256'], icu['sourceAfter'])
            self.assertEqual(halt['sourceBefore'], icu['sourceAfter'])
            self.assertEqual(observed['predecessor_apple_section_accessibility_sha256'],
                             halt['sourceAfter'])
            release = binding['release_rest_v3_transition']
            self.assertEqual(release['sourceBefore'], binding['swift_version_transition']['sourceAfter'])
            self.assertEqual(observed['predecessor_release_rest_v3_sha256'], release['sourceBefore'])
            stock = binding['stock_promotion_transition']
            self.assertEqual(stock['sourceBefore'], release['sourceAfter'])
            self.assertEqual(observed['predecessor_stock_promotion_sha256'], stock['sourceBefore'])
            inspection = binding['android_inspection_deadline_transition']
            self.assertEqual(inspection['sourceBefore'], stock['sourceAfter'])
            self.assertEqual(observed['source_sha256'], inspection['sourceAfter'])
            self.assertEqual(observed['source_sha256'], binding['source']['sha256'])
            seal = json.loads((repo / SOURCE_BINDING.with_name('seal.json')).read_bytes())
            icu_preimages = [SOURCE_BINDING.parent / name for name in seal['members']
                             if name.startswith('icu-notice-predecessor-bytes/')]
            self.assertEqual(len(icu_preimages), len(icu['changes']))
            for name in (*icu_preimages, *map(Path, icu['changes'])):
                with self.subTest(missing_icu_input=name.as_posix()):
                    missing = name.as_posix()
                    command(git + ['sparse-checkout', 'set', '--no-cone', '--stdin'],
                            input=('\n'.join((*patterns, '!/' + missing)) + '\n').encode(), check=True)
                    self.assertFalse((repo / name).exists())
                    failed = command(python + [str(adopter), 'verify', '--workflow-installed'])
                    self.assertEqual(failed.returncode, 1)
                    diagnostic = 'Incomplete authority membership' if name in icu_preimages else missing
                    self.assertIn(diagnostic.encode(), failed.stderr)
            changes = {**binding['changes'], **binding['capability_transition']['changes'],
                       **pair24['changes'], **binding['local_store_transition']['changes'],
                       **inspector['changes'], **release['changes']}
            additions = sorted(name for name, change in changes.items() if change['before'] is None)
            self.assertTrue(additions)
            for name in additions:
                with self.subTest(missing=name):
                    command(git + ['sparse-checkout', 'set', '--no-cone', '--stdin'],
                            input=('\n'.join((*patterns, '!/' + name)) + '\n').encode(), check=True)
                    self.assertFalse((repo / name).exists())
                    failed = command(python + [str(adopter), 'verify', '--workflow-installed'])
                    self.assertEqual(failed.returncode, 1)
                    self.assertIn(name.encode(), failed.stderr)
            command(git + ['sparse-checkout', 'set', '--no-cone', '--stdin'],
                    input=('\n'.join(patterns) + '\n').encode(), check=True)
            restored = base / 'source141'
            command(python + [str(adopter), 'prepare-source141', '--out', str(restored)], check=True)
            progress = Path('cli/build-tests/test_android_inspection_progress.py')
            preimage = SOURCE_BINDING.parent / 'hosted-v71-predecessor-bytes' / progress
            self.assertEqual((restored / progress).read_bytes(), (repo / preimage).read_bytes())
            for name in additions:
                self.assertFalse((restored / name).exists(), name)


if __name__ == '__main__':
    unittest.main()
