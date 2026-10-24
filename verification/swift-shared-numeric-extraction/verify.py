#!/usr/bin/env python3
"""Audit exact snapshots, commands, executed test names, parity, and lint limits."""
from pathlib import Path
from collections import Counter
import hashlib, json, re, tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN=HERE/'results/20261024T003757200365Z'
ORACLES=HERE/'oracles/20261024T004030182031Z'
sha=lambda b:hashlib.sha256(b).hexdigest()
jsonbytes=lambda v:(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def read_json(path):return json.loads(path.read_text())
def archive(path):
    with tarfile.open(path) as tf:
        return {p.name.removeprefix('vm/'):tf.extractfile(p).read() for p in tf.getmembers() if p.isfile()}
def manifest(files):return {p:sha(b) for p,b in files.items()}
def filtered(text,prefix):return [line[line.index(prefix):] for line in text.splitlines() if prefix in line]
def tests(log,listed):
    names=[line[:-6] for line in listed.splitlines() if line.endswith(': test')]
    started=re.findall(r'^test ([\w:]+) \.\.\. (.*)$',log,re.M)
    assert Counter(name for name,_ in started)==Counter(names),'runtime/list mismatch'
    ignored=[name for name,outcome in started if outcome.startswith('ignored')]
    passed=[name for name,outcome in started if not outcome.startswith('ignored')]
    summaries=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',log)
    assert sum(int(x[0]) for x in summaries)==len(passed)
    assert sum(int(x[2]) for x in summaries)==len(ignored)
    assert all(int(x[1])==0 for x in summaries)
    return dict(passed=passed,ignored=ignored,passedCount=len(passed),ignoredCount=len(ignored))
def lint(text):
    lines=text.splitlines();found=[]
    for i,line in enumerate(lines):
        if line.startswith('error:') and not line.startswith('error: could not compile'):
            location=next((x.strip().split('--> ',1)[1] for x in lines[i+1:i+5] if '--> ' in x),None)
            assert location,'unlocated lint diagnostic'
            found.append(dict(message=line,location=location))
    return sorted(found,key=lambda item:(item['location'],item['message']))

main=read_json(MAIN/'receipt.json');oracle=read_json(ORACLES/'receipt.json')
assert main['status']=='passed-host-primitive-dispatch-parity-only'
assert oracle['status']=='passed-explicit-existing-development-oracles-only'
for directory,receipt in [(MAIN,main),(ORACLES,oracle)]:
    for command in receipt['commands']:
        assert sha((directory/command['log']).read_bytes())==command['logSHA256']
        if command['target']:assert command['sourceBeforeAfterVerified']
        if 'clippy-broad' in command['name']:assert command['exit']!=0
        else:assert command['exit']==0
baseline=archive(MAIN/'baseline-source.tar.gz');product=archive(MAIN/'product-source.tar.gz')
assert sha((MAIN/'baseline-source.tar.gz').read_bytes())==main['baselineArchiveSHA256']
assert sha((MAIN/'product-source.tar.gz').read_bytes())==main['productArchiveSHA256']
product_manifest=manifest(product)
assert product_manifest==read_json(MAIN/'product-source-manifest.json')
assert all((ROOT/'vm'/p).read_bytes()==b for p,b in product.items()),'live VM differs from tested snapshot'
assert len(product)==len(baseline)+1
changed={p for p,b in baseline.items() if product[p]!=b}
assert changed=={'src/experimental/execution/mod.rs','src/experimental/execution/borrowed.rs'}
assert set(product)-set(baseline)=={'tests/span_numeric_extraction.rs'}
assert product['tests/span_numeric_extraction.rs']==(HERE/'public_numeric_probe.rs').read_bytes()
for files in [baseline,product]:
    code=files['src/experimental/execution/mod.rs']
    start=code.index(b'        self.reserve(\n            size_of::<Self>()')
    end=code.index(b'        self.values = self.allocation',start)
    formula=code[start:end]
    if files is baseline:original_formula=formula
    else:assert formula==original_formula
    assert code.count(b'    fn numeric(&mut self, opcode: u8, saturating: bool)')==1
probe_input=MAIN/'probe-inputs'
for name,h in main['inputs'].items():assert sha((probe_input/name).read_bytes())==h
for variant,files in [('baseline',baseline),('candidate',product)]:
    derived=dict(files)
    derived['tests/span_numeric_extraction.rs']=(probe_input/'public_numeric_probe.rs').read_bytes()
    derived['src/experimental/execution/mod.rs']+=b'\n#[cfg(all(test, feature = "experimental-span-execution"))]\n#[path = "numeric_layout_probe.rs"]\nmod numeric_layout_probe;\n'
    derived['src/experimental/execution/numeric_layout_probe.rs']=b'use super::*;\n'+(probe_input/'layout_probe.rs').read_bytes()
    assert manifest(derived)==read_json(MAIN/(variant+'-probe-manifest.json'))
selected=[];scope=[]
for variant in ['baseline','candidate']:
    for feature in ['default','span','swift','all']:
        for profile in ['debug','release']:
            name=variant+'-'+feature+'-'+profile
            result=tests((MAIN/(name+'.log')).read_text(),(MAIN/(name+'-list.log')).read_text())
            expected={'default':22,'span':48,'swift':137,'all':186}[feature]
            assert result['passedCount']==expected and result['ignoredCount']==6
            result.update(variant=variant,feature=feature,profile=profile,selectedTargetsOnly=True)
            selected.append(result)
for feature in ['default','span','swift','all']:
    for profile in ['debug','release']:
        a=(MAIN/('baseline-'+feature+'-'+profile+'.log')).read_text()
        b=(MAIN/('candidate-'+feature+'-'+profile+'.log')).read_text()
        for prefix in ['numeric_trace ','primitive_window ','primitive_position ','numeric_offset ',
            'numeric_owner ','numeric_reservation ','layout ','offset ']:
            assert filtered(a,prefix)==filtered(b,prefix)
        if feature in ['span','all']:
            assert len(filtered(a,'numeric_trace '))==454
            sizes=[int(re.search(r'size=(\d+)',line).group(1)) for line in filtered(a,'primitive_window ')]
            assert sizes==[464,416,384,456,384,416,392,424] and max(sizes)<=512
for variant in ['baseline','candidate']:
    for feature in ['default','span','all']:
        for profile in ['debug','release']:
            name=variant+'-'+feature+'-'+profile
            result=tests((ORACLES/(name+'.log')).read_text(),(ORACLES/(name+'-list.log')).read_text())
            assert result['passedCount']==6 and result['ignoredCount']==0
            result.update(variant=variant,feature=feature,profile=profile)
            scope.append(result)
old_lint=lint((MAIN/'baseline-clippy-broad.log').read_text())
new_lint=lint((MAIN/'product-clippy-broad.log').read_text())
assert old_lint==new_lint and len(new_lint)==26
assert all(not any(x in item['location'] for x in ['execution/borrowed.rs','execution/mod.rs','span_numeric_extraction.rs']) for item in new_lint)
summary=dict(schema=1,status='verified-selected-host-primitive-dispatch-slice-only',
    sourceFiles=dict(baseline=len(baseline),product=len(product)),productSourceTreeSHA256=main['productSourceTreeSHA256'],
    selectedTests=selected,explicitOracleTests=scope,selectedPassedExecutions=sum(x['passedCount'] for x in selected),
    explicitOraclePassedExecutions=sum(x['passedCount'] for x in scope),broadClippy=dict(passed=False,baselineCandidateDiagnosticsEqual=True,diagnostics=new_lint),
    scope='Selected library/numeric/allocation/oracle targets; not the complete product integration suite, Swift execution, device, published consumer or GA qualification.',
    mainReceipt=str((MAIN/'receipt.json').relative_to(ROOT)),oracleReceipt=str((ORACLES/'receipt.json').relative_to(ROOT)))
(HERE/'verified-summary.json').write_bytes(jsonbytes(summary))
if (HERE/'seal.json').exists():
    seal=read_json(HERE/'seal.json')
    for name,h in seal['bindings'].items():
        assert sha((ROOT/name).read_bytes())==h,'sealed artifact changed: '+name
print(json.dumps(dict(status=summary['status'],selectedPassedExecutions=summary['selectedPassedExecutions'],explicitOraclePassedExecutions=summary['explicitOraclePassedExecutions'],matchedPublicTraceRecords=454,maximumScalarInventory=464,broadLintDiagnostics=len(new_lint),productSourceTreeSHA256=main['productSourceTreeSHA256']),sort_keys=True))
