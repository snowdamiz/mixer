"""Exact retained R7 malformed-handle cases against unchanged shipping R7."""
import ast, contextlib, contextvars, errno, hashlib, importlib.util, io, json, os, signal, subprocess, sys, types, unittest
from pathlib import Path
from unittest import mock
OWN=Path(__file__).resolve().parent
CAND=OWN.parent/'cache-descriptor-layout-fix-r7'
MODE='optimized' if sys.flags.optimize else 'normal'
EVIDENCE=OWN/('baseline-'+MODE)
EVIDENCE.mkdir()
sys.path[0:0]=[str(OWN),str(CAND)]
import stdin_guard as guard
guard.write_guard(OWN)
def no_process(event,args):
    if event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.kill','os.killpg','os.exec','os.spawn'} or event.startswith('socket.'):
        raise RuntimeError('Baseline forbids process/network operations: '+event)
sys.addaudithook(no_process)
source=OWN.parent/'cache-descriptor-layout-review-r7/review.py'
text=source.read_text()
node=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='R7Additional')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),globals())
spec=importlib.util.spec_from_file_location('unchanged_r7',CAND/'descriptor_preflight.py')
preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
preflight.HERE=OWN
names=['test_none_descriptor_refusal_closes_and_reports','test_string_descriptor_refusal_closes_and_reports']
result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(R7Additional(n) for n in names))
receipts=[json.loads((EVIDENCE/('additional-'+n+'-descriptor.json')).read_bytes()) for n in ['none','string']]
expected=(result.testsRun==2 and len(result.failures)==2 and not result.errors and all(
    r['returncode'] is None and r['escaped']['type']=='TypeError' and r['report'] is None
    and len(r['live_after_candidate'])==4 and r['live_after_candidate']==r['closed_by_review']
    and r['candidate_receipts']==[] and r['io_calls']==[] and r['timer_disarmed']
    and r['all_owned_descriptors_closed'] for r in receipts))
report={'tests':result.testsRun,'failures':[(str(t),e) for t,e in result.failures],
        'errors':[(str(t),e) for t,e in result.errors],'expected_R7_failures_reproduced':expected,
        'review_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'retained_class_sha256':hashlib.sha256(ast.get_source_segment(text,node).encode()).hexdigest(),
        'candidate_preflight_sha256':hashlib.sha256((CAND/'descriptor_preflight.py').read_bytes()).hexdigest(),
        'candidate_source_seal_sha256':hashlib.sha256((CAND/'sources.json').read_bytes()).hexdigest(),
        'python':sys.version,'real_inner_children':0,'actual_original36_run':False}
(EVIDENCE/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'mode':MODE,'expected_R7_failures_reproduced':expected,'tests':2,'failures':len(result.failures)}))
sys.exit(0 if expected else 1)
