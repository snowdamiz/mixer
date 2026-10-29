#!/usr/bin/env python3
"""Authored hosted-only bitmap admission. Pure check does not launch commands.

This harness is separate from the independent product-source review. Root must
review/integrate the workflow before a manual first-attempt run is possible.
"""
import argparse,hashlib,json,os,platform,re,shutil,signal,sys,time,uuid
from pathlib import Path
from bounded_commands import Commands,need,regular,no_symlinks,identity,save,member,json_data,sha,exception_details
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
# Local dirty-file fingerprints are preservation evidence, not hosted VM inputs.
LOCAL_PRESERVATION_ONLY=frozenset({'.github/workflows/hosted.yml','hosted/lib/mixer_hosted/browser_auth/store.ex'})
PACKET=ROOT/'verification/swift-dense512-product-integration'
PRODUCER_SEAL='290909956b188ed46c73c2c73541c8ed60a80788f0d51f9adbca0940579a54f2'
BASELINE='af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b'
PRIOR_CANDIDATE='4f9968797133b17520e5387e8ea9870bad779159968357cd31c50abbeb8c8bbd'
CANDIDATE='674242606ec1f81e8bf53d6d10c0ae390c94c75e78d0a5c0e695bfb36b5eec20'
LIFECYCLE=ROOT/'verification/swift-pin-bitmap-lifecycle-correction'
LIFECYCLE_MEMBER='src/experimental_swift_reactor/lifecycle_tests.rs'
WORKFLOW_PATH='.github/workflows/swift-pin-bitmap-lifecycle-admission.yml'
PROFILE='pin-bitmap-lifecycle-v2'
FROZEN_PACKETS=(
 (PACKET,PRODUCER_SEAL,14),
 (ROOT/'verification/swift-pin-bitmap-independent','84b2cc15c97f951d850904a733ec747fbbb0b17ee23fe8f0b19a8da285c5dfaa',17),
 (ROOT/'verification/swift-pin-bitmap-host-binding-correction','f44236c30b0a789b86171d864cf997537d7055a4a32543243854871081b2ab3f',9),
 (LIFECYCLE,'b3b502ab5027615d1ff6bcb396f893554407e7f4f983ca89c2e3a499b4291ab6',20),
)
ACTIVE_SECONDS=2500
CLEANUP_SECONDS=60
MAX_SOURCE_BYTES=64*1024*1024
MAX_SOURCE_FILE_BYTES=16*1024*1024
FOCUSED_PREFIX='experimental_swift_reactor::cache_tests::'
FOCUSED_SUFFIXES=(
 'pin_bitmap_integration_masks_and_unchanged_policy',
 'pin_bitmap_integration_every_narrow_capacity_and_last_bit',
 'pin_bitmap_integration_hole_reuse_and_constant_selection_work',
 'pin_bitmap_integration_corruption_preserves_records_and_token',
 'pin_bitmap_integration_all_failure_prefixes_and_constructor_admission',
 'pin_bitmap_integration_terminal_cancellation_keeps_release_available',
 'pin_bitmap_integration_geometry_and_consuming_cleanup',
)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def closure(rows):return digest(''.join(n+'\0'+rows[n]['sha256']+'\n'for n in sorted(rows)).encode())
def bound(path,row):
 regular(path);need(type(row['bytes'])is int and 0<=row['bytes']<=MAX_SOURCE_FILE_BYTES,'Member byte bound')
 need(path.stat().st_size==row['bytes'],'Member size: '+str(path));raw=path.read_bytes()
 need(len(raw)==row['bytes']and digest(raw)==row['sha256'],'Member hash: '+str(path));return raw
def sealed_packet(path,expected,count):
 need(sha(regular(path/'seal.json'))==expected,'Frozen packet seal changed: '+str(path))
 seal=json_data((path/'seal.json').read_bytes());need(len(seal['files'])==count,'Frozen packet member count')
 for n,r in seal['files'].items():bound(path/member(n),r)
 return seal

def inputs():
 for path,expected,count in FROZEN_PACKETS:sealed_packet(path,expected,count)
 original=json_data((PACKET/'manifest.json').read_bytes());p=json_data((PACKET/'host-plan.json').read_bytes())
 m=json_data((LIFECYCLE/'manifest.json').read_bytes())
 need(len(original['baselineFiles'])==136 and set(original['baselineFiles'])==set(original['candidateFiles']),'Original VM closure roster')
 need(closure(original['baselineFiles'])==BASELINE and closure(original['candidateFiles'])==PRIOR_CANDIDATE,'Original source closure digest')
 need(len(original['overlayPaths'])==3 and len(set(original['overlayPaths']))==3,'Original overlay roster')
 need(m['baselineFiles']==original['baselineFiles'] and m['priorCandidateFiles']==original['candidateFiles'],'Lifecycle baseline/prior bindings')
 need(m['baselineTreeSHA256']==BASELINE and m['priorCandidateTreeSHA256']==PRIOR_CANDIDATE and m['candidateTreeSHA256']==CANDIDATE,'Lifecycle declared closures')
 need(set(m['candidateFiles'])==set(original['baselineFiles']) and closure(m['candidateFiles'])==CANDIDATE,'Fresh complete VM closure')
 need(m['newOverlayPaths']==[LIFECYCLE_MEMBER] and m['overlayPaths']==[*original['overlayPaths'],LIFECYCLE_MEMBER],'Exactly fourth lifecycle overlay')
 need({n for n in m['candidateFiles']if m['candidateFiles'][n]!=original['candidateFiles'][n]}=={LIFECYCLE_MEMBER},'Only lifecycle changes prior candidate')
 need(set(m['materializationPaths'])==set(m['candidateFiles']),'Materialization roster')
 data={};total=0
 for n,r in original['baselineFiles'].items():
  baseline=bound(ROOT/'vm'/member(n),r)
  expected=('verification/swift-pin-bitmap-lifecycle-correction/candidate/vm/'+n if n==LIFECYCLE_MEMBER else
            'verification/swift-dense512-product-integration/candidate/vm/'+n if n in original['overlayPaths'] else 'vm/'+n)
  need(m['materializationPaths'][n]==expected,'Exact materialization path: '+n)
  selected=bound(ROOT/member(expected),m['candidateFiles'][n])if expected!='vm/'+n else baseline
  need(digest(selected)==m['candidateFiles'][n]['sha256'],'Candidate member mismatch');data[n]=selected;total+=len(selected)
  need(total<=MAX_SOURCE_BYTES,'Source aggregate byte bound')
 for n,r in original['protectedFiles'].items():
  if n not in LOCAL_PRESERVATION_ONLY:bound(ROOT/member(n),r)
 # Return the original public/contract roster for unchanged binding controls.
 m['protectedFiles']=original['protectedFiles']
 plan=[p['firstExecutable'],*p['followupCommands']]
 need(len(plan)==6 and [x['commandSeconds']for x in plan]==[300,300,180,180,600,600],'Exact finite sequence')
 need(p['candidateTreeSHA256']==PRIOR_CANDIDATE and p['custody']['maxWholeReactorAttempts']==0 and p['custody']['retry']is False,'Original plan authority')
 return m,plan,data

def hosted():
 need(os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','Fresh GitHub-hosted runner only')
 need(os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','Manual first attempt only; no rerun')
 need(os.environ.get('GITHUB_REPOSITORY')=='snowdamiz/mixer'and re.fullmatch('[0-9a-f]{40}',os.environ.get('GITHUB_SHA','')),'Bound repository/source revision')
 need(os.environ.get('MIXER_PIN_BITMAP_SELECTION')==PROFILE,'Exact manual selection')
 need(platform.system()=='Linux'and platform.machine()=='x86_64','Linux x86_64 only')
 temp=Path(os.environ['RUNNER_TEMP']);need(temp.is_absolute()and '..'not in temp.parts,'Runner temporary root');identity(temp)
 need(not temp.is_relative_to(ROOT)and not ROOT.is_relative_to(temp),'Temporary root must be separate from checkout')
 return temp

def summary(text,focused=False):
 rows=[dict(zip(('passed','failed','ignored','measured','filtered'),map(int,x)))for x in re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',text,re.M)]
 need(rows and sum(x['passed']for x in rows)>0 and all(x['failed']==0 for x in rows),'Missing/nonpassing/nonzero test summary')
 if focused:
  need(len(rows)==1 and rows[0]['passed']==7 and rows[0]['ignored']==rows[0]['measured']==0,'Exactly seven focused methods required')
  names=re.findall(r'^test (\S+) \.\.\.',text,re.M)
  need(len(names)==7 and set(names)=={FOCUSED_PREFIX+x for x in FOCUSED_SUFFIXES},'Focused names changed or duplicated')
 return rows

def geometry(text):
 lines=re.findall(r'PLAN_PROFILE floor=[^\n]+',text)
 need(len(lines)==1,'Exactly one focused geometry record required')
 parts=dict(x.split('=',1)for x in lines[0].split()[1:])
 numeric=('floor','execution_header','execution_construction','frame_operation','category_ceiling_sum','wasi_max','shared','conservative_combined','combined_limit','constructed_current','constructed_peak','resident_current','resident_peak','frame_peak')
 need(set(parts)==set(numeric)|{'tickets'},'Geometry field set')
 values={n:int(parts[n])for n in numeric};tickets=parts['tickets'].split('/')
 need(len(tickets)==2 and all(re.fullmatch(r'\d+',n)for n in tickets),'Geometry ticket shape')
 values['live_tickets'],values['peak_tickets']=map(int,tickets)
 need(all(x>=0 for x in values.values())and values['conservative_combined']<=values['combined_limit']==268435456 and values['peak_tickets']<=86,'Canonical geometry limits')
 need('PLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0'in text,'Consuming geometry cleanup observation missing')
 values['cleanup_zero']=True;values['scope']='compiled named-storage geometry; not RSS, native ABI or whole-reactor acceptance'
 return values

def source_check(source,m):
 expected=set(m['candidateFiles']);actual=set()
 for directory,dirs,files in os.walk(source,followlinks=False):
  for n in dirs:no_symlinks(Path(directory)/n)
  for n in files:
   p=Path(directory)/n;name=p.relative_to(source).as_posix();need(name in expected,'Unbound source member');bound(p,m['candidateFiles'][name]);actual.add(name)
 need(actual==expected,'Source member missing');return CANDIDATE

def cargo_command(c,name,argv,cwd,env,seconds,source,m,focused):
 """Always attempt source postflight; never replace a primary command failure."""
 before=len(c.receipt['commands']);row=None;primary=None;result=None
 try:
  result=c.run(name,argv,cwd,env,seconds=seconds);text,err,row=result
  row['testSummaries']=summary(text,focused=focused)
  if focused:row['geometry']=geometry(text)
 except BaseException as e:primary=e
 finally:
  if row is None and len(c.receipt['commands'])>before and c.receipt['commands'][-1].get('name')==name:row=c.receipt['commands'][-1]
  if row is None:
   row={'name':name};c.receipt.setdefault('unregisteredCargoPostflights',[]).append(row)
  postflight_error=None
  try:
   row['sourceAfter']=source_check(source,m)
   row['sourcePostflight']={'attempted':True,'verified':True,'members':len(m['candidateFiles'])}
  except BaseException as e:
   row['sourcePostflight']={'attempted':True,'verified':False,'error':exception_details(e)};postflight_error=e
  try:c.save()
  except BaseException as e:
   row['sourcePostflightReceiptError']=exception_details(e)
   postflight_error=postflight_error or e
  primary=primary or postflight_error
 if primary is not None:raise primary
 return result

def expand(item,temp):return item.replace('$RUNNER_TEMP',str(temp))
def execute():
 temp=hosted();m,plan,data=inputs()
 out=temp/'swift-pin-bitmap-lifecycle-v2-evidence';no_symlinks(out);need(not out.exists(),'Fresh evidence directory only');out.mkdir()
 receipt={'schema':1,'status':'running','startedUTC':time.time(),'sourceRevision':os.environ['GITHUB_SHA'],'runID':os.environ.get('GITHUB_RUN_ID'),'runAttempt':1,'candidateTreeSHA256':CANDIDATE,'baselineTreeSHA256':BASELINE,'producerSealSHA256':PRODUCER_SEAL,'priorCandidateTreeSHA256':PRIOR_CANDIDATE,'lifecycleSealSHA256':FROZEN_PACKETS[-1][1],'profile':PROFILE,'pythonVersion':sys.version,'platform':platform.platform(),'activeSeconds':ACTIVE_SECONDS,'cleanupSeconds':CLEANUP_SECONDS,'maxCargoCommands':6,'maxVersionCommands':1,'maxWholeReactorAttempts':0,'perStreamOutputCapBytes':8*1024*1024,'commands':[],'errors':[],'sourceReviewIsRuntimeAcceptance':False,'GAQualified':False,'nativeRuns':0,'automaticRetry':False}
 marker={'purpose':'bitmap-lifecycle-host-admission','token':uuid.uuid4().hex};save(out/'ownership.json',marker);out_id=identity(out)
 save(out/'source-manifest.json',{'sourceRevision':receipt['sourceRevision'],'candidateTreeSHA256':CANDIDATE,'files':m['candidateFiles']})
 save(out/'host-plan.json',{'commands':plan})
 for n in ['admit.py','bounded_commands.py']:
  shutil.copyfile(HERE/n,out/('executed-'+n));receipt.setdefault('harnessFiles',{})[n]=sha(HERE/n)
 c=Commands(out,receipt,time.monotonic()+ACTIVE_SECONDS);claimed=[];failure=None
 handlers={s:signal.getsignal(s)for s in (signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
 def alarm(signum,frame):raise TimeoutError('Bounded active/cleanup allowance expired')
 def interrupt(signum,frame):raise KeyboardInterrupt('Signal '+str(signum))
 signal.signal(signal.SIGALRM,alarm);signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGTERM,interrupt);signal.setitimer(signal.ITIMER_REAL,ACTIVE_SECONDS)
 try:
  scratch=out/'scratch';source=temp/'swift-pin-bitmap-v1';target=temp/'swift-pin-bitmap-v1-target'
  for p in [scratch,source,target]:
   no_symlinks(p);need(not p.exists(),'Fresh owned path only: '+str(p));p.mkdir();claimed.append((p,identity(p)))
  c.bind_scratch(scratch);cargo_home=scratch/'cargo-home';cargo_home.mkdir()
  for n,raw in data.items():
   p=source/member(n);p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb')as f:f.write(raw)
  receipt['materializedSource']=source_check(source,m)
  env={'CARGO_HOME':str(cargo_home),'CARGO_TARGET_DIR':str(target),'CARGO_NET_OFFLINE':'true','RUSTUP_TOOLCHAIN':'1.99.0','CARGO_INCREMENTAL':'0','LC_ALL':'C','LANG':'C'}
  text,err,row=c.run('compiler-identity',['rustup','run','1.99.0','rustc','-vV'],source,env,seconds=30)
  need(re.search(r'^release: 1\.99\.0$',text,re.M)and re.search(r'^host: x86_64-unknown-linux-gnu$',text,re.M),'Wrong actual compiler identity')
  receipt['compilerIdentity']=text
  for i,spec in enumerate(plan):
   need(source_check(source,m)==CANDIDATE,'Precommand source mutation')
   argv=[expand(a,temp)for a in spec['argv']];cwd=Path(expand(spec['cwd'],temp))
   need(argv[:4]==['cargo','+1.99.0','test','--manifest-path']and cwd==source,'Fixed Cargo route')
   cargo_command(c,'cargo-'+str(i+1),argv,cwd,env,spec['commandSeconds'],source,m,focused=i==0)
  need(len(receipt['commands'])==7,'Command count');receipt['status']='six-host-regressions-passed'
 except BaseException as e:
  failure=e;receipt['status']='failed';receipt['errors'].append(exception_details(e))
 finally:
  signal.setitimer(signal.ITIMER_REAL,CLEANUP_SECONDS)
  try:
   need(c.active is None and all(r.get('child_returned')and r.get('owned_group_gone')for r in receipt['commands']if 'pid'in r),'Unresolved command custody: preserve owned roots')
   need(identity(out)==out_id and json_data(regular(out/'ownership.json').read_bytes())==marker,'Evidence ownership changed')
   for p,expected in claimed:need(identity(p)==expected,'Owned root identity changed; preserve')
   for p,expected in reversed(claimed):shutil.rmtree(p);need(not p.exists(),'Owned cleanup incomplete')
   receipt['cleanup']={'ownedRootsRemoved':True,'roots':[str(p)for p,_ in claimed],'childReapAndGroupAbsenceVerified':True,'processInventory':False,'otherProjectProcessesTouched':False}
  except BaseException as e:
   receipt['cleanup']={'ownedRootsRemoved':False,'custodyHold':True,'roots':[str(p)for p,_ in claimed]};receipt['errors'].append(exception_details(e));receipt['status']='failed-custody-or-cleanup';failure=failure or e
  finally:
   signal.setitimer(signal.ITIMER_REAL,0)
   for s,h in handlers.items():signal.signal(s,h)
   receipt['finishedUTC']=time.time();save(out/'receipt.json',receipt)
 if failure is not None:raise failure
 return receipt

def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['check','run']);args=parser.parse_args()
 if args.mode=='check':
  m,plan,data=inputs();print(json.dumps({'candidateTreeSHA256':CANDIDATE,'sourceMembers':len(data),'cargoCommands':len(plan),'actualRustRuns':0}));return
 print(json.dumps(execute()))
if __name__=='__main__':main()
