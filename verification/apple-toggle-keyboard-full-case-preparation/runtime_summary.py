"""All evidence predicates remain fail-closed; native work is not implied."""
import json

def official_methods(base,methods):
    path=base/'runtime/xctest-tests.json'
    if not path.is_file() or not (base/'runtime/xctest-summary.json').is_file():return False
    summary=json.loads((base/'runtime/xctest-summary.json').read_bytes())
    if not (summary.get('result')=='Passed' and summary.get('totalTestCount')==7 and summary.get('passedTests')==7 and all(summary.get(key)==0 for key in ['failedTests','skippedTests','expectedFailures'])):return False
    data=json.loads(path.read_bytes())
    found={}
    case_nodes=[]
    def visit(value):
        if isinstance(value,dict):
            if value.get('nodeType')=='Test Case':
                case_nodes.append(value)
                identifier=value.get('nodeIdentifier','')
                for method in methods:
                    if identifier in [f'ToggleUITests/{method}()',f'ToggleUITests/{method}',f'MixerToggleUITests/ToggleUITests/{method}()']:
                        found.setdefault(method,[]).append(value.get('result'))
            for nested in value.values():visit(nested)
        elif isinstance(value,list):
            for nested in value:visit(nested)
    visit(data)
    return len(case_nodes)==7 and set(found)==set(methods) and all(results==['Passed'] for results in found.values())


def runtime_summary(base,h,oracle,setup_ready,scope,bridge,xctest_exit,failure,cleanup_results):
    settings=None if bridge is None else bridge.settings.summary()
    results=[] if bridge is None else list(bridge.verdicts)
    cursors={} if bridge is None else bridge.keyboard_cases
    complete=bridge is not None and set(cursors)==oracle.CASES and all(c.complete is True and c.failed is False for c in cursors.values())
    path=base/'runtime/attachment-export.json';export=json.loads(path.read_bytes()) if path.is_file() else None
    attachment=export is not None and export.get('passed') is True and export.get('settingsSetupObservedPassed') is True
    from composition import METHODS
    official=official_methods(base,METHODS)
    errors=None if bridge is None else list(bridge.failures)
    ready=bridge is not None and setup_ready(bridge.settings)
    case_oracles=bool(results) and {value.get('case') for value in results}==oracle.CASES and all(value.get('passed') is True and value.get('action')=='native-keyboard' for value in results)
    export_state=getattr(h,'attachment_export_state',{})
    strict=complete and case_oracles and ready and attachment and official and export_state.get('receiptDurablyCommitted') is True
    cleaned=cleanup_results is not None and all(value['passed'] is True for value in cleanup_results)
    return dict(schema='mixer.apple-toggle.keyboard-full-case-runtime.1',scope=scope,xcodebuildExitCode=xctest_exit,
      expectedXCTestMethods=7,dependentApplicationCases=6,officialSevenMethodsPassed=official,
      completeCaseSet=complete,strictNativeVerdictsPassed=strict,bridgeFailures=errors,sessionFailure=failure,
      setupReadyForCases=ready,settingsDiagnostic=settings,publicSettingsSetupObservedPassed=attachment,
      setupV9CompletionMarkersComplete=settings is not None and settings['completionMarkers']==['test-case-finished','suite-finished','bundle-finished'],
      attachmentExport=export,attachmentExportReporting=export_state,nativeUserInteractionVerdicts=results,actualNativeInputActions=len(results),
      dependentCasesUnrun=sorted(oracle.CASES-set(cursors)),cleanupResults=cleanup_results,
      runPassed=xctest_exit==0 and strict and errors==[] and failure is None and cleaned,
      nativeKeyboardQualification=False,carrierAccepted=False,physicalPhones='disconnected-deferred',gaAccepted=False)
