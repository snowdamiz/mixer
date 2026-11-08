"""Adapt only the original accounting helper's finite fake clock."""
import ast
import hashlib

BEFORE = b'  if timed_out:clock.monotonic.side_effect=[100.0,101.0,101.0]\n'
AFTER = b'  if timed_out:clock.monotonic.side_effect=__import__("itertools").chain([100.0,101.0,101.0],__import__("itertools").repeat(101.0))\n'

def bodies(source):
    text=source.decode()
    cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='RunnerControls')
    return {n.name:ast.get_source_segment(text,n) for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}

def adapt(source):
    if source.count(BEFORE)!=1:
        raise RuntimeError('Exact accounting helper clock preimage required')
    derived=source.replace(BEFORE,AFTER,1)
    if bodies(source)!=bodies(derived) or len(bodies(derived))!=36:
        raise RuntimeError('Original 36 test bodies changed')
    return derived

def proof(source):
    derived=adapt(source)
    return {'source_sha256':hashlib.sha256(source).hexdigest(),
            'adapted_sha256':hashlib.sha256(derived).hexdigest(),
            'test_bodies':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in bodies(source).items()},
            'changed_helper_only':'accounting_row: clock keeps its last value after the original three observations; no test assertion changed'}
