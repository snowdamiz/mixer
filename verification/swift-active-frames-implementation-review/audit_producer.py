#!/usr/bin/env python3
"""Independently verify retained producer inputs and replay portable metadata."""
from pathlib import Path
import datetime, hashlib, importlib.util, json, os, re, shutil, subprocess, tarfile

HERE = Path(__file__).resolve().parent
PRODUCER = HERE.parent / 'swift-active-frames-implementation'
MAIN = PRODUCER / 'results/20261024T050444826239Z'
META = PRODUCER / 'metadata/20261024T050606606361Z'
FRESH = HERE / 'layout-results/20261024T050837492680Z'
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / 'producer-audit' / STAMP
BUILD = HERE / 'build' / ('metadata-replay-' + STAMP)
OUT.mkdir(parents=True); BUILD.mkdir(parents=True)
enc = lambda x: (json.dumps(x, sort_keys=True, indent=2) + '\n').encode()
sha = lambda x: hashlib.sha256(x).hexdigest()
file_sha = lambda p: sha(p.read_bytes())


def files(path):
    with tarfile.open(path) as archive:
        return {member.name.removeprefix('vm/'): archive.extractfile(member).read()
                for member in archive if member.isfile()}


def command_logs(root, receipt, permitted_failure=()):
    for command in receipt['commands']:
        for stream in ['stdout', 'stderr']:
            assert file_sha(root / command[stream]) == command[stream + 'SHA256'], command['name']
        assert command['exitCode'] == (101 if command['name'] in permitted_failure else 0), command['name']


def portable(root):
    index = json.loads((root / 'qualifying-artifacts.json').read_text())
    assert file_sha(root / 'qualifying-artifacts.tar.gz') == index['archiveSHA256']
    archive = files(root / 'qualifying-artifacts.tar.gz')
    assert set(archive) == {member['member'] for member in index['members']}
    for member in index['members']:
        assert sha(archive[member['member']]) == member['sha256']
    return index, archive


commands = []
def run(name, argv):
    environment = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
    result = subprocess.run(argv, cwd=BUILD, env=environment, capture_output=True, timeout=60)
    row = dict(name=name, argv=argv, cwd=str(BUILD), exitCode=result.returncode)
    for stream in ['stdout', 'stderr']:
        path = OUT / (name + '.' + stream)
        path.write_bytes(getattr(result, stream)); row[stream] = path.name
        row[stream + 'SHA256'] = file_sha(path)
    commands.append(row)
    assert result.returncode == 0, name
    return result.stdout.decode()


main = json.loads((MAIN / 'receipt.json').read_text())
metadata = json.loads((META / 'receipt.json').read_text())
fresh = json.loads((FRESH / 'receipt.json').read_text())
freeze = json.loads((PRODUCER / 'source-freeze/20261024T045840237261Z/freeze.json').read_text())
assert main['sourceFreeze'] == metadata['sourceFreeze'] == fresh['sourceFreeze'] == freeze
assert freeze['sourceTreeSHA256'] == '4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
command_logs(MAIN, main, ['baseline-clippy-broad', 'baseline-clippy-complete', 'candidate-clippy-broad', 'candidate-clippy-complete'])
command_logs(META, metadata); command_logs(FRESH, fresh)
main_index, main_archive = portable(MAIN)
metadata_index, metadata_archive = portable(META)
assert len(main_index['members']) == 100 and len(metadata_index['members']) == 8
for binary in main['binaries'] + main['abi']:
    assert any(member['sha256'] == binary['sha256'] for member in main_index['members'])
for label in ['baseline', 'candidate']:
    source = files(MAIN / (label + '-source.tar.gz'))
    manifest = {name:sha(data) for name,data in sorted(source.items())}
    assert manifest == json.loads((MAIN / (label + '-manifest.json')).read_text())
    if label == 'candidate':
        assert sha(enc(manifest)) == freeze['sourceTreeSHA256']
        candidate = source
layout_source = files(META / 'layout-source.tar.gz')
layout_manifest = {name:sha(data) for name,data in sorted(layout_source.items())}
assert layout_manifest == json.loads((META / 'layout-source-manifest.json').read_text())
assert sha(enc(layout_manifest)) == metadata['variants'][0]['sourceTreeSHA256']
assert file_sha(META / 'layout-source.tar.gz') == metadata['variants'][0]['archiveSHA256']
changes = sorted(name for name in set(candidate) | set(layout_source) if candidate.get(name) != layout_source.get(name))
assert changes == ['examples/af-layout.rs', 'src/experimental_swift_reactor/execution.rs', 'src/experimental_swift_reactor/frame_operations.rs', 'src/experimental_swift_reactor/mod.rs', 'src/lib.rs']
frame = 'src/experimental_swift_reactor/frame_operations.rs'
assert layout_source[frame] == candidate[frame] + b'\n' + (META / 'layout-probe.rs.txt').read_bytes()
for name in changes:
    if name in candidate:
        assert layout_source[name].startswith(candidate[name]), name

schemas = []
classes = {'permanent':'PermanentPositions', 'active':'ActivePositions'}
for name, mapping in [('frozen-inventory-schema.json',classes), ('implementation-inventory-schema.json', {key:'Implementation'+value for key,value in classes.items()})]:
    for row in json.loads((HERE / 'accounting-final' / name).read_text()):
        schemas.append(dict(row, ownerClass=mapping[row['envelope']]))
assert (META / 'inventory.py').read_bytes() == (PRODUCER / 'inventory.py').read_bytes()
spec = importlib.util.spec_from_file_location('audited_inventory', PRODUCER / 'inventory.py')
inventory = importlib.util.module_from_spec(spec); spec.loader.exec_module(inventory)
typed = []
for item in metadata['typedMIR']:
    config = item['config']; path = META / item['path']
    assert file_sha(path) == item['sha256']
    actual = inventory.typed_rows(path, config)
    expected = [row for row in schemas if row.get('config') == config and 'mirFunction' in row]
    scrub = lambda row: {key:value for key,value in row.items() if key not in ['mirLine','ownerClass']}
    assert list(map(scrub,actual)) == list(map(scrub,expected))
    assert len(actual) == item['positions']
    functions = {}
    for row in actual:
        functions.setdefault(row['mirFunction'],set()).add(row['binding'])
        if row['window'] in ['primitive_push', 'check_construction_owner', *inventory.UNIT_HOOKS]:
            assert row['envelope'] == 'permanent'
    typed.append(dict(config=config, positions=len(actual), functions={key:len(value) for key,value in functions.items()},
                      exactTypesSourceNamesAndTransfers=True, mirLineExcluded='Compiler stream locations move with preceding CTFE; actual complete fresh MIR is preserved and hashed.'))

run('rustc-version', ['rustc','-vV'])
replays = []
for layout in metadata['layouts']:
    member = next(member for member in metadata_index['members'] if member['label'] == layout['label'])
    assert member['sha256'] == layout['binarySHA256']
    executable = BUILD / member['member']; executable.write_bytes(metadata_archive[member['member']]); executable.chmod(0o700)
    original = next(command for command in metadata['commands'] if command['name'] == layout['label']+'-run')
    output = run(layout['label'], [str(executable), *original['argv'][1:]])
    records = [line[line.index('AF_'):] for line in output.splitlines() if 'AF_' in line]
    assert records == layout['records']
    selected = [row for row in schemas if layout['mode'] == 'unit' or row.get('config') != 'unit']
    fields = {}; owner_class = {}
    for line in records:
        if line.startswith('AF_FIELD|'):
            _, cls, name, offset, size, align = line.split('|')
            assert name not in fields; owner_class[name] = cls
            fields[name] = dict(offset=int(offset), bytes=int(size), alignment=int(align))
    expected = next(item for item in fresh['layouts'] if item['unit'] == (layout['mode'] == 'unit'))
    assert fields == expected['fields']
    assert set(fields) == {row['field'] for row in selected}
    assert all(owner_class[row['field']] == row['ownerClass'] for row in selected)
    bounds = list(map(int,next(line for line in records if line.startswith('AF_BOUNDS|')).split('|')[1:]))
    assert [bounds[i] for i in [2,3,4,5,8]] == expected['total'][:5]
    replays.append(dict(label=layout['label'], binarySHA256=member['sha256'], fields=len(fields),
                        records=len(records), exactPortableReplay=True, everyFieldMatchesFreshIndependentCompilation=True,
                        bounds=bounds))

inputs = {}
for prefix, root, names in [('producer-main',MAIN,['receipt.json','qualifying-artifacts.json']),
                            ('producer-metadata',META,['receipt.json','qualifying-artifacts.json','layout-source-manifest.json','layout-source.tar.gz','layout-probe.rs.txt','production-typed-roles.json','unit-typed-roles.json','production.mir','unit.mir','inventory.py']),
                            ('independent-layout',FRESH,['receipt.json'])]:
    dest = OUT / 'inputs' / prefix; dest.mkdir(parents=True)
    for name in names:
        shutil.copyfile(root/name,dest/name);inputs[str((dest/name).relative_to(OUT))] = file_sha(dest/name)
receipt = dict(schema=1,status='passed-retained-producer-audit-and-eight-portable-metadata-replays',
               observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceFreeze=freeze,inputs=inputs,
               commands=commands,portableProducerRuntimeArtifactsVerified=len(main_index['members']),
               producerCommandsVerified=len(main['commands']),producerMetadataCommandsVerified=len(metadata['commands']),
               derivedMetadataSourceChanges=changes,typedMIR=typed,replays=replays,ownedBuildScratch=str(BUILD),
               scope='Host compiler metadata replay and retained-evidence integrity; independent original-owner runtime evidence is a separate receipt. Native/GA gates remain unrun.')
(OUT/'receipt.json').write_bytes(enc(receipt))
print(json.dumps(dict(status=receipt['status'],metadataReplays=len(replays),sourceTreeSHA256=freeze['sourceTreeSHA256'],receipt=str(OUT/'receipt.json')),indent=2))
