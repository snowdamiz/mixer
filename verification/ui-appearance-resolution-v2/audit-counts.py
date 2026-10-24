#!/usr/bin/env python3
"""Audit disjoint XCTest/Swift Testing outcomes in an existing frozen receipt.

The first collector version stored only the first Swift Testing target summary
in sdkTestCounts. This separate immutable audit supersedes that count field,
without modifying the producer source/receipt or duplicating XCTest suite totals.
"""
from pathlib import Path
import datetime, hashlib, json, re, sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
label = sys.argv[1]
if not label or '/' in label or label in ('.','..'): raise ValueError('single candidate label required')
folder = HERE / label
receipt = json.loads((folder/'receipt.json').read_text())
if receipt['status'] != 'passed-pure-v2-data-and-compilation-only': raise RuntimeError('producer not passed')
bindings = {'verification/ui-appearance-resolution-v2/audit-counts.py':sha(Path(__file__)),
    str((folder/'receipt.json').relative_to(ROOT)):sha(folder/'receipt.json')}
function_owners = {}
for path in sorted((folder/'inputs/sdk/Tests').rglob('*.swift')):
    relative = str(path.relative_to(folder/'inputs'))
    if sha(path) != receipt['inputManifest'][relative]: raise RuntimeError('frozen source changed '+relative)
    target = path.relative_to(folder/'inputs/sdk/Tests').parts[0]
    for function in re.findall(r'\bfunc\s+(\w+)\s*\(',path.read_text()):
        function_owners.setdefault(function,set()).add(target)
counts = {}
for mode in ['debug','release']:
    command = next(c for c in receipt['commands'] if c['name'] == 'sdk-'+mode)
    log = ROOT / command['log']
    if command['exitCode'] != 0 or sha(log) != command['sha256']: raise RuntimeError('command/log mismatch')
    bindings[command['log']] = sha(log)
    text = log.read_text()
    xctest = re.findall(r"Test Case '-\[([\w]+)\.([^\]]+)\]' passed",text)
    if len(xctest) != len(set(xctest)): raise RuntimeError('duplicate XCTest case')
    swift = re.findall(r'✔ Test (\w+)\([^\n]*\) passed',text)
    if len(swift) != len(set(swift)): raise RuntimeError('duplicate Swift Testing case')
    summaries = list(map(int,re.findall(r'✔ Test run with (\d+) tests .*passed',text)))
    if len(swift) != sum(summaries): raise RuntimeError('Swift Testing outcome/summary mismatch')
    targets = {}
    for function in swift:
        owners = function_owners.get(function,set())
        if len(owners) != 1: raise RuntimeError('ambiguous/missing frozen test owner '+function)
        owner = next(iter(owners)); targets[owner] = targets.get(owner,0)+1
    xctargets = {}
    for owner,case in xctest: xctargets[owner] = xctargets.get(owner,0)+1
    # Count actual passed cases once. XCTest emits nested 5/3/8/8 suite
    # summaries for these same 8 cases; those are never added together.
    if targets != {'MixerUITests':107,'MixerCoreTests':10,'MixerAppleTests':2}: raise RuntimeError('unexpected observed Swift Testing target counts')
    if xctargets != {'MixerUITests':8}: raise RuntimeError('unexpected observed XCTest target counts')
    counts[mode] = dict(xctest=dict(targets=xctargets,total=len(xctest),passedCases=[owner+'.'+case for owner,case in xctest]),
        swiftTesting=dict(targets=targets,total=len(swift),summaries=summaries,passedFunctions=swift),
        total=len(xctest)+len(swift))
    print(mode,json.dumps({k:v for k,v in counts[mode].items() if k=='total'}), 'XCTest',len(xctest),'SwiftTesting',len(swift))
result = dict(format='mixer.ui-appearance-resolution-v2-count-audit.1',status='passed-observed-count-audit',
    observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),bindings=bindings,counts=counts,
    command=dict(argv=[sys.executable,str(Path(__file__).resolve()),label],cwd=str(Path.cwd()),pythonVersion=sys.version),
    sourceRevision=receipt['sourceRevision'],sourceTreeSHA256=receipt['sourceTreeSHA256'],
    producerFirstTargetOnlyCounts=receipt['sdkTestCounts'],supersedesProducerField='sdkTestCounts',
    explanation='Producer field contains only first Swift Testing target summary. Audit counts actual distinct passed cases/functions and checks all Swift Testing target summaries. XCTest nested suite summaries are not summed. Debug/Release each 127 = 8 XCTest + 107 MixerUI + 10 Core + 2 Apple.',
    scope='Count correction for existing frozen successful test outputs only; no rerun, source mutation, native/device or GA qualification.')
(folder/'count-audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
