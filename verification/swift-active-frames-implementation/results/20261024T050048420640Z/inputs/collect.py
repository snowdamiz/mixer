#!/usr/bin/env python3
"""Immutable, host-only original-owner frame matrix and Frozen regressions."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
FREEZE=HERE/'source-freeze'
if (FREEZE/'latest.json').exists():FREEZE=FREEZE/json.loads((FREEZE/'latest.json').read_text())['directory']
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT=HERE/'results'/STAMP;BUILD=HERE/'build'/STAMP;OUT.mkdir(parents=True);BUILD.mkdir(parents=True)
ENV=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);ENV.pop('RUSTC_BOOTSTRAP',None);ENV.pop('RUSTFLAGS',None)
encoded=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
digest=lambda x:hashlib.sha256(encoded(x)).hexdigest()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):(OUT/name).write_bytes(encoded(x))
def manifest(path):return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
COMMANDS=[];BINARIES=[];LAYOUTS=[];VARIANTS=[];COMPARISONS=[];ABI=[];PRIVACY=[];status='failed-host-verification'
def command(name,args,cwd=ROOT,target=None,closure=None,allowed=False,extra=None):
 if closure is not None:assert manifest(cwd)==closure,('source drift before',name)
 env=dict(ENV)
 if target:env['CARGO_TARGET_DIR']=str(target)
 if extra:env.update(extra)
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,timeout=1200)
 for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(p,stream))
 if closure is not None:assert manifest(cwd)==closure,('source drift after',name)
 COMMANDS.append(dict(name=name,argv=args,cwd=str(cwd),target=str(target) if target else None,startedUTC=started,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,extraEnvironment=extra or {},sourceTreeSHA256=digest(closure) if closure else None,sourceBeforeAfterVerified=closure is not None,stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))))
 print(name,p.returncode,flush=True)
 if not allowed and p.returncode:raise RuntimeError((name,p.stderr.decode(errors='replace')[-6000:]))
 return p.stdout.decode(errors='replace'),p.stderr.decode(errors='replace'),p.returncode

def extract(label,archive):
 path=BUILD/label
 with tarfile.open(archive) as t:t.extractall(path,filter='data')
 vm=path/'vm';closure=manifest(vm);save(label+'-manifest.json',closure)
 with tarfile.open(OUT/(label+'-source.tar.gz'),'w:gz') as t:
  for name in closure:t.add(vm/name,arcname='vm/'+name,recursive=False)
 VARIANTS.append(dict(label=label,manifest=label+'-manifest.json',sourceTreeSHA256=digest(closure),archive=label+'-source.tar.gz',archiveSHA256=sha(OUT/(label+'-source.tar.gz'))))
 return vm,closure

def product(name,vm,closure,flags,release,targets):
 target=BUILD/(name+'-target');args=['cargo','test','--locked','--offline','--no-run','--message-format=json','--lib',*flags]
 for t in targets:args+=['--test',t]
 if release:args+=['--release']
 output,_,_=command(name+'-build',args,vm,target,closure)
 artifacts=[]
 for line in output.splitlines():
  try:item=json.loads(line)
  except ValueError:continue
  if item.get('reason')=='compiler-artifact' and item.get('executable') and item.get('profile',{}).get('test'):artifacts.append((item['target']['name'],Path(item['executable'])))
 assert len(artifacts)==len(targets)+1,(name,len(artifacts),targets)
 tests=[];traces=[];summaries=[]
 for kind,binary in sorted(artifacts):
  list_name=name+'-'+kind+'-list';run_name=name+'-'+kind+'-run'
  listing,_,_=command(list_name,[str(binary),'--list'],vm,target,closure)
  run,_,_=command(run_name,[str(binary),'--nocapture','--test-threads=1'],vm,target,closure)
  identities=[line for line in listing.splitlines() if line.endswith(': test')];tests+=identities
  records=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',run);assert len(records)==1 and records[0][0]=='ok' and records[0][2]=='0',(name,kind,records)
  summaries.append(dict(target=kind,passed=int(records[0][1]),ignored=int(records[0][3])))
  traces += [line[line.index(marker):] for line in run.splitlines() for marker in ['control_trace ','numeric_trace '] if marker in line]
  BINARIES.append(dict(label=name,target=kind,path=str(binary),sha256=sha(binary),runtimeTests=identities,listCommand=list_name,runCommand=run_name))
 return dict(tests=sorted(tests),traces=traces,counts=summaries)

def frozen_method(text,name):
 at=text.index('fn '+name+'(');end=text.index('{',at)+1;depth=1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[at:end]

def lint_identities(stderr, vm):
 ids=[]
 lines=stderr.splitlines()
 for i,line in enumerate(lines):
  if line.startswith('error: ') and not line.startswith('error: could not compile'):
   span=next((v.strip() for v in lines[i+1:i+6] if '-->' in v),'')
   match=re.search(r'--> ([^:]+):(\d+):(\d+)',span)
   assert match,('missing primary lint span',line,span)
   path,number,column=match.groups();source=(vm/path).read_text().splitlines()[int(number)-1].strip()
   ids.append([line,path,column,source])
 return sorted(ids)

def reused_baseline(vm, closure, prior):
 receipt=json.loads((prior/'receipt.json').read_text())
 expected=next(v['sourceTreeSHA256'] for v in receipt['variants'] if v['label']=='baseline')
 assert expected==digest(closure)
 save('reused-baseline-receipt.json',receipt)
 for entry in receipt['commands']:
  if not entry['name'].startswith('baseline-'):continue
  assert entry['sourceTreeSHA256']==expected
  for stream in ['stdout','stderr']:
   assert sha(prior/entry[stream])==entry[stream+'SHA256'];shutil.copyfile(prior/entry[stream],OUT/entry[stream])
  COMMANDS.append(dict(entry,reusedFromReceipt=str(prior/'receipt.json')))
 values={}
 for config in ['swift','all']:
  for release in [False,True]:
   label='baseline-'+config+('-release' if release else '-debug');items=[x for x in receipt['binaries'] if x['label']==label];assert items
   tests=[];traces=[]
   for old in sorted(items,key=lambda x:x['target']):
    path=Path(old['path']);assert sha(path)==old['sha256'];dest=BUILD/'reused-baseline-artifacts'/label/path.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    BINARIES.append(dict(old,path=str(dest),reusedFromReceipt=str(prior/'receipt.json')));tests+=old['runtimeTests']
    run=(prior/(old['runCommand']+'.stdout')).read_text()
    assert re.search(r'test result: ok\. \d+ passed; 0 failed;',run)
    traces += [line[line.index(marker):] for line in run.splitlines() for marker in ['control_trace ','numeric_trace '] if marker in line]
   comparison=next(v for v in receipt['comparisons'] if v['config']==config and v['profile']==('release' if release else 'debug'))
   values[('baseline',config,release)]=dict(tests=sorted(tests),traces=traces,counts=comparison['baselineCounts'])
 stderr=(prior/'baseline-clippy-broad.stderr').read_text()
 return values,lint_identities(stderr,vm)

try:
 command('revision',['git','rev-parse','HEAD']);command('rustc-version',['rustc','-vV']);command('cargo-version',['cargo','-V']);command('python-version',['python3','--version']);command('host',['uname','-a'])
 (OUT/'inputs').mkdir()
 for name in ['collect.py','inventory.py','implementation-inventory-schema.json','frozen-inventory-schema.json','production.mir','unit.mir']:
  shutil.copyfile(HERE/name,OUT/'inputs'/name)
 shutil.copyfile(FREEZE/'freeze.json',OUT/'inputs/freeze.json')
 sources={label:extract(label,HERE/archive) for label,archive in [('baseline','baseline-source.tar.gz'),('candidate',str(FREEZE/'candidate-source.tar.gz'))]}
 assert sources['candidate'][1]==json.loads((FREEZE/'candidate-manifest.json').read_text())
 baseline,candidate=sources['baseline'],sources['candidate']
 ordinary={};lints={}
 for label,(vm,closure) in sources.items():
  reuse=Path(os.environ['MIXER_FRAME_BASELINE_REUSE']) if os.environ.get('MIXER_FRAME_BASELINE_REUSE') else None
  if label=='baseline' and reuse:
   imported,lint=reused_baseline(vm,closure,reuse);ordinary.update(imported);lints[label]=lint;continue
  if label=='candidate':
   command('candidate-format',['cargo','fmt','--all','--','--check'],vm,closure=closure)
   command('candidate-clippy-lib',['cargo','clippy','--locked','--offline','--lib','--all-features','--','-D','warnings'],vm,BUILD/'candidate-clippy-lib-target',closure)
   for config,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
    for release in [False,True]:command('candidate-'+config+('-release' if release else '-debug')+'-check',['cargo','check','--locked','--offline','--lib',*flags,*(['--release'] if release else [])],vm,BUILD/('check-'+config+str(release)),closure)
  _,stderr,_=command(label+'-clippy-broad',['cargo','clippy','--locked','--offline','--all-targets','--all-features','--','-D','warnings'],vm,BUILD/(label+'-clippy-broad-target'),closure,allowed=True);lints[label]=lint_identities(stderr,vm)
  for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
   targets=['differential','float','float_differential','swift_reactor_validation','swift_reactor_validation_allocations','swift_wasi','swift_wasi_allocations']
   if config=='all':targets+=['span_control_extraction','span_numeric_extraction','span_execution','span_execution_allocations','span_execution_oracle','span_function_cache','span_function_cache_allocations']
   for release in [False,True]:ordinary[(label,config,release)]=product(label+'-'+config+('-release' if release else '-debug'),vm,closure,flags,release,targets)
 for config in ['swift','all']:
  for release in [False,True]:
   b=ordinary[('baseline',config,release)];a=ordinary[('candidate',config,release)];added=sorted(set(a['tests'])-set(b['tests']));removed=sorted(set(b['tests'])-set(a['tests']))
   assert len(added)==22 and all('frame_operations::tests::af' in v for v in added),(config,added)
   assert not removed,(config,removed);assert a['traces']==b['traces'],(config,'traces')
   COMPARISONS.append(dict(config=config,profile='release' if release else 'debug',addedTests=added,removedTests=removed,frozenTraceRecords=len(a['traces']),frozenTraceSHA256=digest(a['traces']),frozenTracesEqual=True,baselineCounts=b['counts'],candidateCounts=a['counts']))
 assert lints['candidate']==lints['baseline'],('new clippy identities',set(map(tuple,lints['candidate']))-set(map(tuple,lints['baseline'])));save('broad-clippy-identities.json',lints)
 # Exact compiler-expanded original helpers: bootstrap is diagnostic only.
 expanded={}
 for label,(vm,closure) in sources.items():
  output,_,_=command(label+'-frozen-expansion',['cargo','rustc','--locked','--offline','--lib','--all-features','--','-Zunpretty=expanded'],vm,BUILD/(label+'-expansion-target'),closure,extra={'RUSTC_BOOTSTRAP':'1'})
  owner=output[output.index('impl SpanInstance {'):];expanded[label]={name:frozen_method(owner,name) for name in ['enter','finish','cleanup','pop32','close_control','branch']};save(label+'-frozen-methods.json',expanded[label])
 assert expanded['baseline']==expanded['candidate']
 # Four feature/profile C ABI pairs; retain every actual compiled dylib.
 for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:
   exports={}
   for label,(vm,closure) in sources.items():
    name=label+'-'+config+('-release' if release else '-debug')+'-abi';target=BUILD/(name+'-target')
    command(name+'-build',['cargo','build','--locked','--offline','--lib',*flags,*(['--release'] if release else [])],vm,target,closure)
    binary=target/('release' if release else 'debug')/'libmixer_vm.dylib';listing,_,_=command(name+'-exports',['nm','-gU','-j',str(binary)],vm,target,closure)
    exports[label]=sorted(v for v in listing.splitlines() if v.startswith('_mixer_'));ABI.append(dict(label=name,path=str(binary),sha256=sha(binary),exports=exports[label]))
   assert exports['baseline']==exports['candidate']
 status='passed-private-active-frames-host-matrix-pending-independent-accounting-and-root-review'
finally:
 receipt=dict(schema=1,status=status,sourceFreeze=json.loads((FREEZE/'freeze.json').read_text()),commands=COMMANDS,variants=VARIANTS,binaries=BINARIES,comparisons=COMPARISONS,abi=ABI,computerUse=False,nativeRuntime=False,initializeInvokeDispatcher=False,gaGatePassed=False,scope='Headless host original-owner entry/return/terminal cleanup; no native target or published FieldLog qualification')
 save('receipt.json',receipt)
 # Compact independently retained executables, never dependent on targets.
 members=[]
 with tarfile.open(OUT/'qualifying-artifacts.tar.gz','w:gz') as t:
  for i,item in enumerate(BINARIES+ABI):
   p=Path(item['path']);member=f'{i:03d}-{item["label"]}-{p.name}';t.add(p,arcname=member,recursive=False);members.append(dict(member=member,sha256=sha(p),label=item['label'],sourceTreeSHA256=next(v['sourceTreeSHA256'] for v in VARIANTS if v['label']==item['label'].split('-')[0]),originalPath=str(p)))
 save('qualifying-artifacts.json',dict(archive='qualifying-artifacts.tar.gz',archiveSHA256=sha(OUT/'qualifying-artifacts.tar.gz'),members=members))
 print(OUT,flush=True)
