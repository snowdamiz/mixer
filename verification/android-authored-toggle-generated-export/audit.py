#!/usr/bin/env python3
"""Verify recorded generated-export evidence without executing its contents."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
RUN = PACKET / 'commands/run-1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, label):
    if not value:
        raise ValueError(label)


def check(raw, row):
    require(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'byte binding')


receipt = json.loads((RUN / 'receipt.json').read_bytes())
require(receipt['status'] == 'passed' and receipt['inputs_unchanged'], 'run result')
require(receipt['cleanup']['removed'] and not receipt['cleanup']['owned_process_groups_remaining'], 'cleanup result')
require(not Path(receipt['scratch']).exists(), 'owned scratch remains')
require(digest((RUN / 'collector.py').read_bytes()) == receipt['collector_sha256'], 'executed collector')
inputs = json.loads((RUN / 'inputs-before.json').read_bytes())
require(inputs == json.loads((RUN / 'inputs-after.json').read_bytes()), 'input before/after')
for path, row in inputs.items():
    check((ROOT / path).read_bytes(), row)
    check((RUN / 'source-inputs' / path).read_bytes(), row)
require(digest(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode()) == receipt['source_tree_sha256'], 'source tree')
for command in receipt['commands']:
    require(command['child_returned'] and not command['timed_out'], 'command completion')
    require(json.loads((RUN / (command['name'] + '.json')).read_bytes()) == command, 'command receipt')
    for stream in ['stdout', 'stderr']:
        check((RUN / command[stream]['path']).read_bytes(), command[stream])
    expected_failure = command['name'] == 'javac-omitted-source-control' or command['name'].startswith(('cli-lock-', 'driver-lock-'))
    require((command['exit'] != 0) if expected_failure else (command['exit'] == 0), 'command exit')
for mode in ['debug', 'release']:
    output = (RUN / ('swift-tests-' + mode + '.stdout')).read_text()
    require('Test run with 2 tests in 0 suites passed' in output, 'actual function count')
    require('with 6 test cases passed' in output and output.count('Test case passing 2 arguments') == 6, 'actual case count')
    for filename in ['NativeCoordinatorV2.java', 'AuthoredToggleInputV2.java']:
        for change in ['edit', 'remove', 'rename']:
            require(f'filename → "{filename}", change → "{change}"' in output, 'case absent')
commands = {r['name']: r for r in receipt['commands']}
for name in ['javac-exported', 'javac-omitted-source-control']:
    argv = commands[name]['argv']
    require('-Werror' in argv and '-Xlint:all' in argv and '-implicit:none' in argv, 'strict compilation')
    require(argv[argv.index('--release') + 1] == '17', 'Java bytecode version')
    require(argv[argv.index('-sourcepath') + 1].endswith('/empty-sourcepath'), 'no implicit repository sources')
    require(argv[argv.index('-classpath') + 1].endswith('/platforms/android-37.0/android.jar'), 'classpath')
require(len([a for a in commands['javac-exported']['argv'] if a.endswith('.java')]) == 14, 'positive source count')
require(len([a for a in commands['javac-omitted-source-control']['argv'] if a.endswith('.java')]) == 13, 'negative source count')
require(not any(a.endswith('/AuthoredToggleInputV2.java') for a in commands['javac-omitted-source-control']['argv']), 'negative omission')
expected_classes = json.loads((PACKET / 'proposal-observations.json').read_bytes())['retainedAcceptedAuthoredClassArtifacts']
classes = json.loads((RUN / 'classes.json').read_bytes())
require(len(classes) == 160 and len(expected_classes) == 4, 'class counts')
for name, row in expected_classes.items():
    require(classes[name.removeprefix('production-classes/')] == row, 'unchanged authored class')
project = json.loads((RUN / 'generated-project.json').read_bytes())
dex = json.loads((RUN / 'dex.json').read_bytes())
check((RUN / 'generated-and-compiled.tar.gz').read_bytes(), receipt['retained_archive'])
with tarfile.open(RUN / 'generated-and-compiled.tar.gz', 'r:gz') as archive:
    files = [m for m in archive.getmembers() if m.isfile()]
    require(len(files) == len({m.name for m in files}), 'duplicate archive files')
    require(all(m.isdir() or m.isfile() for m in archive.getmembers()), 'archive member type')
    require(all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in archive.getmembers()), 'archive paths')
    expected = {}
    for prefix, rows in [('GeneratedConsumer', project), ('classes', classes), ('dex', dex)]:
        expected.update({prefix + '/' + name: row for name, row in rows.items()})
    require({m.name for m in files} == set(expected), 'archive closure')
    for m in files:
        check(archive.extractfile(m).read(), expected[m.name])
    for name, row in receipt['exported_java'].items():
        raw = archive.extractfile('GeneratedConsumer/Generated/MixerAndroid/app/src/dev/mixer/android/' + name).read()
        check(raw, row)
        require(raw == (ROOT / 'native/android/app/src/dev/mixer/android' / name).read_bytes(), 'export byte identity')
print(json.dumps({'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'command': ['python3', '-B', str(Path(__file__).relative_to(ROOT))], 'python': platform.python_version(), 'auditor_sha256': digest(Path(__file__).read_bytes()), 'source_tree_sha256': receipt['source_tree_sha256'], 'input_bindings_verified': len(inputs), 'command_outputs_verified': len(receipt['commands']), 'exported_java_sources': 14, 'classes': 160, 'unchanged_authored_classes': 4, 'dex': dex, 'debug_release_test_functions_each': 2, 'lock_cases_each': 6, 'actual_consumer_rejections': 6, 'negative_control': 'Omitting authored source fails strict compilation', 'archive_members_verified': len(files), 'scratch_removed': True, 'artifact_extracted_or_executed': False, 'native_runtime_or_capture_started': False, 'product_or_GA_qualification': False}, indent=2))
