"""Extract only the retained F11 seed and verify its original source anchors."""
import base64
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def document(*children):
    return dict(schemaVersion=1, revision=1, root=node("entry-editor", "vStack", {}, children=children))


def node(identifier, kind, properties, *, actions=(), children=()):
    return dict(id=identifier, kind=kind, properties=properties, actions=actions, children=children)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


STAGE_PIN = "f4a7fca378737786642647939ea61d17df80327d"
RECEIPT = "verification/receipts/fieldlog-f11-android-restored-note-api36-ac305262.json"


def stage_bytes(stage, path):
    return subprocess.check_output(["git", "-C", stage, "show", f"{STAGE_PIN}:{path}"])


def fixture(stage, fieldlog, output):
    receipt_bytes = stage_bytes(stage, RECEIPT)
    receipt = json.loads(receipt_bytes)
    native = receipt["native"]
    original = runpy.run_path(str(stage / "verification/local/fieldlog-f11-ordinary-root/fixture/android_f11.py"))
    assert sha(Path(original["__file__"]).read_bytes()) == native["driverSHA256"]
    seed = original["seed_bytes"]()
    note = original["NOTE"].encode()
    assert sha(seed) == native["seedSHA256"]
    assert sha(note) == native["commit"]["originalNoteSHA256"] and note.count(b"\n") == 4
    assert sha(note + original["SUFFIX"].encode()) == native["commit"]["editedNoteSHA256"]
    corpus_bytes = stage_bytes(stage, "compiler/experiments/fieldlog-change-corpus/corpus.json")
    corpus = json.loads(corpus_bytes)
    case, = (case for case in corpus["cases"] if case["id"] == "F11")
    assert case["anchors"] == receipt["host"]["case"]["anchors"]
    for anchor in case["anchors"]:
        blob = subprocess.check_output(["git", "-C", fieldlog, "cat-file", "blob", anchor["afterBlob"]])
        lo, hi = anchor["afterLines"]
        assert sha(b"".join(blob.splitlines(keepends=True)[lo-1:hi])) == anchor["afterLinesSHA256"]

    field = node("entry." + original["TARGET"].lower() + ".note", "textField",
                 {"label": "Note", "value": original["NOTE"], "axis": "vertical"},
                 actions=[dict(id="entry.note.change", event="textChange")])
    save = node("entry.saveDraft", "button", {"label": "Save draft"},
                actions=[dict(id="entry.saveDraft", event="activate")])
    commit = node("entry.commit", "button", {"label": "Commit entry"},
                  actions=[dict(id="entry.commit", event="activate")])
    prior = json_text(document(node("note-readback", "text", {"text": original["NOTE"]})))
    successor = json_text(document(field, save, commit))
    unavailable = json_text(document(node("status", "text", {"text": "Workspace unavailable"})))
    lines = [
        "static const char expected_note[] = " + json_text('"valueBase64":"' + base64.b64encode(note).decode() + '"') + ";",
        "#if defined(F11_PRIVATE)",
        'static const char denied[] = "permissionDenied";',
        "static const char unavailable_frame[] = " + json_text(unavailable) + ";",
        "#endif",
        "#if defined(F11_SUCCESSOR)",
        "static const char restored_frame[] = " + json_text(successor) + ";",
        "#else",
        "static const char restored_frame[] = " + json_text(prior) + ";",
        "#endif",
    ]
    (output / "seed.json").write_bytes(seed)
    (output / "editable.json").write_text(successor)
    (output / "fixture.h").write_text("\n".join(lines) + "\n")
    return dict(receiptSHA256=sha(receipt_bytes), corpusSHA256=sha(corpus_bytes),
                driverSHA256=native["driverSHA256"], seedSHA256=sha(seed), editableDocumentSHA256=sha(successor.encode()),
                originalNoteSHA256=sha(note), editedNoteSHA256=native["commit"]["editedNoteSHA256"],
                anchors=case["anchors"], comparison=[case["before"], case["after"]])


if __name__ == "__main__":
    stage, fieldlog, output = map(Path, sys.argv[1:])
    print(json.dumps(fixture(stage, fieldlog, output), indent=2))
