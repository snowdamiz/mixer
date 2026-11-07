"""Actual pre-Python admission controls in an owned cloned runtime; never modify installations."""
from pathlib import Path
import os,sys,json,shutil,subprocess,signal,time,hashlib,importlib.util
D=Path(__file__).resolve().parent
if not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):raise SystemExit('controls require -I -B -S')
i=1
while (D/('python-admission-controls-'+str(i))).exists():i+=1
E=D/('python-admission-controls-'+str(i));E.mkdir();scratch=E/'owned-scratch';scratch.mkdir();commands=[];controls=[]
def ident(p):b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def run(name,argv,expected):
 start=time.monotonic();stdout=E/(name+'.stdout');stderr=E/(name+'.stderr')
 env={'PATH':'/foreign','ENV':'/foreign/shell-env','BASH_ENV':'/foreign/bash-env','SHELLOPTS':'xtrace','PYTHONPATH':'/foreign','PYTHONHOME':'/foreign','PYTHONSTARTUP':'/foreign/startup.py','DYLD_INSERT_LIBRARIES':'/foreign/lib.dylib','LD_PRELOAD':'/foreign/lib.so','LC_ALL':'foreign','LANG':'foreign'}
 if str(argv[0])!='/usr/bin/env':env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'}
 with stdout.open('wb') as out,stderr.open('wb') as err:
  p=subprocess.Popen([str(x) for x in argv],cwd=scratch,env=env,stdout=out,stderr=err,start_new_session=True);timed=False
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
  except BaseException:os.killpg(p.pid,signal.SIGKILL);p.wait();raise
 record={'name':name,'argv':[str(x) for x in argv],'exit':p.returncode,'timeout':timed,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'reaped':True,'stdout':ident(stdout),'stderr':ident(stderr)};commands.append(record);save(E/'commands.json',commands);assert p.returncode==expected and not timed,(record,stderr.read_text());return record
def entry(name,expected):
 marker.unlink(missing_ok=True);run(name,['/usr/bin/env','-i','PATH=/usr/bin:/bin','/bin/sh',admission_root/'qualification-entry.sh',scratch],expected);observed=marker.exists();assert observed==(expected==0);controls.append({'name':name,'expected_exit':expected,'Python_bootstrap_started':observed})
def atomic_write(path,data):temp=path.with_name(path.name+'.owned-replacement');temp.write_bytes(data);temp.replace(path)
try:
 original=Path(sys.base_prefix).resolve();source_identity=ident(original/'lib/python3.14/os.py');clone=scratch/'owned-python-runtime';shutil.copytree(original,clone,copy_function=os.link,symlinks=True);(clone/'bin/python3.14._pth').write_text(str(clone/'lib/python3.14')+'\n'+str(clone/'lib/python3.14/lib-dynload')+'\n');admission_root=scratch/'external-admission';marker=scratch/'Python-actually-started.txt';bootstrap=scratch/'admitted-bootstrap.py';bootstrap.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("actual admitted no-site Python reached bootstrap")\n')
 helper=scratch/'prepare-owned-runtime.py';helper.write_text('import importlib.util,json,sys\nfrom pathlib import Path\nspec=importlib.util.spec_from_file_location("preparation",'+repr(str(D/'python_admission.py'))+');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\np=Path('+repr(str(admission_root))+');m.prepare_runtime(p);policy=json.loads((p/"python-runtime-policy.json").read_bytes());policy["root_selected"]=True;(p/"python-runtime-policy.json").write_text(json.dumps(policy,indent=2)+"\\n");m.shell_entry(p,Path('+repr(str(bootstrap))+'))\n')
 run('prepare-known-source-owned-runtime',[clone/'bin/python3.14','-I','-B','-S',helper],0)
 policy=json.loads((admission_root/'python-runtime-policy.json').read_bytes());assert policy['prefix']==str(clone) and policy['runtime_contract']['base_prefix']==str(clone/'bin') and policy['runtime_contract']['sys_path']==[str(clone/'lib/python3.14'),str(clone/'lib/python3.14/lib-dynload')],'owned runtime prefix not actually selected'
 entry('positive-pre-Python-closed-runtime-sanitized',0)
 victim=clone/'lib/python3.14/os.py';original_bytes=victim.read_bytes();atomic_write(victim,original_bytes+b'\n# owned changed runtime support\n');entry('changed-runtime-support-file-before-startup',2);atomic_write(victim,original_bytes)
 victim=clone/'lib/python3.14/email/__init__.py';original_bytes=victim.read_bytes();victim.unlink();entry('missing-runtime-support-file-before-startup',2);atomic_write(victim,original_bytes)
 extra=clone/'lib/python3.14/unselected_admission_module.py';extra.write_text('raise RuntimeError("must not import")\n');entry('extra-runtime-import-support-before-startup',2);extra.unlink()
 link=clone/'bin/python3';target=os.readlink(link);link.unlink();link.symlink_to('unselected-python');entry('changed-runtime-symlink-before-startup',2);link.unlink();link.symlink_to(target)
 extra=clone/'bin/unselected-runtime-link';extra.symlink_to('python3.14');entry('extra-runtime-symlink-before-startup',2);extra.unlink()
 moved=scratch/'saved-owned-runtime';clone.rename(moved);clone.symlink_to(moved,target_is_directory=True);entry('substituted-root-prefix-alias-before-startup',2);clone.unlink();moved.rename(clone)
 # A coherent altered runtime policy/roster cannot change the independently pinned admission core.
 p=admission_root/'python-runtime-policy.json';original_bytes=p.read_bytes();changed=json.loads(original_bytes);changed['prefix']='/foreign/self-approved';p.write_text(json.dumps(changed));entry('coherent-self-approved-runtime-policy-before-startup',2);p.write_bytes(original_bytes)
 # Owned venv .pth is never on the admitted entry path and -S suppresses it in a direct refused bootstrap path too.
 venv=scratch/'owned-venv';run('create-owned-venv-without-pip',[sys.executable,'-I','-B','-S','-m','venv','--without-pip',venv],0);site=venv/('lib/python%d.%d/site-packages'%sys.version_info[:2]);pth_marker=scratch/'unselected-pth-executed';(site/'unselected.pth').write_text('import pathlib; pathlib.Path('+repr(str(pth_marker))+').write_text("must remain absent")\n');entry('foreign-venv-Python-environment-cannot-select-runtime',0);assert not pth_marker.exists()
 assert ident(original/'lib/python3.14/os.py')==source_identity,'global runtime changed'
 shutil.copytree(admission_root,E/'retained-external-root');save(E/'controls.json',{'status':'passed-pre-Python-runtime-admission-controls','controls':controls,'selected_runtime_file_count':len(policy['runtime_files']),'selected_prefix_paths':len(policy['prefix_pathset']),'same_known_source_original_runtime_unchanged':True,'unselected_pth_executed':False,'real_product_or_CI_runtime_accepted':False})
finally:
 shutil.rmtree(scratch);save(E/'cleanup.json',{'owned_runtime_venv_and_scratch_removed':not scratch.exists(),'all_children_reaped':all(c['reaped'] for c in commands),'global_python_JDK_modified':False,'no_native_UI_capture_or_process_inventory':True})
print('PASS actual pre-Python admission controls',len(controls))
