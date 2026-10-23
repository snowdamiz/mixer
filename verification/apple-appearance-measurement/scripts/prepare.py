#!/usr/bin/env python3
"""Derive observation-only inputs from the sealed, unchanged reference."""
from pathlib import Path
import difflib, hashlib, json, shutil
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
BASE = ROOT.parent / 'apple-appearance-reference'
lock = json.loads((BASE / 'input-lock.json').read_text())
for entry in lock['sourceFiles']:
    data = (BASE / 'frozen' / entry['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256']
    if entry['path'].startswith('sdk/') and '/Sources/' in entry['path'] or entry['path'] == 'sdk/Package.swift':
        target = ROOT / 'instrumented-sdk' / Path(entry['path']).relative_to('sdk')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
renderer = ROOT / 'instrumented-sdk/Sources/MixerApple/MixerNativeView.swift'
original = renderer.read_text()
instrumented = original.replace('''        accessibility(render())
            .disabled''', '''        accessibility(observedRender())
            .disabled''')
instrumented = instrumented.replace('''    private var children: some SwiftUI.View {''', '''    private func observedRender() -> AnyView {
        // Section must remain structural in List. Measure its explicit header
        // and child content separately; no fictional section bounding box.
        if node.kind == .section { return render() }
        return AnyView(render().background(MeasurementProbe(nodeID: node.id,
            kind: node.kind.rawValue, explicitFont: node.kind == .text ? font : nil)))
    }

    private var children: some SwiftUI.View {''')
instrumented = instrumented.replace('''header: { SwiftUI.Text(title) })''', '''header: {
                    SwiftUI.Text(title).background(MeasurementProbe(nodeID: node.id + ".header",
                        kind: "sectionHeader", explicitFont: nil))
                })''')
assert instrumented != original
renderer.write_text(instrumented)
(ROOT / 'instrumentation.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), instrumented.splitlines(True), fromfile='frozen/MixerNativeView.swift', tofile='instrumented-sdk/Sources/MixerApple/MixerNativeView.swift')))
harness = ROOT / 'harness'
(harness / 'Fixtures').mkdir(parents=True, exist_ok=True)
for fixture in (BASE / 'harness/Fixtures').glob('*.json'):
    shutil.copyfile(fixture, harness / 'Fixtures' / fixture.name)
source = (BASE / 'harness/ReferenceApp.swift').read_text()
source = source.replace('struct ReferenceApp: App', 'struct MeasurementApp: App')
source = source.replace('''        ], name: "environment.json")''', '''        ], name: "environment.json")
        try MixerAppearanceMeasurement.write(window: window, fixture: fixture)''')
(harness / 'ReferenceApp.swift').write_text(source)
project = (BASE / 'harness/MixerAppearanceReference.xcodeproj/project.pbxproj').read_text()
project = project.replace('MixerAppearanceReference', 'MixerAppearanceMeasurement').replace('dev.mixer.appearancereference', 'dev.mixer.appearancemeasurement').replace('../frozen/sdk', '../instrumented-sdk')
# Add actual Release configuration (whole-program optimization), keeping Debug.
project = project.replace('buildConfigurations = (A00000000000000000000006);', 'buildConfigurations = (A00000000000000000000006,A00000000000000000000026);')
project = project.replace('buildConfigurations = (A00000000000000000000014);', 'buildConfigurations = (A00000000000000000000014,A00000000000000000000027);')
lines = project.splitlines(True)
for key, new in [('A00000000000000000000006', 'A00000000000000000000026'), ('A00000000000000000000014', 'A00000000000000000000027')]:
    line = next(line for line in lines if line.lstrip().startswith(key + ' ='))
    release = line.replace(key, new, 1).replace('name = Debug;', 'name = Release;').replace('SWIFT_OPTIMIZATION_LEVEL = "-Onone";', 'SWIFT_OPTIMIZATION_LEVEL = "-O"; SWIFT_COMPILATION_MODE = wholemodule;')
    project = project.replace(' rootObject =', release + ' rootObject =') if False else project.replace(' };\n rootObject', release + ' };\n rootObject')
p = harness / 'MixerAppearanceMeasurement.xcodeproj/project.pbxproj'
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(project)
manifest = {'format':'mixer.apple-appearance-measurement-inputs.1', 'baselineRevision':lock['sourceRevision'], 'baselineTree':lock['sourceTree'], 'baselineCollectionSHA256':lock['sourceCollectionSHA256'], 'baselineReceiptSHA256':hashlib.sha256((BASE/'receipt.json').read_bytes()).hexdigest(), 'baselineArtifactCollectionSHA256':json.loads((BASE/'receipt.json').read_text())['artifactCollectionSHA256'], 'baselineInputs':lock['sourceFiles']}
(ROOT / 'input-lock.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('Derived isolated SDK and harness from sealed 958998d reference; original reference unchanged.')
