#!/usr/bin/env python3
"""Once-only seal creation after the file-only audit; verify.py never writes."""
import datetime
import sys
from common import *
from verify import audit, inventory, REPORT

def main():
    assert not (BASE / 'handoff.json').exists() and not (BASE / 'handoff.sha256').exists()
    result = audit()
    (BASE / 'seal-receipt.json').write_bytes(canonical({'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(BASE / 'seal.py')], 'cwd': str(ROOT), 'python': sys.version,
        'verifier': binding(BASE / 'verify.py'), 'common': binding(BASE / 'common.py'), 'report': binding(REPORT),
        'readOnlyPreSealAudit': result, 'nativeExecuted': False, 'runtimeSelected': False, 'gaAccepted': False}))
    members = inventory()
    handoff = {'schema': 1, 'scope': 'Exact selected sources; freshly compiled and linked generic iOS Simulator app and runner; build only',
               'sourceRevisionReportedByRoot': REVISION, 'rootSelectionSHA256': PINS[SELECTION],
               'selectedSourceArchiveSHA256': PINS[SOURCE], 'members': members, 'memberTreeSHA256': sha(canonical(members)),
               'audit': result, 'nativeExecuted': False, 'nativeAccepted': False, 'runtimeSelected': False,
               'futureRuntimeIngestionAccepted': False, 'originalOraclePassed': False, 'gaAccepted': False,
               'physicalPhones': 'disconnected-deferred'}
    raw = canonical(handoff)
    (BASE / 'handoff.json').write_bytes(raw)
    (BASE / 'handoff.sha256').write_text(sha(raw) + '  handoff.json\n')
    print(json.dumps({'handoffSHA256': sha(raw), 'sealedMembers': len(members), **result}, indent=2, sort_keys=True))

if __name__ == '__main__': main()
