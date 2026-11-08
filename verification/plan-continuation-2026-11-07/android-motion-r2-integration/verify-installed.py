#!/usr/bin/env python3
"""Verify already-applied R2 sources after the first checker lookup failed."""
from datetime import datetime, timezone
import json
import os
import shutil
import sys
import integrate as I


def main():
    runner = I.authority('installed_r2_verification')
    out = I.HERE / 'verification-commands'
    out.mkdir()
    commands = runner.Commands(out, dict(os.environ), seconds=180, command_seconds=45)
    result = {'schema': 1, 'recordedAt': datetime.now(timezone.utc).isoformat(),
              'priorFailure': 'acceptance.json: patches applied, checker KeyError for nonexistent bootstrap execute function; no source failure or test execution inferred',
              'productPatchAppliedAgain': False, 'nativeQualified': False,
              'ordinaryPair9CIPending': True}
    passed = False
    try:
        sources = json.loads((I.EVIDENCE / 'final-source-map.json').read_text())
        for path, expected in sources.items():
            runner.require(I.identity(I.ROOT / path) == expected, 'Integrated source mismatch: ' + path)
        result['implementationFiles'] = sources
        prepared = json.loads((I.HERE / 'ci-rebind-preparation.json').read_text())
        for path, expected in prepared['files'].items():
            runner.require(I.identity(I.ROOT / path)['sha256'] == expected['after'], 'CI successor mismatch')
        bootstrap = I.BASE / 'generated-java-ci-integration/bootstrap.py'
        base = commands.run('base-bootstrap', ['git', 'show',
            '25ac442c5213326b3601456a5fd62898f152111f:' + str(bootstrap.relative_to(I.ROOT))])
        before, after = I.functions(base), I.functions(bootstrap.read_text())
        runner.require(before.keys() == after.keys(), 'Bootstrap function inventory changed')
        changed = [name for name in before if before[name] != after[name]]
        runner.require(changed == ['admit_source_inputs'], 'Unexpected bootstrap function change')
        runner.require(base.replace("SOURCE_INPUT_SHA256 = '53ad5501dcaa0168ec8196c8816d07a246e6b04bcd0160edadd22ecafd4ff815'",
            "SOURCE_INPUT_SHA256 = 'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca'").replace(
            'reviewed pair8 closure', 'reviewed pair9 closure') == bootstrap.read_text(), 'Bootstrap trust or execution bytes changed')
        profile = runner.load_profile()
        inputs = runner.source_inputs(profile)
        expected = json.loads((I.EVIDENCE / 'canonical-source-inputs-final.json').read_text())
        runner.require(inputs == expected['files'] and len(inputs) == 101 and
            runner.source_digest(inputs) == expected['sha256'], 'Integrated canonical closure mismatch')
        result.update(sourcePair=profile['id'], sourceInputDigest=runner.source_digest(inputs), sourceInputs=inputs)
        for optimized in [False, True]:
            for test in ['test_bootstrap', 'test_sparse_checkout']:
                commands.run(test + ('-optimized' if optimized else '-normal'),
                    [sys.executable, '-I', '-B', '-S'] + (['-O'] if optimized else []) +
                    [I.BASE / 'generated-java-ci-integration' / (test + '.py'), '-v'])
        commands.run('whitespace', ['git', 'diff', '--check'])
        runner.require(runner.source_inputs(profile) == inputs, 'Postflight source drift')
        shutil.copyfile(I.EVIDENCE / 'implementation.patch', I.HERE / 'implementation.patch')
        result['reviewIdentity'] = I.identity(I.BASE / 'android-motion-thread-review-r2/REVIEW.md')
        result['CIRebinding'] = {path: I.identity(I.ROOT / path) for path in prepared['files']}
        passed = True
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        result['terminalCustody'] = commands.custody_terminal()
        result['status'] = 'INTEGRATED_EXACT_R2_CI_PENDING' if passed and result['terminalCustody'] else 'FAIL'
        result['commands'] = I.identity(out / 'commands.json')
        (I.HERE / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
        print(result['status'])


if __name__ == '__main__':
    main()
