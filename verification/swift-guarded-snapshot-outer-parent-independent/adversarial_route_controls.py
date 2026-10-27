#!/usr/bin/env python3
"""Independent hostile trace controls for actual compiled route summaries."""
import datetime,hashlib,json
from pathlib import Path
import sys,time,traceback
HERE=Path(__file__).resolve().parent
OUT=HERE/'commands/adversarial-route-controls'
OUT.mkdir(parents=True)
started=time.monotonic()
def sha(data):return hashlib.sha256(data).hexdigest()
def valid(events,terminal):
    for event,limit in [('I',1),('U',3),('fixture',1),('destroy-call',1),('destroy-returned',1),('token',1),('release',1)]:
        if events.count(event)>limit:return False
    if 'destroy-call' in events and ('I' not in events or events.index('I')>events.index('destroy-call')):return False
    if 'destroy-returned' in events and ('destroy-call' not in events or events.index('destroy-call')>events.index('destroy-returned')):return False
    if 'token' in events and ('destroy-returned' not in events or events.index('destroy-returned')>events.index('token')):return False
    if 'release' in events:
        for earlier in ['fixture','I','destroy-call','destroy-returned','token']:
            if earlier not in events or events.index(earlier)>events.index('release'):return False
    if terminal=='return' and 'token' in events and events.count('release')!=1:return False
    return True
code=0
try:
    paths=json.loads((HERE/'mir-paths.json').read_bytes())['consume_outer_request_v1']
    for route in paths:assert valid(route['events'],route['terminal']),route
    normal=next(p for p in paths if p['terminal']=='return' and 'release' in p['events'])
    events=normal['events'];mutants=[]
    mutants += [('second inspection',events+['I']),('fourth usage snapshot',events+['U']),('second dispatch',events+['fixture']),('second destruction',events+['destroy-call']),('second token',events+['token']),('second release',events+['release'])]
    for missing in ['I','fixture','destroy-call','destroy-returned','token','release']:
        mutants.append(('missing '+missing,[e for e in events if e!=missing]))
    premature=list(events);premature.remove('release');premature.insert(0,'release');mutants.append(('premature release',premature))
    late_inspect=[e for e in events if e!='I'];late_inspect.append('I');mutants.append(('inspect after destruction',late_inspect))
    for label,mutant in mutants:assert not valid(mutant,'return'),(label,mutant)
    refusing=next(p for p in paths if p['terminal']=='return' and p['events']==['U','fixture','U'])
    assert not valid(refusing['events']+['release'],'return')
    report=dict(schema=1,actual_compiled_paths=len(paths),rejected_mutations=len(mutants)+1,assertions=len(paths)+len(mutants)+1,status='passed',scope='Pure Python checks of actual retained MIR path events and deliberately hostile synthetic event mutations; no mutated Rust compilation or product runtime')
except BaseException as error:
    code=1;report=dict(status='failed',error=repr(error),traceback=traceback.format_exc())
stdout=(json.dumps(report,sort_keys=True)+'\n').encode()
(OUT/'stdout').write_bytes(stdout)
(OUT/'stderr').write_bytes(b'')
receipt=dict(schema=1,argv=[sys.executable,str(Path(__file__).resolve())],environment_scope='Inherited host Python environment; no compiler/product/native child spawned',python_version=sys.version,runner_sha256=sha(Path(__file__).read_bytes()),source_revision='975b2e3ef25255a882e7476780caa2e844ce928d',candidate_tree_sha256='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3',mir_paths_sha256=sha((HERE/'mir-paths.json').read_bytes()),exit_code=code,elapsed_seconds=time.monotonic()-started,stdout_sha256=sha(stdout),stderr_sha256=sha(b''),spawned_children=0,native_runtime=False)
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(stdout.decode(),end='')
sys.exit(code)
