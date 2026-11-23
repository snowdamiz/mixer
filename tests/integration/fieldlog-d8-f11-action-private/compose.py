"""Extend the pinned, unchanged F11 vertical replay inside disposable source."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import sys


def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(vertical, recipe, work):
    receipt = vertical.parents[2] / "verification/receipts/l08-d8-f11-private-vertical-host.json"
    assert digest(receipt) == "81dde21cf780bd90535401184d422747d0c8d3c7d993c9dbb5008a6e295c525d"
    observed = json.loads(receipt.read_bytes())
    for name, expected in observed["sameCheckoutReplay"]["recipeSHA256"].items():
        assert digest(vertical / name) == expected, name
    script = (vertical / "worker.sh").read_text()
    script = replace(script, 'recipe="$(cd "$(dirname "$0")" && pwd -P)"',
                     f'recipe={shlex.quote(str(vertical))}\naction={shlex.quote(str(recipe))}')
    script = replace(script, 'phase dependencies', '''
phase action-compose
python3 -B "$action/compose.py" source "$source" "$action" "$work" "$app" "$recipe"
phase dependencies''')
    script = replace(script, '-Xswiftc -DMIXER_PRIVATE_FIELDLOG_EDITOR',
                     '-Xswiftc -DMIXER_PRIVATE_FIELDLOG_EDITOR -Xswiftc -DMIXER_F11_HOST_ACTION_FIXTURE')
    script = replace(script, 'for mode in valid wrong-field wrong-action; do',
                     'for mode in valid wrong-field wrong-action actions lost; do')
    script = replace(script, 'phase receipt', '''
phase cold-committed
"$control" cold-committed "$work/actions" > "$work/cold-committed.json"
phase pair25-write-verification
python3 -B "$action/verify.py" "$stage" "$work" > "$work/writes.json"
phase receipt''')
    script = replace(script, '--slurpfile historical', '''--slurpfile actions "$work/actions.json" --slurpfile lost "$work/lost.json" \\
    --slurpfile writes "$work/writes.json" --slurpfile historical''')
    script = replace(script, 'status:"observed_signed_f11_vertical_edit"',
        'status:"observed_f11_host_actions", stageInputPin:"b9d227c81c1c87b51d40fa55718ffbb18734c258",'
        'stageInputTree:"d7993f666e14ca80a9ea3d14c171d6edd6e51d74", pair25Tree:"9c2d665c31a6f3f2bfabc42bdfffaf72c6661731"')
    script = replace(script, 'valid:$valid[0],', 'valid:$valid[0], actions:$actions[0], lost:$lost[0], writes:$writes[0],')
    print(script, end="")


def source(source, recipe, work, app, vertical):
    baseline = json.loads((vertical.parents[2] / "verification/receipts/l08-d8-f11-private-vertical-host.json").read_bytes())
    overlay = json.loads((work / "overlay.json").read_bytes())
    for field in ("contract", "contractSHA256", "sourceEdits", "repositorySHA256"):
        assert baseline["overlay"][field] == overlay[field], field
    recipe_hashes = baseline["sameCheckoutReplay"]["recipeSHA256"]
    expected_fixtures = {name: recipe_hashes[name] for name in baseline["overlay"]["fixtureSources"]}
    assert overlay["fixtureSources"] == expected_fixtures
    package = source / "capability-activation"
    target = package / "Sources/F11Vertical"
    presentation = package / "Sources/MixerCapabilityActivation/CapabilityGuestUIPresentation.swift"
    before = digest(presentation)
    original = presentation.read_text()
    insertion = (recipe / "Presentation.inc").read_text()
    presentation.write_text(replace(original, "    internal func actionHandler(",
                                    insertion + "\n    internal func actionHandler("))
    control = (target / "Control.swift").read_text()
    control = replace(control, "        let before = try read(workspace,",
                      '''        if phase == "cold-committed" {
            try await F11HostActions.coldCommitted(workspace)
            return
        }

        let before = try read(workspace,''')
    control = replace(control, 'observe(owner, work, valid: phase == "valid")',
                      'observe(owner, work, phase: phase, repository: repository)')
    control = replace(control, '&& before == read(workspace, "workspace.json"),',
                      '&& (phase == "actions" || before == read(workspace, "workspace.json")),')
    control = replace(control, "        await owner.close()\n        await repository.close()", """        await owner.close()
        await repository.close()
        let retirementDeadline = ContinuousClock.now + .seconds(4)
        while !owner.ownerRetired && ContinuousClock.now < retirementDeadline {
            try await Task.sleep(for: .milliseconds(5))
        }""")
    control = replace(control, 'report["workspaceRevision"] = 1', 'report["initialWorkspaceRevision"] = 1')
    control = replace(control, '_ work: URL, valid: Bool)', '_ work: URL, phase: String, repository: WorkspaceRepository)')
    control = replace(control, '        if !valid {', '        if phase == "wrong-field" || phase == "wrong-action" {')
    control = replace(control, '        report["field"] = spec.field', '''        if phase == "actions" || phase == "lost" {
            let actions = try await F11HostActions.exercise(owner: owner, work: work, repository: repository,
                attachment: attachment, initial: display, lost: phase == "lost")
            report["hostActions"] = actions
        }
        report["field"] = spec.field''')
    (target / "Control.swift").write_text(control)
    shutil.copyfile(recipe / "HostActions.swift", target / "HostActions.swift")
    features = package / "Sources/FieldLogFeatures"
    features.mkdir()
    for name in ("EntryEditor.swift", "EntrySaveDecision.swift"):
        shutil.copyfile(app / "Integrations/GeneratedReport/Sources/FieldLogFeatures" / name, features / name)
    manifest = package / "Package.swift"
    manifest.write_text(replace(manifest.read_text(), '    .executableTarget(name: "F11Vertical", dependencies: [',
        '''    .target(name: "FieldLogFeatures", dependencies: ["FieldLogModels",
        .product(name: "MixerCore", package: "sdk")]),
    .executableTarget(name: "F11Vertical", dependencies: ["FieldLogFeatures",'''))
    overlay["actionFixture"] = {
        "presentation": {"before": before, "after": digest(presentation)},
        "controlSHA256": digest(target / "Control.swift"),
        "entryEditorSHA256": digest(features / "EntryEditor.swift"),
        "recipeSHA256": {file.name: digest(file) for file in sorted(recipe.iterdir()) if file.is_file()
                         and file.name != "README.md"},
    }
    (work / "overlay.json").write_text(json.dumps(overlay))


if __name__ == "__main__":
    mode, *paths = sys.argv[1:]
    {"worker": worker, "source": source}[mode](*map(Path, paths))
