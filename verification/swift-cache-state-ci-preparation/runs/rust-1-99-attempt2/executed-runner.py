#!/usr/bin/env python3
"""Closed exact-source fixture host check; no release or semantic authority."""
import argparse
from datetime import datetime,timezone
import gzip,hashlib,json,os,platform,re,selectors,shutil,signal,stat,subprocess,sys,time,uuid
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PACK=HERE/'pack'
RUNS=HERE/'runs'
MANIFEST_SHA256='6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'
SOURCE_SHA256='f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b'
ACTIVE_SECONDS=600
CLEANUP_SECONDS=60
CHILD_SECONDS=60
OUTPUT_CAP=8*1024*1024
APPEND=b'\n#[cfg(test)]\n#[path = "../selected_controls.rs"]\nmod selected_scalar_controls;\n\n#[cfg(test)]\n#[path = "../scalar_cursor_independent.rs"]\nmod scalar_cursor_independent;\n'
FLAGS={'storedPrefixValidated':False,'fullReplayAccepted':False,'semanticMetricsValid':False,'GA_qualified':False,'model_imported_or_evaluated':False}

def need(value,message):
 if not value:raise RuntimeError(message)
def now():return datetime.now(timezone.utc).isoformat()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(path,value):
 q=path.with_name(path.name+'.partial');q.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');os.replace(q,path)
def unique(pairs):
 d={}
 for k,v in pairs:need(k not in d,'Duplicate JSON key');d[k]=v
 return d
def json_data(data):return json.loads(data,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in()).throw(RuntimeError('Nonfinite JSON')))
def member(name):
 need(isinstance(name,str),'Member must be text');p=PurePosixPath(name)
 need(name and name==str(p)and name!='.'and not p.is_absolute()and not any(v in p.parts for v in ['..','.git'])and '\\'not in name and '\x00'not in name,'Noncanonical member path')
 return Path(name)
def no_symlinks(path):
 need(path.is_absolute(),'Absolute path required')
 for p in [*reversed(path.parents),path]:need(not p.is_symlink(),'Symlink forbidden: '+str(p))
def regular(path):
 no_symlinks(path);need(stat.S_ISREG(path.stat().st_mode),'Regular file required');return path
def inventory(base):
 no_symlinks(base);need(stat.S_ISDIR(base.stat().st_mode),'Directory required');rows=[]
 for directory,dirs,files in os.walk(base,followlinks=False):
  for n in sorted(dirs+files):
   p=Path(directory)/n;name=p.relative_to(base).as_posix();member(name);mode=p.lstat().st_mode
   need(stat.S_ISDIR(mode)or stat.S_ISREG(mode),'Nonregular/symlink member')
   if stat.S_ISREG(mode):rows.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)})
 return sorted(rows,key=lambda r:r['path'])
def tree(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verify_pack(base):
 need(sha(regular(base/'manifest.json'))==MANIFEST_SHA256,'Pinned pack manifest differs')
 m=json_data((base/'manifest.json').read_bytes());rows=m['members']
 need(len(rows)==len({r['path']for r in rows})==m['member_count'],'Pack member count')
 need(sum(r['bytes']for r in rows)==m['total_bytes']and tree(rows)==m['tree_sha256'],'Pack digest/count')
 need([r for r in inventory(base)if r['path']!='manifest.json']==rows,'Missing/extra/mutated pack member')
 bindings=json_data((base/'inventories/bindings.json').read_bytes())
 need(bindings['library_sha256']['cache_state.rs']==SOURCE_SHA256,'Selected source hash')
 for n,h in bindings['library_sha256'].items():need(sha(regular(base/'source/library'/n))==h,'Library source differs')
 return m

def identity(path):
 no_symlinks(path);s=path.stat();need(stat.S_ISDIR(s.st_mode)and s.st_uid==os.geteuid(),'Owned directory required');return [s.st_dev,s.st_ino,s.st_uid]
def fresh_output(path):
 need('..'not in path.parts and '.git'not in path.parts,'Output traversal')
 out=Path(os.path.abspath(path));no_symlinks(out)
 need(out.parent==RUNS and out.parent.is_dir()and not out.exists(),'Output must be fresh directly under fixed runs directory')
 out.mkdir();save(out/'ownership.json',{'purpose':'mixer-cache-state-fixture-ci-output','token':uuid.uuid4().hex});return out

def environment(overrides):
 # Direct rustc ignores Cargo, but no inherited compiler/test hook may alter the
 # fixed closure. Toolchain launcher selection remains explicit --rustc input.
 blocked={'RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTC','RUSTDOCFLAGS','TMPDIR','TMP','TEMP'}
 env={k:v for k,v in os.environ.items()if k not in blocked and not k.startswith('RUST_')and not k.startswith('RUSTC_')and not k.startswith('MIXER_')and k not in {'REVIEW_SCRATCH'}}
 env.update(overrides);env['RUSTUP_AUTO_INSTALL']='0';return env

class Commands:
 def __init__(self,out,receipt,deadline):
  self.out,self.receipt,self.deadline=out,receipt,deadline;self.active=None;(out/'commands').mkdir()
 def save(self):save(self.out/'receipt.json',self.receipt)
 def gone(self,pid):
  try:os.killpg(pid,0);return False
  except ProcessLookupError:return True
 def stop(self,proc,row):
  if not self.gone(proc.pid):
   try:os.killpg(proc.pid,signal.SIGKILL);row['owned_group_killed']=True
   except ProcessLookupError:pass
  proc.wait(timeout=5);row['child_returned']=True
  until=time.monotonic()+5
  while not self.gone(proc.pid)and time.monotonic()<until:time.sleep(.01)
  row['owned_group_gone']=self.gone(proc.pid)
 def run(self,name,argv,cwd,env=None,negative=False):
  need(self.active is None,'One child group only');need(re.fullmatch('[A-Za-z0-9_-]+',name),'Command name')
  start=time.monotonic();budget=min(CHILD_SECONDS,self.deadline-start);need(budget>0,'Active deadline exhausted')
  row={'name':name,'argv':list(map(str,argv)),'cwd':str(cwd),'started_utc':now(),'per_child_limit_seconds':CHILD_SECONDS,'effective_timeout_seconds':budget,'per_stream_cap_bytes':OUTPUT_CAP,'environment_overrides':env or {},'exit':None,'timed_out':False,'output_capped':False,'child_returned':False}
  self.receipt['commands'].append(row);self.save();paths=[self.out/'commands'/(name+'.'+suffix)for suffix in ['stdout','stderr']]
  selector=selectors.DefaultSelector();failure=None
  try:
   self.active=subprocess.Popen(row['argv'],cwd=cwd,env=environment(env or {}),stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
   proc=self.active;row.update(pid=proc.pid,pgid=proc.pid,new_session=True)
   for pipe,path in zip([proc.stdout,proc.stderr],paths):selector.register(pipe,selectors.EVENT_READ,{'file':path.open('xb'),'count':0})
   while selector.get_map()or proc.poll()is None:
    if time.monotonic()-start>=budget:row['timed_out']=True;failure='timeout'
    if failure:self.stop(proc,row)
    for key,_ in selector.select(.02):
     b=os.read(key.fileobj.fileno(),65536)
     if not b:key.data['file'].close();selector.unregister(key.fileobj);key.fileobj.close();continue
     space=OUTPUT_CAP-key.data['count'];key.data['file'].write(b[:space]);key.data['count']+=min(space,len(b))
     if len(b)>space:row['output_capped']=True;failure='output-cap'
   proc.wait(timeout=5);row['child_returned']=True;row['exit']=proc.returncode
   if not self.gone(proc.pid):row['descendants_outlived_child']=True
  except OSError as e:row['spawn_error']=str(e)
  finally:
   for key in list(selector.get_map().values()):key.data['file'].close();key.fileobj.close()
   selector.close()
   if self.active is not None:self.stop(self.active,row);row['exit']=self.active.returncode
   self.active=None
   for p in paths:
    if not p.exists():p.write_bytes(b'')
   row.update(elapsed_seconds=round(time.monotonic()-start,6),finished_utc=now(),stdout_sha256=sha(paths[0]),stderr_sha256=sha(paths[1]));self.save();save(self.out/'commands'/(name+'.json'),row)
  need(row['child_returned']and row.get('owned_group_gone')and not row.get('descendants_outlived_child')and not row['timed_out']and not row['output_capped']and row['exit']==(1 if negative else 0),'Command failed; retained receipt: '+name)
  return paths[0].read_text(),paths[1].read_text(),row

def rust_identity(text):
 lines=text.splitlines();need(lines,'Missing compiler identity');m=re.fullmatch(r'rustc (\d+\.\d+\.\d+) \(([0-9a-f]{7,40}) (\d{4}-\d{2}-\d{2})\)',lines[0]);need(m is not None,'Stable rustc header required')
 d={}
 for line in lines[1:]:
  k,sep,v=line.partition(': ');need(sep and k not in d and v==v.strip()and v,'Malformed compiler identity');d[k]=v
 need(set(d)=={'binary','commit-hash','commit-date','host','release','LLVM version'},'Incomplete compiler fields')
 release,commit,date=m.groups();datetime.strptime(date,'%Y-%m-%d')
 need(d['binary']=='rustc'and d['release']==release and re.fullmatch('[0-9a-f]{40}',d['commit-hash'])and d['commit-hash'].startswith(commit)and d['commit-date']==date,'Incoherent compiler identity')
 need((d['host'],release)in {('aarch64-apple-darwin','1.99.0'),('aarch64-apple-darwin','1.98.1')},'Actual compiler host/release not selected')
 need(re.fullmatch(r'\d+\.\d+\.\d+',d['LLVM version']),'Invalid LLVM version');return d

def verify_methods(text,expected,executed=False,filtered=0):
 need(len(expected)==len(set(expected)),'Expected methods duplicate')
 if executed:
  names=re.findall(r'^test (\S+) \.\.\. ',text,re.M)
  summaries=re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out; finished in [^\n]+$',text,re.M)
  need(summaries==[(str(len(expected)),'0','0','0',str(filtered))],'Incomplete/ignored/failed execution')
  need(len(re.findall(r'(?:^|\n)ok$| \.\.\. ok$',text,re.M))==len(expected),'Missing terminal method ok')
 else:
  names=[l[:-6]for l in text.splitlines()if l.endswith(': test')]
  need(re.findall(r'^(\d+) tests, (\d+) benchmarks$',text,re.M)==[(str(len(expected)),'0')],'List summary differs')
 need(len(names)==len(set(names))==len(expected)and set(names)==set(expected),'Exact method inventory differs');return sorted(names)

def verify_layouts(text,expected):
 rows=[{'type':n,'bytes':int(b),'align':int(a)}for n,b,a in re.findall(r'ACCOUNTING_LAYOUT (.+?) size=(\d+) align=(\d+)',text)]
 need(rows==expected['layouts']and len(rows)==expected['count']==23,'Complete accounting layouts differ');return rows

def verify_negative(probe,stderr,base,target,row):
 source=regular(base/member(probe['source']));data=source.read_bytes()
 need(len(data)==probe['bytes']and sha(source)==probe['sha256'],'API source identity differs')
 need(row['exit']==1 and not target.exists(),'Negative API must exit1 and emit no executable')
 expected={(x['byte_start'],x['byte_end'])for x in probe['primary_spans']}
 for span in probe['primary_spans']:need(data[span['byte_start']:span['byte_end']]==span['text'].encode(),'Expected API span bytes differ')
 pending=[json_data(line)for line in stderr.splitlines()if line.strip()];seen=set();matches=[]
 while pending:
  d=pending.pop(0);need(isinstance(d,dict),'Malformed diagnostic');children=d.get('children',[]);need(isinstance(children,list),'Malformed diagnostic children');pending.extend(children)
  need(isinstance(d.get('level'),str)and isinstance(d.get('message'),str),'Malformed diagnostic fields')
  if d['level']!='error':continue
  code=d.get('code')
  if code is None:need(re.fullmatch(r'aborting due to \d+ previous errors?(?:; \d+ warnings? emitted)?',d['message'])is not None,'Unclassified compiler error');continue
  need(isinstance(code,dict)and code.get('code')==probe['code']and all(t in d['message']for t in probe['message_contains']),'Unexpected API error/code/message')
  spans=d.get('spans');need(isinstance(spans,list),'Missing API spans');primary=[]
  for s in spans:
   need(isinstance(s,dict)and type(s.get('is_primary'))is bool and isinstance(s.get('file_name'),str)and type(s.get('byte_start'))is int and type(s.get('byte_end'))is int,'Malformed source span')
   start,end=s['byte_start'],s['byte_end'];need(0<=start<=end,'Invalid source span')
   if s['file_name']==probe['source']:need(end<=len(data),'Source span out of bounds')
   if s['is_primary']:
    need(s['file_name']==probe['source']and(start,end)in expected and(start,end)not in seen,'Wrong/duplicate primary API span');seen.add((start,end));primary.append(s)
  need(primary,'Required primary API error absent');matches.append({'code':probe['code'],'message':d['message'],'primary':primary})
 need(seen==expected and matches,'Complete primary API target coverage absent');return matches

def verify_cases(base,expected):
 need(base.is_dir(),'Case capture missing');need(sorted(p.name for p in base.iterdir())==sorted(c['case']for c in expected['cases']),'Exact captured case inventory differs')
 rows=[]
 for c in expected['cases']:
  q=base/member(c['case']);need(sorted(p.name for p in q.iterdir())==['input-0.bin','input-1.bin','input-2.bin','report.bin','result.txt'],'Case files differ')
  for n,r in c['raw'].items():p=regular(q/member(n));need(p.stat().st_size==r['bytes']and sha(p)==r['sha256'],'Captured File bytes differ '+c['case']+'/'+n)
  text=regular(q/'result.txt').read_text();lines=text.splitlines();need(len(lines)==2 and lines[0]==c['result_first_line']and lines[1].startswith('input_stamps_before_and_after=['),'Exact complete File result differs')
  # The complete first line binds every aggregate/error field; the 32-value
  # projection inventory remains explicit and cannot replace the complete result.
  rows.append({'case':c['case'],'scope':c['scope'],'complete32':c['actual_complete32'],'aggregate_present':c['aggregate_present'],'result_first_line_sha256':hashlib.sha256(lines[0].encode()).hexdigest(),'capture_tree_sha256':tree(inventory(q))})
 need(len(rows)==31 and sum(r['aggregate_present']for r in rows)==29,'Case disposition totals differ');return rows

def cleanup(out,scratch,scratch_id,marker,products,commands):
 need(commands.active is None and all(r.get('owned_group_gone')for r in commands.receipt['commands']if 'pid'in r),'Owned groups pending')
 need(identity(scratch)==scratch_id and json_data(regular(scratch/'ownership.json').read_bytes())==marker,'Scratch identity changed; preserve')
 rows=inventory(scratch);content=out/'content';content.mkdir();retained=[];compiler=[]
 for r in rows:
  p=scratch/member(r['path'])
  if r['path']in products:compiler.append(r);continue
  if r['path']=='ownership.json':continue
  compressed=r['bytes']>16*1024*1024;q=content/(r['sha256']+('.gz'if compressed else'.bin'))
  if not q.exists():
   with p.open('rb')as f,q.open('xb')as g:
    if compressed:
     with gzip.GzipFile(filename='',mode='wb',fileobj=g,mtime=0)as z:shutil.copyfileobj(f,z,1024*1024)
    else:shutil.copyfileobj(f,g,1024*1024)
  h=hashlib.sha256();n=0
  with (gzip.open(q,'rb')if compressed else q.open('rb'))as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b);n+=len(b)
  need(n==r['bytes']and h.hexdigest()==r['sha256'],'Retained bytes differ')
  retained.append(r|{'content':str(q.relative_to(out)),'encoding':'gzip'if compressed else'identity','retained_sha256':sha(q)})
 save(out/'retention.json',{'files':retained,'compiler_products_hashed_before_removal':compiler})
 need(identity(scratch)==scratch_id and json_data((scratch/'ownership.json').read_bytes())==marker and inventory(scratch)==rows,'Scratch changed during retention; preserve')
 shutil.rmtree(scratch);need(not scratch.exists(),'Owned scratch removal incomplete');return {'removed':True,'identity':scratch_id,'marker':marker,'files_hashed_before_removal':len(rows),'products_hashed_before_removal':compiler,'groups_returned':True,'other_project_or_native_discovery':False}

def execute(out,requested):
 start=time.monotonic();runner=Path(__file__).resolve();python=Path(sys.executable).resolve(strict=True)
 receipt={'schema':1,'status':'running','started_utc':now(),'argv':sys.argv,**FLAGS,'active_deadline_seconds':ACTIVE_SECONDS,'cleanup_allowance_seconds':CLEANUP_SECONDS,'per_child_seconds':CHILD_SECONDS,'os':platform.platform(),'machine':platform.machine(),'runner':{'path':str(runner),'sha256':sha(runner)},'python':{'launcher':sys.executable,'resolved':str(python),'sha256':sha(python),'version':sys.version},'commands':[],'errors':[],'limits':['quiescent trusted checkout; no adversarial custody claim','finite exact-source host fixture checks only; no release/target/native/GA authority'],'original_full_Debug_timeout_remains_failed':True,'performance_equivalence_claimed':False}
 c=Commands(out,receipt,start+ACTIVE_SECONDS);scratch=None;compiler=None;products=set();handlers={s:signal.getsignal(s)for s in [signal.SIGALRM,signal.SIGINT,signal.SIGTERM]}
 def alarm(signum,frame):raise TimeoutError('Fixed overall deadline exhausted')
 def interrupt(signum,frame):raise KeyboardInterrupt('Signal '+str(signum))
 signal.signal(signal.SIGALRM,alarm);signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGTERM,interrupt);signal.setitimer(signal.ITIMER_REAL,ACTIVE_SECONDS)
 try:
  shutil.copyfile(runner,out/'executed-runner.py');receipt['output_ownership']={'identity':identity(out),'marker':json_data((out/'ownership.json').read_bytes())}
  manifest=verify_pack(PACK);receipt['pack_manifest_sha256']=MANIFEST_SHA256;receipt['pack_tree_sha256']=manifest['tree_sha256']
  snapshot=out/'pack';shutil.copytree(PACK,snapshot);verify_pack(snapshot)
  scratch=out/'scratch';scratch.mkdir();scratch_id=identity(scratch);marker={'purpose':'mixer-cache-state-fixture-ci-scratch','token':uuid.uuid4().hex};save(scratch/'ownership.json',marker)
  found=shutil.which(str(requested));need(found is not None,'Compiler launcher missing');launcher=Path(os.path.abspath(found));launcher_target=launcher.resolve(strict=True);need(launcher_target.is_file(),'Compiler launcher target required')
  launcher_hash=sha(launcher_target)
  sysroot=c.run('compiler-sysroot',[launcher,'--print','sysroot'],out)[0].strip();need(Path(sysroot).is_absolute()and '\n'not in sysroot,'Invalid compiler sysroot')
  compiler=regular((Path(sysroot)/'bin/rustc').resolve(strict=True));compiler_hash=sha(compiler)
  verbose=c.run('compiler-identity',[compiler,'--version','--verbose'],out)[0];selected=rust_identity(verbose)
  receipt['rustc']={'requested':str(requested),'launcher':str(launcher),'launcher_target':str(launcher_target),'launcher_sha256':launcher_hash,'path':str(compiler),'sha256':compiler_hash,'sysroot':sysroot,'version_verbose':verbose,'identity':selected};c.save()
  receipt['source_revision']=c.run('source-revision',['git','rev-parse','HEAD'],ROOT)[0].strip();receipt['source_tree']=c.run('source-tree',['git','rev-parse','HEAD^{tree}'],ROOT)[0].strip()
  expected=json_data((snapshot/'inventories/methods.json').read_bytes());layouts=json_data((snapshot/'inventories/layouts.json').read_bytes());cases=json_data((snapshot/'inventories/file-cases.json').read_bytes());api=json_data((snapshot/'inventories/api-contract.json').read_bytes());markers=json_data((snapshot/'inventories/control-markers.json').read_bytes())
  derived=scratch/'derived';shutil.copytree(snapshot/'source',derived)
  cp=derived/'library/cache_state.rs';cp.write_bytes(cp.read_bytes()+APPEND)
  for src in ['selected_controls.rs','scalar_cursor_independent.rs']:shutil.copyfile(snapshot/'controls'/src,derived/src)
  receipt['derivative']={'base_sha256':SOURCE_SHA256,'append_utf8':APPEND.decode(),'derived_sha256':sha(cp),'base_prefix_verified':cp.read_bytes()==(snapshot/'source/library/cache_state.rs').read_bytes()+APPEND}
  receipt['modes']={}
  for mode,opts in [('debug',[]),('optimized',['-O'])]:
   mode_row={'methods':{},'api':[]};receipt['modes'][mode]=mode_row
   for lane,source,cfg in [('host','source/library/analyzer.rs',[]),('producer','source/regression/independent_tests.rs',['--cfg','inherited_transport']),('independent','source/library/analyzer.rs',['--cfg','inherited_review']),('controls',str(derived/'library/analyzer.rs'),[])]:
    binary=scratch/(lane+'-'+mode);products.add(binary.relative_to(scratch).as_posix())
    c.run(lane+'-'+mode+'-compile',[compiler,'--edition=2021','--test',*cfg,*opts,source,'-o',binary],snapshot)
    listing=c.run(lane+'-'+mode+'-list',[binary,'--list'],snapshot)[0];verify_methods(listing,expected[lane])
    groups=expected['producer_debug_partition']if lane=='producer'and mode=='debug'else[{'name':'all','args':[],'methods':expected[lane]}];observed=[]
    for group in groups:
     work=scratch/(lane+'-'+mode+'-'+group['name']);work.mkdir();temp=work/'tmp';temp.mkdir();capture=work/'cases'
     env={'TMPDIR':str(temp),'TMP':str(temp),'TEMP':str(temp),'MIXER_ANALYZER_LIBRARY_TEST_SCRATCH':str(work),'MIXER_ENVELOPE_SCRATCH':str(work),'MIXER_REVIEW_SCRATCH':str(work),'REVIEW_SCRATCH':str(work),'MIXER_ANALYZER_LIBRARY_HISTORICAL':str(snapshot/'inputs/historical')}
     if lane in ['host','controls']:env['MIXER_CACHE_FIXTURE_EVIDENCE']=str(capture)
     text=c.run(lane+'-'+mode+'-'+group['name'],[binary,*group['args'],'--test-threads=1','--nocapture'],snapshot,env)[0]
     observed.extend(verify_methods(text,group['methods'],True,len(expected[lane])-len(group['methods'])))
     if lane in ['host','controls']:
      mode_row[lane+'_layouts']=verify_layouts(text,layouts);mode_row[lane+'_File_cases']=verify_cases(capture,cases)
     if lane=='controls':
      for k,v in markers.items():need(re.findall(re.escape(k)+r'=([^\n]+)',text)==[v],'Control finite/layout marker differs: '+k)
    need(sorted(observed)==sorted(expected[lane])and len(observed)==len(set(observed)),'Group closure coverage differs')
    mode_row['methods'][lane]={'names':sorted(observed),'count':len(observed),'binary_sha256':sha(binary),'complete_disjoint_coverage':True}
   library=scratch/('libcache_fixture-'+mode+'.rlib');products.add(library.name);c.run('library-'+mode,[compiler,'--edition=2021',*opts,'--crate-type=lib','--crate-name','cache_fixture','source/library/analyzer.rs','-o',library],snapshot)
   for probe in api['probes']:
    name=probe['name'];command_name=name.replace('/','_');target=scratch/('api-'+command_name+'-'+mode);products.add(target.name)
    need(sha(snapshot/member(probe['source']))==probe['sha256'],'API probe identity')
    _,stderr,row=c.run('api-'+command_name+'-'+mode,[compiler,'--edition=2021',*opts,'--extern',probe['crate_alias']+'='+str(library),'--error-format=json',probe['source'],'-o',target],snapshot,negative=not probe['expected_success'])
    observed={'name':name,'expected_success':probe['expected_success'],'compile_exit':row['exit']}
    if probe['expected_success']:
     observed['binary_sha256']=sha(regular(target));c.run('api-'+command_name+'-'+mode+'-execute',[target],snapshot);observed['executed']=True
    else:observed['diagnostics']=verify_negative(probe,stderr,snapshot,target,row)
    mode_row['api'].append(observed)
   need(len(mode_row['api'])==25 and sum(r['expected_success']for r in mode_row['api'])==2,'API complete disposition count');c.save()
  receipt['source_revision_after']=c.run('source-revision-after',['git','rev-parse','HEAD'],ROOT)[0].strip();receipt['source_tree_after']=c.run('source-tree-after',['git','rev-parse','HEAD^{tree}'],ROOT)[0].strip()
  need(receipt['source_revision']==receipt['source_revision_after']and receipt['source_tree']==receipt['source_tree_after'],'Checkout revision changed')
  receipt['active_checks_completed']=True
 except BaseException as e:receipt['errors'].append({'phase':'active','type':type(e).__name__,'message':str(e)})
 finally:
  signal.setitimer(signal.ITIMER_REAL,CLEANUP_SECONDS);receipt['active_elapsed_seconds']=round(time.monotonic()-start,6);c.save();post={}
  def check(name,fn):
   try:post[name]={'passed':True,'observed':fn()}
   except BaseException as e:post[name]={'passed':False,'error':str(e)};receipt['errors'].append({'phase':'postflight-'+name,'type':type(e).__name__,'message':str(e)})
  def same(p,h):need(sha(regular(p))==h,'Identity changed');return h
  check('pack',lambda:verify_pack(PACK)['tree_sha256'])
  if (out/'pack').exists():check('snapshot',lambda:verify_pack(out/'pack')['tree_sha256'])
  check('runner',lambda:same(runner,receipt['runner']['sha256']))
  if (out/'executed-runner.py').exists():check('runner-snapshot',lambda:same(out/'executed-runner.py',receipt['runner']['sha256']))
  def python_check():need(Path(sys.executable).resolve(strict=True)==python,'Interpreter launcher changed');return same(python,receipt['python']['sha256'])
  check('python',python_check)
  if compiler is not None:
   check('compiler',lambda:same(compiler,compiler_hash))
   def launch_check():need(launcher.resolve(strict=True)==launcher_target,'Compiler launcher changed');return same(launcher_target,launcher_hash)
   check('launcher',launch_check)
  receipt['postflight']=post
  try:
   if scratch is not None:receipt['cleanup']=cleanup(out,scratch,scratch_id,marker,products,c)
   else:receipt['cleanup']={'scratch_created':False}
  except BaseException as e:receipt['errors'].append({'phase':'cleanup','type':type(e).__name__,'message':str(e)});receipt['cleanup']={'removed':False,'recoverable_scratch':str(scratch)}
  signal.setitimer(signal.ITIMER_REAL,0)
  for s,h in handlers.items():signal.signal(s,h)
  receipt.update(finished_utc=now(),elapsed_seconds=round(time.monotonic()-start,6),status='passed-host-fixture-check'if receipt.get('active_checks_completed')and not receipt['errors']else'failed');c.save()
 print(json.dumps({'status':receipt['status'],'receipt':str(out/'receipt.json'),'errors':receipt['errors']}));return 0 if receipt['status']=='passed-host-fixture-check'else 1

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--rustc',required=True);args=p.parse_args()
 try:out=fresh_output(args.out)
 except (RuntimeError,OSError)as e:print('Output refused: '+str(e),file=sys.stderr);return 1
 return execute(out,args.rustc)
if __name__=='__main__':sys.exit(main())
