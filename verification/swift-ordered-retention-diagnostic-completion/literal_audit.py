"""Finite source-literal accounting only; never authorizes any release."""
from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent;O=P.parent/'swift-ordered-retention-diagnostic-rust'
source=(P/'completion_tests.rs').read_text()
# These source ranges contain every template executed by the bounded receipt
# formatter, plus start/path-extension literals. Rust strings here use the
# JSON-compatible ASCII escapes verified by json.loads, not arbitrary Rust.
regions=[source[source.index('    fn custody('):source.index('    fn rows(')],
    source[source.index('    fn usage_keys('):source.index('    fn consume(')]]
strings=[json.loads('"'+x+'"') for region in regions for x in re.findall(r'"((?:[^"\\]|\\.)*)"',region)]
receipt_bytes=sum(len(s.encode()) for s in strings)
table=json.loads((O/'source-code-table.json').read_bytes())
code_bytes=sum(len(s.encode()) for s in table.values())
assert len(table)==24 and code_bytes==502 and receipt_bytes<=1024
value={'receiptLiteralBytesConservativeNoDedup':receipt_bytes,'receiptLiteralCharge':1024,
       'supportedCodeCount':len(table),'supportedCodeLiteralBytes':code_bytes,
       'sourceSHA256':hashlib.sha256(source.encode()).hexdigest(),
       'scope':'finite literal accounting; no syntax-only release or full analyzer acceptance'}
(P/'literal-inventory.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');print(json.dumps(value,sort_keys=True))
