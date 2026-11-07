#!/usr/bin/env python3
"""Materialize the root-selected accepted receiver successor, without native calls."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = HERE.parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()

def put(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)

def function(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno])

root_path = PARENT/'apple-settings-root-selection.json'
root_raw = root_path.read_bytes()
root = json.loads(root_raw)
pins = {
    'candidatePacket': '76d499c09102741e1975ef6dd8a48b7c4b4897c3dc6a5a8fa64dfb7dd2345618',
    'review': 'c81db0d3c29f21d629f127358178d7592060a1980a4109561fa20fa8082261b6',
    'runtimeArchive': '4adaecd0194bfef54f293c0939d7489c19f81c8fe5df03dff83439445dacc7e9',
    'selectionTemplate': '4468517e8ad7b6e8ad7914fe725db1115dbfc0987a15f1fa8f60c9d5009cd202',
    'retainedProducts': '495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904',
}
for name, digest in pins.items():
    assert root[name]['sha256'] == digest
    assert sha((REPO/root[name]['path']).read_bytes()) == digest
assert root['nativeAttemptBudget']['selectedNow'] == 1 and root['nativeAttemptBudget']['automaticRetry'] is False
assert root['fixedSettingsBudgetSeconds'] == 29 and root['rebuild'] is False
assert root['tests'] == ['test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab']
scratch = Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-settings-runtime-', dir='/tmp')).resolve()
scratch.chmod(0o755)
temp = scratch/'tmp'
temp.mkdir(mode=0o700)
prior_path = REPO/'verification/apple-passive-lifecycle-runtime-preparation/prepare.py'
prior = prior_path.read_text()
supervisor_path = PARENT/'apple-runtime/run_w04.py'
supervisor = supervisor_path.read_text()
guard_source = '\n\n'.join(function(prior, n) for n in ['require','sha','stable','row','safe_name','archive_payload','tree','materialize'])
dispatch_source = function(prior, 'dispatch')
original_dispatch_source = dispatch_source
dispatch_source = dispatch_source.replace("source['archive']['sha256'], 'selected/')", "source['archive']['sha256'], 'selected/', explicit_directories=False)",1)
assert dispatch_source != original_dispatch_source
header = '''#!/usr/bin/env python3
"""Fresh accepted packet binding; historical dispatcher grants no authority."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
'''
constants = f'''\nHERE = Path({str(HERE)!r})
ROOT = Path({str(REPO)!r})
BASE = Path({str(scratch)!r})
ROOT_SELECTION = Path({str(root_path)!r})
ROOT_SELECTION_SHA = {sha(root_raw)!r}
BUILD_ATTEMPT = Path({json.loads((REPO/root['selectionTemplate']['path']).read_bytes())['productArchive']!r}).parent
PRODUCT = {pins['retainedProducts']!r}
OUTPUT_PREFIX = 'native-run-v9-'
PINS = {pins!r}
'''
verify_source = '''
def load_baseline():
    path = HERE/'sealed-inputs/verification/apple-passive-lifecycle-runtime-preparation/prepare.py'
    spec = importlib.util.spec_from_file_location('_sealed_baseline_verify', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.BUILD_ATTEMPT = BUILD_ATTEMPT
    return module

def verify():
    require(row(ROOT_SELECTION)['sha256'] == ROOT_SELECTION_SHA, 'Root selection changed')
    selected = json.loads(ROOT_SELECTION.read_bytes())
    for name, digest in PINS.items():
        require(selected[name]['sha256'] == digest and row(ROOT/selected[name]['path'])['sha256'] == digest,
                'Accepted root artifact changed: '+name)
    require(selected['nativeAttemptBudget']['selectedNow'] == 1 and not selected['nativeAttemptBudget']['automaticRetry']
            and selected['fixedSettingsBudgetSeconds'] == 29 and selected['rebuild'] is False
            and selected['tests'] == ['test000PublicSettingsFullKeyboardAccess','test010ReferenceFirstTab'],
            'Exact root attempt/budget/test selection required')
    packet_raw = (HERE/'packet.json').read_bytes()
    require((BASE/'packet.json').read_bytes() == packet_raw, 'Concrete packet changed')
    packet = json.loads(packet_raw)
    require(packet['rootSelectionSHA256'] == ROOT_SELECTION_SHA and packet['acceptedBindings'] == selected,
            'Successor packet root authorization differs')
    for name, expected in packet['files'].items():
        require(row(HERE/name) == expected, 'Successor driver changed: '+name)
    baseline = load_baseline()
    baseline_verified = baseline.verify()
    require(baseline_verified['packetSHA256'] == packet['baselinePacketSHA256'], 'Baseline source/product safeguards changed')
    candidate = json.loads((ROOT/selected['candidatePacket']['path']).read_bytes())
    review = json.loads((ROOT/selected['review']['path']).read_bytes())
    require(review['blockingFindings'] == [] and review['candidatePacketSHA256'] == PINS['candidatePacket']
            and review['candidateRuntimeArchiveSHA256'] == PINS['runtimeArchive']
            and review['candidateSelectionTemplateSHA256'] == PINS['selectionTemplate'], 'Independent acceptance differs')
    for key in ['baselineCompileArchive','baselineNativeHandoff','baselineNativeResult','baselineRuntimeArchive',
                'candidateSelectionTemplate','productArchive','runtimeArchive']:
        binding = candidate[key]
        actual = row(ROOT/binding['path'])
        require(actual['sha256'] == binding['sha256'] and actual['bytes'] == binding['bytes'], 'Candidate artifact changed: '+key)
    source = json.loads((BASE/'runtime-source-manifest.json').read_bytes())
    require(source['files'] == candidate['runtimeFiles'] and len(source['files']) == 32
            and sha(stable(source['files'])) == source['treeSHA256']
            and source['archive']['sha256'] == PINS['runtimeArchive'], 'Accepted runtime manifest differs')
    payload = archive_payload(BASE/'runtime-sources.tar.gz',source['files'],PINS['runtimeArchive'],'selected/',explicit_directories=False)
    old_manifest = json.loads((baseline.BASE/'runtime-source-manifest.json').read_bytes())
    old_payload = baseline.archive_payload(baseline.BASE/'runtime-sources.tar.gz', old_manifest['files'],
                                          old_manifest['archive']['sha256'],'selected/')
    changed = [n for n in sorted(payload) if payload[n] != old_payload[n]]
    require(set(payload) == set(old_payload) and changed == candidate['changedRuntimeFiles']
            and len(changed) == 1 and len(payload)-len(changed) == 31, 'Only accepted Python receiver delta allowed')
    template_raw = (ROOT/selected['selectionTemplate']['path']).read_bytes()
    require((BASE/'selection-template.json').read_bytes() == template_raw, 'Exact accepted selection bytes required')
    template = json.loads(template_raw)
    old_template = json.loads((baseline.BASE/'selection-template.json').read_bytes())
    old_template['files'] = {n:sha(raw) for n,raw in payload.items()}
    require(template == old_template, 'Template changed beyond accepted source binding')
    require((BASE/'importer.py').read_bytes() == payload['importer.py'], 'Original importer differs')
    products = json.loads((BUILD_ATTEMPT/'product-manifest.json').read_bytes())
    require(template['productManifest'] == products and products['sourceTreeSHA256'] == candidate['sourceTreeSHA256']
            and len(products['products']) == 55 and candidate['compileSourceFilesByteIdentical'] == 42
            and candidate['settingsBudgetSeconds'] == 29 and candidate['observationBudgetSeconds'] == 3
            and candidate['originalSettingsOracleUnchanged'] and candidate['originalTabOracleUnchanged']
            and candidate['appAndUITestRunnerRebuildRequired'] is False, 'Retained product/oracle/budget contracts differ')
    archive_payload(BUILD_ATTEMPT/'products.tar.gz',products['products'],PRODUCT,explicit_directories=False)
    return dict(packetSHA256=sha(packet_raw), nativeExecuted=False,
                scope='Fresh root-selected accepted receiver; exact baseline safeguards and retained products')
'''
dispatcher = header + constants + '\n' + guard_source + '\n' + verify_source + '\n' + dispatch_source + '\n'
put(HERE/'dispatch_successor.py', dispatcher.encode())
new_prepare = '''def prepare():
    cloned = prepare_baseline()
    p = load(HERE/'dispatch_successor.py')
    result = p.verify()
    write(HERE/'successor-preflight.json', result)
    return p.BASE
'''
new_child = '''def child():
    cloned = Path(sys.argv[2]); selection = Path(sys.argv[3])
    p = load(HERE/'dispatch_successor.py')
    assert cloned == p.BASE
    root = json.loads(selection.read_bytes())
    print(json.dumps(p.dispatch(root['packetSHA256'],str(selection),sha(selection.read_bytes()))),flush=True)
'''
supervisor = supervisor.replace(function(supervisor, 'prepare'),function(supervisor,'prepare').replace('def prepare():','def prepare_baseline():',1)+'\n\n'+new_prepare,1)
supervisor = supervisor.replace(function(supervisor,'child'),new_child,1)
supervisor = supervisor.replace("'Never retry W04'", "'Never retry accepted Settings R2'")
supervisor = supervisor.replace("{20745, 20770, 20780, 20817, 20842, 20851, 20866, 2424}","{20745, 20770, 20780, 20817, 20842, 20851, 20866, 2424, 2621}")
put(HERE/'run_r2.py',supervisor.encode())
# Load only archive helpers for safe exact materialization. No dispatcher is invoked here.
import importlib.util
spec = importlib.util.spec_from_file_location('_archive_guards',prior_path)
guards = importlib.util.module_from_spec(spec); spec.loader.exec_module(guards)
candidate = json.loads((REPO/root['candidatePacket']['path']).read_bytes())
archive = REPO/root['runtimeArchive']['path']
payload = guards.archive_payload(archive,candidate['runtimeFiles'],pins['runtimeArchive'],'selected/',explicit_directories=False)
manifest = dict(schema=1,files=candidate['runtimeFiles'],treeSHA256=sha(stable(candidate['runtimeFiles'])),archive=guards.row(archive))
put(scratch/'runtime-sources.tar.gz',archive.read_bytes())
put(scratch/'runtime-source-manifest.json',stable(manifest))
put(scratch/'selection-template.json',(REPO/root['selectionTemplate']['path']).read_bytes())
put(scratch/'importer.py',payload['importer.py'])
packet = dict(schema='mixer.apple-settings-reviewed-dispatch-successor.1',
              rootSelectionSHA256=sha(root_raw),acceptedBindings=root,
              baselinePacketSHA256=sha((prior_path.parent/'packet.json').read_bytes()),
              files={n:guards.row(HERE/n) for n in ['dispatch_successor.py','run_r2.py','materialize.py']},
              dispatcherBodyIdenticalExceptAcceptedArchiveDirectoryLayoutBinding=True,archiveGuardFunctionsByteIdentical=True,
              nativeAttemptsSelected=1,automaticRetry=False,buildsSelected=0)
put(HERE/'packet.json',stable(packet));put(scratch/'packet.json',stable(packet))
put(HERE/'materialization.json',stable(dict(createdAtUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scratch=str(scratch),temporaryParent=str(temp),rootSelectionSHA256=sha(root_raw),
    packetSHA256=sha(stable(packet)),baselinePrepareSHA256=sha(prior.encode()),
    priorSupervisorSHA256=sha(supervisor_path.read_bytes()),
    dispatchFunctionSHA256=sha(dispatch_source.encode()),archiveGuardFunctionsSHA256=sha(guard_source.encode()),
    sourceTreeSHA256=candidate['sourceTreeSHA256'],runtimeSourceTreeSHA256=manifest['treeSHA256'],
    exactDispatchBodyPreservedExceptArchiveDirectoryLayout=function(dispatcher,'dispatch')==dispatch_source,
    archiveDirectoryLayout='Accepted candidate archive requires exact zero directory records; existing explicit_directories=False validator contract',
    artifactCustody='Raw native output stays in the unique scratch; compact records remain in the owned evidence directory',
    scratchEnvironment=dict(TMPDIR=str(temp),PYTHONDONTWRITEBYTECODE='1'))))
print(json.dumps(dict(packetSHA256=sha(stable(packet)),scratch=str(scratch),nativeCommandsDispatched=0)))
