#!/usr/bin/env python3
"""Install the reviewed R2 bytes and validate exact CI rebinding."""
from datetime import datetime, timezone
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
CANDIDATE = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-7764d3ec')
EVIDENCE = CANDIDATE / 'verification/plan-continuation-2026-11-07/android-motion-thread-fix-r2'


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def authority(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/ci/check-android-generated-java.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def functions(text):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}


def main():
    runner = authority('before_integration')
    out = HERE / 'integration-commands'
    out.mkdir()
    commands = runner.Commands(out, dict(os.environ), seconds=180, command_seconds=45)
    sources = json.loads((EVIDENCE / 'final-source-map.json').read_text())
    patch = EVIDENCE / 'implementation.patch'
    runner.require(identity(patch)['sha256'] == '7eace381b2fa49a158bbc04d6e8f2bb1ff0fe84639cd8f787df925507a8edabe', 'Review patch drift')
    for path, expected in sources.items():
        runner.require(identity(CANDIDATE / path) == expected, 'Candidate drift')
    preparation = json.loads((HERE / 'ci-rebind-preparation.json').read_text())
    for path, expected in preparation['files'].items():
        runner.require(identity(ROOT / path)['sha256'] == expected['before'], 'CI preimage drift')
    bootstrap = BASE / 'generated-java-ci-integration/bootstrap.py'
    prior_functions = functions(bootstrap.read_text())
    result = {'schema': 1, 'recordedAt': datetime.now(timezone.utc).isoformat(),
              'review': str((BASE / 'android-motion-thread-review-r2/REVIEW.md').relative_to(ROOT)),
              'sourceMap': sources, 'nativeRuntimeQualified': False, 'ordinaryPair9CIPending': True}
    passed = False
    try:
        result['parent'] = commands.run('parent', ['git', 'rev-parse', 'HEAD']).strip()
        commands.run('product-apply-check', ['git', 'apply', '--check', patch])
        commands.run('product-apply', ['git', 'apply', patch])
        for path, expected in sources.items():
            runner.require(identity(ROOT / path) == expected, 'Integrated source differs: ' + path)
        commands.run('ci-apply-check', ['git', 'apply', '--check', HERE / 'ci-rebind.patch'])
        commands.run('ci-apply', ['git', 'apply', HERE / 'ci-rebind.patch'])
        for path, expected in preparation['files'].items():
            runner.require(identity(ROOT / path)['sha256'] == expected['after'], 'CI successor differs')
        current_functions = functions(bootstrap.read_text())
        for name in ['validate_host_signature', 'extract_host', 'download', 'execute']:
            runner.require(prior_functions[name] == current_functions[name], 'Trust/execution function changed: ' + name)
        current = authority('integrated_r2')
        profile = current.load_profile()
        inputs = current.source_inputs(profile)
        expected = json.loads((EVIDENCE / 'canonical-source-inputs-final.json').read_text())
        runner.require(inputs == expected['files'] and len(inputs) == 101 and
            current.source_digest(inputs) == expected['sha256'], 'Integrated source closure differs')
        result.update(sourcePair=profile['id'], sourceInputDigest=current.source_digest(inputs), sourceInputs=inputs)
        for optimized in [False, True]:
            for test in ['test_bootstrap', 'test_sparse_checkout']:
                commands.run(test + ('-optimized' if optimized else '-normal'),
                    [sys.executable, '-I', '-B', '-S'] + (['-O'] if optimized else []) +
                    [BASE / 'generated-java-ci-integration' / (test + '.py'), '-v'])
        commands.run('whitespace', ['git', 'diff', '--check'])
        runner.require(current.source_inputs(profile) == inputs, 'Postflight source drift')
        shutil.copyfile(patch, HERE / 'implementation.patch')
        result['reviewIdentity'] = identity(BASE / 'android-motion-thread-review-r2/REVIEW.md')
        result['CIRebinding'] = {path: identity(ROOT / path) for path in preparation['files']}
        passed = True
    finally:
        result['terminalCustody'] = commands.custody_terminal()
        result['status'] = 'INTEGRATED_EXACT_R2_CI_PENDING' if passed and result['terminalCustody'] else 'FAIL'
        result['commands'] = identity(out / 'commands.json')
        (HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
        print(result['status'])


if __name__ == '__main__':
    main()
