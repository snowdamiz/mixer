from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTROL = HERE.parent / 'native-custody-premise/cleanup_control.py'
EXPECTED = '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
if hashlib.sha256(CONTROL.read_bytes()).hexdigest() != EXPECTED:
    raise RuntimeError('Accepted controller mismatch')
spec = importlib.util.spec_from_file_location('accepted_controller', CONTROL)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
logs = HERE/'commands'
logs.mkdir()
commands = c.Commands(logs, {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}, deadline=time.monotonic()+150)
result = {'controller_sha256':EXPECTED, 'python':sys.version, 'executable':sys.executable,
          'command_limit':1, 'per_command_seconds':120, 'runs':[],
          'scope':'Pure/fake childfree Python normal and optimized controls only'}
try:
    for mode, options in [('normal',[])]:
        projection = HERE/'scratch'/mode
        argv = [sys.executable,'-I','-B','-S',*options,str(HERE/'review_tests.py'),str(projection),mode]
        run = {'mode':mode,'argv':argv}
        try:
            commands.run(mode,argv,ROOT,timeout=120,allowed=(0,1))
        except BaseException as error:
            run['supervision_error']=repr(error)
        if not commands.hold:
            receipt=projection/'verification/plan-continuation-2026-11-07/envelope-output-ownership-fix-r2/review-tests-result.json'
            if receipt.is_file():
                raw=receipt.read_bytes()
                (HERE/(mode+'-tests-result.json')).write_bytes(raw)
                run['tests']=json.loads(raw)
        result['runs'].append(run)
        (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if commands.hold or commands.limit or 'supervision_error' in run:
            break
finally:
    all_passed = len(result['runs']) == 1 and all(
        all(r.get('tests',{}).get(k,{}).get('passed',False) for k in ('original','independent','ownership','r2review'))
        and not r.get('tests',{}).get('denied_runtime_attempts') for r in result['runs'])
    if all_passed and not commands.hold:
        result['cleanup']=commands.cleanup(HERE/'scratch')
    else:
        result['cleanup']={'allTerminalCustody':not commands.hold and all(r['terminal_custody'] for r in commands.records),
                           'hold':commands.hold,'scratchRemoved':False,'reason':'retain failure or unknown custody'}
    result['commands']=commands.records
    (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
