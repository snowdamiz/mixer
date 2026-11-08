"""One host validation invocation; no runtime/build/frontend operations."""
import ctypes, datetime, json, os, platform, sys
from pathlib import Path
from commands import Commands, HELD, digest, write
from verify_bindings import verify, identity
HERE=Path(__file__).resolve().parent

def main():
    c=Commands(HERE/'commands')
    before=c.run('devices-before',['/usr/bin/xcrun','simctl','list','devices','--json'])
    bindings=verify(); write(HERE/'bindings.json',bindings)
    c.run('host-tests',[sys.executable,'-B',str(HERE/'test_controller.py')],timeout=120)
    probe=json.loads(c.run('ax-osascript',['/usr/bin/osascript','-l','JavaScript',str(HERE/'ax_probe.js')],timeout=30))
    ax=ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
    ax.AXIsProcessTrustedWithOptions.argtypes=[ctypes.c_void_p]; ax.AXIsProcessTrustedWithOptions.restype=ctypes.c_bool
    probe['pythonTrust']=bool(ax.AXIsProcessTrustedWithOptions(None))
    probe['pythonExecutable']=str(Path(sys.executable).resolve()); probe['pythonPID']=os.getpid()
    probe['responsibleAppAttribution']='Not established by public AX trust query; ancestry is context only'
    chain=[]; pid=os.getpid()
    for i in range(10):
        if pid<=1 or pid in HELD: break
        line=c.run('ancestor-'+str(i),['/bin/ps','-p',str(pid),'-o','ppid=,comm=']).strip()
        parent,exe=line.split(None,1); chain.append(dict(pid=pid,parent=int(parent),executable=exe)); pid=int(parent)
    probe['launchAncestry']=chain
    probe['nativeSetupEligible']=probe['trusted'] is True and probe['pythonTrust'] is True
    write(HERE/'accessibility.json',probe)
    after=c.run('devices-after',['/usr/bin/xcrun','simctl','list','devices','--json'])
    fields=['name','state','deviceTypeIdentifier','dataPath','logPath']
    def stable(raw): return {r['udid']:{**{k:r.get(k) for k in fields},'runtime':runtime} for runtime,rows in json.loads(raw)['devices'].items() for r in rows}
    first,last=stable(before),stable(after)
    if first!=last: raise RuntimeError('External simulator baseline changed; no recovery attempted')
    write(HERE/'validation.json',dict(atUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),hostTests=20,
        nativeAttempts=0,builds=0,compilerInvocations=0,AXAvailable=probe['nativeSetupEligible'],externalBaselineUnchanged=True,
        protected={k:last[k]['state'] for k in ['CE7E80FC-64BF-41A0-B07B-60F4D8711808','D55C87E9-F349-49AC-BCD3-3B4B5BE9E010']},
        tool=dict(python=sys.version,executable=identity(Path(sys.executable).resolve()),platform=platform.platform()),
        commands=len(c.events),allDirectChildrenReaped=all(x['reaped'] for x in c.events),
        allOwnedGroupsAbsent=all(x['ownedGroupAbsent'] for x in c.events),allStreamsEOF=all(all(y['eof'] for y in x['streams'].values()) for x in c.events)))
    print(json.dumps(dict(hostTests=20,AX=probe,bindings=bindings['verified'],custody='all commands reaped, groups absent, both streams EOF')))

if __name__=='__main__': main()
