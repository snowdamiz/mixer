"""Compose the finite F04 private seam as a distinct F11 fixture in the exported tree."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

source, work, recipe = map(Path, sys.argv[1:])
package = source / "capability-activation"
activation = package / "Sources/MixerCapabilityActivation"
guest = source / "sdk/Sources/MixerGuest"
identity = source / "runtime-identity/Sources/MixerRuntimeIdentity/CapabilityRuntimeIdentity.swift"
marker = source / "updates/Sources/MixerUpdates/FieldLogEditorDevelopment.swift"
contract = {
    "id": "mixer.fieldlog-f11-note-fixture-v1", "version": 1,
    "field": "entry.f1100000-0000-4000-8000-000000000001.note", "action": "entry.note.change",
    "event": "textChange", "axis": "vertical", "frameRevisions": [1, 2],
    "storage": {"namespace": "fieldlog-d8-f11-note", "key": "note", "mode": "read-only"},
}
contract_bytes = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
digest = hashlib.sha256(contract_bytes).hexdigest()
changed = {}


def replace(text, old, new):
    assert old in text, old
    return text.replace(old, new)


def renamed(text):
    for old, new in [
        ("FieldLogTaskRetry", "FieldLogNoteFixture"),
        ("fieldLogTaskRetry", "fieldLogNoteFixture"),
        ("taskRetry", "noteFixture"),
        ("fieldlog_task_retry", "fieldlog_note_fixture"),
    ]:
        text = text.replace(old, new)
    return text


def rewrite(path, edit):
    changed[str(path.relative_to(source))] = hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_text(edit(path.read_text()))


for name in ("CapabilityColdStartWorker", "CapabilityExecutionPolicy", "CapabilityGuestUIRuntime",
             "CapabilityInstalledExecutionMode", "CapabilityRecoveryStore", "InstalledCapabilityExecution"):
    path = activation / (name + ".swift")
    rewrite(path, renamed)
rewrite(guest / "GuestUIExchangeV1.swift", renamed)
rewrite(identity, lambda text: replace(renamed(text),
    "FieldLogEditorDevelopment.noteFixtureDependency].contains(id)",
    'FieldLogEditorDevelopment.noteFixtureDependency, "mixer.fieldlog-task-retry-v1"].contains(id)'))


def note_marker(text):
    text = renamed(text)
    for old, new in [
        ("mixer.fieldlog-task-retry-v1", contract["id"]),
        ("7f1d259ded126ff9cbf13d445a28909823e322e9ed79d22307dd2fb5e38efdc1", digest),
        ("fieldlog-d8-f04-task", contract["storage"]["namespace"]),
        ('noteFixtureKey = "task"', 'noteFixtureKey = "note"'),
    ]:
        text = replace(text, old, new)
    return text


rewrite(marker, note_marker)
storage = activation / "FieldLogTaskRetryStorage.swift"
rewrite(storage, lambda text: replace(replace(renamed(text),
    '["AA==", "AQ=="].contains(response.valueBase64)',
    'response.valueBase64 == "Q2Fmw6kgZcyBIPCfkanwn4+94oCN8J+UrArmnbHkuqwKCkxhc3QgbGluZQo="'),
    """        try authorize(namespace: request.namespace, key: request.key)
        return try await repository.put(request, maximumTotalBytes: maximumTotalBytes, maximumEntries: maximumEntries)""",
    """        throw CapabilityFailure.permissionDenied"""))
shutil.copyfile(recipe / "NoteCodec.swift", guest / "GuestUIFieldLogNoteFixture.swift")

target = package / "Sources/F11Vertical"
target.mkdir()
repo_digest = hashlib.sha256((package / "Sources/FieldLogStorage/WorkspaceRepository.swift").read_bytes()).hexdigest()
release = renamed((work / "Release.swift").read_text())
for old, new in [
    ("d8-f04", "d8-f11-vertical"), ("fieldlog-f04", "fieldlog-f11-vertical"), ("f04.control", "f11.vertical"),
    ("TaskStorage.namespace", "NoteStorage.namespace"),
    ("9a69cb9d97728f5f8f85f78193e1ed5d09059b54", "00c8fe0400bc9a06242371ce7b02cd440f64f31e"),
    ("d51adf50de7e20549e87062e4569609342cdfe25", "c6562ba80b992016c0c963cf4c67a59f1f605fd0"),
    ("db9e4e490263d4b0779b03fadfdc07cfca5d23df2501c5c900b54abb904b86fb", repo_digest),
]:
    release = replace(release, old, new)
(target / "Release.swift").write_text(release)
shutil.copyfile(recipe / "Control.swift", target / "Control.swift")
with (package / "Package.swift").open("a") as manifest:
    manifest.write("""
package.targets.append(contentsOf: [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
    .executableTarget(name: "F11Vertical", dependencies: [
        "MixerCapabilityActivation", "FieldLogModels", "FieldLogStorage",
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        .product(name: "MixerUpdates", package: "updates"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerGuest", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
    ]),
])
""")

# Use the F11 combined fixture's exact field and archived original/edit hashes.
f11 = json.loads((work / "guest/editable.json").read_bytes())
case = json.loads((work / "fixture.json").read_bytes())
field, save, commit = f11["root"]["children"]
assert field["id"] == contract["field"] and field["actions"] == [{"id": contract["action"], "event": contract["event"]}]
assert [save["id"], commit["id"]] == ["entry.saveDraft", "entry.commit"]
f11["root"]["children"] = [field]
note = field["properties"]["value"]
edited = note + "Edited"
assert note.count("\n") == edited.count("\n") == 4
assert hashlib.sha256(note.encode()).hexdigest() == case["originalNoteSHA256"]
assert hashlib.sha256(edited.encode()).hexdigest() == case["editedNoteSHA256"]
import base64
assert base64.b64encode(note.encode()).decode() in storage.read_text()


def wire(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def define(name, value):
    return f"static const char {name}[] = {wire(value)};\n"


frames = [define("valid_frame", wire(f11))]
field["id"] += ".wrong"
frames.append(define("wrong_field_frame", wire(f11)))
field["id"] = contract["field"]
field["actions"][0]["id"] = save["id"]
frames.append(define("wrong_action_frame", wire(f11)))
field["actions"][0]["id"] = contract["action"]
field["properties"]["value"] = "F11_EVENT_PLACEHOLDER"
f11["revision"] = 2
prefix, suffix = wire(f11).split('"F11_EVENT_PLACEHOLDER"')
frames.extend([define("edit_frame_prefix", prefix), define("edit_frame_suffix", suffix)])
event_prefix = f'{{"actionID":"{contract["action"]}","event":"textChange","nodeID":"{contract["field"]}","revision":1,"schemaVersion":1,"sequence":1,"value":'
frames += [define("event_prefix", event_prefix), define("expected_edit", wire(edited))]
(work / "guest/vertical.h").write_text("".join(frames))
(work / "overlay.json").write_text(json.dumps({
    "contract": contract, "contractSHA256": digest, "repositorySHA256": repo_digest,
    "sourceEdits": {name: {"before": before, "after": hashlib.sha256((source / name).read_bytes()).hexdigest()}
                    for name, before in sorted(changed.items())},
    "fixtureSources": {name: hashlib.sha256((recipe / name).read_bytes()).hexdigest()
                       for name in ("NoteCodec.swift", "Control.swift", "Guest.c", "prepare.py", "replay.py", "worker.sh")},
}))
