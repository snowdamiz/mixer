"""Opt-in completion schedule for the adopted v55 custody worker."""

import errno
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import signal
import stat
import subprocess
import sys
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

XCODE = "/usr/bin/xcodebuild"
SWIFT_PROBE = ["/usr/bin/swift", "--version"]
STAGE_SHA256 = "ef64efaa7c48ba1f7510824ec3f4222bf31f0a751cc7bb97bab0c987a256eb5d"
STAGE_PINS = {
    "publicCommit": "201ead70ff68bfe18de24c0642f518701459e0a4",
    "publicTree": "bc795366f84ca7d68890b84a97bd8773fe1dc786",
    "sdkCommit": "fad0d0b3e65fd3be3b49675601693e5d91999fbe",
    "provenanceBaseSHA256": "8c7b6022210d13a8830500ef5c406db8f8fd6bcf93c883ab5e6718ed1f172b90",
    "provenanceOverlaySHA256": "900dd380712ae10365e92b5d494573e0e2659403db77f0838f821fa9f5bdd068",
    "provenanceSourceSHA256": "1338f7f1b16e646b4665ba67cf08a850da1f08b89b00a8bbcb4505ae48b2e161",
    "starterSourceSHA256": "9d1285c5b66eca9c9b09b6471fcf4a6a9bb28445adfa81acd0133de72f0554c9",
    "starterLockSHA256": "cf4f39cd9ff2cfd48cc960c358293f49b5e7c9c75757efdeee291770af983227",
    "cliSHA256": "31770eaa056570232b33970a8b690acfced11ec21f5bb871625641b9e256ffbe",
    "xcode": "Xcode 27.2\nBuild version 27B52",
}
XCODE_SHA256 = "7d9561a7f8e3c5d70a571422a4522de986c003879dab3bf7562963b6cdc3e658"
DEVELOPER_XCODE_SHA256 = "95e0d77f16b7233888fb7fb44fee80963c40bb965bfb5577efb4b7027aaecfca"
XCODE_VERSION_PLIST_SHA256 = "93b253c224fee82d869beb7a0462f2e90138cad83bcdc64784c614eee6f8ba2d"
RECIPE_SECONDS = 420
CLAIM_SECONDS = 45
SETTLE_SECONDS = 30
CLOSED_FACTS = ("terminalCustody", "directChildReaped", "stdoutEOF", "stderrEOF",
                "descriptorsClosed", "ownedGroupAbsent")
RECEIPT_ROOT = re.compile(r"mixer-command-receipts-[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}")
COMMAND_DIR = re.compile(r"command-[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}")


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage_recipe(root, kit, args, result, prepare):
    stage_bytes = args.stage_receipt.read_bytes()
    stage = json.loads(stage_bytes)
    require(kit["sha"](stage_bytes) == STAGE_SHA256
            and all(stage.get(key) == pin for key, pin in STAGE_PINS.items())
            and stage.get("allPreparedCommandsClosed") is True and stage.get("zeroFixtureBuildPOSTs") is True,
            "staging receipt differs from the approved Starter archive, provenance or tool pins")
    result.update(starterStageSHA256=STAGE_SHA256,
                  compilerSourceSHA256=stage["provenanceSourceSHA256"])

    source, staged_cli = (path.absolute() for path in (args.export, args.cli))
    provenance = args.stage_receipt.absolute().parent / "cli-provenance"
    require(all(path.resolve(strict=True) == path for path in (source, staged_cli, provenance)),
            "stage must use canonical absolute export and CLI paths")
    export_argv = stage["commands"]["starter-export"]["argv"]
    require((str(staged_cli), str(source)) == (export_argv[0], export_argv[2]),
            "CLI or export path differs from the verified stage")
    cli_info = staged_cli.lstat()
    require(stat.S_ISDIR(source.lstat().st_mode) and stat.S_ISREG(cli_info.st_mode)
            and cli_info.st_nlink == 1 and cli_info.st_uid == os.getuid()
            and os.access(staged_cli, os.X_OK)
            and 0 < cli_info.st_size <= (256 << 20),
            "expected a staged export and an owned executable CLI")
    # The observer opens a non-writable executable. Freeze a byte-identical
    # private copy without changing the staging owner's executable or its mode.
    cli = root / "mixer"
    shutil.copyfile(staged_cli, cli)
    cli.chmod(0o500)
    with cli.open("rb") as stream:
        magic = stream.read(4)
    require(magic in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
            "staged CLI is not a Mach-O executable")
    require(file_sha(cli) == stage["cliSHA256"], "staged CLI digest differs")

    # Derive the same manifest as prepare-starter.fixture; keep the supplied
    # stage untouched. The worker rechecks the bytes before copying the export.
    sys.path.insert(0, str(root / "hosted/priv/development"))
    import starter_package_closure as starter

    inventory = runpy.run_path(str(root / prepare))["inventory"]
    require(starter.tree_digest(inventory(provenance, kit["sha"])) == stage["provenanceSourceSHA256"],
            "staged compiler source provenance differs")
    files = inventory(source, kit["sha"])
    starter.check_starter_inputs(files, (source / "mixer.lock").read_bytes())
    tree = starter.tree_digest(files)
    require((tree, files["mixer.lock"]) == (stage["starterSourceSHA256"], stage["starterLockSHA256"]),
            "staged Starter tree or lock differs")
    developer = Path(subprocess.check_output(
        ["/usr/bin/xcode-select", "-p"], text=True, timeout=5,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    ).strip()).resolve(strict=True)
    sdk = developer / "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"
    require(sdk.is_dir() and file_sha(Path(XCODE)) == XCODE_SHA256
            and file_sha(developer / "usr/bin/xcodebuild") == DEVELOPER_XCODE_SHA256
            and file_sha(developer.parent / "version.plist") == XCODE_VERSION_PLIST_SHA256,
            f"selected Xcode differs from the pinned 27B52 toolchain or lacks its Simulator SDK: {developer}")
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "DEVELOPER_DIR": str(developer)}
    tools = {str(cli): stage["cliSHA256"], XCODE: XCODE_SHA256}
    manifest = {starter.KEY: starter.VERSION}
    recipe = dict(profile="unsigned-ios-simulator-v1", timeout_seconds=RECIPE_SECONDS,
                  argv=[str(cli), "build", "--platform", "ios", "--directory", str(source)],
                  cwd=str(source), environment=environment,
                  package_policy="exact-owned-local-manifests-no-external-packages",
                  inputs=files, tools=tools, **manifest)
    recipe_path = root / "recipe.json"
    recipe_sha = kit["write"](recipe_path, recipe)
    kit["write"](root / "inputs.json", dict(source_tree_sha256=tree,
                 linux_lock_sha256=files["mixer.lock"], recipe_sha256=recipe_sha))
    result.update(starterSourceSHA256=tree, starterLockSHA256=files["mixer.lock"],
                  cliSHA256=tools[str(cli)], recipeSHA256=recipe_sha, selectedXcode=str(developer),
                  selectedXcodeVersionPlistSHA256=XCODE_VERSION_PLIST_SHA256,
                  selectedXcodeExecutableSHA256=DEVELOPER_XCODE_SHA256,
                  xcodeShimSHA256=tools[XCODE], liveRecipeSeconds=RECIPE_SECONDS)
    spec = dict(source=dict(kind="revision", reference="starter-" + tree, sha256=tree),
                toolchain_lock_sha256=files["mixer.lock"], build_definition_sha256=recipe_sha)
    return spec, dict(root=str(source), recipe=str(recipe_path), files=files), dict(
        cli=str(cli), recipe_sha256=recipe_sha, environment=environment, inputs=files, tools=tools, **manifest)


def command_receipt(path, read_owned):
    require(path.name == "receipt.json" and COMMAND_DIR.fullmatch(path.parent.name)
            and RECEIPT_ROOT.fullmatch(path.parent.parent.name), "unexpected Swift receipt path")
    for directory in (path.parent.parent.parent, path.parent.parent, path.parent):
        info = directory.lstat()
        require(info.st_uid == os.getuid() and info.st_mode == stat.S_IFDIR | 0o700,
                "Swift receipt directory is not private and owned")
    require(not os.path.lexists(path.with_name("HOLD.json")), "Swift recorded a custody hold")
    raw = read_owned(path, 1024 * 1024, allow_owner_write=True)
    require(not os.path.lexists(path.with_name("HOLD.json")), "Swift recorded a custody hold")
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def xcode_argv(project):
    derived = project / ".mixer/ios-build"
    return [
        XCODE, "-project", str(project / "Platforms/iOS/Starter.xcodeproj"), "-scheme", "Starter",
        "-configuration", "Debug", "-sdk", "iphonesimulator",
        "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", str(derived),
        "-clonedSourcePackagesDirPath", str(derived / "SourcePackages"), "-jobs", "4",
        "DEBUG_INFORMATION_FORMAT=dwarf-with-dsym", "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES",
        "ENABLE_DEBUG_DYLIB=NO", "COMPILER_INDEX_STORE_ENABLE=NO", "CODE_SIGNING_ALLOWED=NO", "build",
    ]


def running_xcode(output, native):
    directories = list((output / "tmp").glob("mixer-command-receipts-*/command-*"))
    require(len(directories) <= 2, "unexpected extra Swift owned command")
    entries = []
    for directory in directories:
        require(not os.path.lexists(directory / "HOLD.json"), "Swift recorded a custody hold")
        path = directory / "receipt.json"
        try:
            item, sha = command_receipt(path, native.read_owned)
        except (FileNotFoundError, native.Refusal):
            # Swift replaces the file atomically when advancing state.
            return None
        entries.append((path, item, sha))
    if len(entries) < 2:
        return None
    probes = [entry for entry in entries if entry[1].get("command") == SWIFT_PROBE]
    require(len(probes) == 1, "expected exactly one Swift version receipt")
    [probe] = probes
    [xcode] = [entry for entry in entries if entry != probe]
    path, item, _ = xcode
    project = output / "project"
    require(item.get("schema") == "mixer.owned-command.2" and item.get("directory") == str(project)
            and item.get("command") == xcode_argv(project), "Xcode receipt differs from unsigned generic build")
    if item.get("state") == "RUNNING":
        pid = item.get("pid")
        require(type(pid) is int and pid > 1 and pid == item.get("ownedPGID") == item.get("ownedSession")
                and item.get("released") is True and item.get("terminalCustody") is False
                and type(item.get("runtimeStartedNS")) is int and item["runtimeStartedNS"] > 0,
                "RUNNING Xcode receipt lacks exact released session custody")
        require(probe[0].parent.parent == path.parent.parent
                and swift_probe_closed(probe[1], item["runtimeStartedNS"]),
                "Swift version must positively close before Xcode starts")
        return probe, xcode
    require(item.get("state") in ("INTENT", "FORKED_GATE_CLOSED", "OWNED_GATE_CLOSED"),
            "missed the Xcode RUNNING receipt before closure")
    return None


def swift_probe_closed(probe, xcode_start):
    pid = probe.get("pid")
    return (probe.get("schema") == "mixer.owned-command.2" and probe.get("command") == SWIFT_PROBE
            and type(pid) is int and pid > 1 and pid == probe.get("ownedPGID") == probe.get("ownedSession")
            and probe.get("state") == "TERMINAL" and probe.get("released") is True
            and type(probe.get("exitCode")) is int and probe["exitCode"] == 0 and probe.get("stopReason") is None
            and all(probe.get(key) is True for key in CLOSED_FACTS)
            and type(probe.get("terminalNS")) is int and 0 < probe["runtimeStartedNS"] <= probe["terminalNS"]
            <= xcode_start)


def terminal_xcode(tmp, witness, nested, native, cut_ns):
    probe, (path, active, _) = witness
    basename = native.read_cli_ack(tmp)
    require(basename == path.parent.parent.name and nested["receipt_root"] == basename,
            "CLI did not acknowledge the original Xcode receipt root")
    require(list(tmp.glob("mixer-command-receipts-*")) == [path.parent.parent]
            and set(path.parent.parent.glob("command-*")) == {probe[0].parent, path.parent},
            "terminal roster differs from the Swift probe and lone Xcode invocation")
    require(command_receipt(probe[0], native.read_owned) == probe[1:],
            "original closed Swift probe receipt changed")
    item, sha = command_receipt(path, native.read_owned)
    require(nested["receipt_sha256s"] == [probe[2], sha]
            and all(item[key] == active[key] for key in (
                "command", "directory", "pid", "ownedPGID", "ownedSession", "runtimeStartedNS"))
            and item["state"] == "TERMINAL" and item["released"] is True
            and type(item.get("terminalNS")) is int
            and item["runtimeStartedNS"] <= cut_ns <= item["terminalNS"]
            and all(item.get(key) is True for key in CLOSED_FACTS),
            "original Xcode invocation has no matching positive terminal custody")
    return item, sha


def reap_owned_child(process, wait):
    def reaped():
        pid, status = os.waitpid(process.pid, os.WNOHANG)
        if pid == process.pid:
            process.returncode = os.waitstatus_to_exitcode(status)
            return True
        return False

    wait(reaped, 3)


def complete_after_cut(kit, result, output, config_path, config_sha, spec, binding, auth, scope,
                       first, observer, worker_port, processor, ledger, claim_entry, snapshot, jobs,
                       start_job, sql, owner_unavailable, reopen, rebind_seconds):
    import native_artifact_worker as native

    wait, sha, http = (kit[name] for name in ("wait", "sha", "http"))
    admission = lambda: kit["running_admission"](snapshot(), binding)
    record, operation = binding["record_id"], binding["operation_id"]
    start_id = result["originalObanJobs"]["start"]
    selected = {key: binding[key] for key in ("spec", "ref", "deadline_ms")}
    owner = auth["cookie"]
    tmp = output / "tmp"
    result["stage"] = "live-xcode-running-claim"

    def running():
        claim = claim_entry()
        if claim is None:
            return None
        row, parent, launch, terminal, uncertain, counts, plan, issued = claim
        cli_pid = launch["pid"]
        intent = row["ios_custody"]
        config = kit["read"](config_path)
        authority = {key: config[key] for key in ("tenant", "registration", "policy", "ios_custodian")}
        require((row["starts"], row["status"], parent, terminal, uncertain, counts)
                == (1, "running", observer.pid, None, 0, [1, 1])
                and launch == dict(pid=cli_pid, pgid=cli_pid, sid=cli_pid)
                and row["binding"] == selected and not row.get("tombstone")
                and issued == intent["guard"] and issued["owner_id"].startswith(f"oban:{start_id}:")
                and intent["configuration"] == sha(native.literal(authority).encode())
                and plan == sha(native.literal({"operation_id": operation, "binding": selected,
                                               "intent": intent}).encode()),
                "original worker claim, guard or admission differs")
        witness = running_xcode(output, native)
        return (claim, witness) if witness else None

    claim, witness = wait(running, CLAIM_SECONDS, observer, interval=0.02)
    _, _, launch, _, _, _, plan, issued = claim
    probe, (path, item, digest) = witness
    cli_pid, xcode_pid = launch["pid"], item["pid"]
    before, original_job = admission(), start_job()
    require(original_job["id"] == start_id and first.poll() is None and observer.poll() is None
            and len({first.pid, observer.pid, cli_pid, xcode_pid, probe[1]["pid"]}) == 5
            and os.getpgid(first.pid) == os.getsid(first.pid) == first.pid
            and os.getpgid(cli_pid) == os.getsid(cli_pid) == cli_pid
            and os.getpgid(xcode_pid) == os.getsid(xcode_pid) == xcode_pid,
            "original worker, CLI or Xcode live identity differs")
    require(running_xcode(output, native) == witness, "Xcode receipt changed before the cut")
    result["beforeCut"] = dict(claimSHA256=plan, issuedGuard=issued, startAdmission=before,
                               startJob=original_job, observerPID=observer.pid,
                               cli=launch, workerPID=first.pid, capacityHeld=True,
                               swiftVersionProbe=dict(path=str(probe[0]), receiptSHA256=probe[2],
                                                      pid=probe[1]["pid"], terminalNS=probe[1]["terminalNS"]),
                               xcode=dict(path=str(path), receiptSHA256=digest, pid=xcode_pid,
                                          pgid=item["ownedPGID"], sid=item["ownedSession"],
                                          command=item["command"], state=item["state"],
                                          runtimeStartedNS=item["runtimeStartedNS"]))
    cut_at = time.monotonic()
    os.kill(first.pid, signal.SIGKILL)
    cut_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC)  # Same clock as Swift's owned receipt.
    reap_owned_child(first, wait)
    reaped_ms = time.time_ns() // 1_000_000
    require(first.returncode == -9 and kit["group_absent"](first.pid)
            and kit["connect_errno"](worker_port) == errno.ECONNREFUSED, "owned worker cut did not close the port")
    result["workerCut"] = dict(pid=first.pid, exit=-9, directReaped=True, groupAbsent=True, signalNS=cut_ns)

    def original():
        row, parent, current, terminal, uncertain, counts, current_plan, guard = claim_entry()
        require((row["starts"], parent, current, uncertain, counts, current_plan, guard)
                == (1, observer.pid, launch, 0, [1, 1], plan, issued)
                and row["binding"] == selected and not row.get("tombstone"),
                "replacement, retry, or completion changed original custody")
        return row, terminal

    result["stage"] = "live-offline-oban-retry-and-plain-bind"
    row, claim_at_cut = original()
    offline_guard = row["guard"]
    bind_until = cut_at + rebind_seconds
    outage = result["workerOutage"] = dict(port=worker_port, reapedAtMS=reaped_ms,
                                           firstPlainBindErrno=kit["plain_bind_errno"](worker_port),
                                           outerClosedAtWorkerReap=claim_at_cut is not None)

    def still_offline():
        row, terminal = original()
        require(row["status"] == "running" and row["guard"] == offline_guard
                and "artifacts" not in row and "manifest_sha256" not in row
                and kit["connect_errno"](worker_port) == errno.ECONNREFUSED,
                "worker ledger settled or the port changed while offline")
        return terminal

    def retried():
        job, held = start_job(), admission()
        still_offline()
        require(job["id"] == start_id, "offline retry replaced the original Oban start job")
        if (job["state"] == "scheduled" and job["attemptedAtMS"] is not None
                and job["attemptedAtMS"] > reaped_ms and held[5] > before[5]):
            return {"job": job, "admission": held}

    outage["offlineRetry"] = wait(retried, bind_until - time.monotonic(), processor)
    outage["ownerHTTP"] = owner_unavailable(owner)
    wait(lambda: kit["plain_bind_errno"](worker_port) is None,
         bind_until - time.monotonic(), processor, interval=0.2)
    outage.update(samePortPlainBind=True, plainBindWaitMS=round((time.monotonic() - cut_at) * 1000),
                  admissionBeforeReopen=admission(),
                  outerClosedBeforeReopen=still_offline() is not None)
    require(sha(config_path.read_bytes()) == config_sha, "reopen configuration differs")
    result["stage"] = "live-same-ledger-reopen"
    worker = reopen()
    wait(lambda: kit["listening"](worker_port), 5, worker)
    current = (output.parent / "operations.sqlite").stat()
    require((current.st_dev, current.st_ino) == (ledger.st_dev, ledger.st_ino) and worker.pid != first.pid,
            "restart opened a different ledger or worker identity")
    result["reopen"] = dict(workerPID=worker.pid, port=worker_port, sameLedgerInode=True)

    # The observer can commit closure while the worker is offline. No intermediate
    # 'uncertain' row or live process probe is required after the cut.
    result["stage"] = "live-original-nested-and-outer-closure"

    def closed_claim():
        _, terminal = original()
        return terminal

    terminal = wait(closed_claim, RECIPE_SECONDS, processor)
    reap_owned_child(observer, wait)
    require(observer.returncode == 0 and kit["group_absent"](observer.pid), "original observer did not close")
    outer = terminal["outer"]
    require(type(outer["exit"]) is int and outer == dict(
        launch, parent_pid=observer.pid, exit=outer["exit"], direct_child_reaped=True,
        group_absent=True, descriptors_closed=True), "original CLI has no matching positive outer closure")
    nested, digest = terminal_xcode(tmp, witness, terminal["nested"], native, cut_ns)
    result.update(liveCustodyPending=False, xcodeInvocations=1,
                  liveClosure=dict(claim=terminal, xcodeReceiptSHA256=digest, xcodeExit=nested["exitCode"]))
    require(terminal["outcome"] == "succeeded" and outer["exit"] == nested["exitCode"] == 0
            and nested.get("stopReason") is None and not os.path.lexists(tmp / "cancel-requested"),
            "original unsigned Xcode invocation did not finish successfully without cancellation")

    result["stage"] = "live-original-oban-settlement"

    def settled():
        current = snapshot()
        return current if current["jobs"] == kit["COMPLETED_JOBS"] else None

    final = wait(settled, SETTLE_SECONDS, processor)
    row, final_claim = original()
    guard, closure, artifacts = (row[key] for key in ("guard", "closure", "artifacts"))
    versions = jobs()
    event = "coordinator:1:1:completed"
    require(final_claim == terminal and row["status"] == "native_ready"
            and guard["owner_id"].startswith(f"oban:{start_id}:") and guard["epoch"] > offline_guard["epoch"]
            and guard["revision"] == 1 and closure["ios_custody"] == terminal
            and closure["ios_outcome"] == "succeeded" and closure["closed"] is True
            and closure["commands"] == [
                {"command": command, "pid": pid, "receipt_sha256": receipt_sha, "stop_reason": None,
                 "group_terminate_sent": False}
                for command, pid, receipt_sha in ((SWIFT_PROBE[0], probe[1]["pid"], probe[2]),
                                                  (XCODE, xcode_pid, digest))]
            and final["record"] == [[record, 2]] and final["capacity"] == [[record, 1, 1, False, event]]
            and final["leases"] == [[record, None, None]]
            and final["operations"] == [[operation, record, binding["deadline_ms"], "admitted",
                                         1, guard["epoch"], guard["owner_id"]]]
            and versions[:2] == [[result["originalObanJobs"]["created"], "created", "completed"],
                                  [start_id, "start", "completed"]],
            "original attempt did not settle once and release its capacity")
    [[start, completed]] = json.loads(sql("SELECT json_agg(journal->'events') FROM mixer_builds"))
    result["settlementObservation"] = dict(jobs=versions, journal=[start, completed],
                                           reservation=final["capacity"][0], starts=row["starts"])
    require(set(start) == set(completed) == {"id", "event", "now_ms"}
            and type(start["now_ms"]) is int and type(completed["now_ms"]) is int
            and 0 < start["now_ms"] <= completed["now_ms"] <= binding["deadline_ms"]
            and start["event"] == {"type": "start", "ref": binding["ref"]}
            and completed["id"] == event
            and completed["event"] == {"type": "completed", "ref": binding["ref"],
                "result": {"outcome": "native_succeeded", "artifacts": [
                    {"kind": item["kind"], "sha256": item["sha256"], "size_bytes": item["sizeBytes"]}
                    for item in artifacts]}},
            "journal does not contain exactly one native success for the original attempt")
    report_path = output / "native/native-build.json"
    require(file_sha(report_path) == row["manifest_sha256"], "retained manifest digest differs")
    report = kit["read"](report_path)
    require(report["binding"]["compilerSourceDigest"] == result["compilerSourceSHA256"]
            and report["binding"]["authoritativeSourceDigest"] == spec["source"]["sha256"]
            and report["binding"]["lockSHA256"] == spec["toolchain_lock_sha256"]
            and report["binding"]["cliExecutableSHA256"] == result["cliSHA256"]
            and report["binding"]["command"] == item["command"],
            "retained manifest differs from the staged export, CLI or Xcode command")

    result["stage"] = "live-terminal-owner-readback"
    query = "?" + urlencode(scope)
    status, _, raw = http(auth, kit["BUILD"] + query, cookie=owner)
    detail = json.loads(raw)["build"]
    require((status, detail["buildId"], detail["platform"], detail["state"], detail["attempt"],
             detail["revision"], detail["workerCompletionPending"]) ==
            (200, scope["build_id"], "ios", "native_succeeded", 1, 2, False),
            "authenticated build detail did not show the same completed attempt")
    require([a["kind"] for a in artifacts] == list(kit["ATTACHMENTS"])
            and [{key: a[key] for key in ("kind", "sha256", "sizeBytes")} for a in detail["artifacts"]]
            == artifacts, "authenticated detail does not list the three durable artifacts")
    result["downloadObservations"] = []
    for artifact, descriptor in zip(artifacts, detail["artifacts"], strict=True):
        kind, size, digest = (artifact[key] for key in ("kind", "sizeBytes", "sha256"))
        url = descriptor["downloadPath"]
        route = urlsplit(url)
        require(not (route.scheme or route.netloc or route.fragment)
                and route.path == "/console-api/v1/build-artifacts/" + kind
                and sorted(parse_qsl(route.query, keep_blank_values=True, strict_parsing=True)) ==
                    sorted(scope.items()), "authenticated detail contains an unexpected artifact route")
        status, headers, body = http(auth, url, cookie=owner)
        headers = {k.lower(): v for k, v in headers.items()}
        anonymous_http = http(auth, url)[0]
        result["downloadObservations"].append(dict(kind=kind, ownerHTTP=status, anonymousHTTP=anonymous_http,
                                                    sizeBytes=len(body), sha256=sha(body)))
        require((status, anonymous_http, len(body), sha(body)) == (200, 401, size, digest)
                and headers.get("content-type") == "application/octet-stream"
                and headers.get("content-disposition") == f'attachment; filename="{kind}"',
                "authenticated artifact bytes differ from the original durable digest")
    url = kit["LOGS"] + query
    status, headers, raw = http(auth, url, cookie=owner)
    require((status, http(auth, url)[0]) == (200, 401)
            and {k.lower(): v for k, v in headers.items()}.get("cache-control") == "no-store",
            "authenticated log admission or cache policy differs")
    logs = json.loads(raw)["buildLogs"]
    compiler, outer_log = logs["events"]
    require({k: logs[k] for k in ("buildId", "state", "platform", "attempt", "revision")} ==
            dict(buildId=scope["build_id"], state="native_succeeded", platform="ios", attempt=1, revision=2)
            and {k: v for k, v in compiler.items() if k != "phases"} ==
                dict(event="compiler_finished", exitCode=0, stdoutBytes=nested["stdoutBytes"],
                     stderrBytes=nested["stderrBytes"], tailTruncated=nested["outputTruncated"])
            and outer_log == {"event": "build_command_finished", "exitCode": 0}
            and snapshot() == final and jobs() == versions and original() == (row, terminal),
            "log readback differs from the original receipts or changes settlement")
    result["settled"] = dict(jobs=versions, journal=[start, completed], reservation=final["capacity"][0],
                             guard=guard, manifestSHA256=row["manifest_sha256"], starts=row["starts"],
                             ownerLogHTTP=200, ownerLogEvents=logs["events"], ownerArtifactHTTP=200,
                             ownerState="native_succeeded", artifacts=artifacts, capacityReleases=1)
