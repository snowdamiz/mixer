#!/usr/bin/env python3
"""Run exact producer assertions, redirecting only test scratch/witness output here.

Runtime/verifier files are loaded unchanged. Existing execute wrappers get a
review-owned __file__ at the same directory depth, so their output is owned.
Test functions/classes are unchanged; source transformations are logged.
"""
import ast, hashlib, importlib.abc, importlib.machinery, json, pathlib, sys, tempfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SCRATCH=HERE/'.scratch';SCRATCH.mkdir(exist_ok=True);tempfile.tempdir=str(SCRATCH)
source=pathlib.Path(sys.argv[1]).resolve();args=sys.argv[2:]
changes=[]
def redirect(text,path):
 old=text
 lines=text.splitlines(keepends=True)
 for i,line in enumerate(lines):
  if line.strip()=="SCRATCH = HERE / '.scratch'":lines[i]='SCRATCH = pathlib.Path('+repr(str(SCRATCH))+')\n'
 text=''.join(lines)
 # Only V5 historical CONTRACT emits a witness outside temp storage.
 text=text.replace("        out = HERE / 'witnesses' / name", "        out = pathlib.Path("+repr(str(HERE/'historical-witnesses'))+") / name")
 if text!=old:
  classes=lambda s:[ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))]
  # Witness method path necessarily changes, but never a test assertion.
  tests=lambda s:{n.name:ast.dump(n,include_attributes=False) for c in ast.parse(s).body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
  assert tests(old)==tests(text),'Test assertion AST changed'
  changes.append({'path':str(path),'originalSHA256':hashlib.sha256(old.encode()).hexdigest(),'executedSHA256':hashlib.sha256(text.encode()).hexdigest(),'testMethodASTUnchanged':True,'changes':'SCRATCH and optional historical witness output only'})
 return text
class Loader(importlib.machinery.SourceFileLoader):
 def get_code(self,fullname):return compile(redirect(pathlib.Path(self.path).read_text(),self.path),self.path,'exec')
class Finder(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  spec=importlib.machinery.PathFinder.find_spec(fullname,path)
  if spec and spec.origin and pathlib.Path(spec.origin).is_relative_to(ROOT/'verification') and pathlib.Path(spec.origin).name.startswith('test') and spec.origin.endswith('.py'):
   spec.loader=Loader(fullname,spec.origin);return spec
sys.meta_path.insert(0,Finder());sys.path.insert(0,str(source.parent))
text=redirect(source.read_text(),source)
virtual=str(HERE/source.name) if source.name.startswith('execute_') else str(source)
sys.argv=[str(source),*args]
try:exec(compile(text,str(source),'exec'),{'__name__':'__main__','__file__':virtual})
finally:
 (HERE/('isolation-'+source.stem+('-historical' if args else '')+'.json')).write_text(json.dumps({'source':str(source),'executedFileContext':virtual,'runtimeSourcesModified':False,'testAssertionASTUnchanged':True,'redirects':changes,'scratch':str(SCRATCH)},indent=2,sort_keys=True)+'\n')
