"""Bounded official javap probes over retained attempt-2 classfiles only."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location('execution_fix_runner', ROOT / 'scripts/ci/check-android-generated-java.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
ATTEMPT = Path('/tmp/mixer-20261107-generated-java-pair7-02-xcode266')


def binary_member_indexes(path):
    data = path.read_bytes()
    M.require(data[:4] == b'\xca\xfe\xba\xbe', 'Not a retained classfile')
    count = struct.unpack_from('>H', data, 8)[0]
    pos, index, members = 10, 1, []
    sizes = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4,
             12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    kinds = {9: 'Fieldref', 10: 'Methodref', 11: 'InterfaceMethodref'}
    while index < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            size = struct.unpack_from('>H', data, pos)[0]
            pos += 2 + size
        else:
            M.require(tag in sizes, 'Unsupported constant-pool tag')
            if tag in kinds:
                members.append((str(path), '#' + str(index), kinds[tag]))
            pos += sizes[tag]
        M.require(pos <= len(data), 'Truncated constant pool')
        index += 2 if tag in (5, 6) else 1
    return members


def main():
    name = sys.argv[1]
    flags = {'01-full': ['-v', '-p', '-c', '-s'], '02-minimum': ['-v'],
             '03-fixed': ['-v', '-p', '-c', '-s']}[name]
    out = HERE / name
    out.mkdir(exist_ok=False)
    retained = json.loads((ATTEMPT / 'commands/commands.json').read_text())[-1]
    javap, classes = Path(retained['argv'][0]), list(map(Path, retained['argv'][5:]))
    baseline = json.loads((HERE / 'baseline.json').read_text())
    M.require(M.identity(javap) == {k: baseline['javap_tool'][k] for k in ('bytes', 'sha256')}, 'javap changed')
    before = M.inventory(ATTEMPT / 'debug-original/classes')
    commands = M.Commands(out, os.environ.copy(), seconds=25, command_seconds=20,
                          output_bytes=20 * 1024 * 1024, total_output_bytes=20 * 1024 * 1024)
    if name == '03-fixed':
        commands = M.Commands(out, os.environ.copy(), seconds=25, command_seconds=20,
                              total_output_bytes=20 * 1024 * 1024)
    options = {'stdout_bytes': M.JAVAP_STDOUT_BYTES} if name == '03-fixed' else {}
    dump = commands.run(name, [javap, *flags, *classes], **options)
    members = M.member_references(dump, classes)
    binary = sorted(x for path in classes for x in binary_member_indexes(path))
    parsed = sorted((r['class_file'], r['constant_pool_index'], r['kind']) for r in members)
    M.require(binary == parsed, 'Actual binary constant-pool member inventory differs')
    M.require(M.inventory(ATTEMPT / 'debug-original/classes') == before, 'Retained inputs changed')
    M.save(out / 'members.json', members)
    summary = {'status': 'passed-retained-classfile-probe-only', 'command': commands.records[0],
        'javap_tool': baseline['javap_tool'], 'python': sys.version, 'revision': baseline['revision'],
        'class_inputs_sha256': M.source_digest(before), 'class_count': len(classes),
        'nested_class_count': sum('$' in p.name for p in classes), 'member_count': len(members),
        'binary_constant_pool_member_indexes_equal': True, 'runner': M.identity(ROOT / 'scripts/ci/check-android-generated-java.py'),
        'retained_inputs_unchanged': True, 'max_seconds': 20, 'max_output_bytes': 20 * 1024 * 1024,
        'scope': 'No producer build, javac, D8, device, runtime, or full consumer matrix execution'}
    M.save(out / 'proof.json', summary)
    print(json.dumps({k: summary[k] for k in ('status', 'class_count', 'nested_class_count', 'member_count')} |
                     {'bytes': len(dump.encode()), 'seconds': commands.records[0]['elapsed_seconds']}))


if __name__ == '__main__':
    main()
