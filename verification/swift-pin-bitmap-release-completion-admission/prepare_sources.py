#!/usr/bin/env python3
"""Pure file preparation only. Subject execution is exclusively guarded separately."""
import unittest.mock
import offline
offline.install()
from pathlib import Path
import ast, difflib, hashlib, json
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE = HERE.parent/'swift-pin-bitmap-match-host-admission'

def write(name, text):
    (HERE/name).write_text(text)

def row(path):
    raw=path.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def replace_once(text, old, new):
    assert text.count(old)==1,(old,text.count(old));return text.replace(old,new,1)

for n in ('bounded_commands.py','offline.py','reuse.json'):
    (HERE/n).write_bytes((BASE/n).read_bytes())
write('.gitignore','/local/\n/host-controls-result.json\n/parser-controls-result.json\n/controls-result.json\n/__pycache__/\n/pure-*/\n')
s=(BASE/'admit.py').read_text()
s=replace_once(s,"PROFILE = 'pin-bitmap-lint-regression-v1'","PROFILE = 'pin-bitmap-release-completion-v1'")
s=replace_once(s,"WORKFLOW_PATH = '.github/workflows/swift-pin-bitmap-lint-regression-admission.yml'","WORKFLOW_PATH = '.github/workflows/swift-pin-bitmap-release-completion-admission.yml'")
s=replace_once(s,'ACTIVE_SECONDS, CLEANUP_SECONDS = 1800, 60','ACTIVE_SECONDS, CLEANUP_SECONDS = 660, 60')
s=replace_once(s,"MIXER_PIN_BITMAP_LINT_SELECTION","MIXER_PIN_BITMAP_RELEASE_SELECTION")
for line in s.splitlines(keepends=True):
    if any("'name': '"+n+"'" in line for n in ('format-candidate','clippy-candidate','debug-regression')):
        s=replace_once(s,line,'')
start=s.index("        elif spec['name'] == 'clippy-candidate':")
end=s.index("        elif spec['name'].endswith('-regression'):",start)
s=s[:start]+s[end:]
start=s.index("            if spec['name'] == 'format-candidate':")
end=s.index("            row['sourceAfter']",start)
s=s[:start]+s[end:]
s=replace_once(s,"'maxChildren': 6,","'maxChildren': 3,")
s=replace_once(s,"temp, toolbin = hosted(); manifest, data = inputs(); node = choose_node(temp)","temp, toolbin = hosted(); manifest, data = inputs(); prior = prior_evidence(); node = choose_node(temp)")
s=replace_once(s,"'commands': [], 'errors': [], 'automaticRetry': False,", "'commands': [], 'errors': [], 'automaticRetry': False, 'priorActualEvidence': prior,")
s=replace_once(s,"need(len(receipt['commands']) == 6, 'Exactly six managed children')","need(len(receipt['commands']) == 3, 'Exactly three managed children')")
s=replace_once(s,"receipt['formattedSourceClosure'] = closure(expected)","receipt['unchangedSourceClosure'] = closure(expected)")
s=replace_once(s,"receipt['status'] = 'host-regression-completed'; receipt['DebugPassed'] = receipt['ReleasePassed'] = 699; receipt['ignored'] = 0", "receipt['status'] = 'host-release-completed'; receipt['ReleasePassed'] = 699; receipt['ignored'] = 0")
s=replace_once(s,"'plannedChildren': 6,", "'plannedChildren': 3,")
# Retain the base helper, source/Node and preflight/postflight APIs exactly.
# The formatter/lint pure helper definitions remain for source compatibility,
# but no formatter/Clippy/Debug command or formatting evidence execution remains.
prior='''def prior_evidence():
    path = ROOT / 'verification/swift-pin-bitmap-match-actual-review'
    need(sha(regular(path/'seal.json')) == '935214e22b97e97473d32826923bebcbf68181c3166f8d55b70ec85458357552', 'Prior actual review seal changed')
    seal = json_data((path/'seal.json').read_bytes())
    for name, expected in seal['files'].items():
        bound(path/member(name), expected)
    binding = json_data(regular(HERE/'prior-evidence.json').read_bytes())
    need(binding == PRIOR_EVIDENCE, 'Prior evidence attribution changed')
    return binding


'''
review=json.loads((HERE.parent/'swift-pin-bitmap-match-actual-review/sanitized-result.json').read_text())
pe={'schema':1,'scope':'Historical independent actual review; no rerun and no reversal of failed host admission','reviewPath':'verification/swift-pin-bitmap-match-actual-review','reviewSealSHA256':'935214e22b97e97473d32826923bebcbf68181c3166f8d55b70ec85458357552','runID':40824584975,'attempt':1,'head':'1eec8e0fc270c0409c8920ee22fd2374f3bd249f','tree':'f20be7de5a047f1983931961cc3d774e56de80a3','artifactID':12876267544,'artifactSHA256':'fdd1b83987eb3ecde7912814f27d9cd18d1f35d68d757eadc01b5d75f925810c','hostAttemptStatus':'failed-after-successful-Debug-command-parser-refusal','oldAllowanceConsumed':True,'newAttemptIsRetry':False,'sourceClosure':review['source']['originalClosure'],'formatter':{'exit':0,'changedBytes':0,'closure':review['source']['formattedClosure']},'clippy':{'exit':0,'compilerArtifacts':38,'buildFinished':True,'diagnostics':[]},'Debug':{'exit':0,'seconds':402.217857,'passed':699,'groups':37,'failed':0,'ignored':0,'measured':0,'filtered':0,'nodeOracleCounts':review['tests']['debug-regression']['oracleCounts'],'hostParserAdmitted':False,'independentlyReconstructedTerminals':699},'Release':{'status':'previously-unrun','observedPasses':None},'newlyPlannedCommands':['compiler-identity','node-identity','release-regression'],'historicalResultsAreNewRuns':False,'canonicalPromotionSelected':False,'GAQualified':False}
write('prior-evidence.json',json.dumps(pe,sort_keys=True,indent=2)+'\n')
s=replace_once(s,"NODE_SCRIPT = ","PRIOR_EVIDENCE = "+repr(pe)+"\nNODE_SCRIPT = ")
s=replace_once(s,'def execute():\n',prior+'def execute():\n')
start=s.index('def test_evidence(text):');end=s.index('def checked_command(',start)
s=s[:start]+(HERE.parent/'swift-pin-bitmap-terminal-parser-correction/parser_function.py').read_text().rstrip()+'\n\n\n'+s[end:]
write('admit.py',s)
workflow=(BASE/'workflow.yml').read_text()
workflow=workflow.replace('Bitmap lint and full host regression admission','Bitmap Release-only completion admission').replace('Sole reviewed candidate including explicit existing-Node oracles','Previously unrun Release on unchanged candidate with corrected terminal evidence parser').replace('pin-bitmap-lint-regression-v1','pin-bitmap-release-completion-v1').replace('swift-pin-bitmap-lint-regression-admission','swift-pin-bitmap-release-completion-admission').replace('swift-pin-bitmap-match-host-admission','swift-pin-bitmap-release-completion-admission')
workflow=replace_once(workflow,'timeout-minutes: 40','timeout-minutes: 22')
workflow=replace_once(workflow,'timeout-minutes: 32','timeout-minutes: 14')
workflow=workflow.replace('Install exact hosted Rust formatting and Clippy tools','Install exact pinned Rust tool identities').replace('Six bounded candidate children','Three bounded Release completion children').replace('Retain exact source formatting, full outputs, identities and custody','Retain Release output, historical attribution, identities and custody').replace('MIXER_PIN_BITMAP_LINT_SELECTION','MIXER_PIN_BITMAP_RELEASE_SELECTION').replace('swift-pin-bitmap-lint-regression-${{','swift-pin-bitmap-release-completion-${{')
workflow=replace_once(workflow,'            /verification/swift-pin-bitmap-lint-independent-admission/\n', '            /verification/swift-pin-bitmap-match-actual-review/\n            /verification/swift-pin-bitmap-match-host-admission/\n            /verification/swift-pin-bitmap-terminal-parser-correction/\n')
workflow=replace_once(workflow,'          python3 -B verification/swift-pin-bitmap-release-completion-admission/controls.py','          python3 -B verification/swift-pin-bitmap-release-completion-admission/controls.py')
write('workflow.yml',workflow)
# Adapt original 27 host control bodies narrowly to the Release-only plan.
c=(BASE/'host_controls.py').read_text()
c=c.replace("(6,8388608,33554432,1800,60)","(6,8388608,33554432,660,60)")
start=c.index('    def test_exact_six_child_vectors_and_bounds(self):')
end=c.index('    def test_ambient_hooks',start)
c=c[:start]+'''    def test_exact_three_child_vectors_and_bounds(self):
        p,e,r,t,tools,node,c = self.fixture(); plan = a.command_plan(p,t,c,node)
        self.assertEqual([x['name'] for x in plan], ['compiler-identity','node-identity','release-regression'])
        self.assertEqual([x['seconds'] for x in plan], [30,30,600]);self.assertEqual(sum(x['seconds'] for x in plan),660)
        self.assertEqual(plan[0]['argv'],[str(t/'rustc'),'-vV'])
        self.assertEqual(plan[1]['argv'],[node['path'],'-e',a.NODE_SCRIPT])
        self.assertEqual(plan[2]['argv'],[str(t/'cargo'),'test','--manifest-path',str(p['source']/'Cargo.toml'),'--locked','--offline','--all-features','--release','--','--include-ignored','--test-threads=1','--show-output'])
        self.assertTrue(all(x['accepted_exits']==(0,) for x in plan))

'''+c[end:]
c=c.replace('a.command_plan(p,t,config,node)[4]','a.command_plan(p,t,config,node)[2]')
# Historical Clippy execution is absent; replace its obsolete runtime test by
# a strict command-plan exclusion and prior-attribution binding control.
start=c.index('    def test_failed_clippy_is_not_runtime_admission(self):')
end=c.index('    def test_node_identity',start)
c=c[:start]+'''    def test_prior_evidence_is_bound_and_never_represented_as_rerun(self):
        binding=a.prior_evidence()
        self.assertEqual(binding['runID'],40824584975);self.assertFalse(binding['historicalResultsAreNewRuns'])
        self.assertFalse(binding['Debug']['hostParserAdmitted']);self.assertEqual(binding['Release']['status'],'previously-unrun')
        p,e,r,t,tools,node,config=self.fixture();plan=a.command_plan(p,t,config,node)
        self.assertEqual({x['name'] for x in plan},{'compiler-identity','node-identity','release-regression'})
        with mock.patch.object(a,'PRIOR_EVIDENCE',{}):
            with self.assertRaisesRegex(RuntimeError,'attribution changed'):a.prior_evidence()

'''+c[end:]
c=c.replace("if failure and name=='clippy-candidate'","if failure and name=='release-regression'")
c=c.replace("self.assertEqual(record['status'],'host-regression-completed');self.assertEqual(len(calls),6)","self.assertEqual(record['status'],'host-release-completed');self.assertEqual(len(calls),3)")
c=c.replace("self.assertEqual(record['DebugPassed'],699);self.assertEqual(record['ReleasePassed'],699);self.assertEqual(record['ignored'],0)","self.assertNotIn('DebugPassed',record);self.assertEqual(record['ReleasePassed'],699);self.assertEqual(record['ignored'],0);self.assertFalse(record['priorActualEvidence']['historicalResultsAreNewRuns'])")
c=c.replace("self.assertTrue((out/'formatted-source-manifest.json').exists());self.assertTrue((out/'node-identity.json').exists())", "self.assertFalse((out/'formatted-source-manifest.json').exists());self.assertFalse((out/'format').exists());self.assertTrue((out/'node-identity.json').exists())")
c=c.replace("failure='mock clippy runtime failure'", "failure='mock Release runtime failure'").replace("self.assertEqual(len(calls),4)","self.assertEqual(len(calls),3)")
c=c.replace('timeout-minutes: 32','timeout-minutes: 14').replace('swift-pin-bitmap-lint-regression-v1','swift-pin-bitmap-release-completion-v1').replace('swift-pin-bitmap-match-host-admission','swift-pin-bitmap-release-completion-admission')
c=replace_once(c,"'python3 -B verification/swift-pin-bitmap-release-completion-admission/controls.py'])", "'python3 -B verification/swift-pin-bitmap-release-completion-admission/controls.py'])")
c=c.replace("return ''.join('test '+n+' ... ok\\n' for n in names)","return 'running 699 tests\\n'+''.join('test '+n+' ... ok\\n' for n in names)")
write('host_controls.py',c)
for n in ('admit.py','host_controls.py','workflow.yml'):
    write(n+'.diff',''.join(difflib.unified_diff((BASE/n).read_text().splitlines(keepends=True),(HERE/n).read_text().splitlines(keepends=True),fromfile='accepted/'+n,tofile='release-only/'+n)))
print(json.dumps({'sourcePreparationOnly':True,'writtenOnly':str(HERE),'admit':row(HERE/'admit.py'),'helper':row(HERE/'bounded_commands.py')}))
