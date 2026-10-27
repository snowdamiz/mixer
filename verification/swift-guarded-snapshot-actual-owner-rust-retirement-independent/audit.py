"""Independent offline source/MIR/negative-claim review. Executes no compiler/test."""
from pathlib import Path
import collections,gzip,hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
OLD=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-implementation'
def sha(b):return hashlib.sha256(b).hexdigest()
def row(p):
    b=p.read_bytes();return dict(path=str(p.relative_to(ROOT)),bytes=len(b),sha256=sha(b))
def write(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def main():
    current=P/'source/vm';old=OLD/'source/vm';changed=[]
    manifest=json.loads((P/'source-manifest.json').read_text())
    for m in manifest['members']:
        a=(current/m['path']).read_bytes();b=(old/m['path']).read_bytes()
        if a!=b:changed.append(m['path'])
    assert changed==['src/experimental_swift_reactor/cache/initial_profile_v1.rs','src/experimental_swift_reactor/retained_profile_loader_v1.rs']
    source=(current/changed[1]).read_text();witness=(ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-independent/retirement_witness.inc.rs').read_text()
    assert witness in source
    sourceprod=source[:source.index('    #[cfg(test)]\n    mod prepaid_actual_owner_v1')]
    uses=[dict(line=n,text=s.strip()) for n,s in enumerate(source.splitlines(),1) if 'correlation_retirement_blocked' in s]
    productionuses=[v for v in uses if v['line']<2130]
    assert len(productionuses)==5
    assert 'correlation_retirement_blocked: Cell::new(false)' in sourceprod
    assert sourceprod.count('correlation_retirement_blocked.set(true)')==1
    assert 'correlation_retirement_blocked.set(false)' not in source
    immutable_loader_prefix=(OLD/'source/vm'/changed[1]).read_text().split('// Actual private ownership core.')[0]
    assert source.split('// Actual private ownership core.')[0]==immutable_loader_prefix
    # Custody of all compiler output, including non-function items, is independent
    # of its producer's narrative. This review selects no layout or price.
    raw=gzip.decompress((P/'mir/actual.mir.gz').read_bytes())
    assert len(raw)==85605256 and sha(raw)=='607443be7812f74afb7d2556c5b00c34cf0721aabe2f2d53bd6d788e1462e4c2'
    lines=raw.decode().splitlines(keepends=True);starts=[]
    for i,line in enumerate(lines):
        kind=next((name for prefix,name in [('fn ','fn'),('const ','const'),('static ','static')] if line.startswith(prefix)),None)
        if line.startswith('alloc') and line[5:6].isdigit():kind='alloc'
        if not kind and line and not line[0].isspace() and line.rstrip().endswith(' = {') and ': ' in line:kind='standalone_const'
        if kind:starts.append((i,kind))
    items=[]
    for k,(start,kind) in enumerate(starts):
        end=starts[k+1][0] if k+1<len(starts) else len(lines)
        body=''.join(lines[start:end]).encode()
        items.append(dict(kind=kind,header=lines[start].rstrip(),bytes=len(body),sha256=sha(body)))
    assert items==json.loads((P/'complete-mir-item-inventory.json').read_text())['items']
    selected=[]
    for f in sorted((P/'mir').glob('*.mir')):
        fragment=f.read_bytes();assert raw.count(fragment)==1
        selected.append(row(f))
    assert len(selected)==6
    # Save compact *complete* selected bodies for human review, omitting only
    # compiler source-span comments and local storage/debug declarations.
    compact=[]
    for f in sorted((P/'mir').glob('*.mir')):
        compact.append('\n'+f.name+'\n')
        for line in f.read_text().splitlines():
            text=line.split('//')[0].rstrip()
            if text and not text.lstrip().startswith(('debug ','let ','StorageLive(','StorageDead(')):compact.append(text+'\n')
    (HERE/'mir-control-flow-reviewed.txt').write_text(''.join(compact))
    negative=[]
    for name in ['C01-clone','C03-correspondence','C04-proof-source','C04-root-reservation','C05-expected-fields','C05-admitted-constructor']:
        r=json.loads((P/'commands'/name/'receipt.json').read_text());assert r['exit']!=0 and r['child_reaped'] and r['exact_owned_group_absent'] and r['source_unchanged'] and r['input_unchanged']
        stderr=(P/'commands'/name/'stderr').read_text();errors=[x for x in stderr.splitlines() if x.startswith('error') and not x.startswith('error: aborting')]
        assert len(errors)==(2 if name=='C01-clone' else 1)
        probe=json.loads((P/'probes'/name/'probe.json').read_text())
        for diagnostic in probe['intended_diagnostics']:assert diagnostic in stderr
        negative.append(dict(id=name,errors=errors,probe=row(P/'probes'/name/'probe.json'),stderr=row(P/'commands'/name/'stderr'),receipt=row(P/'commands'/name/'receipt.json'),
            claim='Only the explicitly selected trait/borrow/lifetime/privacy operation shown by exact source and diagnostics.'))
    report=dict(schema=1,command=sys.argv,python=sys.version,offline_review=True,compiler_runtime_executed=False,
        source146_tree=manifest['tree_sha256'],changed=changed,original_IR01_witness_exact=True,loader_prefix_and_host_account_unchanged=True,
        source_barrier_uses=productionuses,
        source_conclusions=[
            'Flag initialized false only at owner construction; set true before duplicate-attempt test and expected/attempt publication. No production reset/discharge API.',
            'Retirement reads flag before retirement_started, original resources, cleanup work or bridge effects. True returns same owner; no Complete token exists on that branch.',
            'Matched, loader-error, provenance-mismatch, association/live refusal, extracted/forgotten/destroyed or unused result cannot change the permanent flag.',
            'Unissued token release subtracts original storage only with checked subtraction, retains work/peak and reserved once flag. Dropping token/owner/reservation has no refund implementation.',
            'Result and extractor have no owner/root lifetime. Result can outlive owner and ledger; no durable charge owner survives ledger destruction. This separate limit prevents broad root-lifetime/ownership acceptance.',
            'Production outer caller destroys child before owner retirement and returns scalar observations; current concrete route does not return the escaping proof carrier.',
            'Production bootstrap policy/startup/allocator/custody remain Pending; native retirement bridge always returns original File with RetirementIncomplete. No currently reachable native success/refund path established.'
        ],
        MIR=dict(archive=row(P/'mir/actual.mir.gz'),uncompressed_sha256=sha(raw),uncompressed_bytes=len(raw),all_items_exact=True,count=len(items),counts=dict(collections.Counter(x['kind'] for x in items)),selected_exact=selected,
            reviewed='correlation scope bb0 set true, bb1 replace attempt, bb4 publish; retirement bb0 get, bb1 branch, bb2 return Retained->bb78; cleanup branch begins only bb5 and cannot be reached from blocked normal return. Correlate/facade moves originals on every return. Token release preserves work/peak; facade drops retained owner without refund.',
            unpriced='New Cell and all owner/call/capture/move/return changes remain unpriced; full MIR custody and control-flow review do not establish stack/layout/native costs.'),
        selected_producer_negatives=negative,
        compiler_claim_limits='No new independent negatives. Fresh producer negatives prove selected six operations only; Copy/replay/unqualified/caller-map/cfg(test) negatives are historical; external metadata consumer unrun. C03 protects live expected borrow, not owned result after that borrow ends.',
        GA_native_funding_layouts_prices_FieldLog_OTA='Pending')
    write(HERE/'source-mir-negative-review.json',report)
    print(json.dumps(dict(source_members=146,changed=changed,MIR_items=len(items),MIR_counts=report['MIR']['counts'],exact_selected=6,negatives_reviewed=6,compiler_runtime=0)))
if __name__=='__main__':main()
