from pathlib import Path
import shutil,json,hashlib,difflib
Q=Path(__file__).resolve().parent;A=Q/'passive-return-probe';E=Q/'passive-return-probe-v2';E.mkdir(exist_ok=False)
for n in ('NativeOutcomeProbe.java','ProbeOutcomeControls.java','LeafBranchWitness.java','selected-return-sites.json','root-preparation-authority.md'):
 shutil.copy2(A/n,E/n)
shutil.copytree(A/'leaves',E/'leaves')
p=E/'leaves/dev/mixer/android/ConcreteHostProbe.java';s=p.read_text().replace('    public static java.util.function.Consumer<Event> auditSink;\n','').replace('if(auditSink!=null)auditSink.accept(event);String key=method+"/"+phase;','String key=method+"/"+phase;');assert 'auditSink' not in s;p.write_text(s)
for folder in ('source','host-leaves','tests'):shutil.copytree(Q/'inputs/accepted'/folder,E/'inputs'/folder)
for f in (E/'leaves').rglob('*.java'):
 rel=f.relative_to(E/'leaves');original=E/'original'/rel;original.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(Q/'inputs/accepted/host-leaves'/rel,original);shutil.copy2(f,E/'inputs/host-leaves'/rel)
shutil.copy2(E/'NativeOutcomeProbe.java',E/'inputs/host-leaves/dev/mixer/android/NativeOutcomeProbe.java');shutil.copy2(Q/'inputs/accepted/descriptor.json',E/'descriptor.json')
run=(A/'run.py').read_text().replace("shutil.copy2(Q/'inputs/instrumentation/ConcreteHostProbe.java' if rel.name=='ConcreteHostProbe.java' else orig,original)","shutil.copy2(orig,original)")
(E/'run.py').write_text(run)
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
roster=[]
for f in sorted((E/'leaves').rglob('*.java')):
 rel=f.relative_to(E/'leaves');original=E/'original'/rel;diff=''.join(difflib.unified_diff(original.read_text().splitlines(True),f.read_text().splitlines(True),fromfile='actual-accepted/'+str(rel),tofile='isolated-v2/'+str(rel)));out=E/(f.name+'.diff');out.write_text(diff);roster.append({'path':str(rel),'accepted_original':ident(original),'derivative':ident(f),'diff':ident(out)})
roster.append({'path':'dev/mixer/android/NativeOutcomeProbe.java','accepted_original':None,'derivative':ident(E/'NativeOutcomeProbe.java')})
(E/'derivative-source-roster.json').write_text(json.dumps({'schema':2,'exact_file_count':len(roster),'records':roster,'baseline':'Actual accepted source leaves, never earlier instrumentation derivative','removed_pre_count_sink':True,'qualification':'pending independent source/class/state review'},indent=2)+'\n')
shutil.copy2(__file__,E/'prepare_passive_v2.py')
(E/'README.md').write_text('Corrected eight-file passive derivative from actual accepted originals. Pre-count auditSink is entirely absent. Only new qualificationHook executes after original count and ordinary hook. New hook lifetime remains explicit, independent of existing reset semantics. NativeOutcomeProbe captures original scalar/reference once; any capture failure or unclosed new hook refuses. Existing hit positions, counts, branch/evaluation order and ordinary hook work remain unchanged. Six Android leaves, ConcreteHostProbe and new NativeOutcomeProbe are the complete roster. Full38 behavioral/state qualification remains pending; getHandler and requestCursorUpdates(II) are not newly captured by this subset. The first derivative and independent rejection history remain separate.\n')
