#!/usr/bin/env python3
"""Read-only integrated source103 artifact audit. Only writes beside this script.

Run: python3 -I -B -S verification/plan-continuation-2026-11-07/store-journal-six-consumers-review/audit.py
No product imports, subprocesses, compiler/JVM/native invocations, or process probes.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import struct
import sys
import time
import zlib
import tarfile
import re
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
PARENT = OUT.parents[2]
ROOT = PARENT
BASE = OUT.parent
RUN = BASE / 'store-journal-six-consumers'
START = time.monotonic()
CHECKS = []
FACTS = {}
MANIFEST = {}


def check(ok, label):
    CHECKS.append({'check': label, 'passed': bool(ok)})
    if not ok:
        raise RuntimeError(label)


def bound():
    if time.monotonic() - START > 115:
        raise RuntimeError('Audit exceeded 115-second read/hash bound')


def ident(path):
    path = Path(path)
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            bound()
            size += len(chunk)
            if size > 4 * 1024**3:
                raise RuntimeError('Audit per-file bound exceeded')
            h.update(chunk)
    return {'bytes': size, 'sha256': h.hexdigest()}


def read(path):
    path = Path(path)
    if path.stat().st_size > 128 * 1024**2:
        raise RuntimeError('Audit materialized file bound exceeded')
    b = path.read_bytes()
    MANIFEST[str(path)] = {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    return b


def pairs(values):
    d = {}
    for k, v in values:
        if k in d:
            raise RuntimeError('Duplicate JSON key ' + k)
        d[k] = v
    return d


def js(path):
    return json.loads(read(path), object_pairs_hook=pairs)


def projection(files):
    return hashlib.sha256(''.join(k + '\0' + v['sha256'] + '\n'
                                  for k, v in sorted(files.items())).encode()).hexdigest()


def inventory(root):
    result = {}
    for p in sorted(root.rglob('*')):
        bound()
        if p.is_symlink():
            raise RuntimeError('Unexpected artifact symlink: ' + str(p))
        if p.is_file():
            result[p.relative_to(root).as_posix()] = ident(p)
            if len(result) > 10000:
                raise RuntimeError('Artifact file-count bound exceeded')
    return result


def distribution(path):
    # Independently reproduce the canonical installed-tree serialization, including links.
    root = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    count = 0
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        links = [d for d in dirs if (Path(base) / d).is_symlink()]
        for name in sorted(names + links):
            bound()
            p = Path(base) / name
            if p.is_symlink():
                target = p.resolve(strict=True)
                if p.is_dir() and not target.is_relative_to(root):
                    raise RuntimeError('Distribution link escapes root')
                value = 'symlink:' + os.readlink(p)
                if p.is_file():
                    value += ':' + ident(p)['sha256']
            else:
                value = ident(p)['sha256']
            h.update((p.relative_to(root).as_posix() + '\0' + value + '\n').encode())
            count += 1
            if count > 250000:
                raise RuntimeError('Distribution file-count bound exceeded')
    return {'sha256': h.hexdigest(), 'entries': count}


def class_members(path):
    data = read(path)
    if data[:4] != b'\xca\xfe\xba\xbe':
        raise RuntimeError('Bad classfile magic')
    minor, major, n = struct.unpack_from('>HHH', data, 4)
    cp, pos, i = {}, 10, 1
    sizes = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4,
             12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    while i < n:
        tag = data[pos]
        pos += 1
        if tag == 1:
            size = struct.unpack_from('>H', data, pos)[0]
            pos += 2
            cp[i] = (tag, data[pos:pos + size])
        else:
            size = sizes[tag]
            cp[i] = (tag, data[pos:pos + size])
        pos += size
        i += 2 if tag in (5, 6) else 1
    def u2(b):
        return struct.unpack('>H', b)[0]
    def utf(index):
        # Member identifiers and descriptors in these files are ASCII/UTF-8.
        return cp[index][1].decode('utf-8')
    this_class = struct.unpack_from('>H', data, pos + 2)[0]
    name = utf(u2(cp[this_class][1]))
    refs = []
    for index, (tag, value) in cp.items():
        if tag in (9, 10, 11):
            owner, nt = struct.unpack('>HH', value)
            member, descriptor = struct.unpack('>HH', cp[nt][1])
            refs.append((str(path), '#' + str(index), {9: 'Fieldref', 10: 'Methodref', 11: 'InterfaceMethodref'}[tag],
                         utf(u2(cp[owner][1])) + '.' + utf(member) + ':' + utf(descriptor)))
    return name, minor, major, refs


def dex_classes(path):
    data = read(path)
    check(data[:8] in [b'dex\n035\0', b'dex\n037\0', b'dex\n038\0', b'dex\n039\0',
                          b'dex\n040\0', b'dex\n041\0'], str(path) + ': DEX magic')
    u32 = lambda off: struct.unpack_from('<I', data, off)[0]
    check(u32(32) == len(data) and u32(36) == 112 and u32(40) == 0x12345678, str(path) + ': DEX header')
    check(hashlib.sha1(data[32:]).digest() == data[12:32] and zlib.adler32(data[12:]) == u32(8), str(path) + ': DEX checksums')
    strings = []
    for i in range(u32(56)):
        pos = u32(u32(60) + i * 4)
        while data[pos] & 128:
            pos += 1
        pos += 1
        end = data.index(0, pos)
        strings.append(data[pos:end])
    types = [strings[u32(u32(68) + i * 4)] for i in range(u32(64))]
    return {types[u32(u32(100) + i * 32)].decode('utf-8') for i in range(u32(96))}


def main():
    baseline = inventory(RUN)
    receipt = js(RUN / 'receipt.json')
    check(receipt['status'] == 'passed-java-crosscompile-only', 'Run passed in its stated Java/D8 scope')
    check(read(OUT / 'git-head.txt').decode().splitlines() == [receipt['revision'], receipt['git_tree']], 'Read-only Git HEAD/tree capture matches receipt')
    check(receipt['revision'] == '62ce9b76840b2fa56306736fc4c4fe2962780adf', 'Current HEAD base; dirty source103 is not this committed tree')
    check(ident(ROOT / 'scripts/ci/check-android-generated-java.py')['sha256'] == 'c758c9685ef536968db06dfaf9f25450eac47db83fd2531a8caa2000cf793e1a', 'Selected exact accepted R2 runner bytes')
    expected_argv = [str(ROOT / 'scripts/ci/check-android-generated-java.py')]
    for flag, key in [('swift','swift'),('swift-sdks','swift_sdks'),('android-artifact','android_artifact'),('jdk','jdk'),('android-sdk','android_sdk')]:
        expected_argv += ['--' + flag, receipt['selected_paths'][key]]
    check(receipt['argv'] == expected_argv + ['--output', str(RUN), '--execute-toolchains'], 'Exact six-consumer outer argv')
    source = receipt['source_inputs']
    check(projection(source) == receipt['source_inputs_sha256'] == 'eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158', 'Exact source103 inventory digest')
    check({p: ident(ROOT / p) for p in source} == source == js(BASE / 'store-journal-delivery/prospective-source103.json') and len(source) == 103, 'All 103 current owning inputs match run and selected source')
    accepted = js(BASE / 'store-journal-source-acceptance.json')
    delivery = js(BASE / 'store-journal-delivery/manifest.json')
    check(ident(ROOT / accepted['review'])['sha256'] == accepted['reviewSHA256'], 'Exact accepted integrity review')
    check(len(accepted['paths']) == 4, 'Exactly four accepted product/test paths')
    for p, digest in accepted['paths'].items():
        check(ident(ROOT / p)['sha256'] == digest and ident(ROOT / p) == delivery['applicationChecks'][p]['after'], 'Accepted candidate integrated byte-for-byte: ' + p)
    for p, value in delivery['protectedBindings'].items():
        if p not in delivery['metadataEdits']:
            check(ident(ROOT / p) == value, 'Protected accepted binding: ' + p)
    check(ident(BASE / 'store-journal-integrity-fix/implementation.patch')['sha256'] == 'a66174135b4756a46426c36e5f38029898774768f8be0bc4049894413f235446', 'Accepted exact four-file patch')
    frozen = {}
    ident(OUT / 'frozen-head.tar')
    with tarfile.open(OUT / 'frozen-head.tar') as archive:
        check(archive.pax_headers.get('comment') == receipt['revision'], 'Git archive commit identity')
        for member in archive:
            if member.isfile():
                check(member.name not in frozen and member.size <= 128 * 1024**2, 'Unique bounded Git archive file: ' + member.name)
                frozen[member.name] = archive.extractfile(member).read()
    old = js(BASE / 'store-journal-delivery/current-source101.json')
    check(len(old) == 101 and projection(old) == 'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca', 'Frozen Git source101 baseline digest')
    check({p: {'bytes':len(frozen[p]), 'sha256':hashlib.sha256(frozen[p]).hexdigest()} for p in old} == old, 'All 101 frozen Git files independently match old inventory')
    check(set(source) - set(old) == {'cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift','cli/Sources/MixerBuild/StoreReconciliation.swift'} and set(old) <= set(source), 'Exactly two owning input additions')
    check({p for p in old if source[p] != old[p]} == {'cli/Sources/MixerCLI/main.swift'}, 'Exactly one existing owning source changes')
    for p, change in delivery['metadataEdits'].items():
        before = frozen[p]
        check({'bytes':len(before),'sha256':hashlib.sha256(before).hexdigest()} == change['before'], 'Frozen metadata before binding: ' + p)
        for edit in change['replacements']:
            check(before.count(edit['old'].encode()) == 1, 'Unique metadata replacement: ' + edit['old'])
            before = before.replace(edit['old'].encode(), edit['new'].encode())
        check(before == read(ROOT / p) and ident(ROOT / p) == change['after'], 'Only authorized count/digest metadata changes: ' + p)
    controls = js(BASE / 'store-journal-root-integration/controls/receipt.json')
    check(controls['status'] == 'passed' and len(controls['commands']) == 6 and controls['cleanup']['allTerminalCustody'] and controls['cleanup']['scratchRemoved'] and controls['cleanup']['hold'] is None, 'Six prior root controls passed and cleaned up')
    for index, control in enumerate(controls['commands']):
        check(control['exit_code'] == 0 and control['state'] == 'TERMINAL' and control['stop'] is None and not control['cleanup_errors'] and all(control[k] is True for k in ('direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent','terminal_custody')), 'Root control terminal receipt ' + str(index))
        check(('-O' in control['argv']) == (index % 2 == 1), 'Root normal/optimized mode ' + str(index))
        logs = ''.join(read(Path(p)).decode() for p in control['logs'].values())
        count = (45,45,28,28,12,12)[index]
        check(re.search(r'Ran ' + str(count) + r' tests in [0-9.]+s\s+OK\s*$', logs) is not None, 'Root control observed test count ' + str(count))
    FACTS.update(accepted_paths=accepted['paths'], frozen_git_source_count=101, current_owning_source_count=103, source103_committed=False, controls_per_mode=[45,28,12], frozen_git_archive=ident(OUT / 'frozen-head.tar'), git_status=read(OUT / 'git-status.txt').decode())
    policy = read(ROOT / 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').decode()
    profile = json.loads(policy.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0], object_pairs_hook=pairs)
    check(profile['id'] == 'mixer.android-source-pair.9', 'Pair9 profile identity')
    expected = {'scripts/ci/check-android-generated-java.py', 'scripts/ci/check-android-binding.py',
                'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift', 'cli/Sources/MixerBuild/Resources/android-build.py'}
    for package in ('cli', 'sdk', 'updates'):
        expected.update(str(p.relative_to(ROOT)) for p in (ROOT / package / 'Sources').rglob('*') if p.is_file())
        expected.update(str(p.relative_to(ROOT)) for p in (ROOT / package).glob('Package.*') if p.is_file())
    for p in profile['adapter_files']:
        expected.add('native/android/' + ('engine/' if p.startswith('Sources/') else '') + p)
    check(set(source) == expected and len(source) == 103, 'Source inventory closed over producer packages, runner, adapter; excludes docs/tracking/tests')
    for kind, count in (('sdk', 22), ('adapter', 24)):
        check(len(profile[kind + '_files']) == count and projection(profile[kind + '_files']) == profile[kind + '_compatibility_sha256'], kind + ' exact profile projection')
    check(profile['adapter_compatibility_sha256'] == 'ee9414d3b68f9d66ba275c93339018e5eaebb161a7dc25d7056538c652305d89', 'Exact R2 adapter digest')
    previous = js(BASE / 'generated-java-pair9-r2-actual-review/audit.json')
    previous_sdk = {k:v for k,v in previous['facts']['source_inputs'].items() if k.startswith('sdk/')}
    check({k:v for k,v in source.items() if k.startswith('sdk/')} == previous_sdk, 'SDK inputs unchanged from accepted pair9 audited source')
    check(profile['sdk_compatibility_sha256'] == previous['facts']['sdk_sha256'] == 'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0', 'Exact unchanged SDK22 digest')
    commands = js(RUN / 'commands/commands.json')
    check(commands == receipt['command_records'] and len(commands) == 79, 'Both 79-command ledgers identical')
    by_label = {c['label']: c for c in commands}
    check(len(by_label) == 79, 'Unique command labels')
    def log(label, stream='stdout'):
        return read(by_label[label]['logs'][stream]['path']).decode()
    used = 0
    held = {40708, 40709, 40711, 23663, 40802230894, 20745, 20770, 20780, 20817, 20842, 20851, 20866, 2424, 2621}
    previous_end = None
    for index, c in enumerate(commands):
        label = c['label']
        check(c['cwd'] == str(ROOT), label + ': exact frozen candidate cwd')
        check(c['exit_code'] == (1 if '-tamper-' in label else 0) and c['stop'] is None and 'execution_error' not in c, label + ': exit/stop')
        check(all(c[k] is True for k in ('direct_child_reaped', 'stdout_eof', 'stderr_eof', 'owned_group_absent', 'terminal_custody'))
              and not c['cleanup_errors'] and c['group_observation']['outcome'] == 'absent'
              and c['group_observation']['attempts'] >= 1, label + ': reap, independent EOFs, positive absence')
        check(c['pid'] == c['owned_pgid'] and c['pid'] not in held and c['pid'] > 1, label + ': custody only owned group')
        check(c['signal']['attempted'] and c['signal']['name'] == 'SIGKILL' and c['signal']['outcome'] in ('sent', 'already-absent'), label + ': recorded cleanup')
        limits = {'stdout': 8388608 if label.endswith('-javap-members') else 4194304, 'stderr': 4194304}
        check(c['stream_output_limits'] == limits and c['total_output_limit'] == 67108864 and c['output_bytes_before'] == used,
              label + ': exact output bounds/accounting')
        check(c['elapsed_seconds'] < 600 and c['cleanup_seconds_limit'] == 5 and c['group_observation']['elapsed_seconds'] <= 5.01,
              label + ': command and cleanup time bounds')
        start = datetime.fromisoformat(c['started_utc']).timestamp()
        check(previous_end is None or start >= previous_end - .02, label + ': serial command custody')
        previous_end = start + c['elapsed_seconds']
        for stream, value in c['logs'].items():
            p = Path(value['path'])
            check(p == RUN / 'commands' / (f'{index:03}-{label}.' + stream), label + ': ' + stream + ' log path')
            actual = ident(p)
            check(actual == {k: value[k] for k in ('bytes', 'sha256')} and actual['bytes'] <= limits[stream], label + ': ' + stream + ' bytes/hash')
            used += actual['bytes']
    duration = previous_end - datetime.fromisoformat(commands[0]['started_utc']).timestamp()
    check(used < 67108864 and duration < 2400 and len(commands) <= 160, 'Aggregate output, time, command limits')
    check(log('revision').strip() == receipt['revision'] and log('git-tree').strip() == receipt['git_tree'], 'Raw revision/tree outputs')
    inspect = receipt['official_toolchain']
    check(json.loads(log('official-inspect')) == inspect == json.loads(log('official-inspect-postflight')), 'Full canonical pre/post inspection identity')
    check(inspect['schema'] == 1 and inspect['sdk_id'] == 'aarch64-unknown-linux-android28' and inspect['min_api'] == 28 and inspect['target_api'] == 37,
          'Canonical platform scope')
    for label in ('official-inspect', 'official-inspect-postflight'):
        check(by_label[label]['argv'][1:] == ['-B', str(ROOT / 'cli/Sources/MixerBuild/Resources/android-build.py'), 'inspect'], label + ': canonical driver invocation')
    for group in ('tools', 'metadata'):
        for name, item in inspect[group].items():
            check(ident(item['path'])['sha256'] == item['sha256'], 'Current installed ' + group + '/' + name + ' bytes')
    dist = {}
    for name, item in inspect['distributions'].items():
        dist[name] = distribution(item['path'])
        check(dist[name]['sha256'] == item['sha256'], 'Full installed distribution rehash: ' + name)
    check(ident(receipt['selected_paths']['android_sdk'] + '/platforms/android-37.0/android.jar') == receipt['android_jar'], 'Official SDK37 android.jar bytes')
    jt = receipt['javap_tool']
    check(ident(jt['path']) == {k: jt[k] for k in ('bytes', 'sha256')} and log('javap-version').strip() == log('javap-version-postflight').strip() == jt['version'], 'javap identity and version postflight')
    check(log('d8-version').strip() == receipt['d8_version'], 'D8 version raw output')
    apple = receipt['apple_producer']
    check(apple['selection'] == {'DEVELOPER_DIR':'/Applications/Xcode_26.6.app/Contents/Developer','SDKROOT':'/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk'}, 'Apple explicit environment selection')
    developer = Path(apple['selection']['DEVELOPER_DIR']).resolve(strict=True)
    sdk = Path(apple['selection']['SDKROOT']).resolve(strict=True)
    check(str(developer) == apple['resolved_developer_dir'] and str(sdk) == apple['resolved_sdkroot'], 'Apple environment resolution')
    check(ident(developer.parent / 'version.plist') == apple['xcode_version_plist'] and ident(sdk / 'SDKSettings.json') == apple['sdk_settings'], 'Apple producer metadata unchanged')
    version = plistlib.loads(read(developer.parent / 'version.plist'))
    sdkdata = js(sdk / 'SDKSettings.json')
    check(version['CFBundleShortVersionString'] == apple['xcode_version'] and version['ProductBuildVersion'] == apple['xcode_build']
          and sdkdata['Version'] == apple['sdk_version'] and sdkdata['CanonicalName'] == apple['sdk_canonical_name'], 'Apple producer metadata interpretation')
    pins = js(ROOT / 'cli/Package.resolved')['pins']
    dependencies = {p['identity']: dict(location=p['location'], revision=p['state']['revision'], version=p['state']['version'], status='') for p in pins}
    scratch = Path(receipt['cleanup']['owned_scratch_path'])
    for mode in ('debug', 'release'):
        producer = receipt['producers'][mode]
        flags = [receipt['selected_paths']['swift'], 'build', '--package-path', str(ROOT / 'cli'), '--scratch-path', str(scratch / ('producer-' + mode)),
                 '--disable-automatic-resolution', '-j', '2', '-c', mode]
        check(producer['build_argv'] == by_label[mode + '-producer-build']['argv'] == flags + ['--product', 'mixer']
              and by_label[mode + '-producer-bin']['argv'] == flags + ['--show-bin-path'] and producer['jobs'] == receipt['producer_jobs'] == 2,
              mode + ': actual producer build flags/jobs')
        cli = (Path(log(mode + '-producer-bin').strip()) / 'mixer').resolve()
        check(cli.is_relative_to(scratch.resolve() / ('producer-' + mode)) and producer['binary']['bytes'] > 1000000 and len(producer['binary']['sha256']) == 64,
              mode + ': recorded producer binary identity and isolated path')
        check(producer['dependencies'] == producer['dependencies_postflight'] == dependencies, mode + ': immutable pinned dependencies')
        for name, pin in dependencies.items():
            for phase in ('dependency', 'post-dependency'):
                label = mode + '-' + phase + '-' + name
                check(log(label + '-revision').strip() == pin['revision'] and log(label + '-status') == '', label + ': raw checkout evidence')
        check(by_label[mode + '-create']['argv'] == [str(cli), 'create', 'GeneratedJavaApp', '--platform', 'android', '--directory', str(scratch / mode / 'original'),
              '--application', 'dev.mixer.generatedjava', '--sdk-path', str(ROOT / 'sdk'), '--android-adapter-path', str(ROOT / 'native/android')], mode + ': actual CLI create')
        check(by_label[mode + '-export']['argv'] == [str(cli), 'export', str(scratch / mode / 'exported'), '--directory', str(scratch / mode / 'original')], mode + ': actual CLI export')
        for outcome in receipt['tamper'][mode]:
            case = outcome['case']
            label = mode + '-tamper-' + case
            code = 'android.sdk-profile-mismatch' if case == 'profile' else 'android.sdk-profile-required' if case == 'missing-lock' else 'android.sdk-compatibility'
            check(by_label[label]['argv'] == [str(cli), 'build', '--platform', 'android', '--directory', str(scratch / mode / 'tamper' / case)], label + ': actual producer call')
            check(json.loads(log(label)) == outcome['refusal'] and outcome['refusal']['status'] == 'error' and outcome['refusal']['code'] == code, label + ': exact refusal')
            driverlabel = mode + '-driver-tamper-' + case
            check(by_label[driverlabel]['argv'][1:] == ['-B', str(scratch / mode / 'tamper' / case / 'Generated/MixerAndroid/android-build.py'), 'build', str(scratch / mode / 'tamper' / case)], driverlabel + ': copied driver call')
            diagnostic = log(driverlabel) + log(driverlabel, 'stderr')
            check(diagnostic == outcome['driver_refusal'] and 'Android local build error:' in diagnostic and 'Traceback' not in diagnostic and not outcome['build_staging_created'], driverlabel + ': actual fail-closed refusal')
        check({v['case'] for v in receipt['tamper'][mode]} == {'sdk', 'adapter', 'descriptor', 'extra-java', 'profile', 'missing-lock'}, mode + ': all six tamper cases')
    consumers = {}
    all_inventory, all_classes, all_dex, all_lock = [], [], [], []
    for mode in ('debug', 'release'):
        for form in ('original', 'relocated', 'exported'):
            label = mode + '-' + form
            dest = RUN / label
            inv = js(dest / 'consumer-inventory.json')
            lock = js(dest / 'mixer.lock')
            r = js(dest / 'receipt.json')
            summary = receipt['consumers'][label]
            check(projection(inv) == summary['inventory_sha256'] and summary['java_count'] == 18 and summary['classes'] == 216, label + ': consumer summary')
            check(ident(dest / 'mixer.lock') == inv['mixer.lock'] and ident(dest / 'descriptor.json') == profile['default_descriptor'] == inv['Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'], label + ': retained lock and descriptor bytes')
            check(lock['android']['profile'] == {k: profile[k] for k in ('id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256', 'default_descriptor')}
                  and lock['android']['toolchain'] == inspect and lock['swiftVersion'] == inspect['swift_version'], label + ': exact profile/tool lock')
            for kind, directory in (('sdk', 'MixerSDK'), ('adapter', 'MixerAndroid')):
                prefix = 'Generated/' + directory + '/'
                files = {p[len(prefix):]: v for p, v in inv.items() if p.startswith(prefix)}
                check(all(files.get(p) == v for p, v in profile[kind + '_files'].items()), label + ': ' + kind + ' pinned byte preservation')
                check(projection(files) == (lock['sdkDigest'] if kind == 'sdk' else lock['android']['adapterDigest']), label + ': ' + kind + ' full lock digest')
                closed = ('Sources/MixerCore/', 'Sources/MixerUI/') if kind == 'sdk' else ('Sources/MixerAndroidRuntime/', 'app/src/', 'bridge/', 'contracts/')
                check({p for p in files if p.startswith(closed)} == {p for p in profile[kind + '_files'] if p.startswith(closed)}, label + ': ' + kind + ' closed source roster')
            dirs = js(dest / 'consumer-directories.json')
            check(len(dirs) == len(set(dirs)) and all(str(p) in dirs for f in inv for p in Path(f).parents if str(p) != '.'), label + ': retained directory topology')
            sources = {'Generated/MixerAndroid/' + p: v for p, v in profile['adapter_files'].items() if p.endswith('.java')}
            check(r['sources'] == sources and {p for p in inv if p.endswith('.java')} == set(sources), label + ': all 18 original product Java sources')
            jar = inspect['distributions']['android_platform']['path'] + '/android.jar'
            javac = [inspect['tools']['javac']['path'], '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-sourcepath', '', '-classpath', jar, '-d', str(dest / 'classes')]
            check(by_label[label + '-javac']['argv'] == javac + [str(scratch / mode / form / p) for p in sorted(sources)], label + ': strict actual javac closure')
            classes = inventory(dest / 'classes')
            dex = inventory(dest / 'dex')
            check(classes == r['classes'] and len(classes) == 216 and dex == r['dex'] and set(dex) == {'classes.dex'}, label + ': all class and DEX file hashes')
            classpaths = [str(dest / 'classes' / p) for p in sorted(classes)]
            check(by_label[label + '-d8']['argv'] == [inspect['tools']['d8']['path'], '--min-api', '28', '--lib', jar, '--output', str(dest / 'dex')] + classpaths, label + ': D8 min28 all-class inputs')
            check(by_label[label + '-dexdump']['argv'] == [inspect['tools']['dexdump']['path'], str(dest / 'dex/classes.dex')], label + ': exact dexdump argv')
            members = js(dest / 'member-references.json')
            check(ident(dest / 'member-references.json') == r['member_references']['inventory'] and r['member_references'] == summary['member_references'], label + ': member receipt binding')
            check(members['class_inputs'] == classes and members['argv'] == by_label[label + '-javap-members']['argv'] == [jt['path'], '-v', '-p', '-c', '-s'] + classpaths, label + ': complete javap inputs')
            raw = read(dest / 'member-references.javap.txt').decode()
            check(raw == log(label + '-javap-members') and ident(dest / 'member-references.javap.txt') == {k: members['raw_output'][k] for k in ('bytes', 'sha256')}, label + ': retained raw javap bytes')
            parsed, scoped, current = [], [], None
            for line in raw.splitlines():
                if line.startswith('Classfile '):
                    current = line[len('Classfile '):].strip()
                    scoped.append(current)
                left, sep, right = line.strip().partition(' = ')
                if sep and right.split()[0] in ('Fieldref', 'Methodref', 'InterfaceMethodref'):
                    parsed.append(dict(class_file=current, constant_pool_index=left, kind=right.split()[0], member=right.partition(' // ')[2], raw_entry=line))
            check(scoped == classpaths and parsed == members['references'] and len(parsed) == r['member_references']['count'] == 4976, label + ': complete raw 216-class/4976-reference inventory')
            binary_refs, binary_names = [], set()
            for path in classpaths:
                name, minor, major, refs = class_members(Path(path))
                check(major == 61 and minor == 0 and name + '.class' == str(Path(path).relative_to(dest / 'classes')), label + ': Java17 binary ' + name)
                binary_refs += refs
                binary_names.add('L' + name + ';')
            reported_refs = [(m['class_file'], m['constant_pool_index'], m['kind'], m['member'].replace('"', '')) for m in parsed]
            check(binary_refs == reported_refs, label + ': independently decoded binary constant-pool refs')
            descriptors = dex_classes(dest / 'dex/classes.dex')
            raw_descriptors = {line.partition(':')[2].strip().strip("'") for line in log(label + '-dexdump').splitlines() if line.strip().startswith('Class descriptor')}
            check(descriptors == raw_descriptors and binary_names <= descriptors, label + ': binary DEX matches dexdump and contains all 216 product classes')
            consumers[label] = {'class_count': len(classes), 'dex_class_count': len(descriptors), 'member_count': len(parsed), 'raw_javap': ident(dest / 'member-references.javap.txt'), 'dex': dex,
                                'class_inventory_sha256': projection(classes), 'consumer_inventory_sha256': projection(inv), 'member_inventory': ident(dest / 'member-references.json')}
            all_inventory.append(inv)
            all_classes.append(classes)
            all_dex.append(dex)
            all_lock.append(read(dest / 'mixer.lock'))
    check(all(v == all_inventory[0] for v in all_inventory), 'All six full consumer inventories byte-identical')
    check(all(v == all_classes[0] for v in all_classes), 'All six class inventories byte-identical')
    check(all(v == all_dex[0] for v in all_dex), 'All six DEX files byte-identical')
    check(all(v == all_lock[0] for v in all_lock), 'All six locks byte-identical')
    cleanup = receipt['cleanup']
    check(cleanup['owned_scratch_started'] and cleanup['owned_scratch_removed'] and cleanup['command_custody_terminal'] and not scratch.exists(), 'Owned scratch removed with terminal recorded custody')
    check(inventory(RUN) == baseline, 'Original completed retained run unchanged throughout audit')
    check({p: ident(ROOT / p) for p in source} == source, 'Final source postflight still exact')
    FACTS.update(run_receipt=ident(RUN / 'receipt.json'), source_revision=receipt['revision'], git_tree=receipt['git_tree'], source_inputs_sha256=projection(source), source_inputs=source,
                 runner=ident(ROOT / 'scripts/ci/check-android-generated-java.py'), producers=receipt['producers'], consumers=consumers,
                 distributions=dist, command_count=len(commands), aggregate_output_bytes=used, run_elapsed_seconds=round(duration, 3),
                 command_ledger=ident(RUN / 'commands/commands.json'), artifact_file_count=len(baseline), artifact_inventory_sha256=projection(baseline),
                 original_artifact_inventory=baseline, adapter_sha256=profile["adapter_compatibility_sha256"], sdk_sha256=profile["sdk_compatibility_sha256"], tamper_refusals=24)


if __name__ == '__main__':
    error = None
    try:
        main()
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    report = dict(schema=1, verdict='ACCEPT' if error is None else 'REQUESTCHANGES', error=error,
                  finished_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic() - START, 3),
                  python=sys.version, python_executable=sys.executable, python_identity=ident(Path(sys.executable).resolve()),
                  audit_script=ident(Path(__file__)), command=[sys.executable, '-I', '-B', '-S', str(Path(__file__).resolve())],
                  checks=CHECKS, facts=FACTS, read_manifest=MANIFEST,
                  limits=dict(seconds=115, artifact_files=10000, distribution_entries=250000, materialized_file_bytes=128 * 1024**2, hashed_file_bytes=4 * 1024**3),
                  scope='Completed exact-artifact Java17/D8 crosscompile review; no tool execution or API-floor approval',
                  limitations=['Producer binaries, generated source directories, dependency checkouts, and tamper trees were removed by the runner; their historical identity/admission and immutability use the hash-bound reviewed runner and retained command/consumer receipts.',
                               'Positive process-group absence is historical receipt evidence; reviewer did not probe any processes. Escaped descendants are outside runner containment.',
                               'No APK, runtime, API28 linkage/floor, device, signing, immutable published package, FieldLog release, or GA qualification.'],
                  reviewer_child_delegation=0, reviewer_compiler_jvm_native_runs=0, reviewer_process_probes_or_signals=0,
                  commits=0, pushes=0, write_ownership=str(OUT))
    destination = OUT / 'audit.json'
    if destination.exists():
        raise RuntimeError('Preserve previous audit: move its report before another invocation')
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'error': error, 'checks': len(CHECKS), 'elapsed_seconds': report['elapsed_seconds']}))
    sys.exit(0 if error is None else 1)
