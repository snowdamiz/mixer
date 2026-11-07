"""Preparation helpers for an externally reviewed pre-Python admission root, never self approval."""
from pathlib import Path
import os,sys,hashlib,json,shlex,re,subprocess,signal,time
SAFE=re.compile(r'^[A-Za-z0-9_./+@-]+$')
UTILITIES=('/bin/sh','/usr/bin/env','/usr/bin/find','/usr/bin/sort','/usr/bin/cmp','/usr/bin/readlink','/usr/bin/shasum','/usr/bin/perl','/usr/bin/mktemp','/bin/rm','/usr/bin/otool')
def need(ok,message):
 if not ok:raise ValueError(message)
def identity(p):b=Path(p).read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def safe(p):s=str(p);need(bool(SAFE.fullmatch(s)) and s.startswith('/'),'preparation context requires selected absolute safe path');return s
def runtime_contract():
 need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.dont_write_bytecode==1,'preparation must run -I -B -S')
 return {'executable':str(Path(sys.executable).absolute()),'resolved_executable':str(Path(sys.executable).resolve()),'base_executable':str(Path(sys._base_executable).absolute()),'prefix':sys.prefix,'base_prefix':sys.base_prefix,'exec_prefix':sys.exec_prefix,'base_exec_prefix':sys.base_exec_prefix,'sys_path':list(sys.path),'startup':{'isolated':1,'no_site':1,'dont_write_bytecode':1,'ignore_environment':1,'safe_path':True}}
def prepare_runtime(root):
 root=Path(root);root.mkdir();contract=runtime_contract();prefix=Path(os.path.commonpath([str(Path(sys.base_prefix).resolve()),*[str(Path(path).parent if path.endswith('.zip') else Path(path)) for path in sys.path]]));need(prefix not in (Path('/'),Path('/Users'),Path('/opt')),'runtime search roots are not a bounded selected installation');need(all(Path(path).is_relative_to(prefix) for path in sys.path),'runtime root must enclose every admitted import path');excluded=prefix/('lib/python%d.%d/site-packages'%sys.version_info[:2]);files={};links={};paths=[];commands=[]
 def link_chain(p):
  p=Path(p).absolute()
  for part in [p,*p.parents]:
   if part.is_symlink():links[safe(part)]=os.readlink(part)
  while p.is_symlink():
   target=os.readlink(p);links[safe(p)]=target;p=Path(os.path.normpath(str(p.parent/target))) if not Path(target).is_absolute() else Path(target)
 def selected_file(p):
  p=Path(p);link_chain(p);resolved=p.resolve();need(resolved.is_file(),'missing selected runtime body');files[safe(resolved)]=identity(resolved)
 for p in sorted(prefix.rglob('*')):
  if p==excluded or excluded in p.parents:continue
  if p.is_file() or p.is_symlink():
   paths.append(safe(p))
   if p.is_symlink():need(p.resolve().is_relative_to(prefix),'runtime prefix symlink escape');links[safe(p)]=os.readlink(p)
   if p.is_file():selected_file(p)
 selected_file(sys.executable);selected_file(sys._base_executable)
 # Include non-OS dynamic-library dependencies of every admitted Python extension/core, transitively.
 queue=[p for p in files if p.endswith(('.so','.dylib')) or p==str(prefix/'Python')];seen=set()
 while queue:
  path=queue.pop()
  if path in seen:continue
  seen.add(path);start=time.monotonic();child=subprocess.Popen(['/usr/bin/otool','-L',path],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env={'PATH':'/usr/bin:/bin','LC_ALL':'C','LANG':'C'})
  try:out,err=child.communicate(timeout=60)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait();raise ValueError('bounded otool dependency read timed out')
  commands.append({'argv':['/usr/bin/otool','-L',path],'exit':child.returncode,'timeout_seconds':60,'elapsed_seconds':time.monotonic()-start,'reaped':True,'stdout':out.decode(),'stderr':err.decode()});need(child.returncode==0,'runtime dependency inspection failed')
  for line in out.decode().splitlines()[1:]:
   dep=line.strip().split(' (',1)[0]
   if dep.startswith(('/System/Library/','/usr/lib/')):continue
   need(dep.startswith('/'),'unresolved Python runtime dependency '+dep)
   selected_file(dep);resolved=str(Path(dep).resolve())
   if resolved!=path and resolved not in seen:queue.append(resolved)
 for utility in UTILITIES:need(Path(utility).is_file(),'missing trusted OS utility '+utility)
 policy={'schema':'mixer.android.external-python-admission.v1','root_selected':False,'runtime_contract':contract,'prefix':safe(prefix),'excluded_unreachable_site_packages':safe(excluded),'runtime_files':dict(sorted(files.items())),'runtime_links':dict(sorted(links.items())),'prefix_pathset':sorted(paths),'trusted_OS_utility_paths':{p:identity(p) for p in UTILITIES},'trust_boundary':'Trusted OS utilities and externally reviewed launcher/runtime admission rosters execute before Python. Python current-state checks only detect drift; they do not authorize prior startup. Unreachable site-packages are excluded only under mandatory -I -B -S and exact sys.path.'}
 (root/'python-runtime-policy.json').write_text(json.dumps(policy,indent=2)+'\n');(root/'python-files.sha256').write_text(''.join(v['sha256']+'  '+p+'\n' for p,v in sorted(files.items())));(root/'python-links.tsv').write_text(''.join(p+'\t'+target+'\n' for p,target in sorted(links.items())));(root/'python-prefix-pathset.txt').write_text(''.join(p+'\n' for p in sorted(paths)));(root/'runtime-dependency-commands.json').write_text(json.dumps(commands,indent=2)+'\n');return policy
def shell_entry(root,bootstrap):
 root=Path(root).resolve();bootstrap=Path(bootstrap).resolve();policy=json.loads((root/'python-runtime-policy.json').read_bytes());quote=shlex.quote
 const={name:identity(root/name)['sha256'] for name in ('python-runtime-policy.json','python-files.sha256','python-links.tsv','python-prefix-pathset.txt')}
 core='''#!/bin/sh
set -efu
PATH=/usr/bin:/bin; LANG=C; LC_ALL=C; TZ=UTC; export PATH LANG LC_ALL TZ
# Caller supplies only an already-owned scratch directory, followed by quoted bootstrap arguments.
scratch=$1; shift
case "$scratch" in /*) ;; *) echo 'refused nonabsolute owned scratch' >&2; exit 2;; esac
[ -d "$scratch" ] && [ ! -L "$scratch" ] || exit 2
work=$(/usr/bin/mktemp -d "$scratch/owned-python-admission.XXXXXX")
trap '/bin/rm -rf -- "$work"' EXIT HUP INT TERM
digest(){ result=$(/usr/bin/shasum -a 256 -- "$1"); result=${result%% *}; printf '%s' "$result"; }
'''
 for name,sha in const.items():core+='[ "$(digest '+quote(str(root/name))+')" = '+quote(sha)+' ] || { echo '+quote('refused altered external admission '+name)+' >&2; exit 2; }\n'
 for utility,wanted in policy['trusted_OS_utility_paths'].items():core+='[ "$(digest '+quote(utility)+')" = '+quote(wanted['sha256'])+' ] || { echo "refused changed external OS utility identity" >&2; exit 2; }\n'
 core+='[ "$(digest '+quote(str(bootstrap))+')" = '+quote(identity(bootstrap)['sha256'])+' ] || { echo "refused altered selected bootstrap" >&2; exit 2; }\n'
 core+='[ ! -L '+quote(policy['prefix'])+' ] || { echo "refused runtime prefix alias" >&2; exit 2; }\n'
 core+='/usr/bin/find '+quote(policy['prefix'])+' -path '+quote(policy['excluded_unreachable_site_packages'])+' -prune -o \\( -type f -o -type l \\) -print > "$work/paths.raw"\n/usr/bin/sort "$work/paths.raw" > "$work/paths.sorted"\n/usr/bin/cmp -s "$work/paths.sorted" '+quote(str(root/'python-prefix-pathset.txt'))+' || { echo "refused missing/extra runtime path" >&2; exit 2; }\n'
 core+='/usr/bin/shasum -a 256 -c '+quote(str(root/'python-files.sha256'))+' > "$work/file-checks" 2>&1 || { echo "refused changed/missing runtime file" >&2; exit 2; }\n'
 core+='tab=$(printf "\\t")\nwhile IFS="$tab" read -r path target; do [ -L "$path" ] && [ "$(/usr/bin/readlink "$path")" = "$target" ] || { echo "refused changed/missing runtime symlink" >&2; exit 2; }; done < '+quote(str(root/'python-links.tsv'))+'\n'
 core+='/usr/bin/env -i PATH=/usr/bin:/bin LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 TZ=UTC '+quote(policy['runtime_contract']['executable'])+' -I -B -S '+quote(str(bootstrap))+' "$@"\n'
 (root/'admission-core.sh').write_text(core)
 # The outer entry always sanitizes shell/locale/Python/loader injection before the core starts.
 fixed='core='+quote(str(root/'admission-core.sh'))+'; result=$(/usr/bin/shasum -a 256 -- "$core"); result=${result%% *}; [ "$result" = '+quote(identity(root/'admission-core.sh')['sha256'])+' ] || { echo "refused altered admission core" >&2; exit 2; }; exec /bin/sh "$core" "$@"'
 entry='#!/bin/sh\nexec /usr/bin/env -i PATH=/usr/bin:/bin LANG=C LC_ALL=C TZ=UTC /bin/sh -c '+quote(fixed)+' mixer-admission "$@"\n';(root/'qualification-entry.sh').write_text(entry)
 (root/'external-root-contract.json').write_text(json.dumps({'schema':1,'external_parent_must_pin_entry':identity(root/'qualification-entry.sh'),'entry_pins_core':identity(root/'admission-core.sh'),'core_pins_bootstrap':identity(bootstrap),'core_pins_admission_rosters':const,'OS_utilities_are_external_trusted_inputs':policy['trusted_OS_utility_paths'],'mandatory_outer_invocation':['/usr/bin/env','-i','PATH=/usr/bin:/bin','/bin/sh',str(root/'qualification-entry.sh'),'<owned-scratch>','<fixed selected bootstrap args>'],'acyclic':'parent -> entry -> core -> bootstrap -> descendant manifest; core -> runtime admission rosters. No descendant pins any ancestor.'},indent=2)+'\n')
