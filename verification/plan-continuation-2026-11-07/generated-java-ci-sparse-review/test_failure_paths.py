#!/usr/bin/env python3
"""Fake-child bootstrap lifecycle probes; no subprocess or native tool execution."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('review_bootstrap', HERE.parent / 'generated-java-ci-integration/bootstrap.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class FailurePaths(unittest.TestCase):
    def exercise(self, terminal):
        authority = B.canonical()

        class FakeCommands:
            def __init__(self, out, env, **limits):
                self.out, self.env, self.records = out, env, []

            def custody_terminal(self):
                return bool(self.records) and all(r['terminal_custody'] for r in self.records)

            def run(self, label, argv, **kwargs):
                failed = label == 'fake-extraction'
                self.records.append({'label': label, 'terminal_custody': terminal if failed else True})
                authority.save(self.out / 'commands.json', self.records)
                (self.out / (label + '.stderr')).write_text('injected extraction failure' if failed else '')
                if failed:
                    raise RuntimeError('injected extraction failure')
                return 'fake-child-result'

        def download(run, identify, label, url, path, size, checksum=None):
            path.write_bytes(b'fake archive; never executed')
            return {'url': url, **authority.identity(path)}

        def extract_host(run, archive, expanded, toolchain):
            run('fake-extraction', ['fake-no-child'])

        with tempfile.TemporaryDirectory(dir=HERE) as td:
            root = Path(td)
            output = root / 'out'
            with patch.object(B, 'canonical', return_value=authority), \
                 patch.object(authority, 'Commands', FakeCommands), \
                 patch.object(B, 'hosted_environment', return_value=(root, root)), \
                 patch.object(B, 'apple_environment', return_value=({}, {'fake': True})), \
                 patch.object(B, 'download', side_effect=download), \
                 patch.object(B, 'extract_host', side_effect=extract_host), \
                 patch.object(B.shutil, 'disk_usage', return_value=SimpleNamespace(free=24 * 1024**3)), \
                 patch.dict(os.environ, {'RUNNER_TEMP': str(root)}), \
                 patch.object(sys, 'argv', ['bootstrap.py', '--output', str(output), '--execute']), \
                 redirect_stdout(io.StringIO()):
                status = B.main()
            result = json.loads((output / 'bootstrap-receipt.json').read_text())
            self.assertEqual(status, 1)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['error'], 'injected extraction failure')
            self.assertEqual(result['cleanup']['terminal_custody'], terminal)
            self.assertEqual(result['cleanup']['owned_removed'], terminal)
            self.assertEqual(Path(result['cleanup']['owned_path']).exists(), not terminal)
            self.assertTrue((output / 'bootstrap-commands/fake-extraction.stderr').is_file())
            self.assertTrue((output / 'bootstrap-commands/commands.json').is_file())
            (HERE / ('failure-terminal.json' if terminal else 'failure-unknown-custody.json')).write_text(
                json.dumps({'scope': 'fake children only', 'result': result}, indent=2) + '\n')

    def test_terminal_failure_removes_owned_scratch_and_keeps_diagnostics(self):
        self.exercise(True)

    def test_unknown_custody_keeps_owned_scratch_and_diagnostics(self):
        self.exercise(False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
