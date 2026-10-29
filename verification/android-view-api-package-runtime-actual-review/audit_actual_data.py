"""Bounded package focused-host DATA audit; never import collector or inspector.

Run only as /opt/homebrew/bin/python3 -I -B -S audit_actual_data.py.
Root supplies local/recovery-001/artifact.zip and acquisition metadata independently.
"""
import sys
sys.dont_write_bytecode = True
import encodings.cp437
import binascii, hashlib, io, json, math, os, re, stat, struct, types
import unicodedata, zipfile, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HOST = "verification/android-view-api-package-runtime-host-preparation"
CANDIDATE = "verification/android-view-api-boundary-candidate"
INSPECTOR = "verification/android-view-api-boundary-bytecode-inspection"
HEAD = "c89b4d1657fc46581d8788169f9c961a2413c4f4"
TREE = "507ff501dbb8130ce37632eb3b207f5990f3689c"
RUN = 40895131023
NONCE = "2c04076528fc4a8a3a41ee6a754dcb7941200f7f5795bb7c525497468de56b95"
ZIP_SHA = "8e3665a6acb472f1ccbbb06eae0a582d5970fa17efdddecb28be405ed7e2c8eb"
READER_SHA = "b643b2303dd8e58fe2f8a9d823e791c26db931e9c5daaa9c1b4bf27846c7152e"
def sha(data): return hashlib.sha256(data).hexdigest()
# Read/compile exact reviewed source directly: import loaders may otherwise read
# an unpinned pre-existing pyc even when -B prevents new bytecode writes.
guard_path = ROOT / "verification/android-view-api-focused-actual-review/guarded_inspector.py"
guard_raw = guard_path.read_bytes()
guard = types.ModuleType("package_actual_review_guard")
guard.__file__ = str(guard_path)
exec(compile(guard_raw, str(guard_path), "exec", dont_inherit=True), guard.__dict__)
guard_record = guard.install_guards()
reader_path = ROOT / "verification/android-view-api-focused-actual-review/audit_data.py"
reader_raw = reader_path.read_bytes()
assert sha(reader_raw) == READER_SHA, "pinned data reader changed"
reader = types.ModuleType("package_actual_strict_reader")
reader.__file__ = str(reader_path)
exec(compile(reader_raw, str(reader_path), "exec", dont_inherit=True), reader.__dict__)
need, identity, canonical = reader.need, reader.identity, reader.canonical
read, strict = reader.read_regular, reader.strict_json

def local_json(path): return strict(read(ROOT / path, ROOT))
def frozen(path, expected):
    raw = read(ROOT / path, ROOT)
    need(identity(raw) == expected, "source identity: " + path)
    return raw
def save(name, value):
    (HERE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
def close_map(rows): return {r["path"]: {"bytes": r["bytes"], "sha256": r["sha256"]} for r in rows}

def source_review(report):
    metadata_raw = read(HERE / "root-connector-observation.json", HERE)
    need(identity(metadata_raw) == {"bytes": 2583, "sha256": "1cfdd92f44ec689558c10a23fd5f3570077c6cb4aa02a3f7371394c7b604dfd4"}, "root connector metadata identity")
    metadata = strict(metadata_raw)
    need(metadata["runID"] == RUN and metadata["runAttempt"] == 1 and metadata["job"]["id"] == 123522047495 and metadata["job"]["name"] == "focused", "actual run/job connector metadata")
    need(metadata["job"]["status"] == "completed" and metadata["job"]["conclusion"] == "success" and all(s["status"] == "completed" and s["conclusion"] == "success" for s in metadata["job"]["steps"]), "actual Actions terminal steps")
    artifact = metadata["artifact"]
    need(artifact["id"] == 12907091274 and artifact["name"] == "android-view-api-focused-" + HEAD + "-" + str(RUN) + "-1" and artifact["size_in_bytes"] == 1530579 and artifact["digest"] == "sha256:" + ZIP_SHA and artifact["expired"] is False and artifact["workflow_run"]["id"] == RUN and artifact["workflow_run"]["head_sha"] == HEAD, "actual service artifact metadata")
    log_row = metadata["decodedJobLog"]
    log_raw = frozen(log_row["path"], {"bytes": 22441, "sha256": "14d46d55ae5ab03818671bf223069005e35f0ab27518e9647e1e7dcb60b605d8"})
    log_text = log_raw.decode("utf-8", "strict")
    need("/usr/bin/python3 -I -B -S" in log_text and "40895131023" in log_text and "ubuntu" in log_text.lower(), "bound decoded job log bootstrap/run/provider")
    acquisitions = {}
    for path in ("local/acquisition.json", "local/recovery-001/acquisition.json"):
        payload = read(HERE / path, HERE); value = strict(payload)
        need(value["run_id"] == RUN and value["run_attempt"] == 1 and value["artifact_id"] == artifact["id"] and value["retries"] == 0, "bound acquisition record")
        acquisitions[path] = {"identity": identity(payload), "record": value}
    old = acquisitions["local/acquisition.json"]["record"]
    recovery = acquisitions["local/recovery-001/acquisition.json"]["record"]
    need(old["http_status"] == 403 and old["bytes_received"] == 0 and old["retained_payload"] is False and old["cleanup"]["cancellation_resolved"] is True, "original acquisition failure preserved")
    need(recovery["status"] == "exact-root-bound-artifact-retained" and recovery["http_status"] == 200 and recovery["payload"] == {"bytes": 1530579, "sha256": ZIP_SHA} and recovery["cleanup"]["reader_released"] is True and recovery["cleanup"]["eof_observed_by_consumer"] is True and recovery["cleanup"]["timeout_fired"] is False, "selected recovery exact/eof/release")
    report["metadata"] = {"identity": identity(metadata_raw), "record": metadata, "decoded_log": {"bytes": len(log_raw), "sha256": sha(log_raw), "lines": len(log_text.splitlines())}, "acquisitions": acquisitions, "connector_consumer_calls_total_root_reported": {"connector": 2, "consumer": 2}}
    delivered = "verification/github-delivery-android-host-followup/"
    selected_raw = frozen(delivered + "manual-package-followup-input.json", {
        "bytes": 1009, "sha256": "016fd1560d9a256cf35709dcd49b00fdf54718522e69d0b05c343d95bf0a1672"})
    selected = strict(selected_raw)
    run_raw = frozen(delivered + "manual-package-followup-run-binding.json", {
        "bytes": 7200, "sha256": "8c30bcb220dec312c11bfcb06e83d0746c528e02bd97caa1c034eace72a6e648"})
    binding = strict(run_raw)
    need(binding["head"] == HEAD and binding["tree"] == TREE and binding["manual"]["id"] == RUN,
         "delivered run/head/tree")
    need(binding["dispatches"] == binding["attempt"] == 1 and binding["retries"] == 0,
         "exactly-once run binding")
    for key in ("reservation", "submitted", "input"):
        row = binding[key]; frozen(row["path"], {"bytes": row["bytes"], "sha256": row["sha256"]})
    selection = strict(frozen(binding["selection"]["path"], {
        "bytes": binding["selection"]["bytes"], "sha256": binding["selection"]["sha256"]}))
    template = selection["manualHosts"]["package"]["exactSelectionBindings"]
    template["github_sha"] = HEAD
    need(template == selected and selected["dispatch_nonce"] == NONCE, "exact dispatched selection")
    need(selected["github_sha"] == HEAD and selected["dispatch_selected"] is True, "selected immutable head")
    for field, path in (("admission_seal_sha256", HOST + "/seal.json"), ("runner_sha256", HOST + "/collect.py"),
                        ("custody_sha256", HOST + "/custody.py"), ("workflow_draft_sha256", HOST + "/workflow.DRAFT.yml"),
                        ("installed_workflow_sha256", selected["workflow_relative_path"]),
                        ("candidate_freeze_sha256", CANDIDATE + "/freeze.json"),
                        ("inspector_seal_sha256", INSPECTOR + "/seal.json")):
        need(sha(read(ROOT / path, ROOT)) == selected[field], "selected pin: " + field)
    packets = {}
    for name in (HOST, INSPECTOR):
        seal = local_json(name + "/seal.json")
        rows = reader.verify_rows(ROOT / name, seal["members"])
        packets[name] = {"seal": identity(read(ROOT / name / "seal.json", ROOT)), "members": rows}
    manifest = local_json(HOST + "/input-manifest.json")
    rows = reader.verify_rows(ROOT, manifest["members"])
    need(len(rows) == 148 and len(manifest["host_sources"]) == 103 and len(manifest["sdk_sources"]) == 17,
         "source148 host103 sdk17")
    producer = local_json(CANDIDATE + "/manifest.json")
    producer_rows = reader.verify_rows(ROOT / CANDIDATE, producer["members"])
    need(len(producer_rows) == 115, "candidate115 exact source rows")
    observed, nodes = set(), 0
    for base, dirs, names in os.walk(ROOT / CANDIDATE, followlinks=False):
        nodes += len(dirs) + len(names)
        need(nodes <= 1024, "candidate node bound")
        dirs[:] = [d for d in dirs if d != "local"]
        for d in dirs:
            need(not (Path(base) / d).is_symlink(), "candidate directory symlink")
        for name in names:
            p = Path(base) / name
            relative = p.relative_to(ROOT / CANDIDATE).as_posix()
            if relative not in ("manifest.json", "freeze.json"):
                read(p, ROOT / CANDIDATE)
                observed.add(relative)
    need(observed == {r["path"] for r in producer_rows}, "candidate115 closed directory membership")
    product = {Path(r["path"]).name: {"bytes": r["bytes"], "sha256": r["sha256"]}
               for r in producer["members"] if r["path"].startswith("source/")}
    need(len(product) == 16 and sha(canonical(product)) == manifest["product_tree"] == reader.TREE, "product16 tree")
    leaf_paths = sorted(r["path"] for r in producer["members"] if r["path"].startswith("tests/host-leaves/") and r["path"].endswith(".java"))
    sources = sorted("source/" + p for p in product)
    need(len(leaf_paths) == 86 and manifest["host_sources"] == sorted(sources + leaf_paths + ["tests/ViewApiBoundaryTests.java"]), "host103 exact")
    need(manifest["sdk_sources"] == sorted(sources + ["tests/cross-leaf/NativeBridge.java"]), "sdk17 exact")
    need(manifest["copied_input_paths"] == sorted(set(manifest["host_sources"] + manifest["sdk_sources"] + ["tests/descriptor.json"])), "copied exact")
    runtime = local_json(HOST + "/jdk-runtime-members.json")
    runtime = runtime["members"] if isinstance(runtime, dict) else runtime
    need(len(runtime) == 74 and sum(r["bytes"] for r in runtime) == 198637181, "JDK74 manifest")
    source = {"members": 148, "map_sha256": sha(canonical(manifest["members"])),
              "product_tree": reader.TREE, "host_inputs": 103, "sdk_inputs": 17}
    report["source"] = {"binding": binding, "packets": packets, "input_manifest": identity(read(ROOT / HOST / "input-manifest.json", ROOT)),
                        "source_summary": source, "runtime_members": 74, "runtime_bytes": 198637181}
    return selected, packets, manifest, runtime, source

def plan_for(output, profile, manifest):
    scratch = output + "/scratch"; temp = scratch + "/tmp"; empty = scratch + "/empty"
    host = scratch + "/host-classes"; sdk = scratch + "/sdk-classes"; dex = scratch + "/dex"
    java = profile["jdk"] + "/bin/java"; javac = profile["jdk"] + "/bin/javac"
    jar = profile["android_platform"] + "/android.jar"; d8jar = profile["android_build_tools"] + "/lib/d8.jar"
    options = ["-Xmx256m", "-XX:MaxMetaspaceSize=256m", "-XX:ReservedCodeCacheSize=128m", "-XX:CompressedClassSpaceSize=128m",
               "-Djava.io.tmpdir=" + temp, "-Duser.home=" + scratch + "/home", "-Dfile.encoding=UTF-8"]
    compiler = ["-J" + o for o in options]
    flags = ["--release", "17", "-proc:none", "-Xlint:all", "-Werror", "-sourcepath", empty]
    commands = [
        {"name": "java-version", "argv": [java, *options, "-version"]},
        {"name": "javac-version", "argv": [javac, *compiler, "-version"]},
        {"name": "d8-version", "argv": [java, *options, "-cp", d8jar, "com.android.tools.r8.D8", "--version"]},
        {"name": "host-compile", "argv": [javac, *compiler, *flags, "-classpath", empty, "-d", host, *[scratch + "/inputs/" + p for p in manifest["host_sources"]]]},
        {"name": "focused-main", "argv": [java, *options, "-ea", "-cp", host, "dev.mixer.android.ViewApiBoundaryTests", scratch + "/inputs/" + manifest["descriptor"]]},
        {"name": "sdk37-compile", "argv": [javac, *compiler, *flags, "-classpath", jar, "-d", sdk, *[scratch + "/inputs/" + p for p in manifest["sdk_sources"]]]}]
    return {"commands": commands, "scratch": scratch, "host_classes": host, "sdk_classes": sdk, "dex_dir": dex,
            "platform_jar": jar, "d8_prefix": [java, *options, "-cp", d8jar, "com.android.tools.r8.D8", "--min-api", "28", "--lib", jar, "--output", dex],
            "command_count": 7, "work_commands": 4, "version_commands": 3}

def actual_review(report, selected, packets, manifest, runtime, source):
    archive = HERE / "local/recovery-001/artifact.zip"
    raw = read(archive, HERE, maximum=192 * 1024 * 1024)
    need(identity(raw) == {"bytes": 1530579, "sha256": ZIP_SHA}, "actual ZIP identity")
    files, inventory = reader.inspect_zip(raw)
    eocd = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
    inventory["zip_members"] = struct.unpack_from("<H", raw, eocd + 10)[0]
    inventory["root_prefixes"] = sorted({n.split("/")[0] for n in files})
    report["archive"] = inventory
    save("archive-inventory.json", inventory)
    output_candidates = [n.removesuffix("/receipt.json") for n in files if n.endswith("/android-view-api-focused-" + str(RUN) + "-1/receipt.json")]
    need(len(output_candidates) == 1, "one exact actual output prefix")
    prefix = output_candidates[0]
    report["output_prefix"] = prefix
    def data(relative):
        key = prefix + "/" + relative
        need(key in files, "missing actual output: " + relative)
        return files[key]
    def obj(relative): return strict(data(relative))
    # Parse every actual JSON member under strict duplicate/size/node/depth rules.
    json_count = 0
    for name, payload in files.items():
        if name.endswith(".json"):
            strict(payload); json_count += 1
    report["strict_json_members"] = json_count
    used = set()
    for name, packet in packets.items():
        tail = "/" + name
        candidates = [n.removesuffix("/seal.json") for n in files if n.endswith(tail + "/seal.json")]
        need(len(candidates) == 1, "one uploaded packet: " + name)
        packet_prefix = candidates[0]
        expected = {packet_prefix + "/" + r["path"]: {"bytes": r["bytes"], "sha256": r["sha256"]} for r in packet["members"]}
        expected[packet_prefix + "/seal.json"] = packet["seal"]
        observed = {n: identity(v) for n, v in files.items() if n.startswith(packet_prefix + "/")}
        need(observed == expected, "uploaded sealed packet exact closure: " + name)
        used.update(expected)
    selected_output = obj("root-selection.json")
    need(selected_output == selected, "output selection exact")
    mat = [n for n in files if n.endswith("/android-view-api-root-selection.json")]
    need(len(mat) == 1 and strict(files[mat[0]]) == selected, "materialized exact selection")
    reserve = [n for n in files if n.endswith("/.mixer-view-api-custody-" + NONCE + ".reservation.json")]
    need(len(reserve) == 1, "one retained nonce reservation")
    reservation = strict(files[reserve[0]])
    need(reservation == {"schema": 1, "dispatch_nonce": NONCE, "github_sha": HEAD, "run_id": str(RUN), "status": "reserved-once-no-restart", "total_children": 7}, "retained reservation exact")
    used.update(mat + reserve)
    receipt = obj("receipt.json")
    report["producer_receipt"] = receipt
    need(receipt["selection"] == {"revision": HEAD, "run_id": str(RUN), "run_attempt": 1, "root_dispatch_nonce": NONCE, "selection_sha256": sha(canonical(selected))}, "receipt selection canonical identity")
    need({k: receipt["one_shot_reservation"][k] for k in ("bytes", "sha256")} == identity(files[reserve[0]]), "reservation receipt identity")
    need(receipt["status"] == "passed-focused-host-and-sdk37-d8-only" and receipt["runtime_accepted"] is True and receipt["errors"] == [], "actual producer result")
    need(receipt["old_process_access_or_cleanup"] is False and receipt["native_ui_capture_phones"] is False, "producer restricted scope")
    need(obj("source-preflight.json") == receipt["source_after"] == source and receipt["source_unchanged"] is True, "before/after source148")
    profile = local_json(HOST + "/tool-profile.json")
    tools = obj("tool-preflight.json")
    def tools_check(value):
        need(value == tools, "within-run exact tools observation")
        need(value["tool_files"] == profile["files"], "SDK37/D8 exact files")
        rows = value["jdk_runtime"]["members"]
        need(len(rows) == 74 and close_map(rows) == close_map(runtime), "actual JDK74 exact pins")
        need(value["jdk_runtime"]["scope"] == profile["packaging_boundary"], "exact runtime membership policy")
        need(all(r["resolved"] == profile["jdk"] + "/" + r["path"] and r["symlink"] is None for r in rows), "ordinary actual JDK74 paths")
        need(value["python"]["version"].startswith("3.12.3 ") and value["python"]["bootstrap_independently_pinned_by_running_collector"] is False, "actual Python provider")
        need('ID=ubuntu' in value["provider_os_release"]["text"] and 'VERSION_ID="24.04"' in value["provider_os_release"]["text"], "actual Ubuntu24.04")
        need(identity(value["provider_os_release"]["text"].encode()) == {k: value["provider_os_release"][k] for k in ("bytes", "sha256")}, "os-release text identity")
    tools_check(tools); tools_check(receipt["tools_before"]); tools_check(receipt["tools_after"])
    actual_plan = obj("plan.json")
    output = actual_plan["scratch"].removesuffix("/scratch")
    need(output == "/home/runner/work/_temp/android-view-api-focused-" + str(RUN) + "-1", "actual output selected RUNNER_TEMP path")
    plan = plan_for(output, profile, manifest)
    need(actual_plan == plan, "independently reconstructed exact argv plan")
    candidate_rows = {r["path"].removeprefix(CANDIDATE + "/"): {"bytes": r["bytes"], "sha256": r["sha256"]} for r in manifest["members"] if r["path"].startswith(CANDIDATE + "/")}
    copied = [{"path": p, **candidate_rows[p]} for p in manifest["copied_input_paths"]]
    need(obj("copied-inputs.json") == copied, "exact copied-inputs map")
    for row in copied:
        need(identity(data("scratch/inputs/" + row["path"])) == {k: row[k] for k in ("bytes", "sha256")}, "copied actual bytes")
    maps = {}
    for kind in ("host", "sdk"):
        rows = obj(kind + "-classes.json")
        observed = {n.removeprefix(prefix + "/scratch/" + kind + "-classes/"): identity(v) for n, v in files.items() if n.startswith(prefix + "/scratch/" + kind + "-classes/")}
        need(observed == close_map(rows) and 1 <= len(rows) <= 512, kind + " exact emitted class closure")
        need(all(n.endswith(".class") and data("scratch/" + kind + "-classes/" + n)[:4] == b"\xca\xfe\xba\xbe" for n in observed), "raw ordinary class identities")
        maps[kind] = rows
    stage = {"files": len(copied), "bytes": sum(r["bytes"] for r in copied), "disposition": "retained; no deletion"}
    stage_pairs = {}
    for name in reader.COMMANDS:
        before = dict(stage)
        if name in ("host-compile", "sdk37-compile"):
            kind = "host" if name == "host-compile" else "sdk"
            stage["files"] += len(maps[kind]); stage["bytes"] += sum(r["bytes"] for r in maps[kind])
        if name == "d8-min28":
            stage["files"] += 1; stage["bytes"] += len(data("scratch/dex/classes.dex"))
        stage_pairs[name] = (before, dict(stage))
    d8 = {"name": "d8-min28", "argv": plan["d8_prefix"] + [plan["sdk_classes"] + "/" + r["path"] for r in maps["sdk"]]}
    need(obj("d8-exact-plan.json") == d8, "D8 exact SDK-emitted argv")
    entries = plan["commands"] + [d8]
    need(receipt["attempted_commands"] == [e["name"] for e in entries] and receipt["commands"] == [{"name": e["name"], "accepted": True} for e in entries], "all seven attempted/accepted order")
    env = {"JAVA_HOME": profile["jdk"], "PATH": profile["jdk"] + "/bin:/usr/bin:/bin", "HOME": plan["scratch"] + "/home", "TMPDIR": plan["scratch"] + "/tmp", "TMP": plan["scratch"] + "/tmp", "TEMP": plan["scratch"] + "/tmp", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
    commands = []
    initial_fields = ("schema", "name", "argv", "cwd", "env", "bounds", "retries", "shell", "group_origin", "terminal_group_observation")
    pids = set()
    for entry in entries:
        name = entry["name"]; pre = "commands/" + name + "/"
        initial = obj(pre + "command.json"); result = obj(pre + "result.json")
        need(all(initial[k] == result[k] for k in initial_fields), name + " initial/final immutable identity")
        need(initial["exit_code"] is None and initial["errors"] == initial["signals"] == [], name + " initial unresolved state")
        for field in ("spawned", "direct_reaped", "exact_kernel_waitpid", "group_absent", "stdout_eof", "stderr_eof", "preflight_ok", "postflight_ok", "direct_exit_observed_without_reap", "signals_retired", "held", "custody_lost", "ownership_valid", "wait_owner_preconditions"):
            need(initial[field] is False, name + " initial custody: " + field)
        need(result["name"] == name and result["argv"] == entry["argv"] and result["cwd"] == plan["scratch"] and result["env"] == env and result["bounds"] == profile["bounds"], name + " command/context/bounds")
        for field in ("spawned", "direct_exit_observed_without_reap", "signals_retired", "direct_reaped", "exact_kernel_waitpid", "group_absent", "stdout_eof", "stderr_eof", "preflight_ok", "postflight_ok", "wait_owner_preconditions", "accepted"):
            need(result[field] is True, name + " true custody: " + field)
        for field in ("held", "custody_lost", "ownership_valid", "shell"):
            need(result[field] is False, name + " false custody: " + field)
        need(result["exit_code"] == result["retries"] == 0 and result["errors"] == result["signals"] == [], name + " terminal clean zero")
        pid = result["pid"]
        need(type(pid) is int and pid > 0 and pid not in pids and result["pgid"] == pid, name + " fresh pid=pgid")
        pids.add(pid)
        need(obj(pre + "spawn.json") == {"pid": pid, "pgid": pid, "new_session": True}, name + " spawn record")
        need(obj(pre + "signal-authority-retired.json") == {"pgid": pid, "irreversible": True, "before_direct_reap": True, "further_signals_or_repeated_group_probes": False}, name + " retirement record")
        need(result["waitid_status"] == {"pid": pid, "code": 1, "status": 0} and result["observed_exit_code"] == 0, name + " exact WNOWAIT status")
        need(result["kernel_waitpid_result"] == {"python_type": "tuple", "repr": "(" + str(pid) + ", 0)"} and result["group_probe_count"] == 1, name + " exact kernel tuple/single ESRCH probe")
        need(result["wait_owner_observation"] == {"SIGCHLD": "SIG_DFL", "SA_NOCLDWAIT": False, "read_only_sigaction": True, "python_main_thread_only": True, "subprocess_active_empty": True, "exclusive_wait_owner_scope": "standalone selected collector; no external reaper proof"}, name + " wait-owner preconditions")
        for flight in ("input_preflight", "input_postflight"):
            f = result[flight]
            need(f["source"] == source, name + " source flight")
            tools_check(f["tools"])
            need(0 <= f["scratch"]["files"] <= profile["scratch_files"] and 0 <= f["scratch"]["bytes"] <= profile["scratch_file_bytes"] and f["scratch"]["disposition"] == "retained; no deletion", name + " scratch bounds")
            need(f["scratch"] == stage_pairs[name][0 if flight == "input_preflight" else 1], name + " exact stage scratch reconciliation")
        streams = {}
        for stream in ("stdout", "stderr"):
            payload = data(pre + stream)
            need(identity(payload) == result[stream + "_identity"] and len(payload) <= profile["bounds"]["stream_bytes"], name + " actual stream identity/bound")
            streams[stream] = identity(payload)
        if name in ("java-version", "javac-version", "d8-version"):
            key = {"java-version": "java_stderr", "javac-version": "javac_stdout", "d8-version": "d8_stdout"}[name]
            stream = key.split("_")[-1]; other = "stderr" if stream == "stdout" else "stdout"
            need(data(pre + stream) == profile["versions"][key].encode() and data(pre + other) == b"", name + " exact version streams")
        else:
            need(data(pre + "stderr") == b"", name + " empty stderr")
            if name != "focused-main": need(data(pre + "stdout") == b"", name + " empty work stdout")
        need(type(result["elapsed_seconds"]) in (int, float) and 0 <= result["elapsed_seconds"] < 60, name + " actual elapsed bound")
        commands.append({"name": name, "pid": pid, "argv_count": len(entry["argv"]), "streams": streams, "elapsed_seconds": result["elapsed_seconds"], "terminal_custody_accepted": True, "preflight_scratch": result["input_preflight"]["scratch"], "postflight_scratch": result["input_postflight"]["scratch"]})
    report["commands"] = commands
    coverage = local_json(CANDIDATE + "/coverage-plan.json")
    lines = data("commands/focused-main/stdout").decode("utf-8", "strict").splitlines()
    groups = [g["name"] for g in coverage["groups"]]
    need(len(groups) == 13 and len(lines) == 14 and lines[:13] == ["PASS " + g for g in groups], "exact actual13 group lines/order")
    m = re.fullmatch(r"PASS 13 focused actual-source groups / ([1-9][0-9]{0,5}) assertions; mechanical host leaves only", lines[-1])
    need(m is not None, "actual assertion summary")
    report["focused"] = {"groups": groups, "assertions": int(m.group(1)), "stdout_lines": len(lines), "source_bound_interruption_calls": 152, "interruption_derivation": {"API29": 4 * 4 * 2, "API30": 5 * 4 * 2, "API36": 5 * 4 * 2, "API37": 5 * 4 * 2}}
    inspections = {}
    for name in ("host-class-inspection.json", "sdk-class-inspection.json", "dex-inspection.json"):
        value = obj(name)
        need(value["accepted"] is True, "actual inspection accepted: " + name)
        need(value["source_binding"] == {"freeze_sha256": selected["candidate_freeze_sha256"], "manifest_sha256": sha(read(ROOT / CANDIDATE / "manifest.json", ROOT)), "product_tree": reader.TREE, "custody_verified_by_this_function": False}, "inspection exact source identity")
        if name != "dex-inspection.json":
            kind = name.split("-")[0]
            need({r["path"]: r["identity"] for r in value["artifacts"]} == close_map(maps[kind]), kind + " report/classmap/raw identity")
            need(value["platform_jar"] == profile["files"][plan["platform_jar"]], kind + " report SDK identity")
        inspections[name] = {"identity": identity(data(name)), "report": value}
    report["inspections"] = inspections
    dex = data("scratch/dex/classes.dex")
    need(dex[:8] == b"dex\n039\0" and receipt["dex"] == identity(dex) == obj("dex-inspection.json")["artifact"], "actual DEX039/report/receipt identity")
    need(struct.unpack_from("<I", dex, 32)[0] == len(dex) and dex[12:32] == hashlib.sha1(dex[32:]).digest() and struct.unpack_from("<I", dex, 8)[0] == zlib.adler32(dex[12:]) & 0xffffffff, "DEX file size/signature/checksum")
    scratch_rows = [{"path": n.removeprefix(prefix + "/scratch/"), **identity(v)} for n, v in files.items() if n.startswith(prefix + "/scratch/")]
    expected_scratch = {"inputs/" + r["path"]: {"bytes": r["bytes"], "sha256": r["sha256"]} for r in copied}
    expected_scratch.update({kind + "-classes/" + r["path"]: {"bytes": r["bytes"], "sha256": r["sha256"]} for kind in ("host", "sdk") for r in maps[kind]})
    expected_scratch["dex/classes.dex"] = identity(dex)
    need(close_map(scratch_rows) == expected_scratch, "closed scratch families; tmp/home/empty contain no files")
    scratch = {"files": len(scratch_rows), "bytes": sum(r["bytes"] for r in scratch_rows), "disposition": "retained; no deletion"}
    need(receipt["final_flight"]["scratch"] == scratch and receipt["final_flight"]["source"] == source, "actual final retained scratch counts")
    tools_check(receipt["final_flight"]["tools"])
    report["scratch"] = scratch
    expected_output = {"root-selection.json", "source-preflight.json", "tool-preflight.json", "plan.json", "copied-inputs.json", "host-classes.json", "host-class-inspection.json", "sdk-classes.json", "sdk-class-inspection.json", "d8-exact-plan.json", "dex-inspection.json", "receipt.json"}
    expected_output.update("commands/" + e["name"] + "/" + n for e in entries for n in ("command.json", "spawn.json", "signal-authority-retired.json", "stdout", "stderr", "result.json"))
    expected_output.update("scratch/" + r["path"] for r in scratch_rows)
    actual_output = {n.removeprefix(prefix + "/") for n in files if n.startswith(prefix + "/")}
    need(actual_output == expected_output, "closed actual output inventory")
    used.update(prefix + "/" + n for n in expected_output)
    need(used == set(files), "closed actual archive file inventory")
    report["actual_counts"] = {"files": inventory["files"], "expanded_bytes": inventory["total_bytes"], "host_classes": len(maps["host"]), "sdk_classes": len(maps["sdk"]), "dex_files": 1, "dex_bytes": len(dex), "commands": 7, "groups": 13, "interruptions": 152, "assertions": int(m.group(1)), "scratch": scratch}
    need(identity(read(archive, HERE, maximum=192 * 1024 * 1024)) == inventory["archive"], "ZIP unchanged after analysis")
    after_files, after_inventory = reader.inspect_zip(raw)
    need(after_inventory["members"] == inventory["members"] and after_inventory["member_map_sha256"] == inventory["member_map_sha256"], "member map unchanged after analysis")

def main():
    report = {"schema": 1, "status": "evidence-incomplete-held", "command": list(sys.orig_argv),
        "python": {"executable": sys.executable, "version": sys.version}, "bootstrap": {"isolated": sys.flags.isolated, "no_site": sys.flags.no_site, "bytecode_disabled": sys.dont_write_bytecode},
        "audit_source": identity(read(__file__, HERE)), "reader_source": {"path": str(reader_path.relative_to(ROOT)), "sha256": READER_SHA},
        "guard": {**guard_record, "source": {"path": str(guard_path.relative_to(ROOT)), **identity(guard_raw)}},
        "bound_run": {"head": HEAD, "tree": TREE, "run_id": RUN, "attempt": 1, "workflow_id": 400656208, "job_id": 123522047495, "artifact_id": 12907091274},
        "scope": "Independent strict archive/JSON/source/command-custody DATA audit; binary semantics independently reparsed in separately owned lane; no collector/inspector import or active oracle."}
    try:
        need(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode, "isolated required")
        selected, packets, manifest, runtime, source = source_review(report)
        actual_review(report, selected, packets, manifest, runtime, source)
        report["status"] = "scoped-data-pass"
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)[:3000]
    report["active_api_denials_triggered"] = [] if "ActiveAPIDenied" not in report.get("error", "") else [report["error"]]
    report["limitations"] = ["Custody is a source-bound producer report; no independent kernel tracing or new process/group query. ESRCH is absence only at its recorded instant.",
        "74 runtime identities and closed scope are reported by the collector; JDK bytes are not uploaded. Ubuntu Python/stdlib/bootstrap, provider OS/loader/system libraries/CA and pinned Actions remain admitted infrastructure.",
        "Separate binary reparse is required for independent class/helper/dataflow/inherited-method semantics; this audit binds the three actual report identities and raw output identities.",
        "No cleanup/disposal, escaped-descendant absence, ART/native startup matrix, canonical source-pair, full public V2/lower-API rendering, IME/TalkBack/OEM, immutable SDK/FieldLog, OTA/store/production/customer/release/GA conclusion.",
        "Simulator/emulator/UI/capture runtime checks remain paused; phones remain disconnected; all existing process/custody holds preserved."]
    attempt = 1
    while (HERE / ("actual-review-attempt-" + str(attempt) + ".json")).exists():
        attempt += 1
    report["audit_attempt"] = attempt
    save("actual-review-attempt-" + str(attempt) + ".json", report)
    save("actual-review.json", report)
    print(json.dumps({"status": report["status"], "error": report.get("error"), "actual_counts": report.get("actual_counts"), "output_prefix": report.get("output_prefix")}))
    if "error" in report: raise SystemExit(1)

if __name__ == "__main__": main()
