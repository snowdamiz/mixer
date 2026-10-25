"""Private composition over packet-local immutable source copies only.

Import mutates only newly loaded snapshot modules, never the old sealed harness.
Read-only run.py verification does not import this module.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys
BASE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path(json.loads((BASE/"runtime-selection.json").read_bytes())["repositoryRoot"])
OUT=pathlib.Path(json.loads((BASE/"runtime-selection.json").read_bytes())["outputBase"])
SNAPSHOT=BASE/'inputs/runtime'
VERIFY=SNAPSHOT/'verification'
PARENT=VERIFY/'apple-toggle-pan-origin-correction'
KEYBOARD=VERIFY/'apple-toggle-keyboard-focus'
V9=VERIFY/'apple-toggle-keyboard-focus-v9-preparation'
selection=json.loads((BASE/'runtime-selection.json').read_bytes())
bootstrap=BASE/'runtime_bindings.py'
if hashlib.sha256(bootstrap.read_bytes()).hexdigest()!=selection['files']['runtime_bindings.py']:
    raise ValueError('Runtime binding guard differs from selected bytes')
_boot_spec=importlib.util.spec_from_file_location('_selected_runtime_bindings',bootstrap)
_boot=importlib.util.module_from_spec(_boot_spec);_boot_spec.loader.exec_module(_boot)
bindings=_boot.RuntimeBindings(BASE,selection)
bindings.check();bindings.module(_boot)
for path in reversed([V9,KEYBOARD,PARENT]): sys.path.insert(0,str(path))
import harness as h
import apps as artifact
import bridge as transport
import keyboard_oracle as oracle
import keyboard_bridge
import settings_telemetry as telemetry
import durable_settings
import attachment_export
import runtime_summary as summary_module
import orchestration
import join_support
import command_observer
import importer
import reference_contract
join_support.configure_root(selection["trustedRootSelection"])
from attachment_export import exporting_commands
RUNTIME_ROOTS=[h,artifact,transport,oracle,keyboard_bridge,telemetry,durable_settings,attachment_export,summary_module,orchestration,join_support,command_observer,importer,reference_contract]
bindings.check(RUNTIME_ROOTS)
CANONICAL_COMMANDS=getattr(h,'_full_case_canonical_commands',h.Commands)
CANONICAL_BRIDGE=getattr(h,'_full_case_canonical_bridge',transport.Bridge)
h._full_case_canonical_commands=CANONICAL_COMMANDS
h._full_case_canonical_bridge=CANONICAL_BRIDGE
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
read=lambda path:json.loads(path.read_bytes())

def load(name,path):
    bindings.check(RUNTIME_ROOTS)
    if str(path.resolve()) not in bindings.files:raise ValueError('Unselected runtime import path')
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    bindings.module(module,str(path.resolve()));bindings.check(RUNTIME_ROOTS+[module]);return module


def setup_ready(settings):
    summary=settings.summary()
    return bool(summary['setupObservationSatisfied'] is True and summary['terminationMarkers']==['terminate-before','terminate-after']
        and summary['completionMarkers']==['test-case-finished'] and summary['persistenceRetirementPending'] is False
        and summary['persistenceUncertain'] is False)


def full_case_bridge(base):
    bindings.check(RUNTIME_ROOTS)
    diagnostic=telemetry.diagnostic_bridge(base)
    class FullCaseBridge(diagnostic):
        def __init__(self,*args,**kwargs):
            bindings.check(RUNTIME_ROOTS)
            super().__init__(*args,**kwargs);self.setup_handed_off=False;self.binding_failure=None
        def request(self,op,body):
            if self.binding_failure is not None:raise self.binding_failure
            try:bindings.check(RUNTIME_ROOTS)
            except BaseException as error:
                self.binding_failure=error
                try:self.record_failure('runtime-binding',error)
                except BaseException:pass
                raise
            return super().request(op,body)
        def _request(self,op,body):
            if op=='evaluate' and type(body) is dict and set(body)=={'settingsDiagnostic'}:
                telemetry.require(not self.setup_handed_off and self.current is None and self.generation==0,'Setup telemetry closed after application handoff')
                return self.settings.request(body['settingsDiagnostic'])
            if op=='begin':
                telemetry.require(setup_ready(self.settings),'Durable measured setup and setup test completion required before application begin')
                telemetry.require(self.current is None or self.current['keyboardCursor'].complete is True,'Prior application case must complete before next begin')
                telemetry.require(type(body) is dict and body.get('case') not in self.keyboard_cases,'Duplicate application case begin refused')
                result=base._request(self,op,body)
                self.setup_handed_off=True
                return result
            return base._request(self,op,body)
    return FullCaseBridge


def inventory(folder):
    result={};total=0
    h.require(folder.resolve()==folder and folder.is_dir() and not folder.is_symlink(),'Attachment export directory redirected')
    for path in sorted(folder.rglob('*')):
        h.require(not path.is_symlink() and (path.is_file() or path.is_dir()),'Unsafe attachment export entry')
        if path.is_file():
            total+=path.stat().st_size;h.require(len(result)<2000 and total<=256_000_000,'Attachment inventory exceeded fixed bound')
            result[str(path.relative_to(folder))]={'sha256':sha(path),'bytes':path.stat().st_size}
    return result


def settings_passed(folder,files):
    for name,item in files.items():
        if item['bytes']>500_000:continue
        try:value=read(folder/name)
        except (ValueError,UnicodeError):continue
        if type(value) is dict and value.get('schema')=='mixer.apple-toggle.keyboard-settings.1' and value.get('step')=='setup-enabled' and value.get('passed') is True and value.get('bundle')=='com.apple.Preferences' and value.get('route')==telemetry.ROUTE and value.get('fullKeyboardAccessValue')=='1':return True
    return False


CandidateApps=join_support.candidate_apps(artifact,BASE,selection)


METHODS=selection["methods"]

def compose():
    bindings.check(RUNTIME_ROOTS)
    reader=load('full_case_reviewed_reader',VERIFY/'apple-toggle-pan-commit-harness-v2/observation_reader.py')
    for name in ['ACTIONS','CASES','CASE_ACTION','CASE_COMMAND_SEQUENCE','COMMANDS','geometry_valid','verdict']:setattr(transport,name,getattr(oracle,name))
    h.Bridge=full_case_bridge(keyboard_bridge.keyboard_bridge(reader.deadline_bridge(CANONICAL_BRIDGE),transport))
    h.Commands=exporting_commands(CANONICAL_COMMANDS,h,OUT,settings_passed,inventory)
    h.DEVELOPER=pathlib.Path(selection['trustedRootSelection']['developerDirectory'])
    h.BASE=OUT;h.ROOT=ROOT;h.PRODUCTS=pathlib.Path(selection["productsRoot"])/"runner-products";h.PRODUCT_ARCHIVE=pathlib.Path(selection["productArchive"])
    h.RUN_DIR=OUT/'runtime';h.packet=CandidateApps;artifact.expected_manifest=CandidateApps.expected_manifest
    h.SCOPES={'interaction':{'cases':set(selection['cases']),'methods':METHODS}}
    h.runtime_summary=lambda *args:join_support.runtime_summary(OUT,h,oracle,setup_ready,*args)
    h.verify=lambda:join_support.verify_packet(BASE)
    h.run=lambda reviewed_seal,scope="interaction":orchestration.run(h,bindings,RUNTIME_ROOTS,reviewed_seal,scope)
    return h

compose()
