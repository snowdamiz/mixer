#!/usr/bin/env python3
"""Authored adapter of reviewed Commands: no local run is implied."""
from datetime import datetime,timezone
import hashlib,json,os,re,resource,selectors,signal,stat,subprocess,time
from pathlib import Path,PurePosixPath
OUTPUT_CAP=8*1024*1024
CHILD_SECONDS=600
MAX_COMMANDS=7
def need(value,message):
 if not value:raise RuntimeError(message)
def now():return datetime.now(timezone.utc).isoformat()
def exception_details(error):
 result={'type':type(error).__name__,'message':str(error)}
 if isinstance(error,OSError):result['errno']=error.errno
 return result
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
def identity(path):
 no_symlinks(path);s=path.stat();need(stat.S_ISDIR(s.st_mode)and s.st_uid==os.geteuid(),'Owned directory required');return [s.st_dev,s.st_ino,s.st_uid]

def environment(overrides):
 # Cargo has more configuration hooks than the reference direct-rustc driver.
 # Allow only launcher selection, locale and explicit per-command overrides.
 keep={'HOME','PATH','RUSTUP_HOME','LANG','LC_ALL'}
 env={k:v for k,v in os.environ.items()if k in keep}
 env.update(overrides);env['RUSTUP_AUTO_INSTALL']='0'
 return env
def context_phase_progress(stderr):return []
def child_usage():
 usage=resource.getrusage(resource.RUSAGE_CHILDREN)
 return {name:getattr(usage,name)for name in ['ru_utime','ru_stime','ru_minflt','ru_majflt']}
def child_accounting(before,after,terminal):
 # Sequential trusted runner: these are aggregate reaped-child counters, never
 # process-isolated measurements. A hold/reap failure suppresses all deltas.
 result={'scope':'reaped-child aggregate in a sequential trusted runner; not isolated process accounting','before':before,'after':after,'terminal_facts_verified':terminal,'aggregate_delta':None}
 if terminal:
  need(before is not None and after is not None and set(before)==set(after),'Missing child resource snapshots')
  delta={k:after[k]-before[k]for k in before};need(all(v>=0 for v in delta.values()),'Child aggregate counters regressed');result['aggregate_delta']=delta
 else:result['unavailable_reason']='spawn absent, child reap failure or owned-group custody hold; aggregate delta withheld'
 return result

class Commands:
 def __init__(self,out,receipt,deadline):
  self.out,self.receipt,self.deadline=out,receipt,deadline;self.active=None;self.scratch=None;(out/'commands').mkdir()
 def bind_scratch(self,scratch):
  need(self.scratch is None and scratch.is_absolute()and '..'not in scratch.parts and scratch.parent==self.out,'Fresh canonical owned child scratch required')
  self.scratch=scratch;self.scratch_identity=identity(scratch);self.child_tmp=scratch/'command-tmp';self.child_tmp.mkdir();identity(self.child_tmp)
 def child_environment(self,overrides):
  need(self.scratch is not None and identity(self.scratch)==self.scratch_identity,'Owned child scratch is not bound')
  env={k:str(self.child_tmp)for k in ['TMPDIR','TMP','TEMP']};env.update(overrides or {})
  need(len({env[k]for k in ['TMPDIR','TMP','TEMP']})==1,'Child temporary directories must agree')
  temp=Path(env['TMPDIR']);need(temp.is_absolute()and '..'not in temp.parts and temp.is_relative_to(self.scratch),'Child temporary directory outside canonical owned scratch');identity(temp)
  return env
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
 def run(self,name,argv,cwd,env=None,negative=False,seconds=60):
  need(self.active is None,'One child group only');need(re.fullmatch('[A-Za-z0-9_-]+',name),'Command name')
  need(len(self.receipt['commands'])<MAX_COMMANDS,'Command count cap');need(type(seconds)is int and seconds in (30,180,300,600),'Fixed child limit required')
  start=time.monotonic();need(start+seconds+20<self.deadline,'Complete next command does not fit aggregate budget');budget=seconds;env=self.child_environment(env)
  row={'name':name,'argv':list(map(str,argv)),'cwd':str(cwd),'started_utc':now(),'per_child_limit_seconds':seconds,'effective_timeout_seconds':budget,'per_stream_cap_bytes':OUTPUT_CAP,'environment_overrides':env or {},'exit':None,'timed_out':False,'output_capped':False,'child_returned':False,'owned_group_gone':False,'errors':[]}
  self.receipt['commands'].append(row);self.save();paths=[self.out/'commands'/(name+'.'+suffix)for suffix in ['stdout','stderr']]
  selector=selectors.DefaultSelector();failure=None;primary=None;cleanup_errors=[];usage_before=None
  def cleanup_error(phase,error):
   cleanup_errors.append(error);row['errors'].append({'phase':phase,**exception_details(error)})
  try:
   usage_before=child_usage()
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
  except BaseException as e:
   primary=e;row['errors'].append({'phase':'spawn'if self.active is None else'active',**exception_details(e)})
   if isinstance(e,OSError)and self.active is None:row['spawn_error']=str(e)
  finally:
   for key in list(selector.get_map().values()):
    for stream in [key.data['file'],key.fileobj]:
     try:stream.close()
     except BaseException as e:cleanup_error('close-stream',e)
   try:selector.close()
   except BaseException as e:cleanup_error('close-selector',e)
   if self.active is not None:
    try:self.stop(self.active,row);row['exit']=self.active.returncode
    except BaseException as e:
     cleanup_error('stop-owned-group',e);row['owned_group_gone_before_cleanup_error']=row['owned_group_gone'];row['owned_group_gone']=False
    # Keep custody if stop did not positively establish both terminal facts.
    if row['child_returned']and row['owned_group_gone']:self.active=None
   row['custody_hold']=self.active is not None
   try:row['child_resource_usage']=child_accounting(usage_before,child_usage(),row['child_returned']and row['owned_group_gone']and not row['custody_hold'])
   except BaseException as e:cleanup_error('child-resource-accounting',e)
   for p in paths:
    try:
     if not p.exists():p.write_bytes(b'')
     row[p.suffix[1:]+'_sha256']=sha(p)
    except BaseException as e:cleanup_error('retain-'+p.suffix[1:],e)
   try:row['context_phase_progress']=context_phase_progress(paths[1].read_text())
   except BaseException as e:cleanup_error('parse-context-progress',e)
   row.update(elapsed_seconds=round(time.monotonic()-start,6),finished_utc=now())
   try:self.save()
   except BaseException as e:cleanup_error('save-receipt',e)
   try:save(self.out/'commands'/(name+'.json'),row)
   except BaseException as e:cleanup_error('save-command-receipt',e)
  if primary is not None:raise primary
  if cleanup_errors:raise cleanup_errors[0]
  need(row['child_returned']and row.get('owned_group_gone')and not row.get('descendants_outlived_child')and not row['timed_out']and not row['output_capped']and row['exit']==(1 if negative else 0),'Command failed; retained receipt: '+name)
  return paths[0].read_text(),paths[1].read_text(),row

