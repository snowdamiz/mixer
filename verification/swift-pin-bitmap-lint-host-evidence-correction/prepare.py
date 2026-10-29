#!/usr/bin/env python3
"""Prepare sibling replacements from frozen source; no subject imports."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'swift-pin-bitmap-lint-independent-admission'
assert hashlib.sha256((SOURCE / 'seal.json').read_bytes()).hexdigest() == '2012b4f0aabe97ebc2c10a501ea0f1dcc06791b0b4dcc5db5bb80c371fb28238'
seal = json.loads((SOURCE / 'seal.json').read_text())
for name, expected in seal['files'].items():
    raw = (SOURCE / name).read_bytes()
    assert {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected
old = (SOURCE / 'admit.py').read_text()
new = old
start = new.index('def test_evidence(text):')
end = new.index('\ndef checked_command(', start)
new = new[:start] + '''def test_evidence(text):
    summary_lines = [line for line in text.splitlines() if line.lstrip().startswith('test result:')]
    pattern = r'test result: (ok|FAILED)\\. (\\d+) passed; (\\d+) failed; (\\d+) ignored; (\\d+) measured; (\\d+) filtered out;(?: finished in [^\\r\\n]*)?'
    summaries = [re.fullmatch(pattern, line) for line in summary_lines]
    need(summaries and all(summaries), 'Malformed or missing test summary')
    need(all(m[1] == 'ok' for m in summaries), 'Non-ok test summary')
    rows = [dict(zip(('passed', 'failed', 'ignored', 'measured', 'filtered'), map(int, m.groups()[1:]))) for m in summaries]
    terminals = re.findall(r'^test (\\S+) \\.\\.\\. (ok|FAILED|ignored[^\\n]*)$', text, re.M)
    need(sum(r['passed'] for r in rows) == 699, 'Exactly 699 passed tests required')
    need(all(r[k] == 0 for r in rows for k in ('failed', 'ignored', 'measured', 'filtered')), 'No failed, ignored, measured or filtered tests')
    need(len(terminals) == 699 and all(status == 'ok' for _, status in terminals), 'Exactly 699 terminal ok lines required')
    names = collections.Counter(name for name, _ in terminals)
    need(all(names[n] == 1 for n in ORACLES), 'All nine exact Node oracles must pass once')
    return {'summaries': rows, 'terminals': terminals, 'passed': 699, 'ignored': 0, 'nodeOracles': list(ORACLES),
            'scope': 'Full all-feature host Debug or Release, including explicit development Node oracles; no production Node interpreter'}

''' + new[end:]
start = new.index('def format_evidence(out,arm,source,before,raw_before):')
end = new.index('\ndef cargo_configs_absent(', start)
new = new[:start] + '''def format_roster(source,expected):
 # Traverse only the expected directory skeleton. Unexpected directories and
 # every symlink are recorded as metadata, never followed or read as source.
 directories={'.'}
 for name in expected:
  directories.update(str(p) for p in member(name).parents if str(p)!='.')
 regular_files=set();unexpected=[];unsafe=[];errors=[]
 def visit(directory,relative):
  try:
   no_symlinks(directory)
   with os.scandir(directory)as entries:
    for entry in entries:
     name=entry.name if relative=='.'else relative+'/'+entry.name
     if entry.is_symlink():
      if name in expected or name in directories:unsafe.append(name)
      else:unexpected.append(name)
     elif name in directories:
      if entry.is_dir(follow_symlinks=False):visit(Path(entry.path),name)
      else:unsafe.append(name)
     elif name in expected:
      if entry.is_file(follow_symlinks=False):regular_files.add(name)
      else:unsafe.append(name)
     else:unexpected.append(name)
  except OSError as e:errors.append({'path':relative,**exception_details(e)})
  except RuntimeError as e:errors.append({'path':relative,**exception_details(e)})
 visit(source,'.')
 return {'regularFiles':sorted(regular_files),'missingPaths':sorted(set(expected)-regular_files),
         'unexpectedPaths':sorted(unexpected),'unsafePaths':sorted(unsafe),'errors':errors}

def format_evidence(out,arm,source,before,raw_before):
 dest=out/'format'/arm;dest.mkdir(parents=True,exist_ok=True);diff=[]
 result={'beforeTreeSHA256':closure(before),'afterTreeSHA256':None,'changedPaths':[],
         'outsideOverlayChanges':[],'files':{},'verified':False}
 # The trusted original before bytes survive even if the source root, roster,
 # or an expected after file is now absent, linked, oversized or unreadable.
 for n in OVERLAYS:
  p=dest/'before'/member(n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw_before[n])
  result['files'][n]={'before':before[n],'after':None,'afterAvailable':False}
 roster=format_roster(source,before);result['roster']=roster
 after={};raw_after={};read_errors=[];total=0
 for n in roster['regularFiles']:
  try:
   p=regular(source/member(n));size=p.stat().st_size
   need(size<=MAX_FILE_BYTES,'Source member byte bound')
   need(total+size<=MAX_SOURCE_BYTES,'Source aggregate bound')
   raw=p.read_bytes();need(len(raw)==size,'Source member size changed while reading')
   total+=len(raw);after[n]=file_row(raw)
   if n in OVERLAYS:raw_after[n]=raw
  except (OSError,RuntimeError)as e:read_errors.append({'path':n,**exception_details(e)})
 result['expectedReadErrors']=read_errors
 result['changedPaths']=sorted(n for n in after if after[n]!=before[n])
 result['outsideOverlayChanges']=sorted(set(result['changedPaths'])-set(OVERLAYS))
 roster_ok=not any(roster[k]for k in ('missingPaths','unexpectedPaths','unsafePaths','errors'))
 complete=roster_ok and not read_errors and set(after)==set(before)
 result['availableExpectedTreeSHA256']=closure(after);result['availableExpectedMembers']=len(after)
 if complete:result['afterTreeSHA256']=closure(after)
 decoding_errors=[]
 for n,raw in raw_after.items():
  p=dest/'after'/member(n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  result['files'][n].update(after=after[n],afterAvailable=True)
  try:after_text=raw.decode()
  except UnicodeDecodeError as e:
   decoding_errors.append({'path':n,**exception_details(e)});after_text=raw.decode(errors='replace')
  diff.extend(difflib.unified_diff(raw_before[n].decode().splitlines(keepends=True),after_text.splitlines(keepends=True),fromfile='before/'+n,tofile='after/'+n))
 (dest/'format.diff').write_text(''.join(diff));result['diffSHA256']=sha(dest/'format.diff')
 result['diffScope']='Available expected overlay files only; exact bytes retained separately; replacement decoding used for invalid UTF-8'
 result['diffDecodingErrors']=decoding_errors
 result['verified']=complete and not result['outsideOverlayChanges'] and not decoding_errors;save(dest/'receipt.json',result)
 need(roster_ok,'Formatter source roster changed; retained explicit roster failure')
 need(complete,'Formatter expected source unavailable; retained available expected files')
 need(not decoding_errors,'Formatter after source is not UTF-8; retained exact bytes and replacement-decoded diff')
 need(result['verified'],'Formatter changed outside the fifteen overlays')
 return after,result

''' + new[end:]
(HERE / 'admit.py').write_text(new)
for name in ('bounded_commands.py', 'offline.py'):
    (HERE / name).write_bytes((SOURCE / name).read_bytes())
(HERE / 'admit.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile='frozen/admit.py', tofile='proposed/admit.py')))
print(json.dumps({'sourceOnly': True, 'changedSource': 'admit.py', 'unchangedCopies': ['bounded_commands.py', 'offline.py']}))
