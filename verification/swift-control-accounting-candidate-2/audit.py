#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,tarfile,difflib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=Path(sys.argv[1])
s=importlib.util.spec_from_file_location('builder',HERE/'build_overlay.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
s=importlib.util.spec_from_file_location('inventory',HERE/'inventory.py');iv=importlib.util.module_from_spec(s);s.loader.exec_module(iv)
enc=b.enc;sha=b.sha;digest=lambda x:hashlib.sha256(enc(x)).hexdigest()
save=lambda n,x:(OUT/n).write_bytes(enc(x))
# Rebind every canonical field to the qualifying draft's unoptimized spanned MIR.
prior=json.loads((HERE/'inventory-schema.json').read_text());bound=[];functions=[]
for config in ['production','unit']:
 path=OUT/('swift-debug-'+config+'.mir');rows,defs=iv.inventory(path,config);rows+=iv.complete_delta(path,config);functions+=defs
 old=[r for r in prior if r['config']==config]
 assert [(r['field'],r['rustType'],r['envelope']) for r in old]==[(r['field'],r['rustType'],r['envelope']) for r in rows],(config,'canonical role/type changed')
 by_name={r['field']:r for r in old};qualifying_sha=sha(path);qualifying_tree=json.loads((OUT/'receipt.json').read_text())['candidateTreeSHA256']
 bodies={name:(params,body,line) for name,params,body,line in iv.prior.functions(path.read_text())}
 for row in rows:
  row['ownerClass']=by_name[row['field']]['ownerClass'];params,body,line=bodies[row['mirFunction']]
  bind=row['binding'];spans=[]
  if bind.startswith('_'):
   for m in re.finditer(r'(?:let (?:mut )?'+re.escape(bind)+r': [^\n]+;|debug [\w_]+ => '+re.escape(bind)+r';)[^\n]*',body):
    location=re.search(r' at (src/[^\n]+)',m.group(0))
    if location:spans.append(location.group(1))
  else:
   for m in re.finditer(r'debug '+re.escape(bind)+r' => [^\n]+',body):
    location=re.search(r' at (src/[^\n]+)',m.group(0))
    if location:spans.append(location.group(1))
  if row['binding'].startswith('literal_'):
   for m in re.finditer(r'const '+re.escape(row['sourceNames'][0])+r'[^\n]*',body):
    location=re.search(r' at (src/[^\n]+)',m.group(0))
    if location:spans.append(location.group(1))
  row['sourceSpans']=sorted(set(spans));row['qualifyingMIR']=path.name;row['qualifyingMIRSHA256']=qualifying_sha
  row['sourceTreeSHA256']=qualifying_tree;bound.append(row)
source=[r for r in prior if r['config']=='source'];bound+=source;assert len(bound)==len(prior)
frame_source=(HERE/'overlay/src/experimental_swift_reactor/frame_operations.rs').read_text();control_source=(HERE/'overlay/src/experimental_swift_reactor/control_operations.rs').read_text()
def source_span(path,text,needle):
 at=text.index(needle);line=text.count('\n',0,at)+1;return f'{path}:{line}:1: {line}:{len(text.splitlines()[line-1])+1}'
slot_span=source_span('src/experimental_swift_reactor/frame_operations.rs',frame_source,'    pub controlled:')
complete_span=source_span('src/experimental_swift_reactor/frame_operations.rs',frame_source,'    pub(crate) fn complete(self, storage:')
drop_span=source_span('src/experimental_swift_reactor/frame_operations.rs',frame_source,'            drop((parts, storage));')
restore_span=source_span('src/experimental_swift_reactor/frame_operations.rs',frame_source,'        let restored = control.end_construction_phase_with_wasi(')
result_span=source_span('src/experimental_swift_reactor/control_operations.rs',control_source,'    pub(crate) fn control_operation(')
failure_span=source_span('src/experimental_swift_reactor/frame_operations.rs',frame_source,'            first_failure: control.record_cleanup(')
for row in bound:
 if row['config']=='source':
  row['sourceSpans']={'fixed_caller':[slot_span], 'prepare_storage':[slot_span], 'complete_storage':[complete_span,slot_span], 'complete_drop_tuple':[drop_span,restore_span], 'return_wrapper':[result_span,slot_span], 'retained_report':[failure_span,complete_span,slot_span]}[row['window']]
  row['logicalRole']='Distinct positive fixed-result transfer roles at the existing fixed storage/completion boundary; not a claim of simultaneous optimizer machine-stack objects.'
 elif not row.get('sourceSpans'):
  capture=re.search(r'\{closure@([^}]+)\}',row['mirType']);assert capture,row;row['sourceSpans']=[capture.group(1)];row['sourceSpanOrigin']='actual compiler closure type identity'
assert all(row.get('sourceSpans') for row in bound)
save('bound-inventory-schema.json',bound);save('canonical-function-manifest.json',functions)
# Exact arithmetic is independent of constructor bootstrap, which completes first.
comparison=json.loads((OUT/'baseline-comparisons.json').read_text())
for row in comparison:
 row['phasePreviousBound']=0;row['phaseBoundaryAt']=row['exactFrameBound'];row['phaseBoundaryBelow']=row['exactFrameBound']-1;row['headerPlusFrameBound']=row['exactHeader']+row['exactFrameBound']
 row['generalPhaseFormula']='checked previous + exactFrameBound; preserve existing rejection debt'
 row['stateBudgetCeiling']=128*1024*1024;row['combinedBudgetCeiling']=256*1024*1024
 row['stateRemainingAfterHeader']=row['stateBudgetCeiling']-row['exactHeader'];row['combinedRemainingAfterHeaderAndFrame']=row['combinedBudgetCeiling']-row['headerPlusFrameBound']
save('corrected-boundary-comparisons.json',comparison)
save('accounting-scope.json',dict(rootClarification='Logical ownership accounting, not optimizer machine-stack bounds. Positive typed map uses actual authored source and canonical unoptimized production/unit transfer roles; existing nested inventories remain occupied exactly once. Optimized Release MIR retained only for coverage. No alias for core::num::niche_types::UsizeNoHighBit or other private optimizer-created temporaries.',binding='verification/swift-active-frames-root-review/acceptance.json',acceptanceSHA256=sha(ROOT/'verification/swift-active-frames-root-review/acceptance.json'),newFields=len(bound),sourceFields=len(source),canonicalProductionFields=sum(r['config']=='production' for r in bound),canonicalUnitFields=sum(r['config']=='unit' for r in bound),sourceSpanRows=sum(bool(r.get('sourceSpans')) for r in bound),optimizedMIRIsMachineStackProof=False))
# Complete concrete existing storage positions, including frozen rows, are exact
# 1096-byte enlargements. Derive directly from current accepted type declarations.
frame=(HERE/'overlay/src/experimental_swift_reactor/frame_operations.rs').read_text()
classes={}
for cls in ['PermanentPositions','ActivePositions','ImplementationPermanentPositions','ImplementationActivePositions']:
 a=frame.index('struct '+cls+' {');z=frame.index('\n}',a);body=frame[a:z]
 fields=[]
 for m in re.finditer(r'(?:#\[cfg\(test\)\]\s*)?([a-zA-Z0-9_]+): ([^\n]*FrameOperationStorage[^\n]*),',body):fields.append(dict(field=m.group(1),rustType=m.group(2),unitOnly='#[cfg(test)]' in m.group(0)))
 classes[cls]=fields
save('all-enlarged-containing-positions.json',classes)
# Build real sibling signatures, then prove original private kind/fields reject.
BUILD=Path('/tmp')/('mixer-control-privacy-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));vm=BUILD/'vm';BASE=b.files(ROOT/'vm')
for name in BASE:
 p=vm/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'vm'/name,p)
for p in (HERE/'overlay').rglob('*'):
 if p.is_file():q=vm/p.relative_to(HERE/'overlay');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR=str(BUILD/'target'));commands=[]
def run(name,args,expect):
 src=b.files(vm);start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(args,cwd=vm,env=env,capture_output=True,timeout=180)
 for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(p,stream))
 commands.append(dict(name=name,argv=args,cwd=str(vm),sourceTreeSHA256=digest(src),startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))))
 assert b.files(ROOT/'vm')==BASE;assert (p.returncode==0)==expect,(name,p.stderr.decode()[-3000:]);print(name,p.returncode,flush=True);return p.stderr.decode()
value=vm/'src/experimental_swift_reactor/value_operations.rs';original=value.read_text();witness='''
#[allow(dead_code)]
fn actual_sibling_control_signatures() {
    let _: fn(&mut super::frame_operations::FrameOperationPhase<'static>, Operation, Option<u32>) -> Result<bool, SwiftRunFailure> = super::frame_operations::FrameOperationPhase::control_operation;
    let _: fn(crate::experimental::cache::ControlKind, usize, usize, usize, bool) -> Control = Control::decoded;
    let _: fn(Control) -> bool = Control::result;
    let _: fn(Control) -> usize = Control::height;
    let _: fn(Control) -> usize = Control::start;
    let _: fn(Control) -> usize = Control::end;
    let _: fn(Control) -> bool = Control::is_loop;
    let _: fn(Control) -> bool = Control::is_function;
    let _: fn(Control) -> bool = Control::is_if;
    let _: fn(&mut Control) = Control::clear_result;
}
'''
try:
 value.write_text(original+witness);save('sibling-manifest.json',b.files(vm));(OUT/'sibling-witness.rs').write_text(witness)
 run('actual-sibling-signatures',['cargo','check','--lib','--all-features','--locked','--offline'],True)
 private='''
fn rejected_original_private_access(mut control: Control) {
    let _ = crate::experimental::execution::Kind::Function;
    let _ = control.kind;
    control.start = 0;
    control.end = 0;
    control.height = 0;
    control.result = false;
}
'''
 value.write_text(original+witness+private);(OUT/'private-rejection-witness.rs').write_text(private);save('private-rejection-manifest.json',b.files(vm))
 errors=run('original-private-kind-and-fields',['cargo','check','--lib','--all-features','--locked','--offline'],False)
 assert 'E0603' in errors and errors.count('E0616')>=5
 value.write_text(original)
 run('external-privacy-build',['cargo','build','--lib','--all-features','--locked','--offline'],True)
 external=BUILD/'external.rs';external.write_text('use mixer_vm::experimental::execution::{Control, Kind};\nuse mixer_vm::experimental::execution::borrowed::shared_control_methods;\nfn main(){}\n')
 rlib=next((BUILD/'target/debug/deps').glob('libmixer_vm.rlib'))
 errors=run('downstream-private-control-and-macros',['rustc','--edition=2021',str(external),'--extern','mixer_vm='+str(rlib),'-L','dependency='+str(BUILD/'target/debug/deps'),'-o',str(BUILD/'external')],False)
 assert 'E0603' in errors
 save('privacy-receipt.json',dict(status='passed-actual-sibling-callability-and-original-privacy',commands=commands,controlMethodsExecuted=False,liveVMUnchanged=b.files(ROOT/'vm')==BASE))
finally:
 shutil.rmtree(BUILD);save('privacy-cleanup.json',dict(removed=str(BUILD),buildRemoved=not BUILD.exists(),nativeInstancesStarted=False))
# Reviewable source patch applies with patch -p1 from vm.
parts=[]
for name in json.loads((HERE/'changed-files.json').read_text()):
 old=(ROOT/'vm'/name).read_text().splitlines(True) if (ROOT/'vm'/name).exists() else []
 new=(HERE/'overlay'/name).read_text().splitlines(True)
 parts+=difflib.unified_diff(old,new,fromfile='a/'+name,tofile='b/'+name)
(HERE/'source.patch').write_text(''.join(parts));print('audit complete',OUT,flush=True)
