"""Pure classification and exact oracle replay; no runtime/module orchestration."""
import copy
SCHEMA = 'mixer.apple-focus-reference-precondition.1'
REFERENCE = 'plain-uibutton-reference'
CASE = 'keyboard-enabled-off'


def result(preconditions, original_results, oracle, observations=None):
    """Raw original verdicts remain nested verbatim; missing evidence fails closed."""
    report = {'schema': 'mixer.apple-focus-reference-diagnostic-result.1', 'diagnosticOnly': True,
        'status': 'incomplete', 'singleTabDiagnosticEvidencePassed': False, 'keyInjectionCount': None,
        'returnedPublicKeyWitnessCount': 0, 'originalOracleResults': original_results,
        'completeCaseSet': False, 'cursorCompletionCredit': False, 'runPassed': False,
        'fullSixCaseQualification': False, 'nativeKeyboardQualification': False, 'carrierAccepted': False,
        'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    try:
        if type(preconditions) is not list or len(preconditions) != 1 or type(original_results) is not list:
            raise ValueError('Exactly one authoritative precondition required')
        p = preconditions[0]
        if type(p) is not dict or set(p) != {'schema','case','phase','generation','actionIndex','requiredFocus',
                'observedFocus','passed','actionInjectionCount','before'}:
            raise ValueError('Closed precondition shape required')
        oracle.ax(p['before'])
        observed = oracle.focused(p['before'])
        if not (p['schema'] == SCHEMA and p['case'] == CASE and p['phase'] == 'acquire'
                and type(p['generation']) is int and p['generation'] > 0 and type(p['actionIndex']) is int and p['actionIndex'] == 1
                and p['requiredFocus'] == REFERENCE and p['observedFocus'] == observed
                and type(p['passed']) is bool and p['passed'] is (observed == REFERENCE)
                and type(p['actionInjectionCount']) is int and p['actionInjectionCount'] == 0):
            raise ValueError('Exact current reference premise required')
        if p['passed'] is False:
            if original_results: raise ValueError('Key result after failed precondition contradicts zero injection')
            report.update(status='failed-reference-precondition', keyInjectionCount=0)
            return report
        report['status'] = 'incomplete-after-passing-precondition'
        if not original_results: return report
        if len(original_results) != 1: raise ValueError('Exactly one original oracle result required')
        v = original_results[0]
        w = oracle.witness(v['keyboardWitness'], v['keyboardBinding'])
        if not (v['schema'] == 'mixer.apple-toggle.keyboard-v2-verdict.1' and v['candidate'] == 'diagnostic'
                and v['case'] == CASE and v['action'] == 'native-keyboard' and v['phase'] == 'acquire'
                and w['phase'] == 'acquire' and w['key'] == 'tab' and w['before'] == p['before']
                and w['generation'] == p['generation'] and w['actionIndex'] == p['actionIndex']
                and v['observedFocusBefore'] == REFERENCE and type(v['passed']) is bool
                and type(v['predicates']) is dict and bool(v['predicates'])
                and all(type(value) is bool for value in v['predicates'].values())
                and v['passed'] is all(value is True for value in v['predicates'].values())):
            raise ValueError('Bound unchanged original oracle result required')
        if type(observations) is not list or len(observations) != 1:
            raise ValueError('One immutable before/after application pair required for unchanged oracle replay')
        pair = observations[0]
        if type(pair) is not dict or set(pair) != {'before','after','fileChanged'} or type(pair['fileChanged']) is not bool:
            raise ValueError('Closed application replay evidence required')
        baseline = copy.deepcopy(pair['before'])
        baseline.update(keyboardWitness=w, keyboardBinding=v['keyboardBinding'])
        replayed = oracle.verdict('diagnostic', CASE, 'native-keyboard', baseline, pair['after'], pair['fileChanged'])
        recorded = copy.deepcopy(v)
        for field in ['ownedSimulatorIdentity', 'generation', 'actionIndex']:
            if field in recorded:
                if field in ['generation', 'actionIndex'] and recorded[field] != w[field]:
                    raise ValueError('Runtime reporting identity differs from original witness')
                recorded.pop(field)
        if replayed != recorded:
            raise ValueError('Original verdict does not match complete unchanged oracle replay')
        report.update(status='one-original-oracle-result', keyInjectionCount=1, returnedPublicKeyWitnessCount=1,
            singleTabDiagnosticEvidencePassed=v['passed'])
    except (KeyError, ValueError, TypeError, IndexError, AttributeError) as error:
        report.update(status='invalid-or-incomplete-evidence', failure=type(error).__name__ + ': ' + str(error))
    return report
