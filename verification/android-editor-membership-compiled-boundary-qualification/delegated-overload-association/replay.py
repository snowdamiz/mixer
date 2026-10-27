from pathlib import Path
import argparse,hashlib,json,os,shutil,signal,subprocess,tempfile,time

BASE=Path(__file__).resolve().parent
def ident(path):
 data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--jdk',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();jdk=args.jdk.resolve();out=args.output.resolve();assert not out.exists()and not out.is_relative_to(BASE);out.mkdir(parents=True);scratch=Path(tempfile.mkdtemp(prefix='owned-delegation-',dir=out));classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir();temp=scratch/'tmp';temp.mkdir();commands=[];status='failed'
 env={'PATH':str(jdk/'bin')+':/usr/bin:/bin','JAVA_HOME':str(jdk),'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC','TMPDIR':str(temp),'TMP':str(temp),'TEMP':str(temp)}
 def run(label,argv):
  start=time.monotonic()
  with (out/(label+'.stdout')).open('wb')as stdout,(out/(label+'.stderr')).open('wb')as stderr:
   child=subprocess.Popen([str(value)for value in argv],cwd=BASE,env=env,stdout=stdout,stderr=stderr,start_new_session=True);timeout=False
   try:child.wait(timeout=60)
   except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
   except BaseException:os.killpg(child.pid,signal.SIGKILL);child.wait();raise
  command={'label':label,'argv':[str(value)for value in argv],'exit':child.returncode,'timeout':timeout,'maximum_seconds':60,'elapsed_seconds':time.monotonic()-start,'reaped':True,'stdout':ident(out/(label+'.stdout')),'stderr':ident(out/(label+'.stderr'))};commands.append(command);save(out/'commands.json',commands);assert child.returncode==0 and not timeout,label
 try:
  signal.alarm(60);manifest=json.loads((BASE/'input-manifest.json').read_bytes());sources=[]
  for item in manifest['sources']:
   rel=Path(item['path']);assert not rel.is_absolute()and'..'not in rel.parts;path=BASE/rel;assert not path.is_symlink()and ident(path)=={key:item[key]for key in('bytes','sha256')};sources.append(path)
  assert{str(path.relative_to(BASE))for path in(BASE/'inputs').rglob('*')if path.is_file()}=={item['path']for item in manifest['sources']};assert ident(BASE/'descriptor.json')==manifest['descriptor'];assert ident(BASE/'producer-run/class-map.json')==manifest['expected_class_map'];tools=json.loads((BASE/'producer-run/source-freeze.json').read_bytes())['tools']
  for name,expected in tools.items():assert ident(jdk/name)==expected,'exact selected JDK tool bytes'
  signal.alarm(0)
  run('java-version',[jdk/'bin/java','-version']);run('javac-version',[jdk/'bin/javac','-version']);run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*sources]);classmap={str(path.relative_to(classes)):ident(path)for path in sorted(classes.rglob('*.class'))};assert classmap==json.loads((BASE/'producer-run/class-map.json').read_bytes()),'exact full actual emitted class closure';save(out/'class-map.json',classmap)
  for name in('TypedSnapshotControls','ObserverFailureControls','EventJoinControls'):run(name,[jdk/'bin/java','-ea','-Xmx256m','-cp',classes,'dev.mixer.android.'+name])
  run('attribute-states',[jdk/'bin/java','-ea','-Xmx512m','-cp',classes,'dev.mixer.android.DirectBoundaryStates',BASE/'descriptor.json','setComposingRegionWithAttributes',out/'attribute-states.rows.jsonl.gz']);status='passed-bounded-host-utility'
 finally:
  signal.alarm(0);shutil.rmtree(scratch);save(out/'receipt.json',{'status':status,'commands':commands,'full_compiled_class_map_matches_selected_packet':status=='passed-bounded-host-utility','all_children_reaped':all(item['reaped']for item in commands),'scratch_removed':not scratch.exists(),'environment':env,'toolchain_admission_full_matrix_native_OTA_GA_accepted':False})
 print(status)
if __name__=='__main__':main()
