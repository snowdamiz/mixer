"""Root-selected finite outer-ZIP/report data audit; no subject import or inner archive."""
import sys
import os
import stat
import struct
import zlib
import binascii
import hashlib
import json
import builtins

ROOT = "/Users/andreyyurlov/Documents/dev/mixer"
HERE = ROOT + "/verification/android-view-api-focused-actual-review/jdk-data-actual-review"
BASE = HERE + "/local/recovery-001"
PREP = ROOT + "/verification/android-view-api-focused-actual-review/jdk-observation-preparation"
HEAD = "47b62878bae3aa3d4dff5d565b63f4a533e7abde"
NONCE = "fda6cf6bedfd7897f576df54eac07bec4c80884e209647c84081124d11950cca"
MANIFEST_SHA = "f865a86fb102646eb2c25e8fab00e13651de4f950e474e7faae4561516e69fb0"
WORKFLOW_SHA = "18a7451271c17ca9fdbaae74091a859a7e49337e93d5f6a3277699f4159d6f0a"
RUNTIME_SHA = "c75e64616ebb599f7337df7d7026286f1fd2d300347b59e28fb8a1051fdef13f"

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")

def parse(data):
    need(len(data) <= 1048576, "JSON input exceeds 1MiB")
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def bad(value):
        raise ValueError("non-finite JSON")
    result = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=pairs, parse_constant=bad)
    pending = [(result, 0)]
    nodes = 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        need(nodes <= 100000 and depth <= 40, "JSON node/depth cap")
        if type(value) is dict:
            pending.extend((x, depth + 1) for x in value.values())
        elif type(value) is list:
            pending.extend((x, depth + 1) for x in value)
    return result

def read_file(path, cap):
    need(path.startswith(ROOT + "/") and "//" not in path, "local input scope")
    parts = path.split("/")
    for index in range(2, len(parts) + 1):
        need(not stat.S_ISLNK(os.lstat("/".join(parts[:index])).st_mode), "local symlink refused")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= cap, "bounded ordinary input")
        blocks, total = [], 0
        while total < before.st_size:
            block = os.read(fd, min(1048576, before.st_size - total))
            need(bool(block), "local input ended early")
            total += len(block)
            blocks.append(block)
        after = os.fstat(fd)
        fields = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        need(fields(before) == fields(after) == fields(os.lstat(path)), "local input changed")
        return b"".join(blocks)
    finally:
        os.close(fd)

def output(path, data):
    need(path.startswith(BASE + "/") and type(data) is bytes, "local output scope")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        at = 0
        while at < len(data):
            written = os.write(fd, data[at:at + 1048576])
            need(written > 0, "local output short write")
            at += written
    finally:
        os.close(fd)

def install_guards():
    need(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.dont_write_bytecode == 1, "-I -B -S required")
    def denied(*args, **kwargs):
        raise RuntimeError("active API denied in finite data audit")
    patched = []
    names = [n for n in dir(os) if n.startswith(("exec", "spawn", "posix_spawn", "fork", "wait"))]
    names += ["system", "popen", "kill", "killpg", "getpid", "getppid", "getpgid", "getpgrp", "getsid", "setsid", "setpgid", "tcgetpgrp", "tcsetpgrp", "uname", "getloadavg", "times", "getpriority", "setpriority", "nice", "abort"]
    for module in (os, sys.modules.get(os.name)):
        if module is not None:
            for name in names:
                if hasattr(module, name):
                    setattr(module, name, denied)
                    patched.append(module.__name__ + "." + name)
    for module_name, selected in (("time", ["sleep", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "process_time", "process_time_ns", "thread_time", "thread_time_ns", "clock_gettime", "clock_gettime_ns", "clock_settime", "clock_settime_ns", "get_clock_info"]), ("_thread", ["start_new_thread", "start_new", "get_ident", "get_native_id", "interrupt_main"])):
        module = sys.modules.get(module_name)
        if module is not None:
            for name in selected:
                if hasattr(module, name):
                    setattr(module, name, denied)
                    patched.append(module_name + "." + name)
    def no_import(*args, **kwargs):
        denied()
    builtins.__import__ = no_import
    def audit(event, args):
        if event == "import" or event.startswith(("subprocess.", "socket.", "ctypes.", "signal.", "_thread.", "pty.")) or event in ("os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.uname"):
            denied()
    sys.addaudithook(audit)
    return {"installed_before_data_audit": True, "subject_imports": 0, "post_guard_imports": 0, "patched": sorted(set(patched)), "active_module_imports": 0, "limitation": "Reviewed Python/stdlib source defense; not hostile-code sandbox or kernel attestation."}

def safe_name(raw):
    name = raw.decode("ascii", "strict")
    need(name and len(raw) <= 512 and len(name.split("/")) <= 16, "ZIP path length/depth")
    need(all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/" for c in name), "ZIP noncanonical path character")
    need(all(p not in ("", ".", "..") for p in name.split("/")), "ZIP unsafe path")
    return name

def extras(raw):
    at, seen = 0, set()
    while at < len(raw):
        need(at + 4 <= len(raw), "truncated ZIP extra")
        kind, length = struct.unpack_from("<HH", raw, at)
        at += 4
        need(kind not in seen and at + length <= len(raw), "ZIP extra duplicate/length")
        need(kind not in (0x7075, 0x6375, 0x9901), "ZIP path/encryption override extra")
        seen.add(kind)
        at += length

def inspect_zip(raw):
    need(identity(raw) == {"bytes": 5904159, "sha256": "b166c2e2ce0dbff158315166ce407cd21915e560fcb22577ffd1630f1556cfb0"}, "exact root artifact identity")
    need(len(raw) <= 8388608 and raw[:4] == b"PK\x03\x04", "ZIP envelope/cap")
    end = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
    need(end >= 0 and end + 22 <= len(raw), "ZIP EOCD absent")
    e = struct.unpack_from("<4s4H2IH", raw, end)
    need(e[1] == e[2] == 0 and e[3] == e[4] and 1 <= e[4] <= 64 and e[5] + e[6] == end and end + 22 + e[7] == len(raw), "ZIP EOCD bounds/disks/trailing")
    cursor, files, seen, ranges, total, rows = e[6], {}, set(), [], 0, []
    for index in range(e[4]):
        need(cursor + 46 <= end, "ZIP central header bound")
        c = struct.unpack_from("<4s6H3I5H2I", raw, cursor)
        need(c[0] == b"PK\x01\x02" and c[13] == 0, "ZIP central signature/disk")
        made, version, flags, method = c[1:5]
        crc, packed, size = c[7:10]
        nl, xl, cl = c[10:13]
        mode, offset = c[15] >> 16, c[16]
        need(version <= 63 and not flags & ~(0x800 | 8 | 6) and method in (0, 8), "ZIP encryption/flags/method")
        need(0 <= size <= 20971520 and packed <= len(raw) and size <= max(1, packed) * 2000, "ZIP member expansion bound")
        need(stat.S_IFMT(mode) in (0, stat.S_IFREG), "ZIP symlink/nonordinary")
        stop = cursor + 46 + nl + xl + cl
        need(stop <= end, "ZIP central variable bound")
        name_bytes = raw[cursor + 46:cursor + 46 + nl]
        name = safe_name(name_bytes)
        need(name.casefold() not in seen, "ZIP duplicate/normalized alias")
        seen.add(name.casefold())
        extras(raw[cursor + 46 + nl:cursor + 46 + nl + xl])
        total += size
        need(total <= 33554432, "ZIP aggregate expansion cap")
        need(0 <= offset <= e[6] - 30, "ZIP local offset")
        h = struct.unpack_from("<4s5H3I2H", raw, offset)
        need(h[0] == b"PK\x03\x04" and h[1] == version and h[2] == flags and h[3] == method, "ZIP local/central header mismatch")
        start = offset + 30 + h[9] + h[10]
        stop_data = start + packed
        need(start <= stop_data <= e[6], "ZIP compressed data bound")
        need(raw[offset + 30:offset + 30 + h[9]] == name_bytes, "ZIP local name mismatch")
        extras(raw[offset + 30 + h[9]:start])
        if flags & 8:
            need(h[6] in (0, crc) and h[7] in (0, packed) and h[8] in (0, size), "ZIP descriptor local values")
            descriptor = stop_data + (4 if raw[stop_data:stop_data + 4] == b"PK\x07\x08" else 0)
            need(descriptor + 12 <= e[6] and struct.unpack_from("<III", raw, descriptor) == (crc, packed, size), "ZIP data descriptor")
            stop_data = descriptor + 12
        else:
            need(h[6:9] == (crc, packed, size), "ZIP local CRC/length")
        packed_data = raw[start:start + packed]
        if method == 0:
            data = packed_data
        else:
            decoder = zlib.decompressobj(-15)
            data = decoder.decompress(packed_data, size + 1)
            need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, "ZIP deflate EOF/trailing/output cap")
        need(len(data) == size and binascii.crc32(data) & 0xffffffff == crc, "ZIP uncompressed CRC/length")
        files[name] = data
        ranges.append((offset, stop_data))
        rows.append({"path": name, **identity(data), "crc32": "%08x" % crc, "compression": method})
        cursor = stop
    need(cursor == end, "ZIP central directory unexplained bytes")
    ranges.sort()
    need(ranges[0][0] == 0 and ranges[-1][1] == e[6] and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])), "ZIP gap/overlap/unindexed data")
    need(all(not any(name.startswith(other + "/") for other in files if other != name) for name in files), "ZIP file prefix collision")
    return files, {"archive": identity(raw), "entries": len(files), "expanded_bytes": total, "members": sorted(rows, key=lambda r: r["path"]), "limits": {"entries": 64, "per_entry_bytes": 20971520, "expanded_bytes": 33554432, "archive_bytes": 8388608}}

def stable(record, path, cap):
    need(record["status"] == "stable-regular-file" and record["path"] == path, "source reported file observation refused")
    need(record["before"] == record["after"], "source reported file metadata changed")
    before = record["before"]
    need(stat.S_ISREG(before["mode"]) and 0 <= before["size"] == record["bytes"] <= cap, "source reported ordinary file/byte cap")
    need(record["known_initial_size_read"] is True and record["extra_eof_read_attempted"] is False, "source read accounting markers")
    need(type(record["sha256"]) is str and len(record["sha256"]) == 64 and all(c in "0123456789abcdef" for c in record["sha256"]), "source digest shape")

def main(report):
    raw = read_file(BASE + "/artifact.zip", 8388608)
    files, inventory = inspect_zip(raw)
    report["outer_zip"] = inventory
    prefix = "mixer/mixer/verification/android-view-api-focused-actual-review/jdk-observation-preparation/"
    out = "_temp/mixer-jdk-observation-40863640582-1/"
    workflow = "mixer/mixer/.github/workflows/android-view-api-jdk-data-observation.yml"
    source_names = ["bootstrap.py", "contract.json", "expected-runtime-members.json", "observe_jdk.py", "workflow-draft.yml", "source-manifest.json"]
    output_names = ["bootstrap-receipt.json", "nonce-reservation.json", "root-selection.json", "observation.json", "ct.sym.raw-data.bin", "jrt-fs.jar.raw-data.bin"]
    expected = {prefix + n for n in source_names} | {out + n for n in output_names} | {workflow}
    report["inventory_delta"] = {"missing": sorted(expected - set(files)), "unexpected": sorted(set(files) - expected)}
    need(set(files) == expected and len(files) == 13, "source-derived exact13 membership")
    manifest_data = files[prefix + "source-manifest.json"]
    need(identity(manifest_data)["sha256"] == MANIFEST_SHA, "source manifest root pin")
    manifest = parse(manifest_data)
    for row in manifest["members"]:
        name = row["path"]
        need(identity(files[prefix + name]) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "uploaded manifest member identity")
    for name in source_names:
        need(files[prefix + name] == read_file(PREP + "/" + name, 1048576), "uploaded/local frozen source bytes")
    need(files[workflow] == files[prefix + "workflow-draft.yml"] and identity(files[workflow])["sha256"] == WORKFLOW_SHA, "installed workflow exact selected draft")
    contract = parse(files[prefix + "contract.json"])
    rows = parse(files[prefix + "expected-runtime-members.json"])
    need(len(rows) == 74 and sum(r["bytes"] for r in rows) == 198674633 and identity(files[prefix + "expected-runtime-members.json"])["sha256"] == RUNTIME_SHA, "original74 expected manifest")
    need(files[prefix + "expected-runtime-members.json"] == read_file(ROOT + "/verification/android-view-api-boundary-linux-tool-profile/runtime-members.json", 65536), "original manifest exact bytes unchanged")
    selection = parse(files[out + "root-selection.json"])
    selected = parse(read_file(PREP + "/root-selection-template.json", 65536))
    selected.update(dispatch_selected=True, delivered_head=HEAD, admit_ambient_ubuntu_python_checkout_upload=True)
    need(selection == selected, "root template exact allowed three-key delta")
    reservation = parse(files[out + "nonce-reservation.json"])
    need(reservation == {"schema": 1, "dispatch_nonce": NONCE, "github_sha": HEAD, "run_id": "40863640582", "run_attempt": 1, "status": "reserved-once-zero-child-commands-no-restart", "child_commands": []}, "nonce reservation exact source binding")
    boot = parse(files[out + "bootstrap-receipt.json"])
    obs = parse(files[out + "observation.json"])
    need(boot["status"] == "sealed-observer-returned-data-only" and boot["observer_exit_code"] == 0 and boot["diagnostic_only"] is True and boot["child_commands"] == [], "bootstrap successful data-only boundary")
    for limit_name, limit_cap in [("RLIMIT_CPU", 90), ("RLIMIT_AS", 536870912), ("RLIMIT_FSIZE", 20971520), ("RLIMIT_NOFILE", 64), ("RLIMIT_CORE", 0), ("RLIMIT_NPROC", 0)]:
        bound = boot["self_limits"][limit_name]
        need(type(bound) is list and len(bound) == 2 and bound[0] == bound[1] and 0 <= bound[0] <= limit_cap, "source reported self limits")
    source = boot["selected_source"]
    need(source == obs["selected_source"], "bootstrap/observer selected-source agreement")
    need(source["delivered_head"] == HEAD and source["run_id"] == "40863640582" and source["run_attempt"] == 1 and source["dispatch_nonce"] == NONCE and source["source_manifest_sha256"] == MANIFEST_SHA and source["workflow_sha256"] == WORKFLOW_SHA and source["workflow_path"] == ".github/workflows/android-view-api-jdk-data-observation.yml", "selected source exact run/head/nonce/pins")
    for name in source_names[:-1]:
        record = source["source_members"][name]
        stable(record, "/home/runner/work/mixer/mixer/verification/android-view-api-focused-actual-review/jdk-observation-preparation/" + name, 1048576)
        need({"bytes": record["bytes"], "sha256": record["sha256"]} == identity(files[prefix + name]), "source-reported member hashes")
    for key, name, path, cap in [("workflow_identity", workflow, "/home/runner/work/mixer/mixer/.github/workflows/android-view-api-jdk-data-observation.yml", 65536), ("source_manifest_identity", prefix + "source-manifest.json", "/home/runner/work/mixer/mixer/verification/android-view-api-focused-actual-review/jdk-observation-preparation/source-manifest.json", 65536), ("original_runtime_manifest_identity", prefix + "expected-runtime-members.json", "/home/runner/work/mixer/mixer/verification/android-view-api-boundary-linux-tool-profile/runtime-members.json", 65536)]:
        stable(source[key], path, cap)
        need({"bytes": source[key]["bytes"], "sha256": source[key]["sha256"]} == identity(files[name]), "source reported fixed-file identity")
    need(obs["status"] == "complete-expected74-data-observation" and obs["runtime_admitted"] is False and obs["prepared13_or152_pass"] is False and obs["diagnostic_only"] is True and obs["child_commands"] == [] and obs["owned_java_attempts"] == 0 and obs["expected_members_observed"] == 74 and obs["unexpected_membership_observed"] is False and obs["old_focused_allowance_reused"] is False, "complete74 data-only no-child boundary")
    need(obs["expected_manifest"] == {"members": 74, "expected_bytes": 198674633, "manifest_sha256": RUNTIME_SHA} and obs["limits"] == contract["limits"] and obs["limitations"] == contract["limitations"], "observer contract limits and expected manifest")
    need(len(obs["members"]) == 74 and [r["path"] for r in obs["members"]] == [r["path"] for r in rows], "exact74 ordered observations")
    differences, actual_total = [], 0
    by_path = {}
    for expected_row, observed_row in zip(rows, obs["members"]):
        need(observed_row["expected"] == expected_row, "observed expected row changed")
        actual = observed_row["observed"]
        stable(actual, "/usr/lib/jvm/temurin-17-jdk-amd64/" + expected_row["path"], 268435456)
        differs = actual["bytes"] != expected_row["bytes"] or actual["sha256"] != expected_row["sha256"]
        need(observed_row["outcome"] == ("differs-from-frozen-expected" if differs else "matches-frozen-expected-data-only"), "independent row classification disagreement")
        if differs:
            differences.append({"path": expected_row["path"], "expected": expected_row, "observed": {"bytes": actual["bytes"], "sha256": actual["sha256"]}})
        actual_total += actual["bytes"]
        by_path[expected_row["path"]] = actual
    need(obs["differing_members"] == [d["path"] for d in differences] and obs["refused_members"] == [] and obs["jdk_actual_bytes_read"] == actual_total <= 335544320, "complete mismatch/refusal/read accounting")
    need(boot["provider"] == obs["provider"], "provider report disagreement")
    provider = obs["provider"]
    need(provider["runner_label_from_reviewed_workflow"] == "ubuntu-24.04" and provider["observed_environment"]["RUNNER_OS"] == "Linux" and provider["observed_environment"]["ImageOS"] == "ubuntu24" and provider["same_image_as_old_run_assumed"] is False, "observed fixed provider context")
    need(boot["python"] == obs["python_bootstrap"] and boot["python"]["flags"] == ["-I", "-B", "-S"] and boot["python"]["alias"]["before"] == boot["python"]["alias"]["after"] and boot["python"]["alias"]["literal_target"] in (None, "python3.12", "/usr/bin/python3.12"), "source reported Python context")
    stable(boot["python"]["executable_file"], "/usr/bin/python3.12" if boot["python"]["alias"]["literal_target"] else "/usr/bin/python3", 33554432)
    for key, path, cap in [("status", "/var/lib/dpkg/status", 8388608), ("md5sums", "/var/lib/dpkg/info/temurin-17-jdk.md5sums", 1048576)]:
        entry = obs["package_metadata"][key]
        stable(entry["observation"], path, cap)
        need(entry["status"] == "exact-package-data-selected" and entry["path"] == path and entry["full_inventory_retained"] is False, "package metadata selected only")
    status = obs["package_metadata"]["status"]
    stanza = status["selected"]["exact_selected_stanza"]
    stanza_bytes = stanza.encode("utf-8")
    span = status["selected"]["selected_span"]
    need(span["bytes"] == len(stanza_bytes) <= 65536 and span["sha256"] == identity(stanza_bytes)["sha256"] and span["ends_with_lf"] == stanza_bytes.endswith(b"\n") and span["separator_after"] in ("\n\n", None) and 0 <= span["start_byte"] and span["start_byte"] + len(stanza_bytes) <= status["observation"]["bytes"], "selected exact raw-span self-consistency")
    fields = {}
    for line in stanza.splitlines():
        if line and line[0] not in " \t":
            key, value = line.split(": ", 1)
            if key in ("Package", "Version", "Architecture", "Status", "Source"):
                need(key not in fields, "selected stanza duplicate identity field")
                fields[key] = value
    need(fields == status["selected"]["fields"] and fields["Package"] == "temurin-17-jdk", "selected package fields from retained exact stanza")
    raw_exports = []
    os.mkdir(BASE + "/raw", 0o700)
    for member, basename, cap in [("lib/ct.sym", "ct.sym.raw-data.bin", 16777216), ("lib/jrt-fs.jar", "jrt-fs.jar.raw-data.bin", 1048576)]:
        data = files[out + basename]
        actual = by_path[member]
        retained = obs["raw_archive_data"][member]
        need(len(data) <= cap and identity(data) == {"bytes": actual["bytes"], "sha256": actual["sha256"]}, "raw data exact observed-file identity")
        need(retained == {"status": "retained-stable-observed-bytes", "path": basename, "source": member, "bytes": len(data), "sha256": identity(data)["sha256"], "mode": "0600-data-only", "archive_inspection_performed": False}, "retained raw report exact identity")
        actual_md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
        need(actual_md5 == actual["package_md5"], "independent actual raw MD5")
        md5record = obs["package_metadata"]["md5sums"]["selected"][member]
        target = "usr/lib/jvm/temurin-17-jdk-amd64/" + member
        need(md5record["path"] == target and md5record["exact_selected_line"].split() == [md5record["md5"], target], "selected package checksum raw line")
        comparison = obs["package_md5_comparisons"][member]
        need(comparison["actual_md5"] == actual_md5 and comparison["package_record_md5"] == md5record["md5"] and comparison["matches"] == (actual_md5 == md5record["md5"]), "package checksum association arithmetic")
        target_path = BASE + "/raw/" + basename
        output(target_path, data)
        raw_exports.append({"member": member, "path": target_path, **identity(data), "package_md5_matches": comparison["matches"], "inner_archive_inspected": False})
    os.mkdir(BASE + "/extracted", 0o700)
    for index, name in enumerate(sorted(files)):
        output(BASE + "/extracted/" + str(index).zfill(2) + "-" + name.rsplit("/", 1)[-1], files[name])
    need(read_file(BASE + "/artifact.zip", 8388608) == raw, "artifact unchanged after audit")
    report.update(status="reviewed-exact13-complete74-data-observation",uploaded_source_members=source_names,source_manifest_sha256=MANIFEST_SHA,workflow_sha256=WORKFLOW_SHA,expected_runtime_manifest_sha256=RUNTIME_SHA,root_selection=selection,nonce_reservation={"identity": identity(files[out + "nonce-reservation.json"]), "content": reservation},provider=provider,python_source_report=boot["python"],runtime_members={"expected": 74, "stable_source_reports": 74, "mismatches": differences, "mismatch_count": len(differences), "matches": 74 - len(differences), "refusals": 0, "expected_bytes": 198674633, "actual_reported_bytes_read": actual_total, "aggregate_cap": 335544320},package_metadata={"fields": fields, "selected_span": span, "status_file_report": status["observation"], "md5sums_file_report": obs["package_metadata"]["md5sums"]["observation"], "selected_checksum_records": obs["package_metadata"]["md5sums"]["selected"], "raw_span_source_origin_independently_verified": False, "full_package_inventory_retained": False},raw_exports=raw_exports,owned_java_attempts_source_report=0,owned_child_commands_source_report=[],runtime_admitted=False,inner_archive_comparison_performed=False,all_prior_holds_preserved=True)
    output(BASE + "/archive-inventory.json", (json.dumps(inventory, sort_keys=True, indent=2) + "\n").encode("utf-8"))

report = {"schema": 1, "status": "audit-started", "command": list(sys.orig_argv), "python": {"sys_executable": sys.executable, "sys_version": sys.version}, "source": identity(read_file(__file__, 1048576)), "connector_calls_total": 2, "consumer_attempts_total": 2, "first_consumer_body_bytes": 0, "recovery_consumer_body_bytes": 5904159, "automatic_retries": 0, "new_hosted_dispatches": 0, "subject_imports_or_execution": 0, "limitations": ["Stable hosted file records, package spans, Python identities and no-child claims are source-bound reports, not independent kernel trace or provider attestation.", "Only exact74 expected runtime paths were observed; unexpected runtime membership and cause/provenance of differences are not established.", "Original focused mismatch bytes remain unknown; a matching provider image label does not establish identical old bytes.", "Outer ZIP CRC/SHA and raw file identities are independently checked. No inner ct.sym/JAR inspection, runtime admission or release/GA promotion."]}
try:
    report["guard"] = install_guards()
    main(report)
except BaseException as error:
    report.update(status="refused-data-audit-retained", error_type=type(error).__name__, error=str(error)[:1000])
output(BASE + "/guarded-audit.json", (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8"))
print(json.dumps({key: report.get(key) for key in ("status", "error", "runtime_members", "raw_exports")}, sort_keys=True))
if report["status"] != "reviewed-exact13-complete74-data-observation":
    raise SystemExit(1)
