from review import *
import difflib
vm=SCRATCH/'candidate/vm';base=SCRATCH/'baseline/vm'
# Measure omitted concrete compiler-owned roles without instantiating an
# accounting carrier or invoking an engine.
source=SCRATCH/'promotion_size.rs';source.write_bytes((HERE/'promotion_size.rs').read_bytes());binary=SCRATCH/'promotion_size'
p=run('promotion-type-compile',['rustc',str(source),'-o',str(binary)]);assert p.returncode==0
p=run('promotion-type-layout',[str(binary)]);assert p.returncode==0
(HERE/'promotion-executable.json').write_bytes(enc(dict(path=str(binary),sha256=sha(binary),bytes=binary.stat().st_size,sourceSHA256=sha(source))))
# Preserve exact failed attempt source and final independent test archive.
for label,name in [('adversarial','historical-adversarial-v1'),('adversarial-v2','adversarial')]:
 actual=manifest(SCRATCH/label/'vm');assert actual==json.loads((HERE/(name+'-source-manifest.json')).read_text())
# Record source review observations and unchanged authorities directly from
# accepted archives, independent of the mutable checkout.
results={}
for name in ['src/experimental_swift_reactor/frame_operations_tests.rs','src/experimental_swift_reactor/control_operations_tests.rs']:
 a=(base/name).read_text();b=(vm/name).read_text();results[name]=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='baseline/'+name,tofile='candidate/'+name))
(HERE/'prior-regression-source-diff.json').write_bytes(enc(results))
s=(vm/'src/experimental_swift_reactor/memory_operations.rs').read_text();lines=s.splitlines();at=next(i+1 for i,l in enumerate(lines) if 'if tests::PC_OVERFLOW.with' in l)
for feature in ['swift','all']:
 text=gzip.decompress((HERE/('mir-'+feature+'-unit.mir.gz')).read_bytes()).decode();m=re.search(r'^const memory_pinned_step::promoted\[0\]:[^\n]+',text,re.M);assert m;end=text.index('\n}',m.start())+2;(HERE/('omitted-promotion-'+feature+'-unit.mir')).write_text(text[m.start():end]+'\n')
# Fixed ticket authority lives in byte-identical source; no dependency changed.
authority=[]
for path in manifest(vm):
 if path.startswith('src/'):
  t=(vm/path).read_text()
  for i,line in enumerate(t.splitlines(),1):
   if '86' in line and ('TICKET' in line or 'ticket' in line):authority.append(dict(path=path,line=i,text=line,sourceUnchanged=sha(vm/path)==sha(base/path)))
assert authority and all(x['sourceUnchanged'] for x in authority)
(HERE/'source-review.json').write_bytes(enc(dict(candidateClosure=digest(manifest(vm)),baselineClosure=digest(manifest(base)),hookLine=at,hookSource='src/experimental_swift_reactor/memory_operations.rs',hookSnippet=lines[at-2:at+3],ticketAuthority=authority,sourceInventoryGap='Unit runtime PC_OVERFLOW call site emits independent promoted backing and return; schema has caller _55 reference only.',AF22='Only memory active term is added to previous frame/value/control formula exactly once; other diffs are crate-private test scaffold visibility. Runtime regressions preserved and executed.',viewLifetime='Actual cache view is a block-local immutable borrow; selected DecodedInstruction/function copied, view ends before cursor/fuel/work/PC/helper effects. Fresh compiler MIR and type-checking reproduce actual shapes.',slotFailure='Vacancy precedes active/cache/debits. Outer success publishes inner result; occupied outcomes preserved. Actual stored failures request terminal/drain; first failure includes original diagnostic plus cleanup observations.',accountingCarrierInstantiated=False)))
print(p.stdout.decode().strip(),flush=True);print('source review and ticket authority captured',flush=True)
