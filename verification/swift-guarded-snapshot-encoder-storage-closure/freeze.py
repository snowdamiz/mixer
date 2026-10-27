"""Finalize read-only evidence and retire only known owned compiler outputs."""
from pathlib import Path
import json,re,hashlib,difflib,shutil
from probe import ROOT,INPUT,verify,sha

def artifact(p):
 b=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)}
if __name__=='__main__':
 custody=verify();vm=ROOT/'owned-work/layout-source/vm';old=INPUT/'source/vm';changed=[];delta=[]
 for p in sorted(vm.rglob('*')):
  if not p.is_file():continue
  relative=p.relative_to(vm);a=(old/relative).read_bytes();b=p.read_bytes()
  if a!=b:
   original=a.decode();measured=b.decode();restored=measured
   for seam in ['encoder-layout-seam.rs','loader-layout-seam.rs','initial-layout-seam.rs']:
    text=(ROOT/seam).read_text()
    if text in restored:restored=restored.replace(text,'',1)
   if relative.as_posix()=='src/lib.rs':restored=restored.removeprefix('#![feature(never_type)]\n')
   assert restored==original,relative
   changed.append({'path':relative.as_posix(),'frozen_sha256':sha(a),'measurement_sha256':sha(b),'behavior_preserved':True})
   delta.extend(difflib.unified_diff(original.splitlines(keepends=True),measured.splitlines(keepends=True),fromfile='frozen/'+relative.as_posix(),tofile='measurement/'+relative.as_posix()))
 assert len(changed)==4
 (ROOT/'measurement-source-delta.patch').write_text(''.join(delta))
 pre=json.loads((ROOT/'commands/actual-type-layouts-exact-private-contexts/source-preimage.json').read_text())
 (ROOT/'layout-source-custody.json').write_text(json.dumps({'schema':1,'source_binding':custody,'measurement_source_tree_sha256':pre['tree_sha256'],'measurement_source_members':144,'measurement_only_changed_members':changed,'source_restoration_equality':True,'LLVM_artifact':artifact(ROOT/'owned-work/type-layouts.ll'),'retained_exact_constant_fragments':['MIXER_ENCODER_STORAGE_ENCODER.llvm','MIXER_ENCODER_STORAGE_LOADER.llvm','MIXER_ENCODER_STORAGE_INITIAL.llvm'],'runtime_calls':0},indent=2)+'\n')
 (ROOT/'source-projection-custody.json').write_text(json.dumps({'schema':1,'source_binding':custody,'unoptimized_MIR_artifact':artifact(ROOT/'owned-work/source-slots.mir'),'retained_bounded_projection':artifact(ROOT/'function-bodies.mir'),'source_function_templates':64,'source_declared_parameter_and_local_slots':2658,'default_optimized_MIR_not_used':True,'runtime_calls':0},indent=2)+'\n')
 owned=ROOT/'owned-work';removed=[artifact(p) for p in sorted(owned.rglob('*')) if p.is_file()]
 shutil.rmtree(owned)
 retired=[]
 for name in ['selected-mir.txt','raw-source-occurrences.json']:
  p=ROOT/name
  if p.exists():retired.append(artifact(p));p.unlink()
 py=ROOT/'__pycache__'
 if py.exists():shutil.rmtree(py)
 commands=[]
 for p in sorted((ROOT/'commands').glob('*/receipt.json')):
  j=json.loads(p.read_text());assert j['child_reaped'] and not j['timed_out'];commands.append({'command':p.parent.name,'owned_process_group':j['owned_process_group'],'exit_code':j['exit_code'],'child_reaped':True,'timed_out':False})
 cleanup={'schema':1,'known_owned_compiler_commands':commands,'known_owned_compiler_children_reaped':True,'disposable_owned_work_removed':True,'removed_artifacts':removed,'superseded_derived_projection_artifacts_removed':retired,'process_inventory_performed':False,'native_or_capture_processes_started':False,'other_projects_processes_touched':False,'scope':'only lane-owned compiler output/source copy and Python cache removed; no process inventory or platform tools'}
 (ROOT/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
 checks=json.loads((ROOT/'checks.json').read_text());source_receipt=json.loads((INPUT/'receipt.json').read_text())
 receipt={'schema':1,'status':'complete bounded encoder-callee source-storage occurrence inventory; integration review pending','source_binding':custody,'frozen_input_source_revision':source_receipt['source_revision'],'checked_source_bytes':40531,'source_roles':2658,'function_templates':64,'compiler_type_identities':243,'actual_nameable_layout_instantiations':247,'closure_expressions':26,'entry_macro_occurrences':8,'host_checks_passed':checks['passed'],'product_source_omissions':[],'physical_stack_or_RSS_claim':False,'operational_floor_or_grant_selected':False,'genuine_writer_executions':0,'encoder_or_VM_runtime_executions':0,'native_device_simulator_emulator_UI_capture_process_inventory_executions':0,'canonical_or_git_mutations':False,'GA_gates_verified':0,'bounded_metadata_compiler':'rustc1.99.0 (b940084d7 2026-09-28), aarch64-apple-darwin, production debug, original feature set','retained_probe_failures':['default optimized MIR folds source copies; unoptimized projection selected','initial exact-type seam placement failed private-module visibility','second seam placement failed nested initial-profile visibility'],'dependencies':'standard-library private frames/ABI/unwind/backend spills and immutable static pointees explicitly outside source-storage model; no missing bounded product role/type','cleanup':{'known_owned_compiler_children_reaped':True,'owned_work_removed':True,'process_inventory_performed':False}}
 (ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 members=[artifact(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='seal.json'];seal={'schema':1,'members':members,'member_count':len(members),'total_bytes':sum(m['bytes'] for m in members),'scope':receipt['status']}
 (ROOT/'seal.json').write_text(json.dumps(seal,indent=2)+'\n');print(json.dumps({'seal_sha256':sha((ROOT/'seal.json').read_bytes()),'member_count':len(members),'total_bytes':seal['total_bytes'],'source_bytes':40531,'source_roles':2658}))
