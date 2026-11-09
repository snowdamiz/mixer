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
            '/verification/plan-continuation-2026-11-07/generated-java-ci-integration/')
GIT_COMMANDS = []


def proposal_patterns(text):
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
    B.require(patterns == PATTERNS, 'Sparse selection differs from reviewed six-directory closure')
    return patterns


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
    def test_actual_proposal_selects_every_canonical_owning_input(self):
        patterns = proposal_patterns((HERE / 'workflow-proposal.yml').read_text())
        a = B.canonical()
        inputs = B.admit_source_inputs(a, a.load_profile())
        self.assertEqual(len(inputs), 114)
        self.assertEqual(a.source_digest(inputs), B.SOURCE_INPUT_SHA256)
        require_coverage(inputs, git_selected(list(inputs), patterns))

    def test_actual_git_excludes_historical_receipts_root_files_and_nearby_names(self):
        rejected = ['verification/android-binding-stage4/receipt.json', 'STATUS.md',
                    '.github/workflows/verify.yml', 'cli-other/Sources/x.swift',
                    'native/android-other/file', 'scripts/ci-other/file',
                    HERE.relative_to(ROOT).as_posix() + '-review/REVIEW.md']
        self.assertEqual(git_selected(rejected), set())

    def test_each_selected_directory_is_necessary_for_complete_dependency_closure(self):
        paths = ['cli/Package.swift', 'sdk/Package.swift', 'updates/Package.swift',
                 'native/android/engine/Package.swift', 'scripts/ci/check-android-binding.py',
                 HERE.relative_to(ROOT).as_posix() + '/test_bootstrap.py']
        require_coverage(paths, git_selected(paths))
        for omitted in PATTERNS:
            with self.subTest(omitted=omitted), self.assertRaisesRegex(RuntimeError, 'omits'):
                require_coverage(paths, git_selected(paths, tuple(p for p in PATTERNS if p != omitted)))

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
        inputs = a.source_inputs(a.load_profile())
        for missing in ('cli/Package.swift', 'scripts/ci/check-android-binding.py'):
            altered = dict(inputs)
            del altered[missing]
            with patch.object(a, 'source_inputs', return_value=altered), self.assertRaisesRegex(RuntimeError, 'owning inputs'):
                B.admit_source_inputs(a, {})
        altered = dict(inputs)
        altered['cli/Package.swift'] = {'bytes': 1, 'sha256': '0' * 64}
        with patch.object(a, 'source_inputs', return_value=altered), self.assertRaisesRegex(RuntimeError, 'owning inputs'):
            B.admit_source_inputs(a, {})

    def test_missing_file_error_propagates(self):
        with self.assertRaises(FileNotFoundError):
            B.admit_source_inputs(Mock(source_inputs=Mock(side_effect=FileNotFoundError('missing owning file'))), {})

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


if __name__ == '__main__':
    unittest.main()
