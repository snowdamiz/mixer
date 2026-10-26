#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
from run_command import P,run
mode=sys.argv[1];directory='release' if mode=='optimized' else 'debug'
found=[p for p in (P/'scratch/cargo-target'/directory/'deps').glob('mixer_vm-*') if p.is_file() and p.suffix=='']
assert len(found)==1,found
binary=found[0];roster=json.loads((P/'required-tests.json').read_text());prefix=roster['namespace'];expected=roster['methods']
assert run(mode+'-list-all',[str(binary),'--list'])
raw=(P/'logs'/f'{mode}-list-all.stdout').read_text();all_methods=[line[:-6] for line in raw.splitlines() if line.endswith(': test')]
assert len(all_methods)==roster['expected_total'] and len(all_methods)==len(set(all_methods))
selected=sorted(x for x in all_methods if x.startswith(prefix));assert selected==expected,(selected,expected)
assert run(mode+'-list-selected',[str(binary),prefix,'--list'])
raw=(P/'logs'/f'{mode}-list-selected.stdout').read_text();assert sorted(line[:-6] for line in raw.splitlines() if line.endswith(': test'))==expected
artifacts=P/'artifacts'/mode;artifacts.mkdir(parents=True,exist_ok=True)
assert run(mode+'-units',[str(binary),prefix,'--nocapture','--test-threads=1'],{'MIXER_PROFILE_EVIDENCE_DIR':str(artifacts)})
raw=(P/'logs'/f'{mode}-units.stdout').read_text();summary=re.search(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',raw);assert summary
counts=list(map(int,summary.groups()));assert counts==[len(expected),0,0,0,len(all_methods)-len(expected)],counts
executed=re.findall(r'^test ('+re.escape(prefix)+r'\w+) \.\.\.',raw,re.M);assert sorted(executed)==expected
record={'mode':mode,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'compiler_listed_total':len(all_methods),'selected':selected,'passed':counts[0],'failed':counts[1],'ignored':counts[2],'filtered':counts[4],'exact_complete_namespace':True}
(P/f'unit-qualification-{mode}.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
