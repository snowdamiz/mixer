#!/usr/bin/env python3
"""Check exact installed CI corrections without running the compiler fixture."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    out = HERE / 'commands'
    out.mkdir()
    spec = importlib.util.spec_from_file_location('ci_commands', ROOT / 'scripts/ci/check-android-generated-java.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    commands = runner.Commands(out, dict(os.environ), seconds=180, command_seconds=45)
    paths = [ROOT / '.github/workflows/verify.yml',
             BASE / 'generated-java-ci-integration/bootstrap.py',
             BASE / 'generated-java-ci-integration/test_bootstrap.py',
             BASE / 'cache-deadline-control-fix/sources.json']
    before = {str(p.relative_to(ROOT)): identity(p) for p in paths}
    receipt = {'schema': 1, 'recordedAt': datetime.now(timezone.utc).isoformat(),
               'sources': before, 'python': sys.version, 'pythonExecutable': sys.executable,
               'scope': 'Reviewed CI correction installation; no compiler fixture or native run',
               'reviews': ['generated-java-signature-review-r2/REVIEW.md',
                           'cache-deadline-control-review/REPORT.txt'],
               'historicalOptimizedCacheResult': '35/36; unresolved EPERM custody PGID23663 preserved',
               'freshCIQualified': False}
    passed = False
    try:
        receipt['revision'] = commands.run('head', ['git', 'rev-parse', 'HEAD']).strip()
        receipt['git'] = commands.run('git-version', ['git', '--version']).strip()
        receipt['adoption'] = json.loads(commands.run('cache-installed-adoption',
            [sys.executable, '-B', BASE / 'cache-deadline-control-fix/adopt_fixture.py',
             'verify', '--workflow-installed']))
        for test in ['test_bootstrap', 'test_sparse_checkout']:
            commands.run(test + '-ci-isolated', [sys.executable, '-I', '-B', '-S',
                BASE / 'generated-java-ci-integration' / (test + '.py'), '-v'])
        commands.run('whitespace', ['git', 'diff', '--check'])
        profile = runner.load_profile()
        inputs = runner.source_inputs(profile)
        receipt['sourcePair'] = profile['id']
        receipt['owningInputCount'] = len(inputs)
        receipt['owningInputDigest'] = runner.source_digest(inputs)
        runner.require(len(inputs) == 101 and receipt['owningInputDigest'] ==
            '53ad5501dcaa0168ec8196c8816d07a246e6b04bcd0160edadd22ecafd4ff815', 'Pair8 drift')
        runner.require(before == {str(p.relative_to(ROOT)): identity(p) for p in paths}, 'Source drift')
        passed = True
    finally:
        receipt['terminalCustody'] = commands.custody_terminal()
        receipt['status'] = 'ACCEPT_INSTALLED_PENDING_CI' if passed and receipt['terminalCustody'] else 'FAIL'
        receipt['commands'] = identity(out / 'commands.json')
        (HERE / 'installation.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(receipt['status'])


if __name__ == '__main__':
    main()
