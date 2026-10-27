"""Independent frozen-source, focused MIR and actual private-control review.

Writes only this packet and its bounded disposable scratch. Never imports a
producer driver, runs admission/writer/VM tests, or examines global processes.
Run a label in a new unsealed packet only; seal.json makes this read-only.
"""
from pathlib import Path
import datetime,difflib,hashlib,json,os,re,shutil,signal,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
PRODUCER=HERE.parent/'swift-guarded-snapshot-phase-retention'
BASE=HERE.parent/'swift-guarded-snapshot-funding-implementation'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SOURCE='9c654ec4967f184bcc262c36ac4d65067a3f9d48107f7f9e72789f4cd88960fd'
BASE_SOURCE='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
CONTROL='src/experimental_swift_reactor/control.rs'
PROFILE='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
OVERLAYS=[(CONTROL,'control-overlay.rs'),(PROFILE,'profile-overlay.rs'),('src/experimental_swift_reactor/cache.rs','cache-overlay.rs')]
def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def write(name,data):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def manifest(root):
 return [dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=digest(p.read_bytes())) for p in sorted(root.rglob('*')) if p.is_file()]
def check_seal(root,expected):
 raw=(root/'seal.json').read_bytes();assert digest(raw)==expected,str(root)
 s=json.loads(raw);rows=s['members'];assert len(rows)==s['member_count']
 assert len({x['path'] for x in rows})==len(rows)
 for row in rows:
  p=root/row['path'];assert p.resolve().is_relative_to(root.resolve()) and not p.is_symlink()
  assert p.stat().st_size==row['bytes'] and digest(p.read_bytes())==row['sha256'],str(p)
 assert sum(x['bytes'] for x in rows)==s['member_bytes']
 assert digest(canonical(rows))==s['tree_sha256']
 return dict(path=str(root/'seal.json'),sha256=expected,members=len(rows),member_bytes=s['member_bytes'],tree_sha256=s['tree_sha256'])
def source_binding():
 rows=manifest(PRODUCER/'source/vm');old=manifest(BASE/'source/vm')
 assert len(rows)==len(old)==144 and digest(canonical(rows))==SOURCE and digest(canonical(old))==BASE_SOURCE
 assert rows==json.loads((PRODUCER/'source-manifest.json').read_text())['members']
 return dict(source_members=144,source_tree_sha256=SOURCE,baseline_source_tree_sha256=BASE_SOURCE,selected_ingress_or_writer_executed=False)
def bounded(argv,env,cwd,timeout):
 start=time.monotonic();p=subprocess.Popen(list(map(str,argv)),env=env,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed=False;actions=[]
 try:out,err=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  timed=True
  for sig,wait in [(signal.SIGTERM,2),(signal.SIGKILL,2)]:
   try:os.killpg(p.pid,sig);actions.append('sent '+sig.name+' only to owned group')
   except ProcessLookupError:pass
   try:out,err=p.communicate(timeout=wait);break
   except subprocess.TimeoutExpired:continue
  else:raise RuntimeError('owned process failed to reap')
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 return out,err,dict(argv=list(map(str,argv)),cwd=str(cwd),elapsed_seconds=time.monotonic()-start,timeout_seconds=timeout,timed_out=timed,exit_code=p.returncode,owned_process_group=p.pid,new_session=True,child_reaped=True,owned_group_absent=absent,cleanup_actions=actions)
def command(label,argv,env,cwd,timeout,expected=0):
 out,err,r=bounded(argv,env,cwd,timeout);d=HERE/'commands'/label;d.mkdir(parents=True,exist_ok=False)
 (d/'stdout').write_bytes(out);(d/'stderr').write_bytes(err)
 r.update(schema=1,environment=env,driver_sha256=digest(Path(__file__).read_bytes()),source_binding=source_binding(),stdout_sha256=digest(out),stderr_sha256=digest(err),expected_exit_code=expected)
 r['expectation_met']=r['exit_code']==expected and not r['timed_out'] and r['owned_group_absent']
 write('commands/'+label+'/receipt.json',r)
 assert r['expectation_met'],label+'\n'+err.decode(errors='replace')[-4000:]
 return out,err,r
def audit():
 checks=[]
 def check(name,value):assert value,name;checks.append(dict(name=name,passed=True))
 root=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-phase-retention-independent-release.json'
 check('root release hash',digest(root.read_bytes())=='12627178051e0747ce835af0f22f44eab5d69e563f86dcf0a210b1cdf9f11f23')
 seals=[check_seal(PRODUCER,'623b5ec0b8ef7c2f68b344c191f9a6d2f5fd93b3085c7f0b4ae02c960c895001'),check_seal(BASE,'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7')]
 check('producer member/byte count',seals[0]['members']==254 and seals[0]['member_bytes']==21540355)
 binding=source_binding();check('exact 144 candidate and baseline source manifests',True)
 acceptance=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-funding-host-acceptance.json'
 check('bounded base funding acceptance hash',digest(acceptance.read_bytes())=='17789ef30bb818f91a928941162029a12c75ca7dddd33e8cfc073ec4950a615f')
 changed=[r['path'] for r in manifest(PRODUCER/'source/vm') if (PRODUCER/'source/vm'/r['path']).read_bytes()!=(BASE/'source/vm'/r['path']).read_bytes()]
 check('only exact two source members changed',changed==[PROFILE,CONTROL])
 replacements=[(CONTROL,'        Ok(previous)\n    }\n}\n\n// Conservative candidate source roles.','        Ok(construction)\n    }\n}\n\n// Conservative candidate source roles.')]
 for a,b in [
  ("Admitted {control:&'c mut RuntimeControl,previous:usize,wasi:","Admitted {control:&'c mut RuntimeControl,retained:usize,wasi:"),
  ('Self::Admitted{control,previous,wasi}=>control.end_construction_phase_with_wasi(storage,previous,wasi),','Self::Admitted{control,retained,wasi}=>control.end_construction_phase_with_wasi(storage,retained,wasi),'),
  ('let previous=control.snapshot_commit_storage_v1(additional)?;','let retained=control.snapshot_commit_storage_v1(additional)?;'),
  ('Ok::<_,AError>((previous,shape,planning,emission))','Ok::<_,AError>((retained,shape,planning,emission))'),
  ('Ok((previous,shape,planning,emission))=>{','Ok((retained,shape,planning,emission))=>{'),
  ('(SnapshotAccessV1::Admitted{control,previous,wasi},storage)','(SnapshotAccessV1::Admitted{control,retained,wasi},storage)')]:replacements.append((PROFILE,a,b))
 text={n:(BASE/'source/vm'/n).read_text() for n in changed}
 for n,a,b in replacements:
  check('unique replacement '+str(len(checks)),text[n].count(a)==1);text[n]=text[n].replace(a,b)
 for n in changed:check('full independent exact reconstruction '+n,text[n]==(PRODUCER/'source/vm'/n).read_text())
 patch=''.join(''.join(difflib.unified_diff((BASE/'source/vm'/n).read_text().splitlines(True),(PRODUCER/'source/vm'/n).read_text().splitlines(True),fromfile='funding144/'+n,tofile='retention144/'+n)) for n in changed)
 (HERE/'exact-source-delta.patch').write_text(patch)
 check('producer patch exact match',patch==(PRODUCER/'source-delta.patch').read_text())
 sites=[]
 for row in manifest(PRODUCER/'source/vm'):
  if not row['path'].endswith('.rs'):continue
  for line_no,line in enumerate((PRODUCER/'source/vm'/row['path']).read_text().splitlines(),1):
   if 'snapshot_commit_storage_v1' in line:sites.append(dict(path=row['path'],line=line_no,text=line))
 check('all 144 source members have exactly definition and sole direct caller',len(sites)==2 and sum('fn snapshot_commit_storage_v1' in r['text'] for r in sites)==1)
 cp=(PRODUCER/'source/vm'/PROFILE).read_text();cc=(PRODUCER/'source/vm'/CONTROL).read_text()
 check('WorkAuditPending precedes commit',cp.index('let emission=proposed_emission_work_v1(&shape)?;')<cp.index('let retained=control.snapshot_commit_storage_v1(additional)?;') and 'Err(AError::WorkAuditPending)' in cp)
 check('same-length retained binding',len('retained')==len('previous'))
 check('same existing export survives completion by source order','let phase_completion=access.complete(storage);\n        SnapshotOuterV1 {primary,export,phase_completion}' in cp)
 check('conservative final ConstructionBound marker remains','Some(ticket.bytes) != foundation_construction_bytes()' in cc)
 check('unchanged fixed policies','combined_bytes: 256 * MIB,' in cc and 'execution_work: 1_000_000_000,' in cc)
 check('funding constants identical',(PRODUCER/'funding-constants.inc.rs').read_bytes()==(BASE/'funding-constants.inc.rs').read_bytes())
 summaries=[]
 for name in ['baseline-production','baseline-unit','candidate-production','candidate-unit','control-tests','scalar-production','scalar-unit','scalar-overflow','scalar-overflow-negative','source-ordering-accounting-controls','source-ordering-accounting-controls-attempt-1']:
  r=json.loads((PRODUCER/'commands'/name/'receipt.json').read_text());summaries.append(dict(label=name,exit_code=r['exit_code'],timed_out=r['timed_out'],child_reaped=r['child_reaped'],owned_group_absent=r['owned_group_absent']))
  check('preserved producer command process custody '+name,r['child_reaped'] and r['owned_group_absent'] and not r['timed_out'])
 check('producer original failed assertion retained',next(x for x in summaries if x['label'].endswith('attempt-1'))['exit_code']==1)
 write('audit.json',dict(schema=1,source_binding=binding,seals=seals,root_release_sha256=digest(root.read_bytes()),funding_acceptance_sha256=digest(acceptance.read_bytes()),checks=checks,checks_passed=len(checks),exact_replacements=7,call_sites=sites,producer_command_observations=summaries,scope='Immutable input and exact source differential review; no release authority'))
 out,err,r=command('repository-revision',['/usr/bin/git','rev-parse','HEAD'],{'PATH':'/usr/bin:/bin'},REPO,10)
 write('environment.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),python_version=sys.version,python_executable=sys.executable,repository_revision=out.decode().strip(),source_binding=binding))
 print(json.dumps(dict(audit_checks=len(checks),source_tree=SOURCE)))
def focused(text):
 found={};block=[]
 for line in text.splitlines(True):
  if line.startswith('fn '):block=[line]
  elif block:
   block.append(line)
   if line=='}\n':
    b=''.join(block);h=block[0];key=None
    if 'snapshot_commit_storage_v1(' in h:key='commit'
    elif 'end_construction_phase_with_wasi' in h:key='normalizer'
    elif 'begin_snapshot_access_v1' in h:key='begin-closure' if '{closure#0}' in h else 'begin'
    elif 'complete(' in h and 'SnapshotAccessV1' in h:key='complete'
    elif 'foundation_construction_bytes(' in h:key='common-floor'
    elif 'snapshot_scope_candidate_foundation_v1(' in h:key='selected-floor'
    if key:assert key not in found;found[key]=b
    block=[]
 assert set(found)=={'commit','normalizer','begin','begin-closure','complete','common-floor','selected-floor'},list(found)
 return found
def normalized(b):
 return '\n'.join(x.split('//',1)[0].rstrip() for x in b.splitlines()).replace('retained','previous')
def compile_run(label):
 assert label in ['baseline-production','baseline-unit','candidate-production','candidate-unit','candidate-controls','baseline-negative-controls']
 source_binding();test=label.endswith('controls');baseline=label.startswith('baseline-')
 scratch=HERE/'owned-scratch';assert not scratch.exists();scratch.mkdir()
 try:
  vm=scratch/'vm';shutil.copytree((BASE if baseline else PRODUCER)/'source/vm',vm)
  pre=dict(schema=1,source_binding=source_binding(),exact_copied_members=manifest(vm),compiler_sha256=digest(RUSTC.read_bytes()),driver_sha256=digest(Path(__file__).read_bytes()),overlays=[])
  if test:
   for target,fragment in OVERLAYS:
    raw=(HERE/fragment).read_bytes()
    if baseline and target==PROFILE:raw=raw.replace(b'control,retained:target,wasi',b'control,previous:target,wasi')
    p=vm/target;p.write_bytes(p.read_bytes()+b'\n'+raw)
    pre['overlays'].append(dict(target=target,fragment=fragment,bytes=len(raw),sha256=digest(raw),baseline_field_spelling_only=baseline and target==PROFILE))
   pre['instrumented_members']=manifest(vm)
  env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'RUSTC_BOOTSTRAP':'1','CARGO_MANIFEST_DIR':str(vm)}
  if not (HERE/'commands/compiler-version').exists():
   out,err,r=command('compiler-version',[RUSTC,'--version','--verbose'],env,HERE,10)
  artifact=scratch/('controls' if test else 'candidate.rmeta');mir=scratch/'candidate.mir'
  argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0','-Zmir-include-spans=yes']
  for feature in FEATURES:argv+=['--cfg','feature="'+feature+'"']
  argv+=['--test'] if test or label.endswith('-unit') else ['--crate-type','rlib']
  argv+=[vm/'src/lib.rs']
  argv+=['-o',artifact] if test else ['--emit=metadata='+str(artifact)+',mir='+str(mir)]
  env.update(MIXER_LOADER_MANIFEST_SHA256=digest(canonical(pre)),MIXER_LOADER_COMMAND_SHA256=digest(canonical(list(map(str,argv)))),MIXER_LOADER_COMPILER_SHA256=digest(RUSTC.read_bytes()),MIXER_LOADER_COMPILER_VERSION_SHA256=digest((HERE/'commands/compiler-version/stdout').read_bytes()))
  env['MIXER_LOADER_COMPILE_ENV_SHA256']=digest(canonical(env))
  write('commands/'+label+'-compile/source-preimage.json',pre)
  # Source preimage is written first without taking ownership of command dir.
  tmp=HERE/'commands'/ (label+'-compile')/'source-preimage.json';pre_raw=tmp.read_bytes();tmp.unlink();tmp.parent.rmdir()
  out,err,r=command(label+'-compile',argv,env,REPO,55)
  (HERE/'commands'/ (label+'-compile')/'source-preimage.json').write_bytes(pre_raw)
  if test:
   args=[artifact,'independent_phase_retention_v1::','--test-threads=1','--nocapture']
   if baseline:args=[artifact,'experimental_swift_reactor::control::independent_phase_retention_v1::same_ticket_complete_keeps_reservation_and_denies_one_more_byte','--exact','--test-threads=1','--nocapture']
   out,err,run=command(label+'-run',args,{'PATH':'/usr/bin:/bin'},scratch,15,expected=101 if baseline else 0)
   if baseline:assert b'FAILED' in out and b'assertion `left == right` failed' in err
   else:assert b'8 passed; 0 failed;' in out
   write('commands/'+label+'-run/executable-binding.json',dict(sha256=digest(artifact.read_bytes()),bytes=artifact.stat().st_size,source_preimage_sha256=digest(pre_raw),scratch_overlay_only=True,genuine_ingress=False,writer_executed=False,expected_regression_rejected=baseline))
   print(out.decode().strip())
  else:
   selections=focused(mir.read_text());(HERE/'commands'/ (label+'-compile')/'focused-functions.mir').write_text('\n'.join(selections.values()))
  write('commands/'+label+'-compile/removed-artifacts.json',[dict(name=p.name,bytes=p.stat().st_size,sha256=digest(p.read_bytes())) for p in [artifact,mir] if p.exists()])
  print(json.dumps(dict(label=label,compile_exit_code=r['exit_code'],elapsed_seconds=r['elapsed_seconds'])),flush=True)
 finally:
  shutil.rmtree(scratch)
  write('commands/'+label+'-compile/cleanup.json',dict(owned_scratch=str(scratch),scratch_removed=not scratch.exists(),global_process_inventory=False))
 source_binding()
def compare():
 details=[]
 for mode in ['production','unit']:
  old=focused((HERE/'commands'/('baseline-'+mode+'-compile')/'focused-functions.mir').read_text())
  new=focused((HERE/'commands'/('candidate-'+mode+'-compile')/'focused-functions.mir').read_text())
  for key in sorted(old):
   a=normalized(old[key]);b=normalized(new[key]);roles_a=re.findall(r'^\s+let (?:mut )?(_\d+): (.*?);(?: //|$)',old[key],re.M);roles_b=re.findall(r'^\s+let (?:mut )?(_\d+): (.*?);(?: //|$)',new[key],re.M)
   assert roles_a==roles_b,(mode,key,'roles')
   operand=None
   if key=='commit':
    previous=re.search(r'debug previous => (_\d+);',a)[1];construction=re.search(r'debug construction => (_\d+);',b)[1]
    return_operand=re.search(r'_0 = Result::<usize, SnapshotAdmissionErrorV1>::Ok\(move (_\d+)\);',a)[1]
    oldread=return_operand+' = copy '+previous+';';newread=return_operand+' = copy '+construction+';'
    assert a.count(oldread)==1 and b.count(newread)==1
    b=b.replace(newread,oldread);operand=dict(existing_operand=return_operand,baseline_local=previous,candidate_local=construction)
   assert a==b,(mode,key,'body')
   details.append(dict(context=mode,function=key,declared_roles=[dict(name=n,type=t) for n,t in roles_a],baseline_sha256=digest(old[key].encode()),candidate_sha256=digest(new[key].encode()),operand_change=operand,role_delta=0,action_delta=0,otherwise_identical=True))
 write('mir-comparison.json',dict(schema=1,source_binding=source_binding(),fresh_exact_compiles=4,focused_functions=details,new_roles=0,new_action_costs=0,context='Pinned rustc1.99 aarch64-apple-darwin only; no runtime dispatch'))
 print(json.dumps(dict(function_contexts_compared=len(details),role_delta=0,action_delta=0)))
def main():
 assert not (HERE/'seal.json').exists(),'packet frozen; copy before rerunning'
 label=sys.argv[1]
 if label=='audit':audit()
 elif label=='compare':compare()
 else:compile_run(label)
if __name__=='__main__':main()
