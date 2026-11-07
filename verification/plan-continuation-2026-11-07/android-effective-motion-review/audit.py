"""Read-only candidate/evidence audit; pure Python admission controls on owned copies."""
import ast
import collections
import datetime
import hashlib
import json
import pathlib
import platform
import re
import stat
import sys

C = pathlib.Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-5a390519')
P = pathlib.Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4')
OUT = pathlib.Path(__file__).resolve().parent
E = C / 'verification/plan-continuation-2026-11-07/android-effective-motion'

def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read_json(path):
    return json.loads(path.read_bytes())

def compare_map(root, mapping):
    mismatches = []
    for name, expected in mapping.items():
        path = root / name
        if not path.is_file():
            mismatches.append({'path': name, 'reason': 'missing'})
        elif (hashlib.sha256(path.read_bytes()).hexdigest() != expected if isinstance(expected,str)
              else identity(path.read_bytes()) != {k: expected[k] for k in ('bytes', 'sha256')}):
            mismatches.append({'path': name, 'reason': 'identity mismatch'})
    return {'files': len(mapping), 'mismatches': mismatches}

report = {'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'python': sys.version, 'platform': platform.platform(),
          'command': ['python3', '-B', str(pathlib.Path(__file__).resolve())],
          'scope': 'source/hash/JSON and pure-Python admission only; no subprocesses, compiler, JVM, native or process probes',
          'candidate': str(C), 'parent': str(P)}
manifest = read_json(E / 'implementation-paths.json')
before = {name: (C/name).read_bytes() for name in manifest['paths']}
report['sourceRevision'] = manifest['sourceRevision']
report['implementation'] = compare_map(C, manifest['paths'])
report['implementationIdentities'] = {name: identity(data) for name, data in before.items()}
report['implementationTreeDigest'] = hashlib.sha256(''.join(name+'\0'+identity(before[name])['sha256']+'\n' for name in sorted(before)).encode()).hexdigest()
report['diagnosticParentIdentical'] = {name: (P/name).read_bytes() == before[name] for name in manifest['diagnosticTestsAlreadyByteIdenticalInParent']}
evidence = read_json(E / 'evidence-manifest.json')['files']
report['evidence'] = compare_map(E, evidence)
report['evidenceBytes'] = sum(item['bytes'] for item in evidence.values())
report['evidenceManifestIdentity'] = identity((E / 'evidence-manifest.json').read_bytes())
report['sourceMaps'] = {}
for folder in ('fullA','fullB','platform-host-complete','observer-host-final'):
    mapping = read_json(E/folder/('source-freeze.json' if folder == 'observer-host-final' else 'source-map.json'))
    if folder == 'observer-host-final': mapping = mapping['files']
    report['sourceMaps'][folder] = {'retainedInputs': compare_map(E/folder/'inputs', mapping), 'currentCandidate': compare_map(C, mapping)}
    commands = read_json(E/folder/'commands.json')
    report['sourceMaps'][folder]['nonzeroRecordedCommands'] = [x for x in commands if x.get('exit',x.get('exit_code',0)) != 0]
report['nativeSourceLock'] = compare_map(C, read_json(E/'source-lock.json')['files'])
for name in ('pair8-python-receipt.json','pair8-swift-receipt.json'):
    report[name] = compare_map(C,read_json(E/name)['sources'])
barrier = read_json(C/'native/android/tests/private-owner-barrier-map.json')
report['barrierBindings'] = {name: hashlib.sha256((C/name).read_bytes()).hexdigest() == digest for name,digest in barrier['source_sha256'].items()}
cases = read_json(E/'fullB/barrier-cases.json')
required = {r['baseline']: set(r['required_cases']) for r in barrier['records']}
actual = collections.defaultdict(set)
for case in cases['cases']:
    if case['hit']: actual[case['site']].add(case['case'])
report['barrierCoverage'] = {'mappedSites': len(required), 'records': len(cases['cases']), 'missingReported': cases['missing'],
                           'missingRequired': {k: sorted(v-actual[k]) for k,v in required.items() if v-actual[k]},
                           'unhitRecords': sum(not case['hit'] for case in cases['cases'])}

# Apply the integration patch to parent bytes in memory only.
patch = (E/'parent-integration.patch').read_text().splitlines(keepends=True)
applied = {}
index = 0
while index < len(patch):
    if not patch[index].startswith('diff --git '): index += 1; continue
    name = patch[index].strip().split(' b/',1)[1]
    end = index+1
    while end < len(patch) and not patch[end].startswith('diff --git '): end += 1
    section = patch[index:end]
    new = '--- /dev/null\n' in section
    source = [] if new else (P/name).read_text().splitlines(keepends=True)
    output = []
    cursor = 0
    h = 0
    while h < len(section):
        if not section[h].startswith('@@'): h += 1; continue
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',section[h])
        start = max(0,int(match[1])-1)
        assert start >= cursor, name
        output.extend(source[cursor:start]); cursor = start; h += 1
        while h < len(section) and not section[h].startswith('@@'):
            line = section[h]
            if line.startswith((' ','-')):
                assert cursor < len(source) and source[cursor] == line[1:], (name,cursor+1)
                cursor += 1
            if line.startswith((' ','+')): output.append(line[1:])
            h += 1
    output.extend(source[cursor:])
    applied[name] = ''.join(output).encode() == before[name]
    index = end
report['integrationPatch'] = {'identity': identity((E/'parent-integration.patch').read_bytes()),
                              'paths': applied, 'excluded': sorted(set(before)-set(applied))}

# Only the admission functions are evaluated. No module initialization/tool paths.
swift = before['cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'].decode()
profile = json.loads(swift.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
driver = before['cli/Sources/MixerBuild/Resources/android-build.py'].decode()
allowed = {'source_profile','profile_lock','profile_required','profile_failure','ordinary_directory','exact_path',
           'closed_sources','sdk_layout','adapter_layout','pinned_read','admit_source_pair','appearance_layout'}
tree = ast.parse(driver)
selected = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in allowed]
assert {node.name for node in selected} == allowed
scope = {'json':json,'hashlib':hashlib,'re':re,'stat':stat,'APPEARANCE_ASSET':'assets/MixerAppearanceV2/descriptor.json'}
exec(compile(ast.Module(body=selected,type_ignores=[]),str(C/'cli/Sources/MixerBuild/Resources/android-build.py'),'exec'),scope)
scope['SOURCE_PROFILE_HEX'] = json.dumps(profile).encode().hex()
assert scope['source_profile']() == profile
input_root = OUT/'control-input'
assert not input_root.exists(), 'one-shot controls; retain prior evidence'
profile_checks = {}
for kind in ('sdk','adapter'):
    target_root = input_root/'Generated'/('MixerSDK' if kind=='sdk' else 'MixerAndroid')
    for name,expected in profile[kind+'_files'].items():
        source = C/('sdk/'+name if kind=='sdk' else 'native/android/'+('engine/' if name.startswith('Sources/') else '')+name)
        data = source.read_bytes()
        profile_checks[kind+'/'+name] = identity(data) == expected
        target = target_root/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data); target.chmod(0o444)
descriptor = input_root/'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'
descriptor.parent.mkdir(parents=True,exist_ok=True)
descriptor.write_bytes((C/'verification/android-default-appearance-packaging/run-2/created-descriptor.json').read_bytes());descriptor.chmod(0o444)
assert identity(descriptor.read_bytes()) == profile['default_descriptor']
assert scope['admit_source_pair'](input_root,profile) == descriptor.read_bytes()
controls = {'exactPair8': 'pass', 'fileIdentities': profile_checks, 'oldLockRefusals': {}}
for label in ('pair7','pair8-old-tuple'):
    lock = dict(scope['profile_lock'](profile))
    lock['adapter_compatibility_sha256'] = 'ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e'
    if label == 'pair7': lock['id'] = 'mixer.android-source-pair.7'
    try: scope['profile_required']({'profile':lock},profile)
    except RuntimeError as error: controls['oldLockRefusals'][label] = str(error)
    else: raise AssertionError(label+' admitted')
previous = json.loads(json.dumps(profile))
previous['id'] = 'mixer.android-source-pair.7'
previous['adapter_compatibility_sha256'] = 'ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e'
previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentV2.java'] = {'bytes':15696,'sha256':'2cff6cc20d1c3c9ae751e217bba3192e315125f438312f29e933d0c79d339eb1'}
previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'] = {'bytes':14154,'sha256':'2f871e9813380b2d645b3ee636f67a7b3eae072f140163e14c7ec7ed60c562b2'}
try: scope['admit_source_pair'](input_root,previous)
except RuntimeError as error: controls['pair7MapRejectsPair8Sources'] = str(error)
else: raise AssertionError('stale map admitted')
scope['SOURCE_PROFILE_HEX'] = json.dumps(previous).encode().hex()
try: scope['source_profile']()
except RuntimeError as error: controls['pair8DecoderRejectsPair7Profile'] = str(error)
else: raise AssertionError('old profile decoded')
report['pythonAdmissionControls'] = controls
report['candidateManifestPathsStable'] = all((C/name).read_bytes()==data for name,data in before.items())
report['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(OUT/'audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({key:report[key] for key in ('implementation','evidence','sourceMaps','nativeSourceLock','barrierBindings','barrierCoverage','candidateManifestPathsStable')},indent=2))
