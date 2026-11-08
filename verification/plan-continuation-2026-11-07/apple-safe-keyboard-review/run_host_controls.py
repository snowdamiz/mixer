"""Own custody for precisely two host-only children; stop on any unknown state."""
import datetime, hashlib, json, os, selectors, signal, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
HELD={40708,40709,40711,23663,20745,20770,20780,20817,20842,20851,20866,2424,2621}
LIMIT=4*1024*1024
START=time.monotonic()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def put(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def child(mode):
    folder=HERE/('command-'+mode);folder.mkdir()
    argv=[sys.executable,'-B']+(['-O'] if mode=='optimized' else [])+[str(HERE/'review_tests.py')]
    began=time.monotonic(); streams={n:bytearray() for n in ['stdout','stderr']};eof={n:False for n in streams}
    row=dict(argv=argv,argvSHA256=sha(json.dumps(argv,separators=(',',':')).encode()),cwd=os.getcwd(),timeoutSeconds=120,python=sys.version,executableSHA256=sha(Path(sys.executable).resolve().read_bytes()),startedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='pure Python/fake backend; zero actual native operations',signals=[],reaped=False,ownedGroupAbsent=False,unknownCustody=True)
    p=None;selector=None
    try:
        p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        row.update(pid=p.pid,pgid=p.pid)
        if p.pid in HELD:raise RuntimeError('Held identity collision; no further process operations')
        selector=selectors.DefaultSelector()
        for n in streams:
            pipe=getattr(p,n);os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ,n)
        while True:
            if time.monotonic()-began>=120:raise RuntimeError('Deadline reached; retain unknown custody without followup')
            for key,_ in selector.select(.02):
                raw=os.read(key.fileobj.fileno(),65536);n=key.data
                if not raw:eof[n]=True;selector.unregister(key.fileobj);key.fileobj.close();continue
                remaining=LIMIT-len(streams[n]);streams[n].extend(raw[:max(0,remaining)])
                if len(raw)>remaining:raise RuntimeError('Stream limit; stop lane and retain custody')
            if p.poll() is not None and all(eof.values()):break
        p.wait();row.update(reaped=True,exitCode=p.returncode)
        try:os.killpg(p.pid,0)
        except ProcessLookupError:row.update(ownedGroupAbsent=True,unknownCustody=False)
        else:raise RuntimeError('Owned group still present; stop lane without followup')
    except BaseException as e:row['failure']=dict(type=type(e).__name__,message=str(e))
    finally:
        if selector:selector.close()
        row['elapsedSeconds']=time.monotonic()-began;row['streams']={}
        for n,raw in streams.items():
            (folder/(n+'.log')).write_bytes(raw);row['streams'][n]=dict(bytes=len(raw),sha256=sha(raw),eof=eof[n])
        put(folder/'receipt.json',row)
    return row
rows=[]
for mode in ['normal','optimized']:
    if time.monotonic()-START>=900:break
    row=child(mode);rows.append(row)
    print(json.dumps(dict(mode=mode,exitCode=row.get('exitCode'),unknownCustody=row['unknownCustody'],elapsedSeconds=row['elapsedSeconds'])),flush=True)
    if row['unknownCustody']:break
put(HERE/'host-receipt.json',dict(commands=rows,elapsedSeconds=time.monotonic()-START,invocations=len(rows),maximumInvocations=2,perInvocationSeconds=120,wholeTaskLimitSeconds=900,perStreamBytes=LIMIT,aggregateLimitBytes=32*1024*1024,retainedStreamBytes=sum(v['bytes'] for r in rows for v in r['streams'].values()),allCustodyResolved=all(not r['unknownCustody'] for r in rows),reviewScripts={n:sha((HERE/n).read_bytes()) for n in ['run_host_controls.py','review_tests.py']},nativeAttempts=0,builds=0,devicesCreated=0,frontendsLaunched=0,UIActions=0,heldProcessOperations=0))
