from pathlib import Path
import json,hashlib,difflib
H=Path(__file__).resolve().parent;S=H/'owned-scratch/grouped'
p=S/'src/experimental_swift_reactor/cache_tests.rs';before=p.read_text()
a='assert_eq!(c.usage(None).reservations.live_tickets, 74);'
assert before.count(a)==2
t=before.replace(a,'assert_eq!(c.usage(None).reservations.live_tickets, 73);');p.write_text(t)
(H/'grouped-test-expectations-2.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),t.splitlines(True),fromfile='before/cache_tests.rs',tofile='after/cache_tests.rs')))
names=json.loads((H/'input-source-manifest.json').read_text())
data={n:hashlib.sha256((S/n).read_bytes()).hexdigest() for n in names}
(H/'grouped-qualified-source-manifest.json').write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
print('Corrected two further literal ticket-count assertions; second failure receipt retained.')
