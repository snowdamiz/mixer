"""Bounded ordinary-host original behavior/alias/source receipt join; no execution."""
from pathlib import Path
import copy, hashlib, json
from classfile import parse
BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[3]
RUN=REPO/'verification/android-editor-membership-compiled-boundary-qualification/state-qualification/full-candidate-v1/run-33'
RELEASE=REPO/'verification/android-editor-boundary-root-review/original98-alias-authority-release.json'
RELEASE_SHA='310c58cdd9af4ee9f9a326bce6a6f6b88d66c0de44fa65439d0fd437619e7055'
SEAL_SHA='8d51b0e6d04b152621e9e6f9ad3b6c46b3301853ed5d0c545fd4781a66c36c6d'

def need(condition,message):
 if not condition:raise ValueError(message)
def ident(path):
 data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def same(a,b):
 if type(a)is not type(b):return False
 if type(a)is dict:return a.keys()==b.keys()and all(same(a[k],b[k])for k in a)
 if type(a)is list:return len(a)==len(b)and all(same(x,y)for x,y in zip(a,b))
 return a==b

def load_inputs():
 need(ident(RELEASE)['sha256']==RELEASE_SHA,'root-released exact authority roster')
 release=json.loads(RELEASE.read_bytes());need(len(release['members'])==4,'exact four authority files')
 documents={}
 for member in release['members']:
  path=REPO/member['path'];need(ident(path)=={k:member[k]for k in('bytes','sha256')},'authority file hash '+member['path']);documents[member['path']]=json.loads(path.read_bytes())
 sealpath=release['members'][0]['path'];need(release['members'][0]['sha256']==SEAL_SHA,'selected original review seal')
 return {'release':release,'documents':documents,'sealpath':sealpath,'roster':json.loads((RUN/'selected-original-behavior-roster.json').read_bytes()),'commands':json.loads((RUN/'commands.json').read_bytes()),'source_freeze':json.loads((RUN/'source-freeze.json').read_bytes()),'class_map':json.loads((RUN/'class-map.json').read_bytes()),'focus_map':json.loads((RUN/'frozen-focus/class-map.json').read_bytes()),'receipt':json.loads((RUN/'receipt.json').read_bytes())}

def command_pass(command,historical):
 need(type(command['exit'])is int and command['exit']==0,'exact successful exit')
 need(command['timed_out'if historical else'timeout']is False and command['reaped']is True,'bounded child timeout/reap')
 need(type(command['timeout_seconds'])is int and command['timeout_seconds']==60,'literal60-second child bound')

def invocation(command,case):
 argv=command['argv'];need(type(argv)is list and all(type(x)is str for x in argv),'string argv')
 need(argv.count(case['class'])==1,'one exact Java main class');at=argv.index(case['class']);need('-ea'in argv[:at]and'-cp'in argv[:at],'original assertions and explicit classpath')
 args=argv[at+1:];need(len(args)==len(case['args']),'original argument count')
 for expected,actual in zip(case['args'],args):
  need(type(expected)is str,'original string args')
  if expected=='<descriptor>':need(Path(actual).is_absolute()and Path(actual).name=='descriptor.json','explicit descriptor argument location')
  else:need(actual==expected,'exact original scenario argument')
 return argv,at,args

def validate(data):
 roster=data['roster'];cases=roster['cases'];need(type(cases)is list and len(cases)==98 and type(roster['unique_behavior_invocations'])is int and roster['unique_behavior_invocations']==98,'complete98 original invocation roster')
 need(type(roster['historical_passed_aliases'])is int and roster['historical_passed_aliases']==99 and roster['source_rewrite']is False,'literal99 aliases and no source rewrite')
 release=data['release'];documents=data['documents'];oldseal=documents[data['sealpath']];need(same(roster['selected_review_seal'],{k:release['members'][0][k]for k in('bytes','sha256')}),'roster selected authority seal identity')
 seal_members={m['path']:m for m in oldseal['members']};reviewroot=Path(data['sealpath']).parent
 oldcommands={}
 for member in release['members'][1:]:
  relative=str(Path(member['path']).relative_to(reviewroot));need(same({k:seal_members[relative][k]for k in('bytes','sha256')},{k:member[k]for k in('bytes','sha256')}),'historical command roster is member of selected seal')
  oldcommands[member['path']]={c['name']:c for c in documents[member['path']]};need(len(oldcommands[member['path']])==len(documents[member['path']]),'unique historical command names')
 commands=data['commands'];need(same(commands,data['receipt']['commands']),'commands equal original run receipt')
 current={c['label']:c for c in commands};need(len(current)==len(commands),'unique actual command labels')
 compile=current['compile'];command_pass(compile,False);compile_sources=[x for x in compile['argv']if x.endswith('.java')];sources=data['source_freeze']['sources'];need(len(sources)==143 and len(compile_sources)==143 and set(compile_sources)=={str(REPO/s['path'])for s in sources},'exact143 compiled source paths')
 need(len({Path(s['path']).name for s in sources})==143,'unambiguous owned copied source filenames')
 for source in sources:need(same(ident(RUN/Path(source['path']).name),{k:source[k]for k in('bytes','sha256')}),'compiled source copy '+source['path'])
 for root,mapkey in((RUN/'classes','class_map'),(RUN/'frozen-focus/classes','focus_map')):
  mapping=data[mapkey];need({str(p.relative_to(root))for p in root.rglob('*')if p.is_file()}==set(mapping),'complete selected emitted class set')
  for name,value in mapping.items():need(same(ident(root/name),value),'actual emitted class hash '+name)
 rows=[];ids=set();aliases=set();invocations=set();expectedlabels=set();source_index={s['path']:s for s in sources}
 for index,case in enumerate(cases):
  need(type(case)is dict and type(case['case_id'])is str and case['case_id']not in ids,'unique immutable case ID');ids.add(case['case_id']);key=(case['variant'],case['class'],tuple(case['args']));need(key not in invocations,'unique original invocation');invocations.add(key)
  need(case['variant']in('main','frozen-focus'),'exact source variant');source=case['source'];oldmatches=[m['path']for m in oldseal['members']if m['bytes']==source['bytes']and m['sha256']==source['sha256']];need(bool(oldmatches),'source is exact selected historical review member')
  label='original-'+f'{index:03d}'+'-'+case['case_id'];expectedlabels.add(label);command=current[label];command_pass(command,False);argv,at,args=invocation(command,case)
  cp=argv[argv.index('-cp')+1].split(':');compile_dir=compile['argv'][compile['argv'].index('-d')+1]
  if case['variant']=='main':
   need(cp==[compile_dir],'exact normal runtime classpath');need(source['path']in source_index and same({k:source[k]for k in('bytes','sha256')},{k:source_index[source['path']][k]for k in('bytes','sha256')}),'original case source in exact143 freeze');owned=RUN/Path(source['path']).name;classes=RUN/'classes';mapping=data['class_map']
  else:
   frozencompile=current['compile-frozen-focus'];command_pass(frozencompile,False);need([x for x in frozencompile['argv']if x.endswith('.java')]==[str(REPO/source['path'])],'exact separate original Focus compile source');outdir=frozencompile['argv'][frozencompile['argv'].index('-d')+1];need(cp==[outdir,compile_dir],'frozen Focus overrides only its own runtime classes');owned=RUN/'frozen-focus'/Path(source['path']).name;classes=RUN/'frozen-focus/classes';mapping=data['focus_map']
  need(same(ident(owned),{k:source[k]for k in('bytes','sha256')}),'exact original selected source bytes');mainrel=case['class'].replace('.','/')+'.class';need(mainrel in mapping,'actual emitted original main class');parsed=parse((classes/mainrel).read_bytes());need(parsed['source_file']==Path(source['path']).name and any(m['name']=='main'and m['descriptor']=='([Ljava/lang/String;)V'and m['access']&9==9 for m in parsed['methods']),'actual public static main/source class')
  for stream in('stdout','stderr'):need(same(ident(RUN/(label+'.'+stream)),command[stream]),'actual original command log '+stream)
  linked=[];need(type(case['historical_aliases'])is list and bool(case['historical_aliases']),'nonempty exact historical aliases')
  for alias in case['historical_aliases']:
   path=alias['command_roster'];need(path in oldcommands,'selected exact historical roster');member=next(m for m in release['members']if m['path']==path);need(same({k:alias[k]for k in('bytes','sha256')},{k:member[k]for k in('bytes','sha256')}),'alias roster hash');need(Path(path).parent.name==alias['run'],'alias named run')
   aliaskey=(path,alias['name']);need(aliaskey not in aliases,'unique global historical alias');aliases.add(aliaskey);old=oldcommands[path][alias['name']];command_pass(old,True);invocation(old,case);linked.append({'run':alias['run'],'name':alias['name'],'command_roster':path,'historical_argv':old['argv'],'historical_passed':True})
  rows.append({'case_id':case['case_id'],'variant':case['variant'],'class':case['class'],'args':case['args'],'original_source':source,'source_members_in_selected_review':oldmatches,'actual_source_copy':str(owned.relative_to(REPO)),'actual_command_label':label,'actual_command':command,'actual_main_class':{'path':str((classes/mainrel).relative_to(REPO)),**mapping[mainrel]},'historical_aliases':linked})
 need({k for k in current if k.startswith('original-')}==expectedlabels and len(aliases)==99,'closed98 actual original commands and99 aliases')
 for failed in roster['historical_failed_excluded']:
  path=str(reviewroot/'runs'/failed['run']/'commands.json');old=oldcommands[path][failed['command']];need(type(old['exit'])is int and old['exit']!=0 and(path,failed['command'])not in aliases,'retained failed historical assertion not selected as pass')
 return {'schema':1,'status':'complete98-original-behavior-and99-historical-alias-receipt-join; not-qualified','selected_review_seal_sha256':SEAL_SHA,'root_release_sha256':RELEASE_SHA,'unique_actual_commands':len(rows),'historical_passed_aliases':len(aliases),'actual_compile_source_files':143,'rows':rows,'historical_failed_excluded':roster['historical_failed_excluded'],'scope':'Receipt/source/log/class-path reconciliation only. Retained timeout child is not promoted; source-specific semantic/output joins, runtime closure, native, OTA and GA remain pending.','qualified':False}
