#!/usr/bin/env python3
"""Read-only independent audit of the producer seal and saved executions."""
from pathlib import Path
from collections import Counter
import hashlib, json, re, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT/'verification/swift-shared-numeric-extraction'
OUT = HERE/'20261024T004648645488Z'
sha = lambda x: hashlib.sha256(x).hexdigest()
jsonbytes = lambda x: (json.dumps(x, sort_keys=True, indent=2)+'\n').encode()
load = lambda p: json.loads(p.read_text())
def archive(path):
    with tarfile.open(path) as tf:
        return {p.name.removeprefix('vm/'): tf.extractfile(p).read() for p in tf.getmembers() if p.isfile()}
def lines(text, prefix):
    return [x[x.index(prefix):] for x in text.splitlines() if prefix in x]
sealpath = PRODUCER/'seal.json'
seal = load(sealpath)
assert sha(sealpath.read_bytes()) == '3aa593f55798bc9e381119a865b1a2388dcebc7272395e1a035a0b3ed04a8e58'
assert len(seal['bindings']) == seal['bindingCount'] == 229
for p,h in seal['bindings'].items(): assert sha((ROOT/p).read_bytes()) == h, p
mainpath = PRODUCER/'results/20261024T003757200365Z'
oraclepath = PRODUCER/'oracles/20261024T004030182031Z'
main = load(mainpath/'receipt.json'); oracle = load(oraclepath/'receipt.json')
baseline = archive(mainpath/'baseline-source.tar.gz'); candidate = archive(mainpath/'product-source.tar.gz')
assert sha((mainpath/'baseline-source.tar.gz').read_bytes()) == main['baselineArchiveSHA256']
assert sha((mainpath/'product-source.tar.gz').read_bytes()) == main['productArchiveSHA256']
candidate_manifest = {p:sha(b) for p,b in candidate.items()}
assert candidate_manifest == load(mainpath/'product-source-manifest.json')
assert sha(jsonbytes(candidate_manifest)) == main['productSourceTreeSHA256']
assert candidate_manifest == load(OUT/'product-source-manifest.json')
assert all((ROOT/'vm'/p).read_bytes() == b for p,b in candidate.items())
assert {p for p in baseline if baseline[p] != candidate[p]} == {
    'src/experimental/execution/mod.rs', 'src/experimental/execution/borrowed.rs'}
assert set(candidate)-set(baseline) == {'tests/span_numeric_extraction.rs'}
baseline_revision = load(PRODUCER/'layout-review/20261024T003352353904Z/receipt.json')['revision']
for p,b in baseline.items():
    blob = subprocess.check_output(['git','show',baseline_revision+':vm/'+p], cwd=ROOT)
    assert blob == b, p
for directory, receipt in [(mainpath,main),(oraclepath,oracle)]:
    for cmd in receipt['commands']:
        assert sha((directory/cmd['log']).read_bytes()) == cmd['logSHA256'], cmd['name']
        assert cmd['exit'] == (101 if 'clippy-broad' in cmd['name'] else 0), cmd['name']
        if cmd['target']: assert cmd['sourceBeforeAfterVerified']
counts=[]
for directory,features in [(mainpath,['default','span','swift','all']), (oraclepath,['default','span','all'])]:
    for variant in ['baseline','candidate']:
        for feature in features:
            for profile in ['debug','release']:
                name=f'{variant}-{feature}-{profile}'
                text=(directory/(name+'.log')).read_text()
                listed=(directory/(name+'-list.log')).read_text()
                names=[x[:-6] for x in listed.splitlines() if x.endswith(': test')]
                actual=re.findall(r'^test ([\w:]+) \.\.\. (.*)$',text,re.M)
                assert Counter(names)==Counter(x for x,_ in actual),name
                summaries=re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text,re.M)
                passed=sum(int(x[0]) for x in summaries); ignored=sum(int(x[2]) for x in summaries)
                assert all(int(x[1])==0 for x in summaries),name
                expected={'default':22,'span':48,'swift':137,'all':186}[feature] if directory==mainpath else 6
                assert passed==expected and ignored==(6 if directory==mainpath else 0),name
                counts.append(dict(kind='selected' if directory==mainpath else 'explicit-oracle',name=name,passed=passed,ignored=ignored))
positions_checked=0
for feature in ['span','all']:
    for profile in ['debug','release']:
        a=(mainpath/f'baseline-{feature}-{profile}.log').read_text()
        b=(mainpath/f'candidate-{feature}-{profile}.log').read_text()
        for prefix in ['numeric_trace ', 'primitive_window ', 'primitive_position ', 'numeric_owner ', 'numeric_offset ', 'numeric_reservation ']:
            assert lines(a,prefix)==lines(b,prefix),prefix
        assert len(lines(a,'numeric_trace '))==454
        windows=lines(a,'primitive_window ')
        sizes=[int(re.search(r'size=(\d+)',x)[1]) for x in windows]
        assert sizes==[464,416,384,456,384,416,392,424]
        bywindow={}
        for item in lines(a,'primitive_position '):
            match=re.fullmatch(r'primitive_position (\w+) (\w+) offset=(\d+) bytes=(\d+)',item)
            assert match,item
            window,field,offset,size=match.groups()
            bywindow.setdefault(window,[]).append((field,int(offset),int(size)))
        for window,size in zip(windows,sizes):
            name=window.split()[1]; ps=bywindow[name]; fields={x[0] for x in ps}
            assert {'new_helper_state_source','new_helper_state_argument','new_values_state_source','new_values_state_argument',
                'new_values_arena_source','new_values_arena_returned','new_values_arena_caller','old_primitive_result_source',
                'old_primitive_result_returned','new_helper_result_caller','new_helper_result_returned','old_owner_result_caller'} <= fields
            intervals=sorted((offset,offset+n) for _,offset,n in ps)
            assert intervals[0][0]==0 and intervals[-1][1]<=size
            assert all(right<=nextleft for (_,right),(nextleft,_) in zip(intervals,intervals[1:]))
            positions_checked+=len(ps)
def lint(text):
    found=[]; source=text.splitlines()
    for i,line in enumerate(source):
        if line.startswith('error:') and not line.startswith('error: could not compile'):
            location=next(x.strip().split('--> ',1)[1] for x in source[i+1:i+5] if '--> ' in x)
            found.append((line,location))
    return sorted(found)
base_lint=lint((mainpath/'baseline-clippy-broad.log').read_text())
new_lint=lint((mainpath/'product-clippy-broad.log').read_text())
assert base_lint==new_lint and len(new_lint)==26
report=dict(schema=1,status='passed-independent-producer-artifact-audit-only',
    producerSealSHA256=sha(sealpath.read_bytes()),bindingsChecked=len(seal['bindings']),
    productSourceTreeSHA256=main['productSourceTreeSHA256'],baselineSourceMatchesGitRevision=baseline_revision,
    productSourceMatchesIndependentTestSnapshot=True,
    mainCommandLogsChecked=len(main['commands']),oracleCommandLogsChecked=len(oracle['commands']),
    runtimeTests=counts,layoutPositionsChecked=positions_checked,maximumDerivedInventoryBytes=464,
    originalScalarComponentBytes=512,baselineCandidateClippyDiagnosticsEqual=26,
    scope='Exact producer seal, archived product and baseline source, command logs, selected runtime test identities, parity traces, disjoint typed inventory positions and unchanged broad Clippy limitation. Inventory probes are derived source maps, not compiler stack measurements; no full Swift target, device, release, consumer or GA qualification.')
(OUT/'producer-audit.json').write_bytes(jsonbytes(report))
print(json.dumps({k:v for k,v in report.items() if k!='runtimeTests'},sort_keys=True))
