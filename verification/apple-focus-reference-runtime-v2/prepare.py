#!/usr/bin/env python3
"""Prepare/freeze a host-only packet; dispatch is a separate root action."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OLD = ROOT/'verification/apple-focus-diagnostic-runtime-v1'
V1 = ROOT/'verification/apple-focus-reference-diagnostic-v1'
V2 = ROOT/'verification/apple-focus-reference-diagnostic-v2'
REVIEW = ROOT/'verification/apple-focus-reference-diagnostic-v2-independent-review'
PRODUCT = '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8'
SOURCE = '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a'
OWNED = ['prepare.py','importer.py','adapter.py','test_importer.py','verify_host.py','freeze.py']
METHODS = ['test000PublicSettingsFullKeyboardAccess','test010ReferenceFirstTab']
ORACLES = ['apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py','apple-toggle-keyboard-focus/keyboard_oracle.py','apple-toggle-keyboard-focus/cases.json','apple-toggle-pan-commit-harness-v2/commit_oracle.py','apple-toggle-pan-commit-harness-v2/cases.json','apple-toggle-native-interruption/interruption_oracle.py','apple-toggle-native-interruption/cases.json','apple-toggle-pan-origin-correction/oracle.py','apple-toggle-semantic-activation/semantic_oracle.py']


def require(value, message):
    if not value: raise ValueError(message)


def sha(value): return hashlib.sha256(value).hexdigest()


def stable(value): return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,'Canonical regular input required: '+str(path))
    data = path.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(data),'sha256':sha(data)}


def checked(path, expected):
    require(row(path)['sha256'] == expected,'Frozen input changed: '+str(path))
    return json.loads(path.read_bytes())


def helpers():
    # Read as data before this guarded import; this module's top level contains
    # definitions only. Never call its prepare/run actions or retired scratch.
    path = OLD/'prepare.py'
    require(row(path)['sha256'] == 'a1f32d62735ff99c29dd7590f20fd2b81067d44d005e51e2fe44e53dde9b569f','Frozen archive helper changed')
    spec = importlib.util.spec_from_file_location('_frozen_archive_functions_only',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def inputs():
    bindings = {}
    for directory, expected in [(V1,'9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c'),(V2,'07776c2af95bcc58e126b4ceb0f0dee39dec1138ea96bc9e33bc8a4a0393a3a0'),(REVIEW,'6ca2e2a7d7264664f50046a506b01465287dcc6d88872be528af239d8c0d5a55')]:
        handoff = checked(directory/'handoff.json',expected)
        require(sha(stable(handoff['members'])) == handoff['memberTreeSHA256'],'Handoff member digest differs')
        for name, expected_row in handoff['members'].items():
            require(row(ROOT/name) == expected_row,'Frozen member changed: '+name)
            bindings[name] = expected_row
        bindings[str((directory/'handoff.json').relative_to(ROOT))] = row(directory/'handoff.json')
    packet = checked(OLD/'packet.json','d7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783')
    manifest = checked(OLD/'selected-runtime-source-manifest.json',packet['selectedSourceArchiveManifestSHA256'])
    for path in [OLD/'packet.json',OLD/'prepare.py',OLD/'selected-runtime-source-manifest.json',OLD/'selected-runtime-sources.tar.gz',ROOT/'AGENTS.md',ROOT/'docs/apple-focus-diagnostic-runtime-v1-checkpoint.md',OLD/'runtime/captures/0001-before-1.json',OLD/'runtime/captures/0001-after-1.json',OLD/'runtime/captures/0001-keyboard-witness-1.json',OLD/'runtime/runtime-verdict.json']:
        bindings[str(path.relative_to(ROOT))] = row(path)
    h = helpers()
    runtime = h.archive_payload(OLD/'selected-runtime-sources.tar.gz',manifest['files'],packet['selectedSourceArchive']['sha256'],'selected/')
    prepared = json.loads((V1/'prepared.json').read_bytes())
    products = json.loads((V1/'compile-attempt-1/product-manifest.json').read_bytes())
    require(prepared['derivativeSourceTreeSHA256'] == SOURCE and products['archive']['sha256'] == PRODUCT,'Wrong frozen source/product')
    accepted = h.archive_payload(V1/'accepted-sources.tar.gz',prepared['derivativeSources'],prepared['archive']['sha256'],'accepted/')
    require(sha(stable(prepared['derivativeSources'])) == SOURCE and len(accepted) == 39,'Exact derivative source tree required')
    h.archive_payload(V1/'compile-attempt-1/products.tar.gz',products['products'],PRODUCT)
    require(sha(runtime['command_observer.py']) == 'c712724207fb5d327da0f6367e7a7f598494b3bb43f8b25fdfefcf94d3aefa88','Observer V2 changed')
    tool_binding=json.loads((V1/'compile-attempt-1/tool-bindings.json').read_bytes())
    for name,expected_row in tool_binding['tools'].items():
        if name.endswith(('/usr/bin/xcodebuild','/Contents/Info.plist','/bin/python3.14','/SDKSettings.json')):
            require(row(Path(name).resolve()) == expected_row,'Pinned tool file changed without invocation: '+name)
            bindings[name]=expected_row
    for name in ['/usr/bin/xcrun','/Applications/Xcode_26.6.app/Contents/Developer/usr/bin/xcresulttool']:
        bindings[name]=row(Path(name))
    return runtime, accepted, products, bindings


def once(value, old, new):
    require(value.count(old) == 1,'Missing/ambiguous derivation anchor: '+old[:90])
    return value.replace(old,new,1)


def derive(runtime):
    derived = dict(runtime); selection = json.loads(derived.pop('runtime-selection.json'))
    # Only packet-local orchestration changes. Oracle, bridge and observer bytes
    # remain exact members of the frozen previous runtime source archive.
    derived['join_support.py'] = once(runtime['join_support.py'].decode().split('\ndef official_methods(base):',1)[0],"'test010EnabledFromOff'","'test010ReferenceFirstTab'").encode() + b'\n' + (BASE/'adapter.py').read_bytes()
    derived['importer.py'] = (BASE/'importer.py').read_bytes()
    derived['reference_contract.py'] = (V2/'reference_contract.py').read_bytes()
    s = runtime['composition.py'].decode()
    s = once(s,'import command_observer\n','import command_observer\nimport importer\nimport reference_contract\njoin_support.configure_root(selection["trustedRootSelection"])\n')
    s = once(s,'join_support,command_observer]','join_support,command_observer,importer,reference_contract]')
    s = once(s,"    h.BASE=OUT;h.ROOT=ROOT;", "    h.DEVELOPER=pathlib.Path(selection['trustedRootSelection']['developerDirectory'])\n    h.BASE=OUT;h.ROOT=ROOT;")
    derived['composition.py'] = s.encode()
    s = runtime['attachment_export.py'].decode()
    s = once(s,'import stat\n','import stat\nimport join_support\n')
    start=s.index('            try:\n',s.index('        def export_official_results('))
    end=s.index('        def export_owned_attachments(',start)
    s=s[:start]+'''            try:
                join_support.capture_official(self,base.run,h,output_base)
            except BaseException as error:
                self.latch_reporting_error('official-result-export',error)
                try:self.record('official-result-export-unavailable',dict(type=type(error).__name__,message=self.redact(str(error))))
                except BaseException:pass
''' + s[end:]
    derived['attachment_export.py'] = s.encode()
    s = runtime['orchestration.py'].decode()
    start=s.index('        before=h.devices(commands);')
    end=s.index('        documents={}',start)
    s=s[:start]+'''        root=join_support._ROOT;identity=root['ownedSimulatorIdentity']
        name=identity['name'];identifier=identity['udid']
        lifecycle=dict(schema='mixer.apple-toggle.xctest-lifecycle.1',ownedName=name,ownedSimulator=identifier,creationIntentRecordedBeforeCommand=False,rootSelectedExistingOwnedSimulator=True,before=root['baselineDevices'],beforeFrontends=root['baselineFrontends'],verifiedHandoff=verified,runtime=runtime,apps={},cleanedUp=False,nativeExecutionAttempted=True,physicalDevices='disconnected-deferred')
        h.last_lifecycle=lifecycle
        h.write(h.RUN_DIR/'lifecycle.json',lifecycle)
        owned=h.owned_device(lifecycle,h.devices(commands))
        h.require(owned is not None and owned['state'] in ['Shutdown','Booted'],'Exact root-owned simulator unavailable')
        if owned['state']=='Shutdown':commands.simctl('boot',identifier)
        commands.run(['/usr/bin/xcrun','simctl','bootstatus',identifier,'-b'],timeout=120)
''' + s[end:]
    # A strict oracle result can fail diagnostically; the original predicates and
    # XCTest code are retained. Qualification is always false. Final import occurs
    # after the five registered cleanup operations.
    start=s.index('        summary=h.runtime_summary(')
    end=s.index('    except BaseException as error:',start)
    s=s[:start]+'''        h.require(xctest_exit in [0,65],'Unsupported XCTest terminal code; preserve evidence')
''' + s[end:]
    # Official capture is one-shot in the command wrapper. Never re-export and
    # overwrite the selected official results in the cleanup path.
    start=s.index('            if result_path is not None and result_path.exists():')
    end=s.index('        except BaseException as error:',start)
    # There is a nested except in the original block; choose its outer delimiter.
    end=s.index("        except BaseException as error:\n            outcome.fail('optional-result-export'",start)
    s=s[:start]+'            pass  # Official output already captured by the selected wrapper.\n'+s[end:]
    derived['orchestration.py'] = s.encode()
    selection.update(methods=METHODS,cases=['keyboard-enabled-off'],scope='One reference-first Tab diagnostic only; no acquisition loop or completion credit')
    selection['moduleAliases'].update(importer='importer.py',reference_contract='reference_contract.py')
    selection.pop('productsRoot',None); selection.pop('outputBase',None)
    for name in ['orchestration.py','composition.py','attachment_export.py','join_support.py']:
        compile(derived[name],name,'exec')
    require(all(derived[name] == raw for name,raw in runtime.items() if name not in ['runtime-selection.json','orchestration.py','composition.py','attachment_export.py','join_support.py']),'Undeclared frozen source change')
    return derived, selection


def manifest(payload): return {name:{'kind':'file','mode':0o644,'bytes':len(raw),'sha256':sha(raw)} for name,raw in payload.items()}


def prepare():
    require(not (BASE/'packet.json').exists(),'Preserve previous packet')
    runtime, accepted, products, bindings=inputs()
    derived, selection=derive(runtime); source_rows=manifest(derived)
    scratch=Path(tempfile.mkdtemp(prefix='host-packet-',dir=BASE))
    try:
        h=helpers(); h.materialize(scratch/'selected',source_rows,derived)
        archive=h.archive_sources(BASE/'runtime-sources.tar.gz',scratch/'selected',source_rows)
    finally: shutil.rmtree(scratch)
    for name, value in [('input-lock.json',bindings),('runtime-source-manifest.json',archive),('selection-template.json',selection)]:
        with (BASE/name).open('xb') as stream:stream.write(stable(value))
    own={name:row(BASE/name) for name in OWNED}
    packet={'schema':'mixer.apple-focus-reference-runtime-packet.2','scope':'Host preparation only; independent review and root fresh selection required before dispatch','preparedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(BASE/'prepare.py'),'prepare'],'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'sourceRevisionLabel':'ba9ad4372f94463ba4d363cdfd76dd565c96413f','sourceRevisionMeaning':'Inherited frozen compile label; exact hashes define this tree; no Git query','sourceTreeSHA256':SOURCE,'productArchiveSHA256':PRODUCT,'productTreeSHA256':json.loads((V1/'compile-attempt-1/receipt.json').read_bytes())['productTreeSHA256'],'methods':METHODS,'cases':['keyboard-enabled-off'],'ownedSources':own,'ownedSourceTreeSHA256':sha(stable(own)),'files':{name:row(BASE/name) for name in ['input-lock.json','runtime-source-manifest.json','runtime-sources.tar.gz','selection-template.json']},'documentation':row(ROOT/'docs/apple-focus-reference-runtime-v2.md'),'cleanup':{'hostPreparationScratchAbsent':not scratch.exists(),'nativeInstancesCreatedOrQueried':0,'servicesStarted':0,'otherProjectsTouched':False},'nativeExecuted':False,'runtimeSelected':False,'compileRerun':False,'runPassed':False,'completeCaseSet':False,'cursorCompletionCredit':False,'fullSixCaseQualification':False,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False,'physicalPhones':'disconnected-deferred'}
    with (BASE/'packet.json').open('xb') as stream:stream.write(stable(packet))
    print('PASS: host-only reference-first packet frozen for independent review; no native dispatch')


def verify():
    packet=json.loads((BASE/'packet.json').read_bytes())
    _,_,_,bindings=inputs()
    require(bindings == json.loads((BASE/'input-lock.json').read_bytes()),'Input closure changed')
    require({name:row(BASE/name) for name in OWNED} == packet['ownedSources'],'Owned source changed')
    require(sha(stable(packet['ownedSources'])) == packet['ownedSourceTreeSHA256'],'Owned tree digest differs')
    for name,item in packet['files'].items():require(row(BASE/name)==item,'Packet member changed: '+name)
    require(row(ROOT/'docs/apple-focus-reference-runtime-v2.md') == packet['documentation'],'Packet document changed')
    manifest=json.loads((BASE/'runtime-source-manifest.json').read_bytes())
    helpers().archive_payload(BASE/'runtime-sources.tar.gz',manifest['files'],manifest['archive']['sha256'],'selected/')
    return {'packetSHA256':sha((BASE/'packet.json').read_bytes()),'nativeExecuted':False,'scope':'Byte/mode/archive/source verification only'}


def dispatch(reviewed_packet, selection_path, selected_sha):
    # This branch is NOT called by preparation/tests/freeze. Root is responsible
    # for independent review, exact selected simulator ownership and command.
    verified=verify();require(reviewed_packet==verified['packetSHA256'],'Root reviewed packet hash differs')
    guard_spec=importlib.util.spec_from_file_location('_root_selection_guard',BASE/'importer.py')
    importer=importlib.util.module_from_spec(guard_spec);guard_spec.loader.exec_module(importer)
    selection_path=Path(selection_path)
    require(row(selection_path)['sha256']==selected_sha,'Root out-of-band selection hash differs')
    root=importer.validate_root(importer.parse(selection_path.read_bytes()),reviewed_packet,fresh=True)
    output=BASE/('native-run-'+root['runID'])
    require(not output.exists() and not output.is_symlink(),'Fresh run output required; never replay a run')
    output.mkdir(mode=0o755)
    h=helpers(); product_manifest=json.loads((V1/'compile-attempt-1/product-manifest.json').read_bytes())
    source_manifest=json.loads((BASE/'runtime-source-manifest.json').read_bytes())
    payload=h.archive_payload(BASE/'runtime-sources.tar.gz',source_manifest['files'],source_manifest['archive']['sha256'],'selected/')
    h.materialize(output/'selected',source_manifest['files'],payload)
    product_payload=h.archive_payload(V1/'compile-attempt-1/products.tar.gz',product_manifest['products'],PRODUCT)
    h.materialize(output/'products',product_manifest['products'],product_payload)
    selection=json.loads((BASE/'selection-template.json').read_bytes())
    selection.update(repositoryRoot=str(ROOT),outputBase=str(output),productsRoot=str(output/'products'),productArchive=str(V1/'compile-attempt-1/products.tar.gz'),productManifest=product_manifest,trustedRootSelection=root,files={name:item['sha256'] for name,item in source_manifest['files'].items()})
    (output/'selected/runtime-selection.json').write_bytes(stable(selection))
    (output/'root-selection.json').write_bytes(selection_path.read_bytes())
    # Loading the packet-local composition is the explicit native dispatch boundary.
    sys.path.insert(0,str(output/'selected'))
    spec=importlib.util.spec_from_file_location('composition',output/'selected/composition.py')
    module=importlib.util.module_from_spec(spec);sys.modules['composition']=module
    try:
        spec.loader.exec_module(module)
        return module.h.run(sha((output/'selected/runtime-selection.json').read_bytes()))
    finally:
        # Product/source scratch is retired after exact post-run verification.
        # Preserve it on any mismatch for root recovery; never broad-delete.
        good=(h.tree(output/'products')==product_manifest['products'] and all((output/'selected'/name).read_bytes()==raw for name,raw in payload.items()))
        receipt={'verifiedBeforeRemoval':good,'paths':[str(output/'products'),str(output/'selected')],'scope':'Packet-owned source/product scratch only; result and observations retained'}
        if good:
            shutil.rmtree(output/'products');shutil.rmtree(output/'selected')
        receipt['scratchAbsent']=not (output/'products').exists() and not (output/'selected').exists()
        (output/'scratch-cleanup.json').write_bytes(stable(receipt))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','verify','dispatch']);parser.add_argument('--reviewed-packet');parser.add_argument('--root-selection');parser.add_argument('--root-selection-sha256');args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='verify':print(json.dumps(verify(),sort_keys=True))
    else:dispatch(args.reviewed_packet,args.root_selection,args.root_selection_sha256)
