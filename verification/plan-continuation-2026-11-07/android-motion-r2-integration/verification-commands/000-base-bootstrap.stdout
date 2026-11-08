#!/usr/bin/env python3
"""Proposed hosted-only bootstrap. Import is inert; execution requires --execute.

No SDK-manager, installer registration, Xcode selection mutation or device use.
The canonical runner remains the sole six-consumer compiler/admission authority.
"""
import argparse
from datetime import datetime, timezone
from enum import Enum
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
DRIVER = ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py'
RUNNER = ROOT / 'scripts/ci/check-android-generated-java.py'
TAG = 'swift-6.3.3-RELEASE'
HOST_URL = f'https://download.swift.org/swift-6.3.3-release/xcode/{TAG}/{TAG}-osx.pkg'
SDK_URL = f'https://download.swift.org/swift-6.3.3-release/android-sdk/{TAG}/{TAG}_android.artifactbundle.tar.gz'
SDK_SHA256 = 'd160cc3206dd1886dae3fef2337af5e25ec034692cd0ec225721c56cc69da7f5'
HOST_BYTES = 1503529808
SDK_BYTES = 333223533
DEVELOPER = Path('/Applications/Xcode_26.6.app/Contents/Developer')
SDKROOT = DEVELOPER / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'
SOURCE_INPUT_COUNT = 101
SOURCE_INPUT_SHA256 = '53ad5501dcaa0168ec8196c8816d07a246e6b04bcd0160edadd22ecafd4ff815'
MINIMUM_FREE_BYTES = 12 * 1024**3


class PackageTrustStatus(Enum):
    DEVELOPER_ID = 'signed by a developer certificate issued by Apple for distribution'
    TRUSTED_MACOS = 'signed by a certificate trusted by macOS'
    TRUSTED_MAC_OS_X = 'signed by a certificate trusted by Mac OS X'


# Swift.org documents this installer identity. Fingerprints pin the reviewed
# official 6.3.3 package's chain, not an arbitrary locally trusted developer.
HOST_CERTIFICATES = (
    ('Developer ID Installer: Swift Open Source (V9AUD2URP3)',
     'AC12310FADC4904F89203418BE5801B6EE79DE3A0DF223A1F1F4127BAB97B1A5'),
    ('Developer ID Certification Authority',
     '7AFC9D01A62F03A2DE9637936D4AFE68090D2DE18D03F29C88CFB0B1BA63587F'),
    ('Apple Root CA',
     'B0B1730ECBC7FF4505142C49F1295E6EDA6BCAED7E2C68C5BE91B5A11001F024'),
)


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical():
    spec = importlib.util.spec_from_file_location('generated_java_ci_authority', RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admit_source_inputs(authority, profile):
    inputs = authority.source_inputs(profile)
    require(len(inputs) == SOURCE_INPUT_COUNT and
            authority.source_digest(inputs) == SOURCE_INPUT_SHA256,
            'Sparse checkout owning inputs differ from reviewed pair8 closure')
    return inputs


def disk_admission(out, receipt):
    # Save the observation before refusing admission; failed jobs retain it too.
    usage = shutil.disk_usage(out)
    receipt['initial_disk_space'] = {
        'observed_utc': datetime.now(timezone.utc).isoformat(), 'path': str(out),
        'free_bytes': usage.free, 'minimum_free_bytes': MINIMUM_FREE_BYTES,
        'admitted': usage.free >= MINIMUM_FREE_BYTES}
    require(receipt['initial_disk_space']['admitted'],
            'Need 12GiB free private bootstrap/build capacity; do not delete shared image tools')


def hosted_environment(environment):
    require(environment.get('GITHUB_ACTIONS') == 'true' and
            environment.get('RUNNER_OS') == 'macOS' and
            environment.get('RUNNER_ARCH') == 'X64',
            'Only the proposed standard macos-26-intel Actions worker is admitted')
    require(environment.get('RUNNER_TEMP'), 'Missing RUNNER_TEMP')
    jdk = Path(environment.get('JAVA_HOME_25_X64', ''))
    android = Path(environment.get('ANDROID_HOME', ''))
    require(jdk.is_absolute() and android.is_absolute(), 'Missing image JDK25/Android absolute paths')
    return jdk.resolve(strict=True), android.resolve(strict=True)


def apple_environment(environment, authority):
    env = dict(environment, DEVELOPER_DIR=str(DEVELOPER), SDKROOT=str(SDKROOT),
               PYTHONDONTWRITEBYTECODE='1')
    # Do not inherit unrelated toolchain routing.
    env.pop('TOOLCHAINS', None)
    evidence = authority.apple_producer_provenance(env)
    require(evidence['xcode_version'] == '26.6' and evidence['xcode_build'] == '17F113' and
            evidence['sdk_version'] == '26.5', 'Hosted Apple producer identity changed')
    return env, evidence


def download(run, identity, label, url, path, size, checksum=None):
    effective = run(label, ['/usr/bin/curl', '--fail', '--silent', '--show-error',
        '--location', '--proto', '=https', '--proto-redir', '=https',
        '--connect-timeout', '20', '--max-time', '300', '--max-filesize', str(size),
        '--output', path, '--write-out', '%{url_effective}', url]).strip()
    require(effective == url, 'Unadmitted download redirect')
    result = identity(path)
    require(result['bytes'] == size, 'Download size differs from observed official HEAD metadata')
    if checksum is not None:
        require(result['sha256'] == checksum, 'Official Swift Android archive checksum mismatch')
    return dict(result, url=url, effective_url=effective)


def validate_host_signature(signature):
    """Admit only reviewed pkgutil reports, after Commands.run verifies exit 0.

    This is an output-policy check, not independent signature verification.
    Consume the entire combined stdout/stderr report to reject ambiguity.
    """
    refusal = 'Swift package is not admitted by macOS package trust'
    require(len(signature) <= 16384 and all(c in '\n\r\t' or ' ' <= c <= '~' for c in signature), refusal)
    lines = [line.strip() for line in signature.splitlines() if line.strip()]

    def take():
        require(bool(lines), refusal)
        return lines.pop(0)

    def date(value):
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+0000', value) is not None, refusal)
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S %z')
        except ValueError as error:
            raise RuntimeError(refusal) from error

    require(re.fullmatch(r'Package "[^"\r\n]+":', take()) is not None, refusal)
    status_line = take()
    statuses = {'Status: ' + status.value: status for status in PackageTrustStatus}
    require(status_line in statuses, refusal)
    status = statuses[status_line]
    require(take() == 'Notarization: trusted by the Apple notary service', refusal)
    timestamp = take()
    prefix = 'Signed with a trusted timestamp on: '
    require(timestamp.startswith(prefix), refusal)
    signed_at = date(timestamp[len(prefix):])
    require(take() == 'Certificate Chain:', refusal)
    for index, (identity, fingerprint) in enumerate(HOST_CERTIFICATES, 1):
        require(take() == f'{index}. {identity}', refusal)
        expiry = take()
        require(expiry.startswith('Expires: '), refusal)
        require(signed_at <= date(expiry[len('Expires: '):]), refusal)
        require(take() == 'SHA256 Fingerprint:', refusal)
        octets = []
        while lines and re.fullmatch(r'[0-9A-F]{2}(?: [0-9A-F]{2})*', lines[0]):
            octets.extend(take().split())
        require(''.join(octets) == fingerprint, refusal)
        if index < len(HOST_CERTIFICATES):
            require(take() == '-' * 72, refusal)
    require(not lines, refusal)
    return status


def extract_host(run, archive, expanded, toolchain):
    # Commands.run requires successful exit and terminal custody before returning;
    # include stderr so a contradictory diagnostic cannot be silently ignored.
    signature = run('swift-package-signature', ['/usr/sbin/pkgutil', '--check-signature', archive],
                    diagnostics=True)
    validate_host_signature(signature)
    run('swift-package-expand', ['/usr/sbin/pkgutil', '--expand', archive, expanded])
    candidates = [p for p in (expanded / 'Payload', expanded / f'{TAG}-osx-package.pkg/Payload') if p.is_file()]
    require(len(candidates) == 1, 'Official Swift package Payload topology changed')
    toolchain.mkdir()
    run('swift-package-payload', ['/usr/bin/tar', '-xf', candidates[0], '-C', toolchain])
    swift = toolchain / 'usr/bin/swift'
    require(swift.is_file() and os.access(swift, os.X_OK), 'Expanded package lacks Swift executable')
    archive.unlink()
    shutil.rmtree(expanded)
    return swift


def inspect_paths(authority, swift, sdks, art, jdk, android):
    args = argparse.Namespace(swift=swift, swift_sdks=sdks, android_artifact=art,
                              jdk=jdk, android_sdk=android)
    paths, env = authority.tool_environment(args)
    return args, paths, env


def validate_inspection(value, paths):
    require(value['schema'] == 1 and value['sdk_id'] == 'aarch64-unknown-linux-android28' and
            value['min_api'] == 28 and value['target_api'] == 37 and
            'Swift version 6.3.3 ' in value['swift_version'] and
            value['javac_version'].startswith('javac 25.'), 'Canonical official inspection identity differs')
    require(value['tools']['swift']['path'] == str(paths['swift']) and
            value['tools']['javac']['path'] == str(paths['jdk'] / 'bin/javac') and
            value['distributions']['android_platform']['path'] == str(paths['android_sdk'] / 'platforms/android-37.0'),
            'Canonical inspection selected unexpected tools')
    require(set(value['distributions']) == {'swift_toolchain', 'swift_android_sdk', 'android_platform',
            'android_build_tools', 'jdk'}, 'Incomplete canonical distribution inspection')


def integration_argv(python, args, output):
    return [python, '-B', RUNNER, '--swift', args.swift, '--swift-sdks', args.swift_sdks,
        '--android-artifact', args.android_artifact, '--jdk', args.jdk,
        '--android-sdk', args.android_sdk, '--output', output, '--execute-toolchains']


def run_integration(authority, args, env, output):
    # Run in this Python process so the canonical runner owns each new child
    # group directly; an outer process-group wrapper cannot contain its groups.
    selected = argparse.Namespace(**vars(args), output=output, execute_toolchains=True)
    previous = os.environ.copy()
    try:
        os.environ.clear()
        os.environ.update(env)
        return authority.execute(selected)
    finally:
        os.environ.clear()
        os.environ.update(previous)


def validate_result(value):
    require(value['status'] == 'passed-java-crosscompile-only', 'Actual integration did not pass')
    expected = {m + '-' + f for m in ('debug', 'release') for f in ('original', 'relocated', 'exported')}
    require(set(value['consumers']) == expected and
            all(v['java_count'] == 18 for v in value['consumers'].values()), 'Incomplete actual six-consumer result')
    cases = {'sdk', 'adapter', 'descriptor', 'extra-java', 'profile', 'missing-lock'}
    require(set(value['tamper']) == {'debug', 'release'}, 'Missing actual tamper modes')
    for mode in ('debug', 'release'):
        outcomes = value['tamper'][mode]
        require(len(outcomes) == 6 and {v['case'] for v in outcomes} == cases and
                all(v['refusal']['status'] == 'error' and v['driver_refusal'] and
                    v['build_staging_created'] is False for v in outcomes), 'Incomplete actual tamper refusal result')
    require(value['producer_jobs'] == 2 and value['cleanup']['command_custody_terminal'] is True and
            value['cleanup']['owned_scratch_removed'] is True, 'Runner concurrency/custody/cleanup differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    require(args.execute, 'Explicit --execute required; no installation during proposal review')
    require(sys.platform == 'darwin', 'Only macOS is supported')
    authority = canonical()
    out = args.output.absolute()
    runner_temp = Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    require(out.parent.resolve(strict=True) == runner_temp and not out.exists() and not out.is_symlink(),
            'Output must be a fresh direct child of RUNNER_TEMP')
    out.mkdir(mode=0o700)
    (out / 'bootstrap-commands').mkdir()
    receipt = {'schema': 1, 'status': 'failed', 'observed_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'argv': sys.argv, 'qualification': 'proposal until actual hosted execution',
        'runtime_API28_signing_published_package_GA': 'pending',
        'workflow_adoption': 'External to this bootstrap; proposal delivery does not install a workflow',
        'limits': {'downloads': 2, 'download_bytes': HOST_BYTES + SDK_BYTES,
                   'bootstrap_seconds': 1200, 'bootstrap_command_seconds': 300,
                   'integration_seconds': 2400, 'producer_jobs': 2}}
    commands = None
    scratch = None
    integration_started = False
    integration_terminal = False
    try:
        disk_admission(out, receipt)
        profile = authority.load_profile()
        receipt['source_inputs'] = admit_source_inputs(authority, profile)
        receipt['source_inputs_sha256'] = authority.source_digest(receipt['source_inputs'])
        jdk, android = hosted_environment(os.environ)
        env, receipt['apple_producer'] = apple_environment(os.environ, authority)
        commands = authority.Commands(out / 'bootstrap-commands', env, seconds=1200, command_seconds=300)
        run = commands.run
        receipt['revision'] = run('revision', ['git', 'rev-parse', 'HEAD']).strip()
        receipt['git_tree'] = run('git-tree', ['git', 'rev-parse', 'HEAD^{tree}']).strip()
        receipt['image'] = {k: os.environ.get(k) for k in ('ImageOS', 'ImageVersion', 'RUNNER_OS', 'RUNNER_ARCH')}
        receipt['bootstrap_system_tools'] = {p: authority.identity(Path(p).resolve(strict=True))
            for p in ('/usr/bin/curl', '/usr/sbin/pkgutil', '/usr/bin/tar', '/usr/bin/ditto', '/bin/bash')}
        receipt['curl_version'] = run('curl-version', ['/usr/bin/curl', '--version'])
        receipt['tar_version'] = run('tar-version', ['/usr/bin/tar', '--version'])
        scratch = Path(tempfile.mkdtemp(prefix='owned-', dir=out))
        env['TMPDIR'] = str(scratch / 'tmp')
        (scratch / 'tmp').mkdir()
        host, sdk = scratch / 'swift.pkg', scratch / 'android.tar.gz'
        receipt['host_download'] = download(run, authority.identity, 'download-swift-host', HOST_URL, host, HOST_BYTES)
        swift = extract_host(run, host, scratch / 'expanded', scratch / 'swift.xctoolchain')
        receipt['host_package_trust'] = 'macOS trusted package signature; full output retained in bootstrap-commands'
        receipt['sdk_download'] = download(run, authority.identity, 'download-swift-android', SDK_URL, sdk, SDK_BYTES, SDK_SHA256)
        sdks = scratch / 'swift-sdks'
        sdks.mkdir()
        run('extract-swift-android', ['/usr/bin/tar', '-xzf', sdk, '-C', sdks])
        sdk.unlink()
        art = sdks / f'{TAG}_android.artifactbundle/swift-android'
        ndk = art / 'android-ndk-r27d'
        # Copy into the hashed bundle: canonical tree() rejects directory links
        # escaping the bundle root. Never mutate the image-supplied NDK.
        run('copy-image-ndk', ['/usr/bin/ditto', android / 'ndk/27.3.13750724', ndk])
        env.update(ANDROID_NDK_HOME=str(ndk), SWIFT_ANDROID_NDK_LINK='1')
        run('official-sdk-setup', ['/bin/bash', art / 'scripts/setup-android-sdk.sh'], cwd=art)
        selected, paths, tool_env = inspect_paths(authority, swift, sdks, art, jdk, android)
        env.update(tool_env)
        # tool_environment copies the process env: restore explicit Apple paths,
        # private temp and NDK setup routing afterwards.
        env.update(DEVELOPER_DIR=str(DEVELOPER), SDKROOT=str(SDKROOT), TMPDIR=str(scratch / 'tmp'),
                   ANDROID_NDK_HOME=str(ndk), SWIFT_ANDROID_NDK_LINK='1')
        env.pop('TOOLCHAINS', None)
        receipt['official_inspect'] = authority.unique_json(run('official-inspect', [sys.executable, '-B', DRIVER, 'inspect']))
        validate_inspection(receipt['official_inspect'], paths)
        authority.save(out / 'bootstrap-receipt.json', receipt)
        # The existing runner owns its own 40-minute budget and bounded children.
        receipt['integration_argv_equivalent'] = list(map(str, integration_argv(sys.executable, selected, out / 'integration')))
        integration_started = True
        result = run_integration(authority, selected, env, out / 'integration')
        integration_terminal = result.get('cleanup', {}).get('command_custody_terminal') is True
        validate_result(result)
        require(result['official_toolchain'] == receipt['official_inspect'], 'Tool identity changed after bootstrap')
        require(authority.source_inputs(profile) == receipt['source_inputs'], 'Owning source changed')
        receipt['status'] = 'passed-hosted-java-crosscompile-only'
    except Exception as error:
        receipt['error'] = str(error)
    finally:
        terminal = (commands is not None and (not commands.records or commands.custody_terminal()) and
                    (not integration_started or integration_terminal))
        receipt['commands'] = commands.records if commands else []
        receipt['cleanup'] = {'terminal_custody': terminal, 'owned_path': str(scratch) if scratch else None,
                              'owned_removed': scratch is None}
        if scratch is not None and terminal:
            try:
                shutil.rmtree(scratch)
                receipt['cleanup']['owned_removed'] = not scratch.exists()
            except Exception as error:
                receipt['cleanup']['error'] = str(error)
        if not terminal or not receipt['cleanup']['owned_removed']:
            receipt['status'] = 'failed'
        authority.save(out / 'bootstrap-receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'error': receipt.get('error')}))
    return 0 if receipt['status'] == 'passed-hosted-java-crosscompile-only' else 1


if __name__ == '__main__':
    sys.exit(main())
