#!/usr/bin/env python3
"""One hosted formatting/lint diagnostic; never installs or executes locally."""
import argparse,collections,difflib,hashlib,importlib.util,json,os,platform,re,shutil,signal,sys,time,uuid
from pathlib import Path
from bounded_commands import Commands,need,regular,no_symlinks,identity,save,member,json_data,sha,exception_details

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PROFILE='pin-bitmap-format-lint-v1'
WORKFLOW_PATH='.github/workflows/swift-pin-bitmap-format-lint-admission.yml'
BASELINE='af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b'
CANDIDATE='674242606ec1f81e8bf53d6d10c0ae390c94c75e78d0a5c0e695bfb36b5eec20'
INPUT_HELPER='verification/swift-pin-bitmap-lifecycle-host-admission/admit.py'
INPUT_HELPER_SHA='23ab09172f130acea527a1c249756cabcd7bdee577f1a399a51e2ec821add409'
OVERLAYS=('src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs')
ACTIVE_SECONDS=900
CLEANUP_SECONDS=60
MAX_FILE_BYTES=16*1024*1024
MAX_SOURCE_BYTES=64*1024*1024
TOOLCHAIN='1.99.0-x86_64-unknown-linux-gnu'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def closure(rows):return digest(''.join(n+'\0'+rows[n]['sha256']+'\n'for n in sorted(rows)).encode())
def file_row(raw):return {'bytes':len(raw),'sha256':digest(raw)}

def inputs():
 # Reuse only the sealed materializer; never invoke its six-command executor.
 path=regular(ROOT/INPUT_HELPER);need(sha(path)==INPUT_HELPER_SHA,'Materializer helper changed')
 spec=importlib.util.spec_from_file_location('sealed_bitmap_materializer',path)
 materializer=importlib.util.module_from_spec(spec);spec.loader.exec_module(materializer)
 m,unused_plan,candidate=materializer.inputs()
 need(m['baselineTreeSHA256']==BASELINE and m['candidateTreeSHA256']==CANDIDATE,'Exact source closures')
 need(m['overlayPaths']==list(OVERLAYS),'Exactly four overlay paths')
 baseline={n:materializer.bound(ROOT/'vm'/member(n),r)for n,r in m['baselineFiles'].items()}
 need(len(baseline)==len(candidate)==136,'Complete source closures')
 need({n for n in baseline if baseline[n]!=candidate[n]}==set(OVERLAYS),'Exact source difference set')
 return m,{'baseline':baseline,'candidate':candidate}

def inventory(source):
 rows={};total=0
 for directory,dirs,files in os.walk(source,followlinks=False):
  for n in dirs:no_symlinks(Path(directory)/n)
  for n in files:
   p=regular(Path(directory)/n);need(p.stat().st_size<=MAX_FILE_BYTES,'Source member byte bound')
   raw=p.read_bytes();total+=len(raw);need(total<=MAX_SOURCE_BYTES,'Source aggregate bound')
   rows[p.relative_to(source).as_posix()]=file_row(raw)
 return rows

def exact_source(source,expected):
 rows=inventory(source);need(rows==expected,'Complete source postflight mismatch');return closure(rows)

def format_evidence(out,arm,source,before,raw_before):
 after=inventory(source);need(set(after)==set(before),'Formatter source roster changed')
 changed=sorted(n for n in before if after[n]!=before[n])
 result={'beforeTreeSHA256':closure(before),'afterTreeSHA256':closure(after),'changedPaths':changed,
         'outsideOverlayChanges':sorted(set(changed)-set(OVERLAYS)),'files':{},'verified':False}
 dest=out/'format'/arm;dest.mkdir(parents=True,exist_ok=True);diff=[]
 for n in OVERLAYS:
  raw_after=(source/member(n)).read_bytes()
  for stage,raw in (('before',raw_before[n]),('after',raw_after)):
   p=dest/stage/member(n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  result['files'][n]={'before':before[n],'after':after[n]}
  diff.extend(difflib.unified_diff(raw_before[n].decode().splitlines(keepends=True),raw_after.decode().splitlines(keepends=True),fromfile='before/'+n,tofile='after/'+n))
 (dest/'format.diff').write_text(''.join(diff));result['diffSHA256']=sha(dest/'format.diff')
 result['verified']=not result['outsideOverlayChanges'];save(dest/'receipt.json',result)
 need(result['verified'],'Formatter changed outside the four overlays')
 return after,result

def cargo_configs_absent(source):
 for directory in (source,*source.parents):
  for n in ('config','config.toml'):need(not(directory/'.cargo'/n).exists(),'Inherited Cargo configuration forbidden')
  for n in ('clippy.toml','.clippy.toml'):need(not(directory/n).exists(),'Inherited Clippy configuration forbidden')

def arm_environment(paths,toolbin):
 return {'HOME':str(paths['home']),'CARGO_HOME':str(paths['cargo']),'CARGO_TARGET_DIR':str(paths['target']),
         'CARGO_NET_OFFLINE':'true','CARGO_INCREMENTAL':'0','RUSTUP_TOOLCHAIN':TOOLCHAIN,
         'RUSTC':str(toolbin/'rustc'),'CLIPPY_CONF_DIR':str(paths['home']),'PATH':str(toolbin)+':/usr/bin:/bin','LANG':'C','LC_ALL':'C'}

def command_plan(paths,toolbin,config):
 plan=[{'name':'toolchain-identity','argv':[str(toolbin/'rustc'),'-vV'],'arm':'baseline','seconds':30,'accepted_exits':(0,)}]
 for arm in ('baseline','candidate'):
  plan.append({'name':'format-'+arm,'argv':[str(toolbin/'rustfmt'),'--edition','2021','--emit','files','--config-path',str(config),*[str(paths[arm]['source']/n)for n in OVERLAYS]],'arm':arm,'seconds':30,'accepted_exits':(0,)})
 for arm in ('baseline','candidate'):
  plan.append({'name':'clippy-'+arm,'argv':[str(toolbin/'cargo'),'clippy','--manifest-path',str(paths[arm]['source']/'Cargo.toml'),'--locked','--offline','--all-features','--all-targets','--message-format=json','--','-D','warnings'],'arm':arm,'seconds':300,'accepted_exits':(0,101)})
 return plan

def lint_evidence(text,exit_code,source):
 messages=[];finished=[];reasons=collections.Counter()
 for line in text.splitlines():
  if not line.strip():continue
  value=json_data(line);need(isinstance(value,dict)and isinstance(value.get('reason'),str),'Malformed Cargo JSON record')
  reasons[value['reason']]+=1
  if value['reason']=='build-finished':need(type(value.get('success'))is bool,'Malformed build completion');finished.append(value['success'])
  if value['reason']=='compiler-message':
   msg=value['message'];need(isinstance(msg,dict)and isinstance(msg.get('message'),str)and isinstance(msg.get('level'),str),'Malformed compiler diagnostic')
   messages.append(msg)
 need(len(finished)==1 and finished[0]==(exit_code==0),'Cargo completion/exit mismatch')
 if exit_code==101:need(any(x['level']=='error'for x in messages),'Nonzero Cargo result has no error diagnostic')
 return {'exit':exit_code,'lintPassed':exit_code==0,'buildFinished':finished[0],'recordReasons':dict(reasons),
         'diagnostics':messages,'sourceRoot':str(source),'scope':'compile/lint only; no Rust tests or product execution'}

def diagnostic_counts(result):
 counts=collections.Counter()
 for m in result['diagnostics']:
  code=m.get('code');code=code.get('code')if isinstance(code,dict)else code
  files=sorted(set(s.get('file_name','').replace(result['sourceRoot']+'/','')for s in m.get('spans',[])))
  key=json.dumps({'code':code,'level':m['level'],'message':m['message'].replace(result['sourceRoot'],'$SOURCE'),'files':files},sort_keys=True)
  counts[key]+=1
 return counts

def comparison(results):
 baseline=diagnostic_counts(results['baseline']);candidate=diagnostic_counts(results['candidate'])
 def rows(values):return [{'diagnostic':json.loads(k),'count':v}for k,v in sorted(values.items())]
 return {'baselineLintPassed':results['baseline']['lintPassed'],'candidateLintPassed':results['candidate']['lintPassed'],
         'shared':rows(baseline&candidate),'baselineOnly':rows(baseline-candidate),'candidateOnly':rows(candidate-baseline),
         'matching':'code/level/message/file multiset; line numbers ignored for formatting shifts; full JSON retained',
         'candidateOnlyIsSemanticAttribution':False,'integrationAccepted':False}

def checked_command(c,spec,paths,toolbin,expected,out,raw_before):
 arm=spec['arm'];source=paths[arm]['source'];primary=None;row=None;result=None
 for name in paths:exact_source(paths[name]['source'],expected[name])
 cargo_configs_absent(source);cargo_configs_absent(paths[arm]['home'])
 try:
  text,err,row=c.run(spec['name'],spec['argv'],source,arm_environment(paths[arm],toolbin),seconds=spec['seconds'],accepted_exits=spec['accepted_exits'])
  if spec['name']=='toolchain-identity':
   need(re.search(r'^release: 1\.99\.0$',text,re.M)and re.search(r'^host: x86_64-unknown-linux-gnu$',text,re.M),'Wrong compiler identity');result={'compilerIdentity':text}
  elif spec['name'].startswith('clippy-'):result=lint_evidence(text,row['exit'],source)
 except BaseException as e:primary=e
 finally:
  if row is None and c.receipt['commands']and c.receipt['commands'][-1]['name']==spec['name']:row=c.receipt['commands'][-1]
  if row is None:row={'name':spec['name']};c.receipt.setdefault('unregisteredPostflights',[]).append(row)
  try:
   if spec['name'].startswith('format-'):
    updated,evidence=format_evidence(out,arm,source,expected[arm],raw_before[arm]);expected[arm]=updated;row['formatEvidence']=evidence
   row['sourceAfter']={name:exact_source(paths[name]['source'],expected[name])for name in paths};row['sourcePostflight']={'attempted':True,'verified':True,'bothArms':True}
  except BaseException as e:row['sourcePostflight']={'attempted':True,'verified':False,'error':exception_details(e)};primary=primary or e
  try:c.save()
  except BaseException as e:row['sourcePostflightReceiptError']=exception_details(e);primary=primary or e
 if primary is not None:raise primary
 return result

def hosted():
 need(os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','GitHub hosted only')
 need(os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','Manual first attempt only')
 need(os.environ.get('GITHUB_REPOSITORY')=='snowdamiz/mixer'and re.fullmatch('[0-9a-f]{40}',os.environ.get('GITHUB_SHA','')),'Bound source revision')
 need(os.environ.get('MIXER_PIN_BITMAP_FORMAT_LINT_SELECTION')==PROFILE,'Exact profile selection')
 need(platform.system()=='Linux'and platform.machine()=='x86_64','Linux x86_64 required')
 temp=Path(os.environ['RUNNER_TEMP']);need(temp.is_absolute()and '..'not in temp.parts,'Canonical runner temp');identity(temp)
 need(not temp.is_relative_to(ROOT)and not ROOT.is_relative_to(temp),'Separate checkout/temp roots')
 rustup=Path(os.environ['RUSTUP_HOME']);need(rustup.is_absolute()and '..'not in rustup.parts,'Explicit canonical rustup home');identity(rustup)
 toolbin=rustup/'toolchains'/TOOLCHAIN/'bin';identity(toolbin)
 for n in ('rustc','rustfmt','cargo','cargo-clippy','clippy-driver'):regular(toolbin/n)
 return temp,toolbin

def execute():
 temp,toolbin=hosted();m,data=inputs();out=temp/(PROFILE+'-evidence');no_symlinks(out);need(not out.exists(),'Fresh evidence only');out.mkdir()
 receipt={'schema':1,'status':'running','sourceRevision':os.environ['GITHUB_SHA'],'runID':os.environ.get('GITHUB_RUN_ID'),'runAttempt':1,
          'profile':PROFILE,'baselineTreeSHA256':BASELINE,'candidateTreeSHA256':CANDIDATE,'pythonVersion':sys.version,
          'activeSeconds':ACTIVE_SECONDS,'cleanupSeconds':CLEANUP_SECONDS,'maxChildren':5,'perStreamOutputCapBytes':8*1024*1024,
          'aggregateOutputCapBytes':32*1024*1024,'commands':[],'errors':[],'automaticRetry':False,'RustTestsRun':0,'GAQualified':False,
          'installerCustodyEvidence':False,'standaloneRustfmtClippyVersionStrings':False,'canonicalInstallationSelected':False,
          'materializerHelper':{'path':INPUT_HELPER,'sha256':INPUT_HELPER_SHA}}
 marker={'purpose':PROFILE,'token':uuid.uuid4().hex};save(out/'ownership.json',marker);out_id=identity(out)
 save(out/'source-manifest.json',m)
 for n in ('admit.py','bounded_commands.py'):shutil.copyfile(HERE/n,out/('executed-'+n))
 receipt['harnessFiles']={n:sha(HERE/n)for n in ('admit.py','bounded_commands.py')}
 receipt['toolchainFiles']={n:{'path':str(toolbin/n),'sha256':sha(toolbin/n)}for n in ('rustc','rustfmt','cargo','cargo-clippy','clippy-driver')}
 save(out/'receipt.json',receipt)
 component=regular(toolbin.parent/'lib/rustlib/components');receipt['components']={'sha256':sha(component),'text':component.read_text()}
 need({'rustfmt-preview','clippy-preview'}<=set(component.read_text().splitlines()),'Required pinned components absent')
 c=Commands(out,receipt,time.monotonic()+ACTIVE_SECONDS);scratch=out/'scratch';owned=None;failure=None
 handlers={s:signal.getsignal(s)for s in (signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
 def alarm(signum,frame):raise TimeoutError('Finite diagnostic budget expired')
 def interrupt(signum,frame):raise KeyboardInterrupt('Signal '+str(signum))
 signal.signal(signal.SIGALRM,alarm);signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGTERM,interrupt);signal.setitimer(signal.ITIMER_REAL,ACTIVE_SECONDS)
 try:
  no_symlinks(scratch);need(not scratch.exists(),'Fresh scratch only');scratch.mkdir();owned=identity(scratch);c.bind_scratch(scratch)
  paths={};expected={};raw_before={}
  for arm in ('baseline','candidate'):
   paths[arm]={n:scratch/arm/n for n in ('source','target','cargo','home')}
   for p in paths[arm].values():p.mkdir(parents=True)
   for n,raw in data[arm].items():
    p=paths[arm]['source']/member(n);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(raw)
   expected[arm]=m['baselineFiles'if arm=='baseline'else'candidateFiles'].copy();exact_source(paths[arm]['source'],expected[arm]);raw_before[arm]={n:data[arm][n]for n in OVERLAYS}
  config=scratch/'rustfmt.toml';config.write_text('edition = "2021"\n')
  plan=command_plan(paths,toolbin,config);save(out/'command-plan.json',plan);results={}
  for spec in plan:
   result=checked_command(c,spec,paths,toolbin,expected,out,raw_before)
   if spec['name']=='toolchain-identity':receipt.update(result)
   if spec['name'].startswith('clippy-'):results[spec['arm']]=result;save(out/('clippy-'+spec['arm']+'.json'),result)
  need(len(receipt['commands'])==5,'Exact five commands')
  save(out/'comparison.json',comparison(results));receipt['lintPassed']={a:r['lintPassed']for a,r in results.items()}
  receipt['formattedSourceClosures']={a:closure(v)for a,v in expected.items()}
  receipt['status']='diagnostic-completed'if all(r['lintPassed']for r in results.values())else'diagnostic-completed-with-lint-findings'
 except BaseException as e:failure=e;receipt['status']='failed';receipt['errors'].append(exception_details(e))
 finally:
  signal.setitimer(signal.ITIMER_REAL,CLEANUP_SECONDS)
  try:
   need(c.active is None and all(r.get('child_returned')and r.get('owned_group_gone')for r in receipt['commands']if 'pid'in r),'Unresolved custody: preserve scratch')
   need(identity(out)==out_id and json_data(regular(out/'ownership.json').read_bytes())==marker,'Evidence ownership changed')
   if owned is not None:need(identity(scratch)==owned,'Owned scratch identity changed');shutil.rmtree(scratch);need(not scratch.exists(),'Scratch cleanup incomplete')
   receipt['cleanup']={'ownedScratchRemoved':True,'childReapAndGroupAbsenceVerified':True,'processInventory':False,'otherProjectsTouched':False}
  except BaseException as e:receipt['cleanup']={'ownedScratchRemoved':False,'custodyHold':True};receipt['errors'].append(exception_details(e));receipt['status']='failed-custody-or-cleanup';failure=failure or e
  finally:
   signal.setitimer(signal.ITIMER_REAL,0)
   for s,h in handlers.items():signal.signal(s,h)
   receipt['finishedUTC']=time.time();save(out/'receipt.json',receipt)
 if failure is not None:raise failure
 return receipt

def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('check','run'));args=parser.parse_args()
 if args.mode=='check':
  m,data=inputs();print(json.dumps({'baselineTreeSHA256':BASELINE,'candidateTreeSHA256':CANDIDATE,'membersPerArm':len(data['baseline']),'commands':5,'actualRustRuns':0}));return
 print(json.dumps(execute()))
if __name__=='__main__':main()
