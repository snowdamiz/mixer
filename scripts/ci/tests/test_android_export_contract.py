"""Host controls for the public Android export command's tool boundary."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'check-android-generated-java.py'
SPEC = importlib.util.spec_from_file_location('android_export_contract_runner', RUNNER)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ExportContractControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='android-export-contract-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(strict=True)

    def test_export_admits_source_and_staged_swift_probes(self):
        argv = ['/owned/mixer', 'export', '/owned/export', '--directory', '/owned/source']
        required = M.inner_contract(argv, 'export')
        for suffix in ('ABC012', 'XYZ789'):
            folder = self.root / ('TemporaryDirectory.' + suffix)
            folder.mkdir(mode=0o700)
            marker = folder / '.keep-directory'
            marker.touch(mode=0o644)
            marker.chmod(0o644)

        for live in (True, False):
            with self.subTest(live=live):
                evidence = []
                self.assertEqual(M.inner_paths(self.root, live=live, tool_tmp_limit=len(required),
                                               tool_tmp_evidence=evidence), [])
                self.assertEqual([item['writer'] for item in evidence], ['swift --version'] * 2)
        self.assertEqual(required, ('version', 'version'))

        extra = self.root / 'TemporaryDirectory.ABC345'
        extra.mkdir(mode=0o700)
        with self.assertRaisesRegex(RuntimeError, 'Unexpected tool temporary directory'):
            M.inner_paths(self.root, live=True, tool_tmp_limit=len(required))


if __name__ == '__main__':
    unittest.main()
