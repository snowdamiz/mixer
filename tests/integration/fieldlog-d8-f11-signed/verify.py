"""Run the owned F11 host controls and emit one compact receipt."""
from argparse import Namespace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time

from fixtures import RECEIPT, STAGE_PIN, sha, stage_bytes
from journey import PIN, run_journey
from resume import UnknownCustody, run


def verify(stage, tools, work, build_seconds, observed_public=None):
    started = time.monotonic()
    host = work / "swift/out/Products/Debug/F11Control"
    fixtures = work / "source/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
    guests = work / "guest"
    vm = work / "rust/release/libmixer_vm.a"
    seed = guests / "seed.json"
    tmp = work / "tmp"
    env = dict(os.environ, TMPDIR=str(tmp), NO_PROXY="127.0.0.1")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)

    def invoke(*args):
        return run(host, *args, cwd=work, env=env, timeout=18)

    def public_trial(output):
        run_journey(Namespace(control=host, fixtures=fixtures, guests=guests, vm=vm,
            origin=tools / "stock-mixer-service", cli=tools / "mixer", output=output, seed=seed))
        return json.loads((output / "receipt.json").read_bytes())

    first = work / "public"
    earlier_failure = None
    try:
        public = (json.loads(observed_public.read_bytes()) if observed_public is not None
                  else public_trial(first))
    except UnknownCustody:
        raise
    except RuntimeError:
        failed = json.loads((first / "receipt.json").read_bytes())
        state = json.loads((first / "recovery/state.json").read_bytes())
        if (failed["hold"] or not failed["originCleanup"]["groupAbsent"] or
                not failed["originCleanup"]["portRefused"] or failed["commands"][-1]["name"] != "offline"
                or state["lastRecovery"] != "effects_deadline"):
            raise
        earlier_failure = {"phase": "offline", "reason": state["lastRecovery"],
                           "originCleanup": failed["originCleanup"]}
        public = public_trial(work / "public-retry")
    assert public["status"] == "observed_signed_editor_refusal" and not public["hold"]

    private = work / "private"
    private.mkdir()
    invoke("prepare", private, fixtures, guests / "private", vm, seed, "--private-retry")
    private_result = json.loads(invoke("successor", private, "--private-retry"))
    assert private_result["refusal"] == "ui_protocol_after_effects"
    assert private_result["workspaceReads"] == private_result["workspaceWrites"] == 0
    contract = json.loads(invoke("contract", guests / "editable.json"))
    private_result["packets"] = {name: sha((private / "successor" / name).read_bytes())
                                 for name in ("signed-manifest.json", "assignment.json", "payload.wasm")}

    ordinary = work / "ordinary"
    ordinary.mkdir()
    store = ordinary / "workspace.json"
    shutil.copyfile(seed, store)
    save_hash = invoke("ordinary-save", ordinary).decode().strip()
    saved = store.read_bytes()
    commit_hash = invoke("ordinary-commit", ordinary).decode().strip()
    committed = store.read_bytes()
    cold = invoke("ordinary-read", ordinary).decode().strip()
    assert cold == commit_hash == sha(committed) and committed == store.read_bytes()
    assert save_hash == sha(saved)
    archives = stage / "verification/local"
    f11 = runpy.run_path(str(archives / "fieldlog-f11-ordinary-root/fixture/android_f11.py"))
    f12_file = archives / "fieldlog-f12-ordinary-root/fixture/android_f12.py"
    assert sha(f12_file.read_bytes()) == "38fa8bdbfa7ec8716eb48e0203f14c5a58c9c16ac238096d8e199a0ba1fc1d9d"
    raw_members = runpy.run_path(str(f12_file))["raw_members"]
    validate = f11["verify_write"]
    validate(seed.read_bytes(), saved, commit=False, raw_members=raw_members)
    event = validate(saved, committed, commit=True, raw_members=raw_members)

    native = json.loads(stage_bytes(stage, RECEIPT))["native"]
    archived_event = native["commit"]["event"]
    normalized = json.loads(committed)
    normalized["outbox"][-1] = archived_event
    normalized["entries"][-1]["savedAt"] = archived_event["createdAt"]
    normalized_hash = sha(json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
    assert normalized_hash == native["checkpoints"][-1]["workspaceSHA256"]

    used_bytes = int(subprocess.check_output(["du", "-sk", work]).split()[0]) * 1024
    seconds = build_seconds + round(time.monotonic() - started, 2)
    assert seconds < 600 and used_bytes <= int(1.2 * 2**30)
    pair = work / "pair/fieldlog"
    sources = ("Sources/FieldLogModels/Workspace.swift", "Sources/FieldLogStorage/WorkspaceRepository.swift",
               "Integrations/GeneratedReport/Sources/FieldLogFeatures/EntryEditor.swift",
               "Integrations/GeneratedReport/Sources/FieldLogFeatures/EntrySaveDecision.swift")
    return {
        "schema": 1, "row": "L08 D8 F11", "observedUTC": datetime.now(timezone.utc).isoformat(),
        "status": "observed_signed_editor_refusal",
        "scope": "Android-scoped V3 headless macOS host with owned VM and stock loopback origin. Reauthored first-frame witness from the original F11 fixture and action. Ordinary Pair25 editor and disk controls ran in separate host processes.",
        "stage": STAGE_PIN, "hostSource": PIN,
        "fixture": json.loads((work / "fixture.json").read_bytes()),
        "pair25": {"tree": native["fieldLogTree"], "sdk": native["sdkRevision"], "apkSHA256": native["apkSHA256"],
                   "compiledSourceBlobs": {path: subprocess.check_output(["git", "hash-object", pair / path],
                                                                         text=True).strip() for path in sources}},
        "tools": {name: (work / (name + "-version")).read_text().strip() for name in ("swift", "cargo", "clang")},
        "recipeSHA256": {path.name: sha(path.read_bytes()) for path in sorted(Path(__file__).parent.iterdir())
                         if path.suffix in (".c", ".swift", ".py", ".sh")},
        "public": {key: public[key] for key in ("originSHA256", "cliSHA256", "hostSHA256", "vmSHA256",
                    "hostProfile", "phases", "publications", "packets", "audit", "originCleanup",
                    "signedPacketFilesUnchanged", "hold")},
        "earlierPublicAttempt": earlier_failure, "private": private_result,
        "contract": dict(contract, hostSHA256=sha(host.read_bytes())),
        "ordinary": {"revisions": [1, 2, 3, 3], "draftSHA256": save_hash, "commitSHA256": commit_hash,
                     "coldSHA256": cold, "linkedEvent": event, "normalizedInstalledCommitSHA256": normalized_hash,
                     "unrelatedJSONIdentical": True, "duplicateCommitChangedBytes": False},
        "bounds": {"seconds": seconds, "allocatedBytes": used_bytes, "maximumSeconds": 600, "maximumGiB": 1.2},
        "smallestNextStep": "Independently review a signed note-specific scope for vertical entry.note.change, bounded private draft hydration, and expected-revision Save draft and Commit entry. Then replay the same fixture, including repeated commit, in a fresh owned VM.",
    }


if __name__ == "__main__":
    stage, tools, work = map(Path, sys.argv[1:4])
    observed_public = Path(sys.argv[5]) if len(sys.argv) == 6 else None
    print(json.dumps(verify(stage, tools, work, int(sys.argv[4]), observed_public), indent=2))
