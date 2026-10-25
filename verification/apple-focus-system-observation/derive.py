#!/usr/bin/env python3
"""Exact two-member isolated derivative; refuses a drifted accepted source."""
import hashlib,json,pathlib,difflib
HERE=pathlib.Path(__file__).resolve().parent
BASE=HERE/'inputs/accepted/source/Prototype'
OUT=HERE/'candidate/accepted/source/Prototype'
changes={}
def replace(text,old,new):
 assert text.count(old)==1,old
 return text.replace(old,new)
for name in ['main.swift','DiagnosticTrace.swift']:
 old=(BASE/name).read_text();new=old
 if name=='main.swift':
  new=replace(new,'        super.viewDidLoad()\n','        super.viewDidLoad()\n        DiagnosticTrace.shared.focusSystemObserver = { [weak self] site, sequence in\n            guard let self else { return }\n            FocusSystemObservation.shared.capture(site: site, contextSequence: sequence, stage: self.stage, controller: self,\n                                                  controls: [self.toggle, self.referenceButton, self.nextButton])\n        }\n')
  new=replace(new,'    func snapshot() -> [String:Any] {\n        [','    func snapshot() -> [String:Any] {\n        DiagnosticTrace.shared.focusSystemObserver?("snapshot", nil)\n        return [')
  new=replace(new,'"referencePan": trace.gesture(referencePanSurface.pan)]','"referencePan": trace.gesture(referencePanSurface.pan), "focusSystemDiagnostic": FocusSystemObservation.shared.value]')
 else:
  new=replace(new,'    static let shared = DiagnosticTrace()\n','    static let shared = DiagnosticTrace()\n    var focusSystemObserver: ((String, Int?) -> Void)?\n')
  new=replace(new,'"previous": focusEndpoint(context.previouslyFocusedItem), "next": focusEndpoint(context.nextFocusedItem)])\n','"previous": focusEndpoint(context.previouslyFocusedItem), "next": focusEndpoint(context.nextFocusedItem)])\n        focusSystemObserver?(source + "-callback", focusContextRevision)\n')
  new+=(HERE/'FocusSystemObservation.swift.fragment').read_text()
 (OUT/name).write_text(new)
 changes[name]={'beforeSHA256':hashlib.sha256(old.encode()).hexdigest(),'afterSHA256':hashlib.sha256(new.encode()).hexdigest()}
 (HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='accepted/'+name,tofile='candidate/'+name)))
(HERE/'source-changes.json').write_text(json.dumps({'schema':1,'changedMembers':changes,'originalArchiveMembers':40,'candidateMembers':40,'unchangedMembers':38},indent=2,sort_keys=True)+'\n')
print(json.dumps(changes,sort_keys=True))
