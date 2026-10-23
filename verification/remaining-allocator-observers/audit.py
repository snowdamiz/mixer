#!/usr/bin/env python3
"""Audit retained source identities and executable results for this test-only slice."""
from datetime import datetime, timezone
import hashlib, io, json, platform, re, subprocess, tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]; evidence=Path(__file__).resolve().parent
receipt=json.loads((evidence/'receipt.json').read_text()); original=json.loads((evidence/'original/receipt.json').read_text()); replay=json.loads((evidence/'original-replay-receipt.json').read_text())
checks=[]
def check(name,value):
    checks.append({'check':name,'passed':bool(value)})
    if not value:print('FAIL: '+name)
def digest(data):return hashlib.sha256(data).hexdigest()
def files(data):
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:return {m.name:digest(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
base=(evidence/'original/baseline-vm-snapshot.tar').read_bytes(); snap=(evidence/'tested-vm-snapshot.tar').read_bytes()
check('retained original revision archive',digest(base)==original['baseline_vm_export_sha256']==receipt['baseline_vm_export_sha256'])
check('baseline git export identity',base==subprocess.check_output(['git','archive','--format=tar',receipt['baseline_revision'],'vm'],cwd=root))
check('retained tested snapshot digest',digest(snap)==receipt['full_snapshot_sha256'])
base_files=files(base); snapshot_files=files(snap)
check('complete tested snapshot manifest',snapshot_files==receipt['source_before']['files'])
check('complete tested source digest',digest(json.dumps(snapshot_files,sort_keys=True).encode())==receipt['source_before']['sha256'])
check('immutable tested source',receipt['source_stable'] and receipt['source_before']==receipt['source_after'])
changed={p for p in set(base_files)|set(snapshot_files) if base_files.get(p)!=snapshot_files.get(p)}
check('exactly the four named test overlay paths differ',changed==set(receipt['overlay']))
for name,sha in receipt['overlay'].items():check('current overlay '+name,digest((root/name).read_bytes())==sha==snapshot_files[name])
ledger='vm/tests/common/allocation_observer.rs'
check('reviewed pointer ledger unchanged',base_files[ledger]==snapshot_files[ledger]==receipt['unchanged_pointer_ledger_sha256']==original['original_files'][ledger]==digest((root/ledger).read_bytes()))
# Compare complete assertion invocations, retaining strings and dropping only
# lexical whitespace. Runtime evidence remains the substantive pass condition.
def assertions(text):
    values=[]
    for match in re.finditer(r'\bassert(?:_eq|_ne)?!\s*\(',text):
        start=match.start();i=match.end();depth=1;quoted=False;escaped=False
        while depth:
            c=text[i]
            if quoted:
                if escaped:escaped=False
                elif c=='\\':escaped=True
                elif c=='"':quoted=False
            elif c=='"':quoted=True
            elif c=='(':depth+=1
            elif c==')':depth-=1
            i+=1
        value=text[start:i];tokens=[];quoted=False;escaped=False
        for c in value:
            if quoted:
                tokens.append(c)
                if escaped:escaped=False
                elif c=='\\':escaped=True
                elif c=='"':quoted=False
            elif c=='"':quoted=True;tokens.append(c)
            elif not c.isspace():tokens.append(c)
        values.append(''.join(tokens))
    return values
assertion_counts={}
for name in receipt['overlay']:
    if '/common/' in name:continue
    before=(evidence/'original'/Path(name).name).read_text();after=(root/name).read_text()
    a,b=assertions(before),assertions(after);check('all original assertions unchanged '+name,a==b)
    assertion_counts[name]=len(a)
prefixes=('native validate-only','native create32pages','native post allocation refusal','constructor requested allocation events=','fallible argument allocation refusal:','eight argument/completion payloads:','ready-poll/ack allocation calls=','close/drop/last-ticket-ack allocation calls=','all 12 allocation ordinals','observation ')
def measurements(log):return [line for line in log.splitlines() if line.startswith(prefixes)]
reference=measurements((evidence/'logs/original-baseline-debug.log').read_text())
check('all original measurement categories present',len(reference)==17)
for case in replay['cases']:
    snapshot_data=(root/case['full_snapshot']).read_bytes();check('original retained snapshot identity '+case['name'],digest(snapshot_data)==case['full_snapshot_sha256'] and files(snapshot_data)==case['source_files'])
    log=(root/case['log']).read_bytes();check('original command expected exit '+case['name'],case['exit']==case['expected_exit']);check('original log identity '+case['name'],digest(log)==case['log_sha256']);check('original source stable '+case['name'],case['source_stable'])
    text=log.decode()
    if case['mode']=='baseline':check('original exact measurements '+case['name'],measurements(text)==reference)
    elif case['mode']=='live':check('original exact synthetic hosted delta '+case['name'],'left: (20, 8389508, 8389508)' in text and 'right: (16, 8388608, 8388608)' in text)
    else:check('original background consumes first fault '+case['name'],'original fault worker allocated=false;calls_before_guest=1' in text and 'unwrap_err()` on an `Ok` value: Some(I32(0))' in text)
max_slots={}
for case in receipt['checks']:
    log=(root/case['log']).read_bytes();check('repaired command pass '+case['name'],case['exit']==0);check('repaired log identity '+case['name'],digest(log)==case['log_sha256']);check('repaired command source stable '+case['name'],case['source_before_sha256']==case['source_after_sha256']==receipt['source_before']['sha256'])
    if case['name']!='clippy':
        text=log.decode();check('three successful test processes '+case['name'],text.count('test result: ok. 1 passed; 0 failed; 0 ignored')==3);check('exact original measurements '+case['name'],measurements(text)==reference);check('1016-byte Arc OOM child remains abort '+case['name'],'known Shared Arc OOM abort: status=signal: 6 (SIGABRT)' in text and 'memory allocation of 1016 bytes failed' in text)
        slots=[int(v) for v in re.findall(r'observer maximum ownership slots=(\d+) capacity=4096',text)];max_slots[case['name']]=slots;check('bounded ledger observations '+case['name'],len(slots)==3 and all(0<v<=4096 for v in slots))
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'command':'python3 verification/remaining-allocator-observers/audit.py','python':platform.python_version(),'auditor_source_sha256':digest(Path(__file__).read_bytes()),'baseline_revision':receipt['baseline_revision'],'snapshot_sha256':receipt['full_snapshot_sha256'],'tested_tree_sha256':receipt['source_before']['sha256'],'tested_file_count':len(snapshot_files),'overlay':receipt['overlay'],'original_assertion_counts':assertion_counts,'original_measurements':reference,'max_ledger_slots_by_run_in_order_ffi_stream_guest':max_slots,'checks':checks,'passed':all(c['passed'] for c in checks),'scope':'Local host test instrumentation audit. Original hosted CI allocation stack remains unattributed. No physical-device, published-package, release, or GA qualification.'}
(evidence/'audit-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(f"{sum(c['passed'] for c in checks)}/{len(checks)} checks passed")
raise SystemExit(not result['passed'])
