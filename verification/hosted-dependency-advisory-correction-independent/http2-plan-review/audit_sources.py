#!/usr/bin/env python3
"""Bounded file/hash and pure finite arithmetic review; no product/tool import."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DESIGN = REPO / "verification/hosted-dependency-advisory-correction/http2-qualification-plan"
COMMIT = "220b9dfd27f9a21305be2afc75cbe585ddc24e7a"


def digest(path):
    assert time.monotonic() - START < 55
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def finite_first_read(frame_sizes, outstanding_header=1):
    # Source-derived finite arithmetic only: held stream, sixteen outstanding
    # messages, rest buffered into one delivery after its mailbox drains.
    direct_count = 16 - outstanding_header
    messages = frame_sizes[:direct_count]
    if len(frame_sizes) > direct_count:
        messages += [sum(frame_sizes[direct_count:])]
    count = 0
    for index, size in enumerate(messages):
        count += size
        remote_closed = index == len(messages) - 1
        if count >= 32768:
            tag = "ok" if count == 32768 and remote_closed else "more"
            return {"bytes": count, "tag": tag}
    return {"bytes": count, "tag": "ok"}


def main():
    assert digest(DESIGN / "seal.sha256") == "73abbc2d2a9198c2c5df0c2824672bae5cf1f3d3bdd9d8457bf4580687b8f2bd"
    members = []
    for line in (DESIGN / "seal.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert digest(DESIGN / name) == expected
        members.append(name)
    assert len(members) == len(set(members)) == 5
    evidence = read(DESIGN / "source-evidence.json")
    preparation = read(DESIGN / "preparation-receipt.json")
    for name, pin in evidence["inputs"].items():
        path = REPO / name
        assert path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"], name
    matrix = read(DESIGN / "case-matrix.json")
    assert matrix["named_test_methods"] == len(matrix["cases"]) == 5
    assert matrix["finite_subcases"] == sum(len(case.get("variants", [None])) for case in matrix["cases"]) == 7
    assert len(matrix["proposed_new_files"]) == 2 and matrix["bounds"]["module_ms"] == 25000
    assert matrix["bounds"]["case_ms"] == 3000 and matrix["bounds"]["cleanup_ms"] == 500
    assert sum(case.get("input_body_bytes", 0) for case in matrix["cases"]) <= matrix["bounds"]["suite_body_bytes"]
    retrieval = read(OUT / "retrieval.json")
    tag = read(OUT / "upstream/tag-ref.json")
    assert tag["object"] == {"sha": COMMIT, "type": "commit", "url": f"https://api.github.com/repos/mtrudel/bandit/git/commits/{COMMIT}"}
    assert retrieval["repository"] == "mtrudel/bandit" and retrieval["tag"] == "1.14.0" and retrieval["commit"] == COMMIT
    assert len(retrieval["files"]) == 8
    license_raw = (OUT / "upstream/LICENSE").read_bytes()
    assert hashlib.sha1(b"blob " + str(len(license_raw)).encode() + b"\0" + license_raw).hexdigest() == retrieval["license"]["git_blob_sha"]
    sources = []
    for pin in retrieval["files"]:
        path = OUT / "upstream" / pin["path"]
        raw = path.read_bytes()
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == pin["git_blob_sha"]
        assert pin["url"] == f"https://github.com/mtrudel/bandit/blob/{COMMIT}/{pin['path']}"
        sources.append({**pin, "bytes": len(raw), "sha256": digest(path)})
    version = (OUT / "upstream/mix.exs").read_text()
    stream = (OUT / "upstream/lib/bandit/http2/stream.ex").read_text()
    connection = (OUT / "upstream/lib/bandit/http2/connection.ex").read_text()
    adapter = (OUT / "upstream/lib/bandit/adapter.ex").read_text()
    handler = (OUT / "upstream/lib/bandit/http2/handler.ex").read_text()
    assert 'version: "1.14.0"' in version
    assert 'else: now() + timeout' in stream and 'case do_recv(stream, remaining(deadline))' in stream
    assert ':timeout ->\n          {:more, Enum.reverse(acc), stream}' in stream
    assert '{:more, body, %{adapter | transport: transport, metrics: metrics}}' in adapter
    assert 'owner == self()' in adapter and 'Adapter functions must be called by stream owner' in adapter
    assert '@max_unbuffered_stream_messages 16' in connection and 'if delta != 0 do' in connection
    assert 'buffer = {<<data::binary, frame.data::binary>>' in connection
    assert 'frame.payload} |> send_frame' in connection
    assert 'Enum.reduce_while({:ok, state}' in handler
    ordinary = finite_first_read([16384, 16384, 7233])
    refined = finite_first_read([1] * 32 + [16384, 16384, 7201])
    assert ordinary == {"bytes":32768,"tag":"more"}
    assert refined == {"bytes":40001,"tag":"more"}
    assert finite_first_read([1] * 32 + [16384, 16384, 7201], 0) == refined
    assert 32 * 32768 == 1048576
    assert 31 * 32768 + 32769 == 1048577
    shutdown = REPO / "hosted/deps/thousand_island/lib/thousand_island/server_config.ex"
    assert 'shutdown_timeout: 15_000' in shutdown.read_text()
    result = {"schema":1,"status":"recommend-two-file-implementation-with-four-narrow-design-amendments",
        "created_at":datetime.now(timezone.utc).isoformat(),"python":sys.version,
        "command":"python3 -B verification/hosted-dependency-advisory-correction-independent/http2-plan-review/audit_sources.py",
        "script_sha256":digest(Path(__file__)),"design_seal_sha256":digest(DESIGN / "seal.sha256"),
        "design_members_verified":5,"local_input_pins_verified":len(evidence["inputs"]),
        "declared_preparation_input_count":preparation["input_count"],"official_sources":sources,
        "official_tag_commit":COMMIT,"target_public_timeout_shape_confirmed":"{:more, <<>>, conn}",
        "finite_source_model":{"not_runtime_or_protocol_proof":True,"ordinary_16KiB_frame_first_return":ordinary,"small_prefix_batched_first_return":refined},
        "source_ranges":{"adapter.ex":[[69,95],[348,352]],"stream.ex":[[315,383],[434,486],[522,527]],"connection.ex":[[22,38],[155,227],[334,376],[420,477],[547,590]],"handler.ex":[[20,56]],"flow_control.ex":[[13,41],[54,71]]},
        "upstream_MIT_license_preserved":{"sha256":digest(OUT / "upstream/LICENSE"),"git_blob_sha":retrieval["license"]["git_blob_sha"]},
        "local_extra_source":{"path":str(shutdown),"sha256":digest(shutdown),"observed_default_shutdown_ms":15000},
        "required_narrow_amendments":[
            {"id":"H2R01","priority":"P2","issue":"B1 must force the version-bound batching path","change":"Use 32 one-byte DATA frames then 39,969 bytes in 16KiB/16KiB/7201-byte frames; final END_STREAM and PING/ACK fence before release; retain measured >32768 witness"},
            {"id":"H2R02","priority":"P2","issue":"B2/B3 need deterministic final read/input boundaries","change":"B2: pace 32 successive 32768-byte tranches by observer completion, last payload END_STREAM. B3: use 31 completed tranches then a reserved-credit 32769-byte single write of two 16KiB DATA plus one-byte END_STREAM; preserve actual sent count and cap-branch limitation"},
            {"id":"H2R03","priority":"P2","issue":"500ms failure cleanup cannot rely on 15s listener default","change":"Select finite public ThousandIsland shutdown_timeout within cleanup reserve, explicitly dispose only the correlated held stream, stop only owned listener and require both DOWN witnesses within shared cleanup deadline"},
            {"id":"H2R04","priority":"P3","issue":"preparation declared 23 source inputs but pinned map contains 24","change":"Correct the count in a successor receipt; preserve sealed original"}],
        "recommend_narrow_implementation":True,"five_methods_seven_subcases_two_files_25s_unchanged":True,
        "product_source_fix_established":False,"wire_qualifications_passed":False,
        "network_retrieval":"one official GitHub tag ref, eight exact-commit source GETs and upstream MIT LICENSE GET via connector; evidence copies only",
        "Mix_compiler_listener_test_native_or_process_probe_invocations":0,
        "scope":"Public adapter behavior source binding and finite fixture design; no actual Hex-tar/tag equivalence claim, runtime proof, exhaustive advisory coverage, mailbox/memory bound, provider/deployment/native/device/GA pass.",
        "elapsed_seconds":round(time.monotonic()-START,6)}
    for name, ranges in result["source_ranges"].items():
        count = len(next((OUT / "upstream").rglob(name)).read_text().splitlines())
        assert all(1 <= first <= last <= count for first, last in ranges)
    (OUT / "audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({key:value for key,value in result.items() if key != "official_sources"},indent=2))


if __name__ == "__main__":
    main()
