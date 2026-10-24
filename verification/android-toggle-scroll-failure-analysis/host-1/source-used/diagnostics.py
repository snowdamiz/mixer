"""Root-only finite private trace export, separate from inherited log budget."""
import hashlib,json,re
LIMIT=524288
def capture(execute,identity,process,adb,package,out,receipt,root):
    record={'scope':'private original-protocol scroll trace on exact owned emulator','maximumRetainedBytes':LIMIT+8192,'beforeEmulatorCleanup':True,'captures':[],'status':'not-captured'}
    receipt['scrollDiagnostics']=record
    def command(name,argv,maximum):
        entry={'name':name,'argv':list(map(str,argv)),'maximumRetainedBytes':maximum};record['captures'].append(entry)
        try:
            result=execute(entry['argv'],cwd=root,timeout=15);retained=result.stdout[:maximum];path=out/(name+'.log')
            with path.open('xb') as stream:stream.write(retained)
            entry.update(exitCode=result.returncode,output=path.name,bytes=len(retained),sha256=hashlib.sha256(retained).hexdigest(),observedBytes=len(result.stdout),truncated=len(result.stdout)>maximum,ownedCommandGroupCleanup=result.groupCleanup)
            return result.returncode,retained
        except BaseException as error:entry['failure']=repr(error);return -1,b''
    if process is None or process.poll() is not None:record['status']='owned emulator unavailable';return
    code,data=command('scroll-owned-process',['ps','-p',str(process.pid),'-o','pid=,pgid=,command='],8192)
    if code or not identity(data.decode(errors='replace').strip(),process.pid):record['status']='refused exact owned identity';return
    command('scroll-private-trace',adb+['exec-out','run-as',package,'cat','files/toggle-scroll-trace.json'],LIMIT)
    record['status']='finite trace export attempted before unchanged owned cleanup'
def bind_trace(record,instrument,out):
    rows=[row for row in record['captures'] if row['name']=='scroll-private-trace'];declared=re.findall(rb'INSTRUMENTATION_RESULT: scrollTraceSHA256=([0-9a-f]{64})',instrument)
    bound=len(rows)==1 and rows[0].get('exitCode')==0 and not rows[0].get('truncated',True) and declared==[rows[0]['sha256'].encode()]
    record['instrumentationHashVerified']=bound;record['traceValid']=False
    if not bound:return False
    try:
        value=json.loads((out/rows[0]['output']).read_text());entries=value['entries']
        record['entryCount']=len(entries);record['traceValid']=value['schema']==1 and value['mode']=='original-protocol' and value['dropped']==0 and value['observerFailures']==0 and value['listenerConsumes'] is False and 0<len(entries)<=2048
        record['completedScrollCases']=[row['case'] for row in entries if row['stage']=='scroll.geometry.after']
        record['conjunctStates']=[{'case':row['case'],'state':row['state']} for row in entries if row['stage']=='scroll.geometry.after']
    except (KeyError,TypeError,ValueError,OSError) as error:record['validationFailure']=repr(error)
    return record['traceValid']
