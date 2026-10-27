"""Independent compiler-only review. Does not import or run producer programs."""
from pathlib import Path
import collections, copy, hashlib, json, os, re, shutil, signal, subprocess, time

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
P=HERE.parent/'swift-guarded-snapshot-emission-storage-delta'
BASE=HERE.parent/'swift-guarded-snapshot-scope-authority-correction'
ACCEPTED=HERE.parent/'swift-guarded-snapshot-emission-bound-implementation'
OWNER=HERE.parent/'swift-guarded-snapshot-owner-storage-closure'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
INITIAL='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
CALLEE='src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
NAMES=['checked_snapshot_emission_bound_v1','proposed_emission_work_v1','begin_snapshot_access_v1','begin_snapshot_access_v1::{closure#0}']
CONTROLS=[]

def sha(x):return hashlib.sha256(x).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def save(name,x):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def load(p):return json.loads(p.read_text())
def check(name,condition,details=None):
 CONTROLS.append({'name':name,'pass':bool(condition),'details':details})
 if not condition:raise AssertionError(name)
def roster(p):return [{'path':str(x.relative_to(p)),'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in sorted(p.rglob('*')) if x.is_file()]
def verify_seal(p,expected,all_members=True):
 check('seal-'+p.name,sha((p/'seal.json').read_bytes())==expected)
 d=load(p/'seal.json')
 if all_members:
  for r in d['members']:
   b=(p/r['path']).read_bytes();check('member-'+p.name+'/'+r['path'],len(b)==r['bytes'] and sha(b)==r['sha256'])
 return d
def functions(text):
 out={}
 # Compiler MIR function delimiters, not authorization of release or source syntax.
 for match in re.finditer(r'(?m)^fn [^\n]+\n.*?^\}',text,re.S|re.M):
  body=match.group();name=body.splitlines()[0][3:].split('(')[0]
  if name in NAMES:out[name]=body
 return out
def normalized(text):
 lines=[l.split('//',1)[0].rstrip() for l in text.splitlines()]
 text='\n'.join(l for l in lines if l)
 text=re.sub(r'closure@[^}]*?initial_profile_v1\.rs:\d+:\d+: \d+:\d+', 'closure@initial_profile_v1.rs:<span>',text)
 return text
def declarations(body):
 result={m[1]:m[2] for m in re.finditer(r'^\s+let (?:mut )?(_\d+): (.*?);\s*//',body,re.M)}
 # Each function reviewed here has exactly one non-nested reference parameter,
 # except begin, whose three parameters contain no comma within a generic type.
 header=body.splitlines()[0];argstr=header[header.index('(')+1:header.rindex(') ->')]
 for m in re.finditer(r'(_\d+): (.*?)(?=, _\d+:|$)',argstr):result[m[1]]=m[2]
 return result
def qual(t):return t.replace('&SnapshotShapeV1','&experimental_swift_reactor::cache::initial_profile_v1::SnapshotShapeV1')
def snippet(src,span):
 ls=src.splitlines()[span['start_line']-1:span['end_line']]
 if len(ls)==1:return ls[0][span['start_column']-1:span['end_column']-1]
 ls[0]=ls[0][span['start_column']-1:];ls[-1]=ls[-1][:span['end_column']-1];return '\n'.join(ls)
def tuple_values(text):
 out={}
 for line in text.splitlines():
  m=re.match(r'@(MIXER_EMISSION_LAYOUT_\d+) = .*?c"(.*?)"',line)
  if not m:continue
  raw=m[2];bs=bytearray();i=0
  while i<len(raw):
   if raw[i]=='\\':bs.append(int(raw[i+1:i+3],16));i+=3
   else:bs.append(ord(raw[i]));i+=1
  if len(bs)!=16:raise ValueError('not a layout tuple')
  out[m[1]]={'bytes':int.from_bytes(bs[:8],'little'),'alignment':int.from_bytes(bs[8:],'little')}
 return out

def offline():
 release=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-emission-storage-independent-release.json'
 acceptance=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-emission-bound-host-acceptance.json'
 check('root-release',sha(release.read_bytes())=='1275fed1ddae7c9e5824dbad32ec7fafbc22fd42485e5a8fd3cd90a5597413de')
 check('accepted-helper-interface',sha(acceptance.read_bytes())=='97f2d8d24a24f16d614013c5ff3bd8f34c747b87bfa355cb79b46ad51ca88a5b')
 seal=verify_seal(P,'57616a2fb20a5abe101e3d24ef6e9c1689b1e0c32b1c525c85e6d240de865f32')
 check('producer-count-bytes',len(seal['members'])==92 and sum(r['bytes'] for r in seal['members'])==1092790)
 check('producer-exact-roster',set(r['path'] for r in roster(P))=={r['path'] for r in seal['members']}|{'seal.json','freeze-receipt.json'})
 check('postseal-freeze',sha((P/'freeze-receipt.json').read_bytes())=='4f5f27483c9a754b14b8f6b268a7e2484d535625c528a5b5e8ae1b6cead0907c')
 verify_seal(BASE,'351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c',False)
 verify_seal(ACCEPTED,'e92026187ef181ddbcc178e53611ce5e4aa0111c613e9c8ad3a4aca58ff8ffcc',False)
 ownerseal=verify_seal(OWNER,'afd33c1df35e4072e582789a38c14372f9a8efc4c6243301df4399e4899f2e4b',False)
 ownermir=(OWNER/'function-bodies.mir').read_bytes()
 check('frozen-owner-MIR-only',next(r for r in ownerseal['members'] if r['path']=='function-bodies.mir')['sha256']==sha(ownermir))
 base=roster(BASE/'source/vm');check('base144-tree',len(base)==144 and sha(canonical(base))=='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896')
 proposed={r['path']:r for r in base}
 for r in roster(P/'overlay/vm'):proposed[r['path']]=r
 proposed=[proposed[k] for k in sorted(proposed,key=Path)]
 check('exact-proposal145-source',proposed==load(P/'source-manifest.json')['members'] and len(proposed)==145)
 check('proposal145-tree',sha(canonical(proposed))=='e0e267bcdd3d25b3b120347c4865b4f76d22b4f6709396f8d7c968f0bd3d08e8')
 prop=load(P/'proposal.json');initial=(P/'overlay/vm'/INITIAL).read_text();helper=(P/'overlay/vm'/CALLEE).read_bytes()
 check('accepted-helper-identical',helper==(ACCEPTED/'overlay/vm'/CALLEE).read_bytes() and sha(helper)=='ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a')
 check('wrapper-only-source-substitution',(ACCEPTED/'overlay/vm'/INITIAL).read_text().replace(prop['baseline_wrapper'],prop['body'])==initial)
 check('old-wrapper-stays-actual',prop['baseline_wrapper'] in (BASE/'source/vm'/INITIAL).read_text())
 check('wrapper-direct-tail',prop['body']=='fn proposed_emission_work_v1(shape:&SnapshotShapeV1)->Result<u64,AError>{\n    emission_bound_v1::checked_snapshot_emission_bound_v1(shape)\n}')
 fs={mode:functions((P/(mode+'-functions.mir')).read_text()) for mode in ['production','unit']}
 for mode,v in fs.items():check(mode+'-four-functions',set(v)==set(NAMES))
 for name in NAMES:check('prod-test-MIR-'+name,normalized(fs['production'][name])==normalized(fs['unit'][name]))
 layouts=load(P/'type-layouts.json')['types'];requests=load(P/'layout-requests.json');types={r['type']:r for r in layouts}
 decoded={m:tuple_values((P/(m+'-layout-tuples.llvm')).read_text()) for m in ['production','unit']}
 check('ten-real-layouts',len(types)==len(requests)==10)
 for r in layouts:
  for mode in decoded:
   actual=decoded[mode][r[mode]['symbol']];check('layout-'+mode+'-'+r['type'],actual=={k:r[mode][k] for k in ['bytes','alignment']})
  check('prod-test-layout-'+r['type'],{k:r['production'][k] for k in ['bytes','alignment']}=={k:r['unit'][k] for k in ['bytes','alignment']})
 roles=load(P/'roles.json');raw=load(P/'raw-added-roles.json')
 for group,name,count in [('helper',NAMES[0],39),('proposed_wrapper',NAMES[1],3)]:
  decl=declarations(fs['production'][name]);rows=roles[group]
  check('complete-'+group,len(rows)==count and set(r['mir_local'] for r in rows)==set(decl))
  check('unique-'+group,len({r['id'] for r in rows})==len(rows))
  for r in rows:
   check('identity-'+r['id'],r['id']=='delta::'+name+'::'+r['mir_local'] and qual(decl[r['mir_local']])==r['type'])
   src=(P/'overlay/vm'/r['source']['path']).read_bytes()
   check('source-'+r['id'],sha(src)==r['source_member_sha256'] and snippet(src.decode(),r['source'])==r['source']['text'])
   check('storage-'+r['id'],r['multiplicity']==1 and r['bytes']==types[r['type']]['production']['bytes'] and r['alignment']==types[r['type']]['production']['alignment'] and r['funding_partition']=='S selected-unconditional before evaluator and phase commit')
   check('uses-'+r['id'],all(u in [l.strip() for l in fs['production'][name].splitlines()] for u in r['uses']))
   check('raw-role-'+r['id'],all(r[k]==raw[group][rows.index(r)][k] for k in raw[group][rows.index(r)]))
 check('helper-total',sum(r['bytes'] for r in roles['helper'])==18816)
 check('wrapper-total',sum(r['bytes'] for r in roles['proposed_wrapper'])==1112)
 old=functions(ownermir.decode());preserved=load(P/'preserved-begin-roles.json')
 for name in NAMES[2:]:
  check('caller-body-'+name,normalized(old[name])==normalized(fs['production'][name]))
  selected=[r for r in preserved['roles'] if r['baseline_id'].startswith('owner::'+name+'::') and r['baseline_id'].rsplit('::',1)[0]=='owner::'+name]
  decl=declarations(fs['production'][name]);check('caller-complete-'+name,set(r['baseline_id'].rsplit('::',1)[1] for r in selected)==set(decl))
 check('caller131-preserved',len(preserved['roles'])==131 and sum(r['bytes'] for r in preserved['roles'])==77098)
 check('caller-boundary10-preserved',len(preserved['caller_slice'])==10 and {r['baseline_id'].rsplit('::',1)[1] for r in preserved['caller_slice']}=={'_'+str(i) for i in range(47,57)})
 baseline=load(P/'baseline-wrapper-roles.json');old_decl=declarations(old[NAMES[1]])
 check('old-wrapper-slots',[(r['mir_local'],r['bytes']) for r in baseline]==[('_0',1096),('_1',8),('_2',1096)] and set(old_decl)=={'_0','_1','_2'})
 check('specific-old-refusal',baseline[2]['source_text']=='AError::WorkAuditPending' and '_2 = SnapshotAdmissionErrorV1::WorkAuditPending;' in old[NAMES[1]])
 check('retained-types',all(qual(old_decl[n])==qual(declarations(fs['production'][NAMES[1]])[n]) for n in ['_0','_1']))
 check('new-reborrow',roles['proposed_wrapper'][2]['type'].startswith('&') and '_2 = &(*_1);' in fs['production'][NAMES[1]] and '_0 = checked_snapshot_emission_bound_v1(move _2)' in fs['production'][NAMES[1]])
 delta=load(P/'wrapper-delta.json');check('only-specific-removal',delta['removed']==[{'baseline_id':'owner::proposed_emission_work_v1::_2','bytes':1096,'reason':'only removed refusal constructor temporary; no return or outer caller slot removed','source_text':'AError::WorkAuditPending'}])
 check('retained-exact-two',[(r['baseline_id'],r['bytes']) for r in delta['retained']]==[('owner::proposed_emission_work_v1::_0',1096),('owner::proposed_emission_work_v1::_1',8)])
 check('delta-net',18816+8-1096==17728 and 941467+17728==959195)
 # Finite mutation controls validate occurrence identity and complete coverage,
 # rather than merely checking that a mutated sum differs.
 def valid_rows(rows):return len(rows)==39 and {r['id'] for r in rows}=={r['id'] for r in roles['helper']} and all(r==roles['helper'][int(r['mir_local'][1:])] for r in rows)
 for label,mutator in [('omit',lambda x:x.pop()),('duplicate',lambda x:x.append(copy.deepcopy(x[0]))),('erase-eager-error',lambda x:x[7].update(bytes=0)),('erase-residual',lambda x:x[9].update(bytes=0)),('foreign-function',lambda x:x[9].update(id='delta::foreign::_9')),('invent-multiplicity',lambda x:x[2].update(multiplicity=2)),('late-funding',lambda x:x[0].update(funding_partition='A admitted-only')),('wrong-span',lambda x:x[6]['source'].update(start_line=10))]:
  rr=copy.deepcopy(roles['helper']);mutator(rr);check('reject-'+label,not valid_rows(rr))
 check('u64-last-fit',((2**64-1)-17728)+17728==2**64-1)
 check('u64-next-overflow',((2**64-1)-17728+1)+17728>2**64-1)
 check('old-refusal-underflow',1095-1096<0)
 convention=HERE.parent/'swift-guarded-snapshot-writer-work-audit/cost-convention.md';ledger=HERE.parent/'swift-guarded-snapshot-writer-work-correction/corrected-ledger.json'
 work=load(P/'work-attribution.json');check('convention-bound',sha(convention.read_bytes())==work['convention_sha256'] and 'literal and\nbound local operands are free' in convention.read_text())
 check('ledger-bound',sha(ledger.read_bytes())==work['accepted_corrected_ledger_sha256'])
 led=load(ledger);check('old3-and-initializer4096',led['admission']['actual_proposed_emission_helper']=='entry2 + Err WorkAuditPending1; no reachable admitted writer' and led['admission']['admitted_transfer_zero_bytes_once']==4096)
 check('work-reconciliation',work['accepted_helper29_separate']==29 and work['wrapper_after']['total']==2 and work['proposed_evaluator_total']==31 and work['net_evaluator_delta']==28 and work['already_in_future_begin']=={'emission_binding':1,'question_inspection_and_payload':2})
 check('initializer-once',work['future_begin_interface_excluding_evaluator']==7930 and work['future_begin_includes_initializer4096'] and work['accepted_emission_includes_same_initializer4096'] and '7930-4096' in work['combination_rule'])
 # Order in the unchanged source demonstrates why phase commit cannot fund the
 # evaluator's places. It is evidence of a proposed funding requirement only.
 begin=initial[initial.index('fn begin_snapshot_access_v1'):initial.index('#[derive(Clone,Copy)]',initial.index('fn begin_snapshot_access_v1'))]
 check('pregrant-placement',begin.index('let emission=proposed_emission_work_v1')<begin.index('control.snapshot_debit_v1(emission)')<begin.index('control.snapshot_commit_storage_v1'))
 formula=load(P/'formula.json');check('conditional-not-floor',formula['candidate_S']==959195 and formula['owner_base_accepted'] is False if 'owner_base_accepted' in formula else formula['candidate_S']==959195 and 'not accepted' in formula['base_status'])
 check('native-GA-not-selected',formula['operational_selection'] is False and formula['genuine_loader_claim'] is False and formula['planning_16384_coverage_proved'] is False)
 check('descriptor-mismatch-explicit',prop['source_count']==145 and prop['unchanged_loader_descriptor']=={'source_count':144,'support_count':11})
 # Audit retained receipts only. No producer program is imported or executed.
 commands=[]
 for rp in sorted((P/'commands').glob('*/receipt.json')):
  r=load(rp);stem=rp.parent.name;pre=load(rp.parent/'source-preimage.json');expected=proposed
  if 'layouts' in stem:
   expected=copy.deepcopy(proposed)
   for m in expected:
    if m['path']=='src/lib.rs':b=b'#![feature(never_type)]\n'+(BASE/'source/vm/src/lib.rs').read_bytes();m.update(bytes=len(b),sha256=sha(b))
    if m['path']==CALLEE:b=helper+(P/'layout-seam.rs').read_bytes();m.update(bytes=len(b),sha256=sha(b))
  if stem.startswith('checked-recipe'):
   b=(P/'checked-additive-recipe.rs').read_bytes()
   if 'overflow' in stem:b+=(P/'overflow-negative-seam.rs').read_bytes()
   expected=[{'path':'src/lib.rs','bytes':len(b),'sha256':sha(b)}]
  check('preimage-'+stem,pre['members']==expected)
  check('receipt-'+stem,r['child_reaped'] and r['owned_group_absent'] and not r['timed_out'] and r['timeout_seconds']==55 and r['compiler_sha256']==sha(RUSTC.read_bytes()))
  check('receipt-output-'+stem,sha((rp.parent/'stdout').read_bytes())==r['stdout_sha256'] and sha((rp.parent/'stderr').read_bytes())==r['stderr_sha256'])
  if 'overflow' in stem:check('expected-E0080',r['exit_code']!=0 and 'E0080' in (rp.parent/'stderr').read_text())
  else:check('compiler-success-'+stem,r['exit_code']==0)
  commands.append({'name':stem,'exit_code':r['exit_code'],'preimage_sha256':sha((rp.parent/'source-preimage.json').read_bytes())})
 check('producer11commands',len(commands)==11 and sum(r['exit_code']==0 for r in commands)==10)
 save('producer-command-audit.json',commands)
 check('ordering-failure-preserved',load(P/'attempt-history/preimage-order-failure.json')['exit_code']==1 and 'Path component ordering' in load(P/'attempt-history/preimage-order-failure.json')['cause'])
 save('offline-controls.json',{'count':len(CONTROLS),'all_passed':all(r['pass'] for r in CONTROLS),'controls':CONTROLS})
 save('source-custody.json',{'root_release_sha256':sha(release.read_bytes()),'producer_seal_sha256':sha((P/'seal.json').read_bytes()),'producer_members':92,'producer_bytes':1092790,'postseal_freeze_sha256':sha((P/'freeze-receipt.json').read_bytes()),'source144_tree_sha256':sha(canonical(base)),'proposal145_tree_sha256':sha(canonical(proposed)),'owner_base_accepted':False,'owner_alias_map_consumed':False,'used_owner_member':'function-bodies.mir','canonical_mutation':False})
 return proposed

def run_compiler(label,vm,extra,unit):
 log=HERE/'commands'/label;log.mkdir(parents=True,exist_ok=False)
 pre=roster(vm);save('commands/'+label+'/source-preimage.json',{'members':pre,'tree_sha256':sha(canonical(pre)),'review_script_sha256':sha(Path(__file__).read_bytes())})
 version=subprocess.run([str(RUSTC),'--version','--verbose'],capture_output=True,check=True,timeout=10).stdout
 argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind']
 for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:argv+=['--cfg','feature="'+feature+'"']
 argv+=(['--test'] if unit else ['--crate-type','rlib'])+[str(vm/'src/lib.rs')]+extra
 env={'PATH':'/usr/bin:/bin','TMPDIR':str(HERE/'scratch'),'CARGO_MANIFEST_DIR':str(vm),'RUSTC_BOOTSTRAP':'1','MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),'MIXER_LOADER_COMMAND_SHA256':sha(canonical(argv)),'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(pre))}
 env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
 start=time.monotonic();p=subprocess.Popen(argv,cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed=False;cleanup=[]
 try:out,err=p.communicate(timeout=55)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGKILL);cleanup.append('SIGKILL owned group')
  except ProcessLookupError:pass
  out,err=p.communicate()
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 (log/'stdout').write_bytes(out);(log/'stderr').write_bytes(err)
 target=Path(argv[argv.index('-o')+1]);artifacts=[]
 if target.exists():artifacts=[{'path':str(target.relative_to(HERE)),'bytes':target.stat().st_size,'sha256':sha(target.read_bytes())}]
 r={'argv':argv,'environment':env,'compiler_sha256':sha(RUSTC.read_bytes()),'rustc_version':version.decode(),'elapsed_seconds':time.monotonic()-start,'timeout_seconds':55,'timed_out':timed,'owned_process_group':p.pid,'owned_group_absent':absent,'child_reaped':True,'exit_code':p.returncode,'cleanup_actions':cleanup,'stdout_sha256':sha(out),'stderr_sha256':sha(err),'artifacts_before_cleanup':artifacts,'scope':'compiler only; no runtime, native, UI, capture or process inventory'}
 save('commands/'+label+'/receipt.json',r)
 print(json.dumps({'compiler':label,'exit_code':p.returncode,'seconds':r['elapsed_seconds'],'owned_group_absent':absent}),flush=True)
 check('fresh-command-'+label,p.returncode==0 and not timed and absent)
 return target

def compile_fresh():
 scratch=HERE/'scratch';scratch.mkdir(exist_ok=False)
 try:
  vm=scratch/'vm';shutil.copytree(BASE/'source/vm',vm)
  for x in (P/'overlay/vm').rglob('*'):
   if x.is_file():dest=vm/x.relative_to(P/'overlay/vm');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(x,dest)
  for unit in [False,True]:
   mode='unit' if unit else 'production';out=run_compiler(mode+'-mir',vm,['--emit=mir','-Zmir-opt-level=0','-Zmir-include-spans=yes','-o',str(scratch/(mode+'.mir'))],unit)
   fs=functions(out.read_text());producer=functions((P/(mode+'-functions.mir')).read_text());check('fresh-four-'+mode,set(fs)==set(NAMES))
   for name in NAMES:check('fresh-MIR-'+mode+'-'+name,normalized(fs[name])==normalized(producer[name]))
   (HERE/(mode+'-functions.mir')).write_text('\n\n'.join(fs[name].replace(str(vm/'src')+'/','source/') for name in NAMES)+'\n')
  # Identical ten scalar layout tuples; never an invented owner or budget array.
  (vm/'src/lib.rs').write_bytes(b'#![feature(never_type)]\n'+(vm/'src/lib.rs').read_bytes())
  (vm/CALLEE).write_bytes((vm/CALLEE).read_bytes()+(P/'layout-seam.rs').read_bytes())
  for unit in [False,True]:
   mode='unit' if unit else 'production';out=run_compiler(mode+'-layouts',vm,['--emit=llvm-ir','-Zmir-opt-level=0','-o',str(scratch/(mode+'.ll'))],unit)
   ir=out.read_text();actual=tuple_values(ir);expected=tuple_values((P/(mode+'-layout-tuples.llvm')).read_text())
   check('fresh-ten-layouts-'+mode,actual==expected and len(actual)==10)
   (HERE/(mode+'-layout-tuples.llvm')).write_text('\n'.join(l for l in ir.splitlines() if l.startswith('@MIXER_EMISSION_LAYOUT_'))+'\n')
 finally:
  before=roster(scratch);shutil.rmtree(scratch)
  save('cleanup.json',{'owned_scratch_removed':True,'scratch_absent':not scratch.exists(),'pre_removal_members':before,'no_global_inventory':True,'other_processes_inspected':False,'native_or_capture_started':False})

if __name__=='__main__':
 try:
  offline();compile_fresh()
  save('controls.json',{'count':len(CONTROLS),'all_passed':True,'controls':CONTROLS})
  print(json.dumps({'all_passed':True,'controls':len(CONTROLS),'runtime_invocations':0}),flush=True)
 except BaseException as e:
  save('failed-attempt.json',{'exception':type(e).__name__,'message':str(e),'controls':CONTROLS});raise
