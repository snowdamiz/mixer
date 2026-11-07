#!/usr/bin/env python3
"""Root-only keyboard execution; preparation/verification never addresses native instances."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import signal
import stat
import subprocess
import sys

BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
PARENT=ROOT/'verification/apple-toggle-pan-origin-correction';PAN=ROOT/'verification/apple-toggle-pan-commit-harness-v2'
sys.path.insert(0,str(PARENT))
import harness as inherited
import apps as artifact
import bridge as transport
import keyboard_oracle as oracle
import keyboard_bridge
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
require=artifact.require
original_manifest=artifact.expected_manifest

def expected_manifest(key):return read(BASE/'built-app-manifest.json') if key=='diagnostic' else original_manifest(key)
artifact.expected_manifest=expected_manifest
class CandidateApps:
    CONFIGS=artifact.CONFIGS
    @staticmethod
    def restore(destination,key):
        config=artifact.CONFIGS[key];manifest=expected_manifest(key)
        folder=BASE if key=='diagnostic' else artifact.ORIGINAL/config['folder']
        payload,modes=artifact.archive_payload(folder/'built-app.tar.gz',manifest,config)
        require(not destination.exists() and not destination.is_symlink() and destination.resolve()==destination,'Fresh canonical restore destination required')
        destination.mkdir(parents=True);app=destination/config['app']
        for directory in [app,app/'Frameworks',app/'_CodeSignature']:directory.mkdir(exist_ok=True);directory.chmod(0o755)
        for name,value in payload.items():
            target=app/artifact.relative_name(name);target.write_bytes(value);target.chmod(modes[name])
        return artifact.verify_restored(app,key)
    verify_installed=staticmethod(artifact.verify_installed)


def prerequisite():
    review=ROOT/'verification/apple-toggle-pan-commit-harness-v2-root-review/runtime-review.json'
    r=read(review);life=read(PAN/'runtime/lifecycle.json');summary=read(PAN/'runtime/runtime-verdict.json')
    require(r['status']=='accepted-private-native-pan-commit-and-regression-components' and r['completeCaseSet'] is True and r['originProofPassed'] is True,'Pan carrier prerequisite not root accepted')
    require(r['sourceRevisionContext']['candidateSourceClosureSHA256']=='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46' and r['sourceRevisionContext']['candidateArchiveSHA256']=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393','Pan prerequisite app identity changed')
    require(summary['runPassed'] is True and summary['strictNativeVerdictsPassed'] is True and summary['scopedDirectComponentsPassed'] is True and summary['bridgeFailures']==[],'Pan prerequisite runtime incomplete')
    require(life['cleanedUp'] is True and life['ownedDeviceAbsent'] is True and life['ephemeralWorkspaceAbsent'] is True and all(x['passed'] is True for x in life['cleanupResults']),'Pan prerequisite cleanup incomplete')
    return {'status':'root-accepted-private-pan-prerequisite','reviewSHA256':sha(review),'runtimeSHA256':sha(PAN/'runtime/runtime-verdict.json'),'lifecycleSHA256':sha(PAN/'runtime/lifecycle.json'),'sourceRevisionContext':r['sourceRevisionContext'],'priorOwnedSimulatorAbsent':True}


def verify():
    seal=read(BASE/'packet-seal.json');require(seal['schema']=='mixer.apple-toggle.keyboard-focus.1','Wrong keyboard seal')
    for name,digest in seal['files'].items():
        p=ROOT/artifact.relative_name(name);require(p.is_file() and not p.is_symlink() and sha(p)==digest,'Sealed keyboard source changed: '+name)
    p=subprocess.run([sys.executable,'-B',str(PAN/'run.py'),'verify'],cwd=ROOT,capture_output=True,text=True,timeout=60)
    require(p.returncode==0,'Reviewed parent preflight failed: '+p.stderr);parent=json.loads(p.stdout)
    require(parent['sealSHA256']=='f4410706adc7eae9e2c2367888b4ee6055d67a8028a28b008d1d202e5fe4b41d','Reviewed pan identity changed')
    reuse=read(BASE/'immutable-app-reuse.json')
    require(all(sha(ROOT/n)==d for n,d in reuse['files'].items()),'Immutable reused app bytes changed')
    actual={str(p.relative_to(BASE/'source')):sha(p) for p in sorted((BASE/'source').rglob('*')) if p.is_file()}
    lock=read(BASE/'source-lock.json');require(actual==lock['sha256'],'Unchanged app source lock mismatch')
    digest=hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(digest==lock['sourceClosureSHA256']==seal['candidateSourceClosureSHA256']=='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46','App closure changed')
    manifest=expected_manifest('diagnostic');require(manifest['archiveSHA256']==seal['candidateArchiveSHA256']=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393','App archive changed')
    artifact.archive_payload(BASE/'built-app.tar.gz',manifest,artifact.CONFIGS['diagnostic'])
    runner=read(BASE/'build-products-manifest.json')
    require(inherited.tree(inherited.PRODUCTS)==runner['products'],'New runner product tree changed');inherited.product_archive_payload(runner)
    require(all(sha(ROOT/n)==d for n,d in runner['sourceFiles'].items()),'New runner sources changed')
    require(all(sha(pathlib.Path(n))==d for n,d in runner['toolFiles'].items()),'Pinned runner tools changed')
    require(hashlib.sha256(inherited.json_bytes(runner['products'])).hexdigest()==runner['productTreeSHA256'],'Runner digest mismatch')
    controls=read(BASE/'host-controls.json');require(controls['exitCode']==0 and controls['testsRun']==controls['expectedTestsRun'] and controls['stderr'].rstrip().endswith('OK'),'Keyboard host controls failed')
    require(all(sha(ROOT/n)==d for n,d in controls['sourceFiles'].items()),'Keyboard control sources changed')
    for row in read(BASE/'official/manifest.json')['installedOfficialHeaders']:require(sha(pathlib.Path(row['source']))==row['sha256']==sha(BASE/row['snapshot']),'Official SDK declaration changed')
    return {'schema':'mixer.apple-toggle.keyboard-preflight.1','sealSHA256':sha(BASE/'packet-seal.json'),
            'candidateSourceClosureSHA256':digest,'candidateArchiveSHA256':manifest['archiveSHA256'],
            'testRunnerProductTreeSHA256':runner['productTreeSHA256'],'testRunnerArchiveSHA256':runner['productArchiveSHA256'],
            'panPrerequisite':prerequisite(),'parentSealSHA256':parent['sealSHA256'],'expectedXCTestMethods':7,'dependentAppCases':6,
            'settingsGate':'Public Settings UI method must pass; otherwise six app methods remain explicitly skipped/unrun',
            'nativeExecution':False,'physicalDevicesQueried':False,'gaAccepted':False}


def inventory(folder):
    result={};total=0
    require(folder.resolve()==folder and folder.is_dir() and not folder.is_symlink(),'Attachment export directory redirected')
    for p in sorted(folder.rglob('*')):
        require(not p.is_symlink() and (p.is_file() or p.is_dir()),'Unsafe attachment export entry')
        if p.is_file():
            total+=p.stat().st_size;require(len(result)<2000 and total<=256_000_000,'Attachment inventory exceeded fixed bound')
            result[str(p.relative_to(folder))]={'sha256':sha(p),'bytes':p.stat().st_size}
    return result


def settings_passed(folder,files):
    for name,item in files.items():
        if item['bytes']>500_000:continue
        try:value=json.loads((folder/name).read_bytes())
        except (ValueError,UnicodeError):continue
        if type(value) is dict and value.get('schema')=='mixer.apple-toggle.keyboard-settings.1' and value.get('step')=='setup-enabled' and value.get('passed') is True and value.get('bundle')=='com.apple.Preferences' and value.get('route')==['Accessibility','Keyboards & Typing','Full Keyboard Access'] and value.get('fullKeyboardAccessValue')=='1':return True
    return False

BaseCommands=inherited.Commands
class ExportingCommands(BaseCommands):
    def run(self,argv,*args,**kwargs):
        values=[str(x) for x in argv]
        is_test=len(values)>1 and values[0]==str(inherited.DEVELOPER/'usr/bin/xcodebuild') and values[1]=='test-without-building'
        try:return super().run(argv,*args,**kwargs)
        finally:
            if is_test:self.export_owned_attachments(values)
    def export_owned_attachments(self,argv):
        record={'schema':'mixer.apple-toggle.keyboard-attachment-export.1','passed':False,'settingsSetupObservedPassed':False,'scope':'Official owned xcresult attachments only; export failure never suppresses inherited cleanup'}
        try:
            runtime=BASE/'runtime';require(inherited.RUN_DIR==runtime and runtime.resolve()==runtime and self.output==runtime/'commands.json','Only fixed keyboard runtime export permitted')
            require(argv.count('-resultBundlePath')==1,'Exactly one owned result path required')
            result=pathlib.Path(argv[argv.index('-resultBundlePath')+1]);life=read(runtime/'lifecycle.json');ephemeral=life['ephemeralWorkspace'];parent=pathlib.Path(ephemeral['path']);info=parent.lstat()
            require(parent.resolve()==parent and result.parent==parent and result.name=='session.xcresult' and result.resolve()==result,'Owned canonical result bundle required')
            require(stat.S_ISDIR(info.st_mode) and not parent.is_symlink() and info.st_dev==ephemeral['device'] and info.st_ino==ephemeral['inode'] and info.st_uid==ephemeral['uid'] and stat.S_IMODE(info.st_mode)==0o700,'Owned result workspace identity changed')
            require(result.is_dir() and not result.is_symlink(),'Owned result bundle unavailable after test command')
            output=runtime/'attachments';require(not output.exists() and output.parent==runtime,'Fresh fixed attachment output required')
            command=['/usr/bin/xcrun','xcresulttool','export','attachments','--path',str(result),'--output-path',str(output)]
            code,stdout,stderr=super().run(command,timeout=30,check=False)
            files=inventory(output) if output.is_dir() else {};record.update(argv=command,timeoutSeconds=30,exitCode=code,files=files,artifactInventorySHA256=hashlib.sha256(inherited.json_bytes(files)).hexdigest(),settingsSetupObservedPassed=settings_passed(output,files))
            record['passed']=code==0 and bool(files) and 'manifest.json' in files
        except BaseException as error:
            record['failure']={'type':type(error).__name__,'message':self.redact(str(error))}
            try:self.record('attachment-export-failure',record['failure'])
            except BaseException:pass
        try:inherited.write(BASE/'runtime/attachment-export.json',record)
        except BaseException as error:
            try:self.record('attachment-export-receipt-unavailable',{'type':type(error).__name__,'message':self.redact(str(error))})
            except BaseException:pass

# Only this dedicated process selects reviewed reader and explicit keyboard adapters.
spec=importlib.util.spec_from_file_location('reviewed_keyboard_reader',PAN/'observation_reader.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
for name in ['ACTIONS','CASES','CASE_ACTION','CASE_COMMAND_SEQUENCE','COMMANDS','geometry_valid','verdict']:setattr(transport,name,getattr(oracle,name))
inherited.Bridge=keyboard_bridge.keyboard_bridge(reader.deadline_bridge(transport.Bridge),transport)
inherited.BASE=BASE;inherited.PRODUCTS=BASE/'build/Build/Products';inherited.PRODUCT_ARCHIVE=BASE/'test-runner-products.tar.gz'
inherited.packet=CandidateApps;inherited.verify=verify;inherited.Commands=ExportingCommands
METHODS=['test000PublicSettingsFullKeyboardAccess']+[x['method'] for x in oracle.SPECS.values()]
inherited.SCOPES={'interaction':{'cases':oracle.CASES,'methods':METHODS}}

def summary(scope,bridge,xctest_exit,failure,cleanup_results):
    results=None if bridge is None else list(bridge.verdicts);errors=None if bridge is None else list(bridge.failures)
    cursors={} if bridge is None else bridge.keyboard_cases
    complete=bridge is not None and set(cursors)==oracle.CASES and all(c.complete is True and c.failed is False for c in cursors.values())
    export_path=BASE/'runtime/attachment-export.json';export=read(export_path) if export_path.is_file() else None
    evidence=export is not None and export['passed'] is True and export['settingsSetupObservedPassed'] is True
    strict=None if results is None else complete and all(x['passed'] is True for x in results) and evidence
    return {'schema':'mixer.apple-toggle.keyboard-runtime.1','scope':scope,'xcodebuildExitCode':xctest_exit,'xcodebuildTerminalResultAvailable':xctest_exit is not None,
            'completeCaseSet':complete,'strictNativeVerdictsPassed':strict,'bridgeFailures':errors,'sessionFailure':failure,
            'expectedXCTestMethods':7,'dependentApplicationCases':6,'actualNativeInputActions':None if results is None else len(results),
            'caseProgress':{name:{'acquisitionTabs':c.acquisitions,'fixedPhasesCompleted':c.phase_index,'disabledHeldSpaceObserved':c.held_space,'complete':c.complete,'failed':c.failed} for name,c in cursors.items()},
            'nativeUserInteractionVerdicts':results,'directSemanticCallbacksQualified':False,
            'publicSettingsSetupObservedPassed':None if export is None else export['settingsSetupObservedPassed'],'attachmentExport':export,
            'dependentCasesUnrun':sorted(oracle.CASES-set(cursors)),'requiredEvidenceAvailable':evidence,
            'officialSummaryAvailable':(BASE/'runtime/xctest-summary.json').is_file(),'officialTestsAvailable':(BASE/'runtime/xctest-tests.json').is_file(),
            'cleanupResults':cleanup_results,'runPassed':xctest_exit==0 and strict is True and errors==[] and failure is None and cleanup_results is not None and all(x['passed'] is True for x in cleanup_results),
            'carrierAccepted':False,'physicalPhones':'disconnected-deferred','physicalKeyboardMatrix':'pending-final-acceptance','gaAccepted':False,'capabilityRetained':False}
inherited.runtime_summary=summary

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','run','cleanup']);p.add_argument('--scope',choices=['interaction'],default='interaction');p.add_argument('--reviewed-seal');a=p.parse_args()
    if a.action=='verify':print(json.dumps(verify(),sort_keys=True))
    elif a.action=='run':prerequisite();inherited.run(a.reviewed_seal,a.scope)
    else:
        inherited.RUN_DIR=inherited.select_runtime_directory(a.scope);life=read(inherited.RUN_DIR/'lifecycle.json');require(life['verifiedHandoff']['sealSHA256']==verify()['sealSHA256'],'Recovery handoff changed');commands=ExportingCommands(inherited.RUN_DIR/'recovery-commands.json')
        values=inherited.cleanup_independently([('owned-simulator-and-baseline-reconciliation',lambda:inherited.cleanup(life,commands)),('ephemeral-capability-workspace-removal',lambda:inherited.remove_ephemeral(life))]);life.update(cleanedUp=all(x['passed'] for x in values),recoveryCleanupResults=values);inherited.write(inherited.RUN_DIR/'lifecycle.json',life);require(life['cleanedUp'],'Cleanup incomplete')
if __name__=='__main__':
    def stop(signum,frame):raise KeyboardInterrupt('Root keyboard harness interrupted')
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop);main()
