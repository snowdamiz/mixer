#!/usr/bin/env python3
"""V9 sealed setup diagnostic. Verify/build do not query native instances."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import signal
import subprocess
import sys
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
V6=BASE.parent/'apple-toggle-keyboard-focus-v6-preparation'
V7=BASE.parent/'apple-toggle-keyboard-focus-v7-preparation'
PREVIOUS=BASE.parent/'apple-toggle-keyboard-focus'
sys.path.append(str(PREVIOUS))
import keyboard_oracle
import settings_telemetry
spec=importlib.util.spec_from_file_location('immutable_keyboard_diagnostic_runtime_v9',PREVIOUS/'run.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
h=runtime.inherited
sha,read,require=runtime.sha,runtime.read,runtime.require
runtime.BASE=BASE;h.BASE=BASE
h.PRODUCTS=V7/'build/Build/Products';h.PRODUCT_ARCHIVE=V7/'test-runner-products.tar.gz'
h.Bridge=settings_telemetry.diagnostic_bridge(h.Bridge)
h.SCOPES={'interaction':{'cases':keyboard_oracle.CASES,'methods':['test000PublicSettingsFullKeyboardAccess']}}

def verify():
    from packet import verify_packet
    return verify_packet()


def summary(scope,bridge,xctest_exit,failure,cleanup_results):
    settings=None if bridge is None else bridge.settings.summary()
    export=read(BASE/'runtime/attachment-export.json') if (BASE/'runtime/attachment-export.json').is_file() else None
    boundary=failure is not None and failure['type']=='ValueError' and failure['message']=='Strict XCTest result failed; preserved evidence is authoritative' and xctest_exit==0
    return {'schema':'mixer.apple-toggle.keyboard-v9-runtime.1','status':'DIAGNOSTIC_ONLY','scope':scope,'xcodebuildExitCode':xctest_exit,'xcodebuildTerminalResultAvailable':xctest_exit is not None,'diagnosticCompleted':xctest_exit is not None and settings is not None and settings['settingsEvidenceComplete'] is True and settings['persistenceUncertain'] is False and settings['terminationMarkers']==['terminate-before','terminate-after'] and settings['completionMarkers']==['test-case-finished','suite-finished','bundle-finished'],'setupEvidenceComplete':settings is not None and settings['settingsEvidenceComplete'] is True and settings['persistenceUncertain'] is False,'settingsDiagnostic':settings,'expectedDiagnosticQualificationBoundary':boundary,'sessionFailure':failure,'sessionFailureClassification':'expected-diagnostic-only-inherited-qualification-boundary' if boundary else None if failure is None else 'observed-command-or-session-failure','strictNativeVerdictsPassed':False,'bridgeFailures':None if bridge is None else list(bridge.failures),'persistenceWarnings':None if bridge is None else list(bridge.persistence.ancillary),'persistenceUncertainty':None if bridge is None else bridge.persistence.uncertainty,'persistenceRetirement':None if bridge is None else bridge.persistence.retirement,'ancillaryFailures':None if bridge is None else list(bridge.ancillary_failures),'expectedXCTestMethods':1,'actualNativeInputActions':0,'nativeUserInteractionVerdicts':[],'applicationCasesExecuted':0,'dependentCasesUnrun':sorted(keyboard_oracle.CASES),'nativeKeyboardQualification':False,'attachmentExport':export,'officialSummaryAvailable':(BASE/'runtime/xctest-summary.json').is_file(),'officialTestsAvailable':(BASE/'runtime/xctest-tests.json').is_file(),'cleanupResults':cleanup_results,'runPassed':False,'carrierAccepted':False,'physicalPhones':'disconnected-deferred','gaAccepted':False}

h.verify=verify;h.runtime_summary=summary

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','run','cleanup']);p.add_argument('--scope',choices=['interaction'],default='interaction');p.add_argument('--reviewed-seal');a=p.parse_args()
    if a.action=='verify':print(json.dumps(verify(),sort_keys=True))
    elif a.action=='run':runtime.prerequisite();h.run(a.reviewed_seal,a.scope)
    else:
        h.RUN_DIR=h.select_runtime_directory(a.scope);life=read(h.RUN_DIR/'lifecycle.json');require(life['verifiedHandoff']['sealSHA256']==verify()['sealSHA256'],'Cleanup handoff changed')
        commands=runtime.ExportingCommands(h.RUN_DIR/'recovery-commands.json')
        values=h.cleanup_independently([('owned-simulator-and-baseline-reconciliation',lambda:h.cleanup(life,commands)),('ephemeral-capability-workspace-removal',lambda:h.remove_ephemeral(life))]);life.update(cleanedUp=all(x['passed'] for x in values),recoveryCleanupResults=values);h.write(h.RUN_DIR/'lifecycle.json',life);require(life['cleanedUp'],'Cleanup incomplete')

if __name__=='__main__':
    def stop(signum,frame):raise KeyboardInterrupt('Root diagnostic interrupted')
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop);main()
