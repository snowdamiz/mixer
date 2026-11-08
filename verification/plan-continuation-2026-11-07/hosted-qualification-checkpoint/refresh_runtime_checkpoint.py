"""Record observed runtime and permission results without promoting GA gates."""
import datetime
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent
PREFIX = str(BASE.relative_to(ROOT)) + '/'
OUT = Path(__file__).resolve().parent


def read(name):
    return json.loads((BASE / name).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


runtime = read('native-custody-premise/runtime-attempt/receipt.json')
require(runtime['status'] == 'passed-smoke', 'runtime result')
require(runtime['cleanup']['allTerminalCustody'] and runtime['cleanup']['scratchRemoved'], 'runtime cleanup')
require(len(runtime['commands']) == 50 and all(c['terminal_custody'] for c in runtime['commands']), 'command custody')
require(read('pair9-api28-package-acceptance.json')['decision'] == 'ACCEPT_EXACT_PAIR9_API28_PACKAGE_ONLY', 'package acceptance')
require(not read('apple-accessibility-after-toggle/receipt.json')['bothTrusted'], 'AX observation')

replacements = [
    ('A fresh bounded campaign is testing the custody premise before selecting another controller. Callback/restoration/silence evidence remains pending.',
     'The [custody premise campaign](verification/plan-continuation-2026-11-07/native-custody-premise/packet.json) selected reaping before signalling and before group-absence checks, with EPERM still stopping on unknown custody. [Independent controller review](verification/plan-continuation-2026-11-07/native-custody-review/review.json) admitted one attempt. That [API37 arm64 run](verification/plan-continuation-2026-11-07/native-custody-premise/runtime-attempt/receipt.json) passed 104 checks, including the original 11 smoke assertions, main-thread motion callbacks, owner refresh, exact packet preservation, effective/raw restoration and observed silence after listener removal. All 50 owned command records reached terminal custody; scratch and private keys were removed. Independent actual-runtime review is pending; the earlier failures and holds remain unchanged.'),
    ('Independent package review is active. ART/JNI runtime remains unrun, and pair8 packaging does not qualify pair9.',
     '[Independent review and root acceptance](verification/plan-continuation-2026-11-07/pair9-api28-package-acceptance.json) cover this exact package only. ART/JNI runtime remains unrun; a controller using the accepted lifecycle is being prepared for the exact APK. Historical PAIR8 harness labels require binding the runtime result to the accepted pair9 APK hash.'),
    ('A [safe controller successor](verification/plan-continuation-2026-11-07/apple-safe-keyboard-controller/REPORT.txt) is under independent review. Fresh public AX checks returned false for osascript and Python; the responsible TCC entry remains unconfirmed.',
     '[Independent safe-controller review](verification/plan-continuation-2026-11-07/apple-safe-keyboard-review/REPORT.txt) requires fixes for exception latching, uncertain window identity, missing held groups and nested-process custody; R2 is in progress. macOS27.0.1 calls the permission pane Device Control and Data Access. Retained TCC logs identify Acid (`com.t3tools.t3code`) as responsible for both helpers. After the user toggled only Acid off and back on, [fresh osascript and Python checks still report false](verification/plan-continuation-2026-11-07/apple-accessibility-after-toggle/receipt.json). Installed Acid has an ad hoc signature; a read-only identity investigation is pending, with no signing or permission change.'),
    ('The user has been asked to identify the Accessibility entries. Original Tab remains dependent on verified access and safe cleanup.',
     'The user screenshot shows Acid enabled in the correct pane. Original Tab remains dependent on verified access and safe cleanup; no additional native attempt was consumed.'),
    ('R2 passes 13 host groups and is under independent review. Its permanent admission closure after 16 distinct credential fingerprints is a specific root review concern.',
     'R2 passes 13 host groups, but [independent review](verification/plan-continuation-2026-11-07/store-status-review-r2/REPORT.md) rejects its permanent admission closure after 16 distinct credential fingerprints. A separate R3 correction is active to preserve historical credential redaction while allowing normal credential rotation.'),
]
snapshots = {}
for name in ('PLAN.md', 'STATUS.md'):
    path = ROOT / name
    original = path.read_text()
    current, marker, historical = original.partition('\n## Previous')
    snapshots[name] = current
    for old, new in replacements:
        require(current.count(old) == 1, name + ': stale checkpoint phrase')
        current = current.replace(old, new)
    path.write_text(current + marker + historical)
    require(path.read_text().partition('\n## Previous')[2] == historical, 'historical section changed')

checkpoint = 'Pair9 R2 at96f03ab6 has independently accepted ordinary host CI and hosted six-consumer Java/D8 evidence. One API37 arm64 run passes104checks with50terminal command records and clean scratch; actual-runtime review pending. API28 package accepted; ART/JNI unrun and controller preparation active. All historical custody holds remain; no GA promotion.'
for name, key, ids in [('work-graph.json', 'packages', {'W02', 'W05'}), ('gates/ga.json', 'gates', {'G02', 'G06'})]:
    path = ROOT / name
    data = json.loads(path.read_text())
    gate_states = [(x['id'], x.get('status')) for x in data[key]]
    for item in data[key]:
        if item['id'] in ids:
            item['currentCheckpoint'] = checkpoint
            c = item['continuation20261107']
            c['state'] = 'pair9 host/Java accepted; API37 actual pass awaiting review; API28 package accepted'
            c['nativeCustodyCampaign'].update(state='accepted prospective controller; one actual API37 attempt passed', review=PREFIX + 'native-custody-review/review.json', historicalHoldsCleared=False)
            c['pair9API37Actual'] = {
                'status': 'passed-smoke; independent actual review pending',
                'receipt': PREFIX + 'native-custody-premise/runtime-attempt/receipt.json',
                'sourceRevision': runtime['sourceRevision'], 'attempts': 1,
                'checks': 104, 'originalSmokeChecks': 11, 'motionChecks': 93,
                'commands': 50, 'recordedTerminalCustody': True,
                'scratchRemoved': True, 'effectiveAndRawRestored': True,
                'runtimeAccepted': False, 'gaAccepted': False,
            }
            c['pair9API28Packaging'].update(state='independently accepted exact package; runtime unrun', acceptance=PREFIX + 'pair9-api28-package-acceptance.json', runtimeExecuted=False)
        if name == 'work-graph.json' and item['id'] == 'W04':
            item['currentCheckpoint'] = 'Settings passes; original firstTab fails. Safe-controller review requests four corrections; R2 active. TCC identifies Acid; user toggled Acid permission off/on but both helpers still report false. One original native attempt remains; protected-device recovery and failed cleanup remain recorded.'
            item['continuation20261107']['accessibility'].update(responsibleApp='com.t3tools.t3code', systemPane='Device Control and Data Access', userToggledAcid=True, bothHelpersTrusted=False, afterToggle=PREFIX + 'apple-accessibility-after-toggle/receipt.json', controllerReview=PREFIX + 'apple-safe-keyboard-review/REPORT.txt')
        if name == 'work-graph.json' and item['id'] == 'W13':
            item['currentCheckpoint'] = 'Existing ASC status R2 passed13hostgroups but independent review rejected permanent16credential lockout. R3 correction active; historical credential redaction must remain. Canonical integration,103input rebind and freshconsumers pending; no liveASC/store/D6 acceptance.'
    require(gate_states == [(x['id'], x.get('status')) for x in data[key]], 'gate status changed')
    path.write_text(json.dumps(data, indent=2) + '\n')
with (OUT / 'runtime-checkpoint-before.json').open('x') as stream:
    stream.write(json.dumps(snapshots, indent=2) + '\n')
result = {
    'schema': 1, 'updatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'historicalMarkdownSectionsUnchanged': True, 'gateStatesUnchanged': True,
    'changed': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ('PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json')},
    'nativeReceiptSHA256': hashlib.sha256((BASE / 'native-custody-premise/runtime-attempt/receipt.json').read_bytes()).hexdigest(),
}
with (OUT / 'runtime-checkpoint-receipt.json').open('x') as stream:
    stream.write(json.dumps(result, indent=2) + '\n')
print(json.dumps({'updated': list(result['changed']), 'gaPromoted': False}))
