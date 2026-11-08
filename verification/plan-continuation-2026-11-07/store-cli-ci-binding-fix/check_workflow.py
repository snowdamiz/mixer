"""Pure assertions over the actual workflow candidate; no substituted CLI."""
import hashlib
import json
from pathlib import Path
import shlex

HERE = Path(__file__).resolve().parent


def check():
    before = (HERE / 'verify.yml.before').read_text()
    candidate = (HERE / 'verify.yml.candidate').read_text()
    anchor = '      - name: Swift SDK, update verifier and CLI\n        run: |\n'
    assert before.count(anchor) == candidate.count(anchor) == 1
    block = candidate.split(anchor)[1].split('      - name:')[0]
    before_block = before.split(anchor)[1].split('      - name:')[0]
    original = '          swift test --package-path cli\n'
    assert before_block.count(original) == 1
    injected = [line for line in block.splitlines() if line not in before_block.splitlines()]
    assert len(injected) == 4
    build, locate, executable, test = [line.strip() for line in injected]
    assert shlex.split(build) == ['swift', 'build', '--package-path', 'cli', '--product', 'mixer', '-j', '2']
    assert locate == 'MIXER_STORE_CLI_BIN_DIR="$(swift build --package-path cli --product mixer -j 2 --show-bin-path)"'
    assert shlex.split(executable) == ['test', '-x', '$MIXER_STORE_CLI_BIN_DIR/mixer']
    assert shlex.split(test) == ['MIXER_STORE_TEST_CLI=$MIXER_STORE_CLI_BIN_DIR/mixer', 'swift', 'test', '--package-path', 'cli']
    replacement = '\n'.join(injected) + '\n'
    assert candidate == before.replace(original, replacement)
    assert candidate.count('MIXER_STORE_TEST_CLI') == 1
    assert 'export ' not in replacement
    assert block.replace(replacement, original) == before_block
    assert block.index(build) < block.index(locate) < block.index(executable) < block.index(test)
    # No filter, skip, metadata env, toolchain selection or other step changed.
    return {
        'status': 'passed',
        'workflowBeforeSHA256': hashlib.sha256(before.encode()).hexdigest(),
        'workflowCandidateSHA256': hashlib.sha256(candidate.encode()).hexdigest(),
        'onlyChange': 'Replace the original CLI test line with product build, SwiftPM path query, executable guard and command-local environment binding',
        'sdkCoreAndOtherCommandsUnchanged': True,
        'cliTestArgumentsUnchanged': True,
        'cliEnvironmentCommandLocal': True,
        'buildProduct': 'mixer', 'buildJobs': 2,
        'binaryLocation': 'SwiftPM --show-bin-path with the same package/product/jobs',
        'actualBinaryExecutionEvidence': 'receipt.json and the unfiltered CLI suite logs; this pure check alone is not runtime evidence',
    }


if __name__ == '__main__':
    result = check()
    (HERE / 'workflow-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
