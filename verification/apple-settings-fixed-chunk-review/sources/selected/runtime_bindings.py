"""Origin checks for the selected closed runtime closure, never historical evidence."""
import hashlib
import json
import pathlib
import sys
import types

class RuntimeBindings:
    def __init__(self,base,manifest):
        self.base=base
        for name in manifest['files']:
            path=base/name
            if path.resolve()!=path or path.is_symlink():raise ValueError('Selected runtime path redirected: '+name)
        self.files={str(base/name):digest for name,digest in manifest['files'].items()}
        self.aliases={name:str(base/path) for name,path in manifest['moduleAliases'].items()}
        self.case_data={name:base/path for name,path in manifest.get('caseDataAliases',{}).items()}
        self.registered={}
    def check_files(self):
        for name,digest in self.files.items():
            path=pathlib.Path(name)
            if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError('Selected runtime source/data changed: '+name)
    def module(self,module,expected=None):
        actual=getattr(module,'__file__',None)
        origin=getattr(getattr(module,'__spec__',None),'origin',None)
        wanted=expected or self.aliases.get(getattr(module,'__name__',''))
        if actual is None or origin is None:raise ValueError('Owned runtime module lacks selected origin')
        actual=str(pathlib.Path(actual).resolve());origin=str(pathlib.Path(origin).resolve())
        if wanted is None:wanted=actual if actual in self.files and actual.endswith('.py') else None
        if wanted is None or actual!=wanted or origin!=wanted:
            raise ValueError('Owned runtime module outside selected origin: '+str(getattr(module,'__name__','?')))
        if actual not in self.files or hashlib.sha256(pathlib.Path(actual).read_bytes()).hexdigest()!=self.files[actual]:
            raise ValueError('Owned runtime module source differs from selected bytes: '+actual)
        # A module attribute/spec claiming the selected path cannot authorize a
        # TransactionStore or other owned definition compiled from another file.
        for value in vars(module).values():
            if isinstance(value,types.FunctionType) and value.__module__==module.__name__:
                if str(pathlib.Path(value.__code__.co_filename).resolve())!=actual:
                    raise ValueError('Owned function code outside selected origin: '+value.__qualname__)
            if isinstance(value,type) and value.__module__==module.__name__:
                for method in vars(value).values():
                    if isinstance(method,(staticmethod,classmethod)):method=method.__func__
                    if isinstance(method,types.FunctionType) and method.__module__==module.__name__:
                        if str(pathlib.Path(method.__code__.co_filename).resolve())!=actual:
                            raise ValueError('Owned method code outside selected origin: '+value.__qualname__)
        if module.__name__ in self.case_data:
            if pathlib.Path(getattr(module,'BASE','')).resolve()!=pathlib.Path(actual).parent:
                raise ValueError('Owned case-data origin redirected: '+module.__name__)
            expected_data={row['name']:row for row in json.loads(self.case_data[module.__name__].read_bytes())}
            if json.dumps(getattr(module,'SPECS',None),sort_keys=True,allow_nan=False)!=json.dumps(expected_data,sort_keys=True,allow_nan=False):
                raise ValueError('Owned case-data differs from selected bytes: '+module.__name__)
        self.registered[id(module)]=(module,actual)
    def preloads(self):
        for alias,expected in self.aliases.items():
            if alias in sys.modules:
                module=sys.modules[alias]
                if module is None:raise ValueError('Owned module cache entry unavailable: '+alias)
                self.module(module,expected)
    def check(self,roots=()):
        self.check_files();self.preloads()
        pending=list(roots)+[entry[0] for entry in self.registered.values()];seen=set()
        while pending:
            module=pending.pop()
            if id(module) in seen:continue
            seen.add(id(module));self.module(module)
            for value in vars(module).values():
                if not isinstance(value,types.ModuleType):continue
                name=getattr(value,'__name__','');file=getattr(value,'__file__',None)
                if name in self.aliases or file is not None and str(pathlib.Path(file).resolve()) in self.files:
                    pending.append(value)
