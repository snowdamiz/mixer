#!/usr/bin/env python3
"""Derive a separate font-candidate copy from the sealed public measurement harness."""
from pathlib import Path
import difflib,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'apple-appearance-measurement'
receipt=json.loads((BASE/'receipt.json').read_text())
for e in receipt['artifacts']:
 p=BASE/e['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256']
 if e['path'].startswith(('instrumented-sdk/','harness/')) and 'xcuserdata' not in p.parts and '.xcworkspace' not in e['path']:
  t=ROOT/e['path'];t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(p.read_bytes())
renderer=ROOT/'instrumented-sdk/Sources/MixerApple/MixerNativeView.swift';original=renderer.read_text();s=original
s=s.replace('''        case .button:
            return AnyView(SwiftUI.Button(node.properties["label"]!.string!, role: buttonRole) { emit(.activate) })''','''        case .button:
            if FontProfileEvidence.candidateEnabled {
                return AnyView(SwiftUI.Button(node.properties["label"]!.string!, role: buttonRole) { emit(.activate) }.font(.body))
            }
            return AnyView(SwiftUI.Button(node.properties["label"]!.string!, role: buttonRole) { emit(.activate) })''')
s=s.replace('''            return AnyView(SwiftUI.Toggle(node.properties["label"]!.string!, isOn: binding))''','''            if FontProfileEvidence.candidateEnabled {
                return AnyView(SwiftUI.Toggle(node.properties["label"]!.string!, isOn: binding).font(.body))
            }
            return AnyView(SwiftUI.Toggle(node.properties["label"]!.string!, isOn: binding))''')
s=s.replace('''                    SwiftUI.Text(title).background(MeasurementProbe(nodeID: node.id + ".header",
                        kind: "sectionHeader", explicitFont: nil))''','''                    if FontProfileEvidence.candidateEnabled {
                        SwiftUI.Text(title).font(.headline).background(MeasurementProbe(nodeID: node.id + ".header",
                            kind: "sectionHeader", explicitFont: .headline))
                    } else {
                        SwiftUI.Text(title).background(MeasurementProbe(nodeID: node.id + ".header",
                            kind: "sectionHeader", explicitFont: nil))
                    }''')
assert s!=original and s.count('FontProfileEvidence.candidateEnabled')==3
renderer.write_text(s)
(ROOT/'candidate-fonts.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='sealed-measurement/MixerNativeView.swift',tofile='font-profile/MixerNativeView.swift')))
app=ROOT/'harness/ReferenceApp.swift';s=app.read_text().replace('struct MeasurementApp: App','struct FontProfileApp: App')
s=s.replace(r'''    @Environment(\.colorScheme) private var colorScheme''',r'''    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.fontResolutionContext) private var fontContext''')
s=s.replace('''                        colorScheme: colorScheme == .dark ? "dark" : "light")''','''                        colorScheme: colorScheme == .dark ? "dark" : "light")
                    try FontProfileEvidence.write(context: fontContext,
                        fixture: fixture, dynamicType: String(describing: dynamicTypeSize))''')
s=s.replace('''        MixerNativeView(host: host, onAction: { _ in })''','''        MixerNativeView(host: host, onAction: { _ in })
            .background(FontLineBoxSampler())''')
app.write_text(s)
old=ROOT/'harness/MixerAppearanceMeasurement.xcodeproj';new=ROOT/'harness/MixerAppearanceFontProfile.xcodeproj';new.mkdir(exist_ok=True)
s=(old/'project.pbxproj').read_text().replace('MixerAppearanceMeasurement','MixerAppearanceFontProfile').replace('dev.mixer.appearancemeasurement','dev.mixer.appearancefontprofile')
(new/'project.pbxproj').write_text(s);shutil.rmtree(old)
(ROOT/'input-lock.json').write_text(json.dumps(dict(format='mixer.apple-appearance-font-profile-inputs.1',baselineRevision=receipt['baselineRevision'],baselineTree=receipt['baselineTree'],
 measurementReceiptSHA256=hashlib.sha256((BASE/'receipt.json').read_bytes()).hexdigest(),measurementCollectionSHA256=receipt['artifactCollectionSHA256'],
 measurementSourceCollectionSHA256=receipt['sourceCollectionSHA256'],sourceFiles=[e for e in receipt['artifacts'] if e['path'].startswith(('instrumented-sdk/','harness/'))]),indent=2)+'\n')
print('Derived separate candidate font copy; both earlier sealed evidence sets remain immutable.')
