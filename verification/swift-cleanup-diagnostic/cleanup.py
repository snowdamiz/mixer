#!/usr/bin/env python3
"""Remove only this lane's recorded scratch after identity and holder checks."""
import json,os,stat,subprocess,shutil
from pathlib import Path
import collect as c
from owned_process import members

def main():
 h=c.HERE;s=c.scratch();expected=json.loads((h/'session.json').read_text())
 assert s.is_absolute()and str(s).startswith('/private/tmp/mixer-cleanup-repair-')and not s.is_symlink()
 identity=lambda:(s.stat().st_dev,s.stat().st_ino)
 assert identity()==(expected['scratchDevice'],expected['scratchInode'])
 groups=[]
 for path in(h/'commands').glob('*/receipt.json'):
  r=json.loads(path.read_text());assert not r['groupCleanup']['after'];groups.append(r['ownedProcessGroup'])
 surviving={str(group):members(group)for group in sorted(set(groups))if members(group)}
 assert not surviving,surviving
 count=0;size=0
 for base,dirs,files in os.walk(s,followlinks=False):
  for name in files:
   st=os.lstat(Path(base)/name);count+=1;size+=st.st_size
 p=subprocess.run(['lsof','-nP','+D',str(s)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (h/'cleanup-lsof.stdout').write_bytes(p.stdout);(h/'cleanup-lsof.stderr').write_bytes(p.stderr)
 assert p.returncode==1 and not p.stdout and not p.stderr,(p.returncode,p.stdout,p.stderr)
 assert identity()==(expected['scratchDevice'],expected['scratchInode'])
 before=identity();shutil.rmtree(s);assert not s.exists()
 bytecode=h/'__pycache__';bytecode_count=0
 if bytecode.exists():
  bytecode_count=sum(x.is_file()for x in bytecode.rglob('*'));shutil.rmtree(bytecode)
 row={'schema':1,'observedUTC':c.now(),'ownedScratch':str(s),'device':before[0],'inode':before[1],'files':count,'bytes':size,'holderCheckArgv':['lsof','-nP','+D',str(s)],'holderCheckExitCode':p.returncode,'holderCheckEmpty':True,'ownedCommandGroupsChecked':len(set(groups)),'survivingOwnedGroups':surviving,'signalsSentAtFinalCleanup':[],'ownedScratchRemoved':True,'ownedBytecodeFilesRemoved':bytecode_count,'nativeInstancesStarted':0,'deviceDiscovery':False,'physicalRuns':0,'otherProjectProcessesModified':False,'liveSourceModified':False,'gitMutation':False}
 c.save('cleanup.json',row);print('Cleaned',count,'files /',size,'bytes;',len(set(groups)),'finished command groups; zero holders')
if __name__=='__main__':main()
