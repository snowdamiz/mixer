"""Pure review guard; deny all live process/network/session/signal/wait operations."""
import os,sys,signal,socket,subprocess,resource
from pathlib import Path
HERE=Path(__file__).resolve().parent

def denied(*args,**kwargs):raise AssertionError('pure review: real process/network/session/signal/wait denied')
def install():
 sys.dont_write_bytecode=True
 def audit(event,args):
  if event.startswith(('subprocess.','socket.','pty.','ctypes.'))or event in {'os.system','os.fork','os.forkpty','os.posix_spawn','os.exec','os.kill','os.killpg','os.chdir'}:denied()
  if event=='open':
   name,mode,flags=args;writing=isinstance(mode,str)and any(x in mode for x in 'wax+')
   writing|=isinstance(flags,int)and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
   if writing and(not isinstance(name,(str,bytes,os.PathLike))or not Path(os.fsdecode(name)).resolve().is_relative_to(HERE)):denied()
  if event in {'os.remove','os.rmdir','os.mkdir','os.rename','os.chmod'}:
   name=Path(os.fsdecode(args[0]));relative=event in {'os.remove','os.rmdir'}and len(args)>1 and isinstance(args[1],int)and args[1]>=0 and len(name.parts)==1
   if not relative and not name.resolve().is_relative_to(HERE):denied()
   if event=='os.rename'and not Path(os.fsdecode(args[1])).resolve().is_relative_to(HERE):denied()
 sys.addaudithook(audit)
 subprocess.Popen=subprocess.run=subprocess.call=subprocess.check_call=subprocess.check_output=denied
 socket.socket=socket.create_connection=socket.socketpair=resource.getrusage=denied
 for name in [n for n in dir(os)if n.startswith(('exec','spawn','posix_spawn'))]+['system','fork','forkpty','kill','killpg','wait','waitpid','wait3','wait4','waitid','popen','setsid','setpgid','getpgid','getsid']:
  if hasattr(os,name):setattr(os,name,denied)
 for name in ('signal','setitimer','alarm','getsignal','raise_signal','pthread_kill','sigwait','sigwaitinfo','sigtimedwait'):
  if hasattr(signal,name):setattr(signal,name,denied)
