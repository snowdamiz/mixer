"""Read materialized source bytes as data and seal this review; execute no subject."""
from pathlib import Path
import hashlib
import json
import stat
import sys

ROOT = Path(__file__).resolve().parents[4]
REC = 'verification/github-delivery-axis-binding-stage-recovery'
PREP = REC + '/local/continuation-preparation'
OUT = ROOT / (REC + '/review/continuation-preparation-review')
FINAL = ROOT / (REC + '/review/continuation-source-review.json')
GUARD = b'raise SystemExit("UNRUN source-only template; root must independently review and materialize exact final bytes before any authority or execution")\n'


def read(path):
    p = ROOT / path
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size < 5000000
    return p.read_bytes()


def row(path):
    b = read(path)
    return {'path': path, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


prep_row = row(REC + '/review/continuation-preparation-review/preparation-review.json')
assert prep_row == {'path': REC + '/review/continuation-preparation-review/preparation-review.json', 'bytes': 16084, 'sha256': '8e56194d7acd26c98ea83bbd2fe6e3d779964fba37b6462af45425f84a6783af'}
accepted = json.loads(read(prep_row['path']))
assert accepted['decision'] == 'accept-exact-stage-recovery-continuation-preparation-pending-final-file-readback'
assert row(accepted['readSet']['path']) == accepted['readSet']
readset = json.loads(read(accepted['readSet']['path']))
for expected in readset['rows']:
    assert row(expected['path']) == expected, expected['path']

readback = []
for expected in accepted['driverSources']:
    name = expected['path'].rsplit('/', 1)[-1]
    template = read(PREP + '/' + name + '.template')
    lines = template.splitlines(keepends=True)
    assert lines[1] == GUARD and template.count(GUARD) == 1
    final_bytes = b''.join(lines[:1] + lines[2:])
    assert read(expected['path']) == final_bytes and row(expected['path']) == expected
    readback.append({'kind': 'driver', **expected, 'exactReconstructedFinalBody': True})
for phase, expected in accepted['argvApprovals'].items():
    name = expected['path'].rsplit('/', 1)[-1]
    assert read(expected['path']) == read(PREP + '/' + name) and row(expected['path']) == expected
    readback.append({'kind': 'argv', 'phase': phase, **expected, 'exactPreparedManifest': True})
for expected in (accepted['helper'], accepted['inspectionSource'], accepted['inspectionRootSeal'], *accepted['acceptedInspectionRows']):
    assert row(expected['path']) == expected
readback_path = REC + '/review/continuation-preparation-review/final-readback.json'
(ROOT / readback_path).write_text(json.dumps({'schema': 1, 'decision': 'all-eleven-materialized-source-and-argv-files-match-reviewed-bytes', 'preparationReview': prep_row, 'readback': readback, 'retainedFrozenReadSetMembers': len(readset['rows']), 'subjectHelperControlExecution': 0, 'gitGhCompilerNetworkProbeSignalNativeUIActions': 0, 'python': sys.version}, indent=2) + '\n')
final = {'schema': 1, 'decision': 'accept-exact-stage-recovery-continuation-source', 'selection': accepted['selection'], 'baseline': accepted['baseline'], 'driverSources': accepted['driverSources'], 'helper': accepted['helper'], 'inspectionSource': accepted['inspectionSource'], 'argvApprovals': accepted['argvApprovals'], 'preparationReview': prep_row, 'finalReadback': row(readback_path), 'acceptedInspectionSeal': accepted['inspectionRootSeal'], 'acceptedInspectionRows': accepted['acceptedInspectionRows'], 'acceptedPreflight': accepted['acceptedPreflight'], 'selectedPaths': 123, 'selectedPayloadBytes': 4897969, 'selectedObjectDigestSHA256': accepted['selectedObjectDigestSHA256'], 'phaseCommandCounts': {x['phase']: x['commands'] for x in accepted['phases']}, 'reviewer': 'independent-continuation-source-review-lane', 'sourceOnlyReview': True, 'preparedDataChecks': accepted['dataCheckCount'], 'finalSourceFilesReadBack': 6, 'finalArgvFilesReadBack': 5, 'findings': [], 'commandsExecuted': 0, 'subjectHelperControlExecution': 0, 'gitGhCompilerNetworkProbeSignalNativeUIActions': 0, 'actualAuthorityCreated': False, 'continuationAuthorizedByThisReview': False, 'allExistingHoldsUntouched': True, 'limitations': ['Accepts exact reviewed source and argv bytes only. No subject/helper/control execution or live Git/process/remote evidence was performed.', 'Every phase still requires separate root authority binding these exact rows and actual evidence. Original failed delivery remains consumed and may never be replayed.', 'Engine and axis runtime outcomes, native/device, compiler, custody and GA holds remain outside this source review.']}
with FINAL.open('x') as handle:
    handle.write(json.dumps(final, indent=2) + '\n')
final_row = row(str(FINAL.relative_to(ROOT)))
print(json.dumps({'decision': final['decision'], 'seal': final_row, 'materializedSources': 6, 'materializedArgv': 5, 'retainedFrozenReadSetMembers': len(readset['rows'])}, separators=(',', ':')))
