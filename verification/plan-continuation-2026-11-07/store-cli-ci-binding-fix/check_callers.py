"""Pure checks for the three active caller candidates, without running Swift."""
import hashlib
import json
from pathlib import Path
import shlex

from check_workflow import check

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def check_callers():
    workflow = check()
    result = {'workflow': workflow, 'activeCallers': {}, 'actualCompilerCommands': 0}
    contract = '''swift build --package-path cli --product mixer -j 2
MIXER_STORE_CLI_BIN_DIR="$(swift build --package-path cli --product mixer -j 2 --show-bin-path)"
test -x "$MIXER_STORE_CLI_BIN_DIR/mixer"
MIXER_STORE_TEST_CLI="$MIXER_STORE_CLI_BIN_DIR/mixer" swift test --package-path cli
'''
    pairs = [('scripts/verify.sh', 'verify.sh'), ('README.md', 'README.md')]
    for path, label in pairs:
        before = (HERE / (label + '.before')).read_text()
        candidate = (HERE / (label + '.candidate')).read_text()
        assert (ROOT / path).read_text() == before, 'canonical caller changed: ' + path
        assert candidate.count(contract) == 1
        assert candidate.count('MIXER_STORE_TEST_CLI') == 1
        assert 'export MIXER_STORE_TEST_CLI' not in candidate
        expected = before.replace('swift test --package-path cli\n', contract)
        if path == 'README.md':
            anchor = 'compiler candidates; the default Xcode compiler does not match Android/Wasm SDKs.\n\n'
            expected = expected.replace(anchor, anchor + 'The CLI tests require the `mixer` executable built with the same Swift toolchain.\n\n')
            expected = expected.replace('Run the source CLI with `scripts/mixer`, or build `cli/` and use\n`cli/.build/debug/mixer` directly:\n', 'Run the source CLI with `scripts/mixer`, or use\n`"$MIXER_STORE_CLI_BIN_DIR/mixer"` after the build above:\n')
            first_code = candidate.split('```sh\n', 1)[1].split('```', 1)[0]
            old_code = before.split('```sh\n', 1)[1].split('```', 1)[0]
            assert first_code.replace(contract, 'swift test --package-path cli\n') == old_code
            (HERE / 'README-local-development.sh').write_text(first_code)
        assert candidate == expected
        if path == 'scripts/verify.sh':
            assert candidate.replace(contract, 'swift test --package-path cli\n') == before
            assert candidate.startswith('#!/bin/sh\nset -eu\n')
        result['activeCallers'][path] = {
            'beforeSHA256': hashlib.sha256(before.encode()).hexdigest(),
            'candidateSHA256': hashlib.sha256(candidate.encode()).hexdigest(),
            'allExistingCommandsPreserved': True,
            'commandLocalCLIEnvironment': True,
        }
    # The contract queried by every caller selects the same package, product and jobs.
    assert shlex.split(contract.splitlines()[0]) == ['swift', 'build', '--package-path', 'cli', '--product', 'mixer', '-j', '2']
    assert not any(line.lstrip().startswith('export ') for line in contract.splitlines())
    result.update(status='passed', historicalDesignRecipeEdited=False,
                  compiledBinaryValidation='Not established: the sole local build campaign failed before product build; no new compiler attempt')
    return result


if __name__ == '__main__':
    result = check_callers()
    (HERE / 'caller-check.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))
