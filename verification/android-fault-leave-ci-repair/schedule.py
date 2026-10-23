from pathlib import Path
import subprocess,json,hashlib,datetime
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
build=HERE/'build';build.mkdir(exist_ok=True)
commands=[]
inputs=['verification/android-fault-leave-ci-repair/leave_schedule.c','verification/android-fault-leave-ci-repair/schedule.py','native/android/signed-guest-ui/transport/transport.c','native/android/signed-guest-ui/transport/internal.h','native/android/signed-guest-ui/transport/include/mixer_ui_transport.h']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={n:sha(ROOT/n) for n in inputs}
def run(name,cmd):
    r=subprocess.run([str(x) for x in cmd],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
    log=HERE/(name+'.log');log.write_bytes(r.stdout)
    commands.append({'command':[str(x) for x in cmd],'cwd':str(ROOT),'exit':r.returncode,'log':str(log.relative_to(ROOT)),'sha256':sha(log)})
    print(name,r.returncode,r.stdout.decode(),flush=True)
    if r.returncode or b'WARNING: ThreadSanitizer' in r.stdout:raise RuntimeError(name)
try:
    run('clang-version',['xcrun','clang','--version'])
    run('platform',['uname','-a'])
    for mode,flags in [('debug',['-O0','-g']),('release',['-O2','-g']),('tsan',['-O1','-g','-fsanitize=thread'])]:
        exe=build/('leave-'+mode)
        run(mode+'-compile',['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-DMIXER_UI_TRANSPORT_TESTING',*flags,'-Inative/android/signed-guest-ui/transport',HERE/'leave_schedule.c','native/android/signed-guest-ui/transport/transport.c','-o',exe])
        for case in ['old','fixed']:run(mode+'-'+case,[exe,case])
    if manifest!={n:sha(ROOT/n) for n in inputs}:raise RuntimeError('source changed')
finally:
    (HERE/'schedule-receipt.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'inputs':manifest,'commands':commands,'scope':'Actual unchanged C transport deterministic schedule; fixed hooks are test drivers, not the Swift binding. Demonstrates old predicate permits coalesced leave and fixed predicate separates callbacks. Does not identify which wait timed out in sparse hosted log. First probe incorrectly expected OK completion after sticky fault; initial-probe retains that failed assertion and source. Corrected expectation follows the real CLOSE_PENDING completion.'},indent=2)+'\n')
