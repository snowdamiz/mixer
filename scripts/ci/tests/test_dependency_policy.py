"""Exercise dependency guard decisions through the real command entry point."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class DependencyPolicyTests(unittest.TestCase):
    def check(self, content):
        with tempfile.TemporaryDirectory(prefix='mixer-dependency-policy-') as folder:
            root = Path(folder)
            (root / 'scripts').mkdir()
            shutil.copyfile(ROOT / 'scripts/check-policy.py', root / 'scripts/check-policy.py')
            for name in ('gates/ga.json', 'work-graph.json', 'dogfood/receipts/milestones.json'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            (root / 'package-lock.json').write_text(content)
            result = subprocess.run([sys.executable, str(root / 'scripts/check-policy.py')],
                                    capture_output=True, text=True, timeout=10)
            return result.returncode, json.loads(result.stdout)

    def test_wasm32_architectures_are_not_interpreter_dependencies(self):
        code, result = self.check(json.dumps({'packages': {
            'node_modules/@img/sharp-wasm32': {'cpu': ['wasm32']},
            'node_modules/@img/sharp-freebsd-wasm32': {
                'resolved': 'https://registry.npmjs.org/@img/sharp-freebsd-wasm32/-/sharp-freebsd-wasm32-0.35.5.tgz'},
            'target': 'wasm32-unknown-unknown',
        }}))
        self.assertEqual(code, 0, result)
        self.assertEqual(result['failures'], [])

    def test_prohibited_engine_names_suffixes_and_urls_still_fail(self):
        for reference in ('wasm3', 'WASM3', 'wasm3-sys', 'wasm3_sys',
                          'https://github.com/wasm3/wasm3', 'libwasm3.a',
                          'wasmkit', 'wasmtime', 'wasmer', 'skiptools/skip',
                          'patch-release/tool', 'skipstone', 'skip-fuse',
                          'skip-ui', 'patch-swift'):
            with self.subTest(reference=reference):
                code, result = self.check(json.dumps({'dependency': reference}))
                self.assertEqual(code, 1, result)
                self.assertTrue(any('prohibited engine/dependency' in x for x in result['failures']))

    def test_architecture_does_not_mask_prohibited_engine_on_same_line(self):
        code, result = self.check('{"cpu":"wasm32","dependency":"wasm3"}')
        self.assertEqual(code, 1, result)
        self.assertEqual(len(result['failures']), 1)


if __name__ == '__main__':
    unittest.main()
