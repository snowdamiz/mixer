"""One offline CLI build and full CLI suite, under the accepted custody module."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import sys
import tarfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVISION = '3e2f0907a259a73e7fa96c43f18bbe02c0a46921'
SOURCE103 = 'eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158'
CONTROL = HERE.parent / 'native-custody-premise/cleanup_control.py'
CONTROL_HASH = '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
SWIFT = Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
DEV = Path('/Applications/Xcode_26.6.app/Contents/Developer')
SDK = DEV / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            result.update(chunk)
    return result.hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def files(directory):
    return {p.relative_to(directory).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(directory.rglob('*')) if p.is_file()}


def main():
    assert not (HERE / 'receipt.json').exists(), 'single campaign; never rerun'
    assert sha(CONTROL) == CONTROL_HASH
    custody = load_module('accepted_custody', CONTROL)
    inventory = load_module('canonical_inventory', ROOT / 'scripts/ci/check-android-generated-java.py')
    owning_before = inventory.source_inputs(inventory.load_profile())
    assert len(owning_before) == 103 and inventory.source_digest(owning_before) == SOURCE103
    save('source103-before.json', owning_before)
    tests_before = files(ROOT / 'cli/Tests')
    save('cli-tests-before.json', tests_before)
    assert shutil.disk_usage(HERE).free > 2 * 1024**3
    scratch = HERE / 'scratch'
    scratch.mkdir(exist_ok=False)
    for name in ['temporary', 'cache', 'config', 'security', 'source', 'build']:
        (scratch / name).mkdir()
    command_dir = HERE / 'commands'
    command_dir.mkdir()
    env = {k: os.environ[k] for k in ['HOME', 'USER', 'LOGNAME'] if k in os.environ}
    env.update(PATH=str(SWIFT.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
               DEVELOPER_DIR=str(DEV), SDKROOT=str(SDK),
               TMPDIR=str(scratch / 'temporary') + '/',
               GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1')
    assert 'TOOLCHAINS' not in env and 'MIXER_ASC_BEARER_TOKEN' not in env
    started = time.monotonic()
    active_deadline = started + 600
    commands = custody.Commands(command_dir, env, deadline=active_deadline + 5,
        output_bytes=8*1024**2, total_output_bytes=64*1024**2, cleanup_seconds=5)
    receipt = {
        'recordedAt': datetime.now(timezone.utc).isoformat(), 'status': 'running',
        'scope': 'One unchanged committed-source CLI product build and unfiltered CLI suite; no live network/provider/ASC, native runtime, device, CI dispatch, canonical edits, commit or push',
        'requestedModel': {'model': 'gpt-6.1-sol', 'reasoningEffort': 'xhigh', 'speed': 'default'},
        'revision': REVISION, 'source103': SOURCE103, 'sourceCount': 103,
        'python': sys.version, 'host': platform.platform(),
        'cleanupModule': {'path': str(CONTROL), 'sha256': CONTROL_HASH},
        'runnerSHA256': sha(__file__), 'swift': {'path': str(SWIFT), 'resolvedPath': str(SWIFT.resolve()), 'sha256': sha(SWIFT)},
        'environment': env, 'TOOLCHAINS': 'unset',
        'SDKROOTResolved': str(SDK.resolve()),
        'bounds': {'campaigns': 1, 'buildCommands': 1, 'testCommands': 1, 'jobs': 2,
                   'activeSeconds': 600, 'cleanupSecondsPerCommand': 5,
                   'commandBytes': 8*1024**2, 'aggregateBytes': 64*1024**2},
        'workflowBeforeSHA256': sha(ROOT / '.github/workflows/verify.yml'),
        'patchSHA256': sha(HERE / 'workflow.patch'),
    }
    save('receipt.json', receipt)

    def short(label, argv, cwd=ROOT):
        return commands.run(label, argv, cwd, timeout=30)

    def campaign_command(label, argv, *, cli_binary=None):
        commands.env = dict(env)
        if cli_binary is not None:
            commands.env['MIXER_STORE_TEST_CLI'] = str(cli_binary)
        item = commands.start(label, argv, scratch / 'source')
        record = item['record']
        record['environmentOverrides'] = {'MIXER_STORE_TEST_CLI': str(cli_binary)} if cli_binary else {}
        record['shellCommand'] = (('MIXER_STORE_TEST_CLI=' + shlex.quote(str(cli_binary)) + ' ') if cli_binary else '') + shlex.join(list(map(str, argv)))
        record['startedAt'] = datetime.now(timezone.utc).isoformat()
        try:
            while not commands.hold:
                if time.monotonic() >= active_deadline:
                    record['stop'] = 'campaign-active-deadline'
                    break
                commands.pump(.02)
                if commands.hold or commands.limit:
                    break
                if commands.reaped(item) and record['stdout_eof'] and record['stderr_eof']:
                    break
        except BaseException as error:
            record['execution_error'] = repr(error)
        finally:
            commands.stop(item)
            record['elapsedSeconds'] = time.monotonic() - record['started_monotonic']
            commands.persist(item)
            commands.env = env
        assert not commands.hold and not commands.limit and record['terminal_custody'], 'nonterminal custody or output limit'
        assert record['stop'] is None and 'execution_error' not in record and record['exit_code'] == 0, label + ' failed'
        return commands.captured(label)

    try:
        assert short('git-head', ['git', 'rev-parse', 'HEAD']) == REVISION
        receipt['gitTree'] = short('git-tree', ['git', 'rev-parse', REVISION + '^{tree}'])
        short('patch-applicability', ['git', 'apply', '--check', str(HERE / 'workflow.patch')])
        short('workflow-pure-check', [sys.executable, '-B', str(HERE / 'check_workflow.py')])
        block = (HERE / 'verify.yml.candidate').read_text().split('      - name: Swift SDK, update verifier and CLI\n        run: |\n')[1].split('      - name:')[0]
        shell = HERE / 'affected-step.sh'
        shell.write_text('\n'.join(line[10:] for line in block.splitlines()) + '\n')
        short('workflow-shell-syntax', ['/bin/bash', '-n', str(shell)])
        # Only standard SwiftPM repository caches are read, never an old build or scratch.
        seeds = {}
        for name in ['swift-crypto-7e0614ea', 'swift-asn1-7065ad2c']:
            source = Path.home() / 'Library/Caches/org.swift.swiftpm/repositories' / name
            assert source.is_dir() and not source.is_symlink()
            assert not any(p.is_symlink() for p in source.rglob('*'))
            before = files(source)
            destination = scratch / 'cache/repositories' / name
            shutil.copytree(source, destination)
            assert files(destination) == before == files(source)
            seeds[name] = {'source': str(source), 'files': before}
        save('dependency-cache-seeds.json', seeds)
        for pin in json.loads((ROOT / 'cli/Package.resolved').read_text())['pins']:
            repository = next((scratch / 'cache/repositories').glob(pin['identity'] + '-*'))
            short('cached-pin-' + pin['identity'], ['git', '--git-dir=' + str(repository), 'cat-file', '-e', pin['state']['revision'] + '^{commit}'])
        selection = [*owning_before, 'cli/Tests']
        archive = scratch / 'committed-source.tar'
        short('committed-source-archive', ['git', 'archive', '--format=tar', '--output=' + str(archive), REVISION, '--', *selection])
        receipt['committedArchiveSHA256'] = sha(archive)
        with tarfile.open(archive) as stream:
            assert all(m.isdir() or m.isfile() for m in stream.getmembers())
            stream.extractall(scratch / 'source', filter='data')
        snapshot = scratch / 'source'
        snapshot_hashes = {p: inventory.identity(snapshot / p) for p in owning_before}
        assert snapshot_hashes == owning_before
        assert files(snapshot / 'cli/Tests') == tests_before
        snapshot_before = files(snapshot)
        save('committed-inputs-before.json', snapshot_before)
        sandbox = HERE / 'offline.sb'
        sandbox.write_text('(version 1)\n(allow default)\n(deny network*)\n')
        prefix = ['/usr/bin/sandbox-exec', '-f', str(sandbox)]
        receipt['networkPolicy'] = {'profile': str(sandbox), 'sha256': sha(sandbox), 'rule': '(deny network*)', 'appliesTo': 'Swift version, bin-path query, build, test and all descendants'}
        receipt['swiftVersion'] = short('swift-version', [*prefix, SWIFT, '--version'], snapshot)
        assert 'Swift version 6.3.3' in receipt['swiftVersion']
        receipt['xcodeVersion'] = short('xcode-version', [*prefix, '/usr/bin/xcodebuild', '-version'], snapshot)
        receipt['sdkSettingsSHA256'] = sha(SDK / 'SDKSettings.json')
        receipt['sdkVersion'] = json.loads((SDK / 'SDKSettings.json').read_text())['Version']
        assert receipt['sdkVersion'] == '26.5'
        common = ['--package-path', str(snapshot / 'cli'), '--scratch-path', str(scratch / 'build'),
                  '--cache-path', str(scratch / 'cache'), '--config-path', str(scratch / 'config'),
                  '--security-path', str(scratch / 'security'), '--skip-update', '--disable-automatic-resolution', '-j', '2']
        build = [*prefix, SWIFT, 'build', *common, '--product', 'mixer']
        locate = [*prefix, SWIFT, 'build', *common, '--product', 'mixer', '--show-bin-path']
        save('receipt.json', receipt)
        campaign_command('build-cli-product', build)
        bin_dir = Path(short('swiftpm-bin-path', locate, snapshot))
        assert bin_dir.is_absolute() and bin_dir.is_relative_to(scratch / 'build')
        binary = bin_dir / 'mixer'
        assert binary.is_file() and os.access(binary, os.X_OK)
        receipt['binaryBeforeTests'] = {'path': str(binary), **inventory.identity(binary)}
        receipt['resolvedDependencyPins'] = json.loads((snapshot / 'cli/Package.resolved').read_text())['pins']
        save('receipt.json', receipt)
        log = campaign_command('full-cli-suite', [*prefix, SWIFT, 'test', *common], cli_binary=binary)
        receipt['binaryAfterTests'] = {'path': str(binary), **inventory.identity(binary)}
        assert receipt['binaryBeforeTests'] == receipt['binaryAfterTests']
        receipt['testSummary'] = [line for line in log.splitlines() if 'Test run with ' in line or 'StoreSubmissionReconciliationTests passed' in line or 'INDEPENDENT concurrentRealCLI' in line]
        assert 'Test run with 74 tests in 1 suite passed' in log
        assert 'INDEPENDENT concurrentRealCLI rounds=2 processes=48 issued=48 retainedCredentials=48' in log
        receipt['status'] = 'passed'
    except BaseException as error:
        receipt.update(status='failed', error=repr(error))
    finally:
        # Always stop a still-running *owned* item once, using the unchanged module.
        for item in reversed(commands.owned):
            if commands.hold:
                break
            if item['record']['state'] == 'RUNNING':
                commands.stop(item)
        owning_after = inventory.source_inputs(inventory.load_profile())
        save('source103-after.json', owning_after)
        save('cli-tests-after.json', files(ROOT / 'cli/Tests'))
        receipt['source103Stable'] = owning_after == owning_before
        receipt['canonicalCLITestsStable'] = files(ROOT / 'cli/Tests') == tests_before
        receipt['workflowCanonicalStable'] = sha(ROOT / '.github/workflows/verify.yml') == receipt['workflowBeforeSHA256']
        receipt['cleanupModuleStable'] = sha(CONTROL) == CONTROL_HASH
        receipt['swiftStable'] = sha(SWIFT) == receipt['swift']['sha256']
        snapshot_path = scratch / 'source'
        if 'snapshot_before' in locals():
            snapshot_after = files(snapshot_path)
            save('committed-inputs-after.json', snapshot_after)
            receipt['committedInputsStable'] = snapshot_after == snapshot_before
        receipt['dependencyCachesStable'] = all(files(Path(value['source'])) == value['files'] for value in locals().get('seeds', {}).values())
        receipt['terminalCustody'] = not commands.hold and all(r['terminal_custody'] for r in commands.records)
        receipt['aggregateOutputBytes'] = commands.used_output
        receipt['elapsedSecondsBeforeFinalCleanup'] = time.monotonic() - started
        stable = all(receipt.get(k) for k in ['source103Stable', 'canonicalCLITestsStable', 'workflowCanonicalStable', 'cleanupModuleStable', 'swiftStable', 'committedInputsStable', 'dependencyCachesStable'])
        if not stable or not receipt['terminalCustody']:
            receipt['status'] = 'failed'
        if receipt['status'] == 'passed':
            receipt['cleanup'] = commands.cleanup(scratch)
            if not receipt['cleanup']['allTerminalCustody'] or not receipt['cleanup']['scratchRemoved']:
                receipt['status'] = 'failed'
        else:
            for item in commands.owned:
                commands.persist(item)
            if receipt['terminalCustody']:
                commands.selector.close()
            receipt['cleanup'] = {'allTerminalCustody': receipt['terminalCustody'], 'scratchRemoved': False, 'retainedScratch': str(scratch), 'hold': commands.hold, 'reason': 'Failed single campaign preserved; no automatic rerun'}
        receipt['commands'] = commands.records
        receipt['logHashes'] = {p.name: inventory.identity(p) for p in sorted(command_dir.iterdir()) if p.suffix in ['.stdout', '.stderr']}
        save('receipt.json', receipt)
        print(json.dumps({k: receipt.get(k) for k in ['status', 'error', 'testSummary', 'source103Stable', 'committedInputsStable', 'terminalCustody', 'aggregateOutputBytes', 'cleanup']}), flush=True)
    return 0 if receipt['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
