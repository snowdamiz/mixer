#!/usr/bin/env python3
"""File-only bindings and inspection shared by this build evidence lane."""
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import stat
import struct
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / 'attempt-1'
SCRATCH = OUT / 'owned-build'
REVISION = '6b8aba350224ed19f678669bdbea6b359d8de68b'
DEV = Path('/Applications/Xcode_26.6.app/Contents/Developer')
SDK = DEV / 'Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk'
SWIFT = DEV / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc'
SELECTION = 'verification/apple-passive-lifecycle-generic-build/selection.json'
SOURCE = 'verification/apple-passive-lifecycle-observer/review-source-package.tar.gz'
OLD_SOURCE = 'verification/apple-focus-system-observation/review-source-package.tar.gz'
ORIGINAL = 'verification/apple-focus-reference-diagnostic-v1/compile-attempt-1'
RECIPE = ORIGINAL + '/command-receipts.json'
OLD_SCRATCH = str(ROOT / ORIGINAL / 'scratch')
CHANGED = ['accepted/source/Prototype/main.swift']
ADDED = ['accepted/source/Prototype/PassiveLifecycleData.swift', 'accepted/source/Prototype/PassiveLifecycleObserver.swift']
PROTOTYPE_NAMES = ['AppearanceNativePathsV2.swift', 'AuthoredToggleCarrier.swift', 'DiagnosticRequirement.swift', 'DiagnosticTrace.swift', 'NativeInterruptionChecks.swift', 'PanCommitChecks.swift', 'PassiveLifecycleData.swift', 'PassiveLifecycleObserver.swift', 'SemanticActivationChecks.swift', 'TogglePanAdmission.swift', 'TogglePanPolicy.swift', 'main.swift']
HARNESS_NAMES = ['DiagnosticTransport.swift', 'PublicSwitchSelection.swift', 'SettingsFailureDiagnostic.swift', 'ToggleUITests.swift']
HANDOFFS = {
 'verification/apple-passive-lifecycle-observer/handoff.json': ('9e30a9aeef107094d70b17fc83fc632f0278af9d0384a58564cd7b0456efbd75', 73),
 'verification/apple-passive-lifecycle-review/handoff.json': ('376642724000ecd82914f322337ee498b5b083f3bd927dcfab03d8259d425a27', 53),
 'verification/apple-focus-system-native-build/handoff.json': ('a51cc040f4093661789317f2f508bd61888579dd059cc1cef6c2f73920e5aa57', 53),
 'verification/apple-focus-reference-diagnostic-v1/handoff.json': ('9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c', 36),
 'verification/apple-focus-reference-diagnostic-v1-independent-review/handoff.json': ('d70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb', 12),
}
PINS = {
 SOURCE: '042c47cc39166ad25e475a5f213815e2aab926590a520e3eb51e0e04cd97774e',
 OLD_SOURCE: 'd1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda',
 RECIPE: '5d4b081c7d9b328a67e431584caaecb423abfa4438bc3ce120962153fe75cafb',
 ORIGINAL + '/packaging-derivation.json': '91d2eb1fbeea1feb960b5347876ee1506c7f30f877e8fc0894b193733c01f5c7',
 ORIGINAL + '/tool-bindings.json': 'f2f194e2e5476cdd5f79518446442d99ded76c2bf31cfb87ad0a443219b6aec8',
 'verification/apple-focus-reference-diagnostic-v1/build.py': '9af6dc5f47437143ed253c4f12837d05b9d73bacc2803960534968ee74d3a2e7',
 **{n: v[0] for n, v in HANDOFFS.items()},
}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
def row(raw, mode): return {'kind': 'file', 'mode': mode, 'bytes': len(raw), 'sha256': sha(raw)}
def save(name, value): (OUT / name).write_bytes(canonical(value))

def safe(name):
    p = PurePosixPath(name)
    assert name and not p.is_absolute() and '..' not in p.parts and str(p) == name, name

def binding(path, exclusive=False):
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode) and not path.is_symlink(), path
    assert not exclusive or s.st_nlink == 1, path
    return row(path.read_bytes(), stat.S_IMODE(s.st_mode))

def payload(raw):
    result, seen = {}, set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for m in archive:
            safe(m.name)
            assert m.name not in seen, m.name
            seen.add(m.name)
            assert m.isdir() or m.isfile(), (m.name, m.type)
            if m.isfile(): result[m.name] = (archive.extractfile(m).read(), m.mode)
    for name in result:
        assert not any(str(p) in result for p in PurePosixPath(name).parents)
    return result

def rows(values): return {n: row(b, m) for n, (b, m) in sorted(values.items())}

def materialize(values, destination):
    assert not destination.exists()
    destination.mkdir(parents=True)
    for name, (raw, mode) in sorted(values.items()):
        safe(name)
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        p.chmod(mode)

def tree(path):
    result = {}
    for p in sorted(path.rglob('*')):
        s = p.lstat()
        assert stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode), p
        if stat.S_ISREG(s.st_mode): result[str(p.relative_to(path))] = binding(p, True)
    return result

def archive_tree(path, source):
    expected = tree(source)
    assert not path.exists()
    with path.open('wb') as out:
        with gzip.GzipFile(filename='', fileobj=out, mode='wb', mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w', format=tarfile.PAX_FORMAT) as archive:
                for name, r in expected.items():
                    m = tarfile.TarInfo(name)
                    m.size, m.mode, m.mtime = r['bytes'], r['mode'], 0
                    archive.addfile(m, io.BytesIO((source / name).read_bytes()))
    assert rows(payload(path.read_bytes())) == expected
    return expected

def verify_inputs():
    for n, expected in PINS.items(): assert binding(ROOT / n)['sha256'] == expected, n
    counts = {}
    for n, (_, count) in HANDOFFS.items():
        h = json.loads((ROOT / n).read_bytes())
        assert len(h['members']) == count, n
        for name, expected in h['members'].items():
            safe(name)
            actual = binding(ROOT / name)
            assert all(actual[k] == v for k, v in expected.items()), name
        counts[n] = count
    selection = json.loads((ROOT / SELECTION).read_bytes())
    assert selection['sourceContextRevisionReportedByRoot'] == REVISION
    assert selection['sourceArchiveSHA256'] == PINS[SOURCE]
    assert selection['genericSimulatorBuildOnly'] and selection['freshAppRequired'] and selection['freshRunnerRequired']
    assert not selection['reuseOldProducts'] and not selection['sourceEditsPermitted'] and not selection['runtimeSelected']
    assert selection['rootCoordinationConfirmed']
    package, old = payload((ROOT / SOURCE).read_bytes()), payload((ROOT / OLD_SOURCE).read_bytes())
    assert len(package) == 42 and len(old) == 40 and set(old) < set(package)
    assert sorted(set(package) - set(old)) == ADDED
    assert [n for n in sorted(old) if package[n][0] != old[n][0]] == CHANGED
    assert all(v[1] == 0o444 for v in package.values()) and all(v[1] == 0o444 for v in old.values())
    assert sorted(n.rsplit('/', 1)[1] for n in package if n.startswith('accepted/source/Prototype/') and n.endswith('.swift')) == PROTOTYPE_NAMES
    assert sorted(n.rsplit('/', 1)[1] for n in package if n.startswith('accepted/harness/') and n.endswith('.swift')) == HARNESS_NAMES
    assert sum(n.endswith('.swift') for n in package) == 37
    return {'pins': PINS, 'selection': binding(ROOT / SELECTION), 'handoffMembersVerified': counts, 'sourceMembers': 42,
            'changedBytesFromPriorCompileClosure': CHANGED, 'addedSourceMembers': ADDED, 'unchangedCompileClosureFileBytes': 39,
            'selectedArchiveMode': 0o444, 'prototypeSwiftFiles': PROTOTYPE_NAMES, 'harnessSwiftFiles': HARNESS_NAMES, 'overallSwiftFiles': 37}

def recipe_commands():
    old = json.loads((ROOT / RECIPE).read_bytes())['commands']
    result = []
    for c in old:
        argv = [a.replace(OLD_SCRATCH, str(SCRATCH)) for a in c['argv']]
        explicit = {k: v.replace(OLD_SCRATCH, str(SCRATCH)) for k, v in c['explicitEnvironment'].items()}
        if c['name'] == 'app':
            old_sources = [a for a in argv if a.endswith('.swift')]
            expected_old = [str(SCRATCH / 'accepted/source/Prototype' / n) for n in PROTOTYPE_NAMES if n not in ['PassiveLifecycleData.swift', 'PassiveLifecycleObserver.swift']]
            assert old_sources == expected_old
            first = argv.index(old_sources[0]); end = first + len(old_sources)
            assert argv[first:end] == old_sources
            argv[first:end] = [str(SCRATCH / 'accepted/source/Prototype' / n) for n in PROTOTYPE_NAMES]
        result.append({'name': c['name'], 'argv': argv, 'explicitEnvironment': explicit,
                       'cwd': c['cwd'], 'timeoutSeconds': c['timeoutSeconds']})
    assert [c['name'] for c in result] == ['xcode-version', 'swift-version', 'sdk-version', 'python-version', 'mixer-core', 'mixer-ui', 'app', 'runner']
    selected = payload((ROOT / SOURCE).read_bytes())
    explicit_swift = [a for c in result for a in c['argv'] if a.endswith('.swift')]
    expected = [str(SCRATCH / n) for n in selected if n.startswith('accepted/source/') and n.endswith('.swift')]
    assert sorted(explicit_swift) == sorted(expected) and len(expected) == 33
    project = selected['accepted/harness/MixerToggleUITests.xcodeproj/project.pbxproj'][0].decode()
    for n in HARNESS_NAMES: assert n in project
    assert sum(n.endswith('.swift') for n in selected if n.startswith('accepted/harness/')) == 4
    return result

def warning_messages(raw):
    return [line.split('warning:', 1)[1].strip() for line in raw.decode().splitlines() if 'warning:' in line]

def version(x): return f'{x >> 16}.{(x >> 8) & 255}.{x & 255}'

def macho(raw):
    """Inspect Mach-O data only; never load or execute a product."""
    if raw[:4] == b'\xca\xfe\xba\xbe':
        n = struct.unpack_from('>I', raw, 4)[0]
        assert n <= 16 and 8 + n * 20 <= len(raw)
        slices = []
        for i in range(n):
            cpu, sub, start, size, align = struct.unpack_from('>5I', raw, 8 + i * 20)
            assert start + size <= len(raw)
            slices.append({'cpuType': cpu, 'cpuSubtype': sub, 'offset': start, 'bytes': size,
                           'inspection': macho(raw[start:start + size])})
        return {'format': 'fat32', 'slices': slices}
    assert raw[:4] == b'\xcf\xfa\xed\xfe', raw[:4].hex()
    _, cpu, sub, typ, n, size, flags, _ = struct.unpack_from('<8I', raw)
    assert 32 + size <= len(raw) and n <= 1024
    result = {'format': 'mach-o64-le', 'cpuType': cpu, 'cpuSubtype': sub, 'fileType': typ,
              'loadCommandCount': n, 'flags': flags, 'buildVersions': [], 'dylibs': [], 'rpaths': [], 'uuids': [], 'codeSignatureCommands': 0}
    o = 32
    for _ in range(n):
        cmd, count = struct.unpack_from('<2I', raw, o)
        assert count >= 8 and o + count <= 32 + size
        data = raw[o:o + count]
        if cmd == 0x32:
            _, _, platform, minimum, sdk, tools = struct.unpack_from('<6I', data)
            result['buildVersions'].append({'platform': platform, 'minimumOS': version(minimum), 'sdk': version(sdk), 'toolCount': tools})
        elif cmd in [0xc, 0xd, 0x80000018, 0x8000001f, 0x80000023]:
            start = struct.unpack_from('<I', data, 8)[0]
            result['dylibs'].append({'command': cmd, 'name': data[start:].split(b'\0', 1)[0].decode()})
        elif cmd == 0x8000001c:
            start = struct.unpack_from('<I', data, 8)[0]
            result['rpaths'].append(data[start:].split(b'\0', 1)[0].decode())
        elif cmd == 0x1b: result['uuids'].append(data[8:24].hex())
        elif cmd == 0x1d: result['codeSignatureCommands'] += 1
        o += count
    assert o == 32 + size
    return result

def product_inspection(values):
    result = {'machO': {}, 'plists': {}}
    for name, (raw, _) in sorted(values.items()):
        if raw[:4] in [b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe']:
            result['machO'][name] = {'binding': row(raw, values[name][1]), **macho(raw)}
        if name.endswith('Info.plist'):
            parsed = plistlib.loads(raw)
            result['plists'][name] = {'binding': row(raw, values[name][1]), 'properties': parsed}
    return result
