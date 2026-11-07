"""Closed descendant execution payload. Trust selection is supplied only by external bootstrap."""
from pathlib import Path
import hashlib,json,os,sys
def need(ok,message):
 if not ok:raise ValueError(message)
def decode(p):
 def pairs(items):
  out={}
  for key,value in items:
   need(key not in out,'duplicate JSON key '+key);out[key]=value
  return out
 return json.loads(Path(p).read_bytes(),object_pairs_hook=pairs)
def identity(path):
 p=Path(path);need(p.is_file() and not p.is_symlink(),'nonregular execution file '+str(p));data=p.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def tree(root,allow_symlinks=False):
 root=Path(root);need(root.is_dir() and not root.is_symlink(),'execution root must be a regular directory');out={}
 for p in sorted(root.rglob('*')):
  rel=str(p.relative_to(root));need(not p.is_symlink() or allow_symlinks,'symlink execution artifact '+rel)
  if p.is_symlink():
   target=os.readlink(p);need(p.resolve().is_relative_to(root.resolve()),'tool symlink escapes installation '+rel);out[rel]={'kind':'symlink','target':target}
  elif p.is_file():out[rel]={'kind':'file',**identity(p)}
  else:need(p.is_dir(),'unexpected execution artifact '+rel)
 return out
def safe_path(root,relative):
 need(type(relative) is str and relative and not Path(relative).is_absolute() and '..' not in Path(relative).parts,'unsafe execution relative path');return Path(root)/relative
def check(manifest_path,selected_sha256,payload_root,classes,jdk_home):
 need(type(selected_sha256) is str and len(selected_sha256)==64,'external bootstrap selection required');need(identity(manifest_path)['sha256']==selected_sha256,'foreign execution manifest; no self approval');m=decode(manifest_path)
 need(m.get('schema')=='mixer.android.execution-closure.v1','execution manifest schema');need(m.get('root_selected') is True,'execution closure remains draft')
 need(tree(payload_root)==m['payload_tree'],'changed/missing/extra execution payload source');need(tree(classes)==m['class_tree'],'changed/missing/extra emitted product/support class');need(tree(jdk_home,True)==m['jdk_tree'],'changed/missing/extra JDK installation artifact');need(identity(Path(sys.executable).resolve())==m['python_executable'],'changed bootstrap Python executable')
 sources=m['compile']['sources'];need(type(sources) is list and sources and len(sources)==len(set(sources)),'exact explicit compiler source roster');need(all(str(s).endswith('.java') and s in m['payload_tree'] for s in sources),'compiler source outside selected payload');need(m['compile']['flags']==['--release','17','-Xlint:all','-Werror','-proc:none'],'unselected compiler flags');need(m['compile']['classpath']=='empty' and m['compile']['sourcepath']=='empty','unselected compiler search path')
 for name in ('checker','producer'):
  value=m[name];need(type(value) is str and value.endswith('.py') and value in m['payload_tree'],'unselected '+name)
 need(m['environment']=={'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'},'unselected invocation environment')
 return m
def precompile(manifest_path,selected_sha256,payload_root,jdk_home):
 # Identical closure checks before producer execution, without pretending prior classes are freshly compiled.
 need(identity(manifest_path)['sha256']==selected_sha256,'foreign execution manifest; no self approval');m=decode(manifest_path);need(m.get('schema')=='mixer.android.execution-closure.v1' and m.get('root_selected') is True,'execution closure remains draft');need(tree(payload_root)==m['payload_tree'],'changed/missing/extra execution payload source');need(tree(jdk_home,True)==m['jdk_tree'],'changed/missing/extra JDK installation artifact');need(identity(Path(sys.executable).resolve())==m['python_executable'],'changed bootstrap Python executable');return m
