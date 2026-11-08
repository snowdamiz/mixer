#!/usr/bin/env python3
"""Verify the all-format notarization correction without a real toolchain."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INTEGRATION = HERE.parent / 'generated-java-ci-integration'
SOURCES = [INTEGRATION / 'bootstrap.py', INTEGRATION / 'test_bootstrap.py']


def identity(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def frozen():
    paths = []
    for name in ('generated-java-signature-fix', 'generated-java-signature-review'):
        paths.extend(p for p in (HERE.parent / name).rglob('*') if p.is_file())
    return [identity(p) for p in sorted(paths)]


def main():
    output = HERE / 'commands'
    output.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('bounded_commands', ROOT / 'scripts/ci/check-android-generated-java.py')
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    commands = runner.Commands(output, dict(os.environ), seconds=180, command_seconds=45,
                               output_bytes=1_048_576, total_output_bytes=8_388_608)
    before, sealed = [identity(p) for p in SOURCES], frozen()
    receipt = {'schema': 1, 'observed_utc': datetime.now(timezone.utc).isoformat(),
               'python': sys.version, 'executable': sys.executable, 'platform': sys.platform,
               'sources': before, 'preserved_evidence': sealed,
               'scope': 'Pure/fake-child bootstrap and bounded read-only Git sparse controls only',
               'policy': 'Every admitted package status requires positive trusted Apple notarization; pkgutil success, exact signer/chain, timestamps and full-report refusal remain required.',
               'runtime_or_toolchain_qualification': False}
    passed = False
    try:
        receipt['revision'] = commands.run('head', ['git', 'rev-parse', 'HEAD']).strip()
        receipt['tree'] = commands.run('tree', ['git', 'rev-parse', 'HEAD^{tree}']).strip()
        receipt['git'] = commands.run('git-version', ['git', '--version']).strip()
        for optimized in (False, True):
            for test in ('test_bootstrap', 'test_sparse_checkout'):
                label = test + ('-optimized' if optimized else '-normal')
                argv = [sys.executable, '-B'] + (['-O'] if optimized else []) + [str(INTEGRATION / (test + '.py'))]
                commands.run(label, argv)
        paths = [str(p.relative_to(ROOT)) for p in SOURCES]
        commands.run('whitespace', ['git', 'diff', '--check', '--', *paths])
        patch = commands.run('candidate-patch', ['git', 'diff', '--', *paths])
        (HERE / 'change.patch').write_text(patch)
        receipt['patch'] = identity(HERE / 'change.patch')
        receipt['sources_unchanged'] = before == [identity(p) for p in SOURCES]
        receipt['sealed_evidence_unchanged'] = sealed == frozen()
        runner.require(receipt['sources_unchanged'] and receipt['sealed_evidence_unchanged'], 'Input drift')
        passed = True
    except BaseException as error:
        receipt['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        receipt['terminal_custody'] = commands.custody_terminal()
        receipt['passed'] = passed and receipt['terminal_custody']
        receipt['commands'] = identity(output / 'commands.json')
        (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'passed': receipt['passed'], 'terminal_custody': receipt['terminal_custody'],
                          'receipt': str(HERE / 'receipt.json')}))


if __name__ == '__main__':
    main()
