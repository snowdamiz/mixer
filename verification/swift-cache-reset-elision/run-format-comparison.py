#!/usr/bin/env python3
"""Read-only formatting comparison; source copies only, inherited files never rewritten."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,subprocess,time
out=Path(__file__).resolve().parent;root=out.parent.parent
assert not(out/'format-comparison.json').exists()
base=out/'baseline-format';manifest=json.loads((out/'baseline-manifest.json').read_text())
for relative,expected in manifest.items():
 source=root/'vm'/relative;assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
 destination=base/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
parent=json.loads((out/'matrix-fmt.command.json').read_text());env=parent['environment'];rows=[]
for label,cwd,source_manifest in [('candidate-final',out/'scratch','candidate-source-manifest.json'),('baseline',base,'baseline-manifest.json')]:
 stem='format-'+label;argv=parent['argv'];start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True,timeout=30)
 (out/f'{stem}.stdout').write_text(r.stdout);(out/f'{stem}.stderr').write_text(r.stderr)
 files=sorted(set(line.split(str(cwd)+'/',1)[1].rsplit(':',2)[0] for line in r.stdout.splitlines() if line.startswith('Diff in '+str(cwd)+'/')))
 record={'argv':argv,'cwd':str(cwd),'environment':env,'beganAt':began,'elapsedSeconds':time.monotonic()-start,'exitCode':r.returncode,'timeoutSeconds':30,'timedOut':False,'sourceManifestRef':source_manifest,'sourceManifestSHA256':hashlib.sha256((out/source_manifest).read_bytes()).hexdigest(),'stdoutSHA256':hashlib.sha256((out/f'{stem}.stdout').read_bytes()).hexdigest(),'stderrSHA256':hashlib.sha256((out/f'{stem}.stderr').read_bytes()).hexdigest(),'filesWithFormattingDiffs':files}
 (out/f'{stem}.command.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');rows.append(record)
assert rows[0]['exitCode']==rows[1]['exitCode']==1
assert rows[0]['filesWithFormattingDiffs']==rows[1]['filesWithFormattingDiffs']
assert 'src/experimental_swift_reactor/cache.rs' not in rows[0]['filesWithFormattingDiffs']
assert 'src/experimental_swift_reactor/cache_tests.rs' not in rows[0]['filesWithFormattingDiffs']
assert 'src/experimental_swift_reactor/lifecycle_tests.rs' not in rows[0]['filesWithFormattingDiffs']
result={'baselineAndFinalCandidateBothFailInheritedFormatting':True,'sameAffectedFiles':rows[0]['filesWithFormattingDiffs'],'candidateOwnedFilesHaveNoFormatDiff':True,'commands':['format-candidate-final.command.json','format-baseline.command.json']}
(out/'format-comparison.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,indent=2))
