import sys,subprocess,socket,json,time,zlib,struct
from pathlib import Path
def forbidden(*args,**kwargs):raise AssertionError('Native command/service forbidden in independent host probe')
subprocess.Popen=forbidden
socket.socket.bind=forbidden
socket.socket.connect=forbidden
sys.path.insert(0,sys.argv[1])
import composition
base=Path(composition.selection['outputBase'])
runtime=base/'runtime';runtime.mkdir()
documents=base/'synthetic-documents';documents.mkdir()
bridge=composition.h.Bridge({'diagnostic':documents},runtime/'captures','a'*64,composition.selection['trustedRootSelection']['ownedSimulatorIdentity'],allowed_cases={'keyboard-enabled-off'})
rows=[]
def observe(stage):
    inventory=[{'name':p.name,'kind':'directory' if p.is_dir() else 'file'} for p in sorted((runtime/'captures').iterdir())]
    try:result=composition.join_support.application_captures(base);accepted=True;failure=None
    except Exception as error:result=None;accepted=False;failure=type(error).__name__+': '+str(error)
    rows.append({'stage':stage,'inventory':inventory,'accepted':accepted,'failure':failure,'capturedRoles':None if result is None else sorted(result)})
observe('actual-composed-bridge-construction')
bridge.settings.request({'kind':'start','case':composition.telemetry.CASE,'uptime':time.monotonic()})
observe('actual-session-start-transaction-commit')
def chunk(name,payload):return struct.pack('>I',len(payload))+name+payload+struct.pack('>I',zlib.crc32(name+payload)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\x00\x00\x00'))+chunk(b'IEND',b'')
composition.telemetry.png(png)
bridge.persistence.commit(('settings-0001',{'record':'host-only-independent-synthetic-payload-publication'}),[('settings-0001-ax','ax',b'Host-only synthetic AX text'),('settings-0001-png','png',png)])
observe('actual-transactionstore-ax-and-png-publication')
print(json.dumps({'syntheticOnly':True,'nativeExecuted':False,'rows':rows,'guardAbsent':not bridge.persistence.guard.exists(),'retirementPending':bridge.persistence.retirement_pending,'persistenceUncertain':bridge.persistence.uncertain},sort_keys=True))
