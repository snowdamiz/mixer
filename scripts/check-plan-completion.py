#!/usr/bin/env python3
"""Check local completion records without running application tests."""

import json
from pathlib import Path
import sys


INPUTS = ('gates/local.json', 'gates/ga.json', 'work-graph.json',
          'dogfood/receipts/milestones.json')
STATUSES = {'planned', 'running', 'passed', 'failed', 'blocked'}


def has_pass_evidence(record):
    evidence, reviewer = record['evidence'], record['reviewer']
    return (isinstance(evidence, list) and bool(evidence)
            and all(isinstance(item, str) and item.strip() for item in evidence)
            and isinstance(reviewer, str) and bool(reviewer.strip()))


def check_documents(documents):
    local, launch, work, dogfood = (documents[name] for name in INPUTS)
    failures = []
    expected = [f'L{i:02}' for i in range(1, 9)]
    gates = local['gates']
    if [gate['id'] for gate in gates] != expected:
        failures.append('Local completion requires ordered L01-L08 records')
    for gate in gates:
        if gate['status'] not in STATUSES:
            failures.append(f"{gate['id']}: invalid local status")
        if gate['status'] == 'passed' and not has_pass_evidence(gate):
            failures.append(f"{gate['id']}: local pass lacks evidence/reviewer")
    if local['status'] not in {'in_progress', 'complete'}:
        failures.append('Local plan status must be in_progress or complete')
    if local['status'] == 'complete' and (
            len(gates) != 8 or any(gate['status'] != 'passed' for gate in gates)):
        failures.append('Plan completion requires all eight local gates to pass')

    mapping = local['originalGateMapping']
    if [row['id'] for row in mapping] != [f'G{i:02}' for i in range(1, 39)]:
        failures.append('Map all original G01-G38 requirements in order')
    originals = {gate['id']: gate['requirement'] for gate in launch['gates']}
    for row in mapping:
        if row['originalRequirement'] != originals.get(row['id']):
            failures.append(f"{row['id']}: original launch requirement changed without updating its mapping")
        if any(gate not in expected for gate in row['localGates']):
            failures.append(f"{row['id']}: unknown local gate mapping")

    policy = local['policy']
    for document in (launch, work, dogfood):
        if document['completionPolicy'] != policy:
            failures.append('Completion policy disagrees across plan records')
    for field in ('launchGatesBlockPlanCompletion', 'paymentsRequiredForPlanCompletion',
                  'paymentImplementationRequiredForEarlyLaunch',
                  'paymentActivationRequiredForEarlyLaunch',
                  'physicalDevicesRequiredForPlanCompletion',
                  'publishedPackagesRequiredForPlanCompletion',
                  'historicalHoldsReleased', 'deploymentAuthorized',
                  'evidenceReclassifiedAsPassed'):
        if policy[field] is not False:
            failures.append(f'Completion policy must keep {field}=false')
    if policy['testingAndEarlyLaunch'] != 'free':
        failures.append('Testing and early launch must remain free')
    if [package['id'] for package in work['packages']] != [f'W{i:02}' for i in range(1, 19)]:
        failures.append('Retain ordered W01-W18 packages')
    for package in work['packages']:
        if not package['acceptance'] or not package.get('launchAcceptance'):
            failures.append(f"{package['id']}: missing local or retained launch acceptance")
    if [milestone['id'] for milestone in dogfood['milestones']] != [f'D{i}' for i in range(9)]:
        failures.append('Retain ordered D0-D8 milestones')
    for milestone in dogfood['milestones']:
        acceptance = milestone['localAcceptance']
        required = milestone['id'] != 'D7'
        if acceptance['requiredForPlanCompletion'] is not required:
            failures.append(f"{milestone['id']}: incorrect local completion scope")
        if acceptance['status'] not in STATUSES:
            failures.append(f"{milestone['id']}: invalid local status")
        if required and not acceptance['requiredEvidence']:
            failures.append(f"{milestone['id']}: missing local evidence requirement")
        if acceptance['status'] == 'passed' and not has_pass_evidence(acceptance):
            failures.append(f"{milestone['id']}: local pass lacks evidence/reviewer")
        if required and any(gate['id'] == 'L08' and gate['status'] == 'passed' for gate in gates):
            if acceptance['status'] != 'passed':
                failures.append(f"L08: required local {milestone['id']} remains unfinished")
    return failures


def check(root):
    try:
        return check_documents({name: json.loads((root / name).read_text()) for name in INPUTS})
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f'Invalid local completion records: {error}']


if __name__ == '__main__':
    failures = check(Path(__file__).resolve().parents[1])
    print(json.dumps({'status': 'failed' if failures else 'passed',
                      'scope': 'plan-record-consistency-only',
                      'failures': failures}, indent=2))
    sys.exit(bool(failures))
