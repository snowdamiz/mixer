"""Independent finite data, not a loader, model replay, allocator or authority."""
import hashlib
import struct

LIMITS = [1947, 1_000_000, 65_536, 1_000_000, 10_000]
U64 = (1 << 64) - 1
MIN_I64, MAX_I64 = -(1 << 63), (1 << 63) - 1


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(raw, offset, value):
    struct.pack_into("<Q", raw, offset, value)


def encoded_list(entries):
    return struct.pack("<Q", len(entries)) + b"".join(
        struct.pack("<Q", len(value)) + value for value in entries)


def record(magic, sections, offsets):
    out = bytearray(512 + sum(map(len, sections)))
    out[:8] = magic
    for offset, value in [(8, 1), (16, 512), (24, len(out))]:
        put(out, offset, value)
    for index, part in enumerate(sections):
        put(out, offsets + index * 8, len(part))
    out[512:] = b"".join(sections)
    return out


def identity_words(dev, inode, extent, shift=0):
    return [dev, inode, extent, 0o100600, MIN_I64 + shift, -1, shift, MAX_I64 - shift]


def encode_identity(values):
    return struct.pack("<QQQQqqqq", *values)


def mutated(base, label, offset, raw, stage, diagnostic):
    result = bytearray(base)
    result[offset:offset + len(raw)] = raw
    return {"id": label, "offset": offset, "replace_hex": raw.hex(),
            "result_sha256": sha(result), "reject_at": stage, "diagnostic": diagnostic}


def make():
    paths = [b"source", b"build", b"session", b"rows-\xff", b"snapshot-\xfe"]
    path = bytearray(64 + sum(map(len, paths)))
    path[:8] = b"MIXPTH01"
    put(path, 8, 1)
    put(path, 16, len(path))
    for i, value in enumerate(paths):
        put(path, 24 + i * 8, len(value))
    path[64:] = b"".join(paths)
    path_cases = [mutated(path, "path-magic", 0, b"X", "path parser", "magic"),
                  mutated(path, "path-version", 8, struct.pack("<Q", 2), "path parser", "version"),
                  mutated(path, "path-total", 16, struct.pack("<Q", len(path) + 1), "path parser", "total")]
    cursor = 64
    for i, value in enumerate(paths):
        path_cases += [mutated(path, f"path-empty-{i}", 24 + i * 8, bytes(8), "path parser", "positive length"),
                       mutated(path, f"path-overflow-{i}", 24 + i * 8, struct.pack("<Q", U64), "path parser", "cap or checked end"),
                       mutated(path, f"path-nul-{i}", cursor, b"\0", "path parser", "NUL")]
        cursor += len(value)
    path_extra = bytes(path) + b"z"
    path_extra = bytearray(path_extra)
    put(path_extra, 16, len(path_extra))
    long_paths = [b"a" * 4097] + paths[1:]
    long_packet = bytearray(64 + sum(map(len, long_paths)))
    long_packet[:8] = b"MIXPTH01"
    put(long_packet, 8, 1)
    put(long_packet, 16, len(long_packet))
    for i, value in enumerate(long_paths):
        put(long_packet, 24 + i * 8, len(value))
    long_packet[64:] = b"".join(long_paths)

    source = bytes(1947)  # parser-only bytes; not a validator-valid proof source
    executable = b"preaccess parser-only executable\n"
    build_sections = [b"preaccess parser-only manifest; not authority\n",
                      encoded_list([b"rustc", b"--edition=2021"]),
                      encoded_list([b"A=1", b"B=2"]), b"preaccess version\n"]
    build = record(b"MIXLBD01", build_sections, 48)
    put(build, 32, 146)
    put(build, 40, 11)
    put(build, 80, len(executable))
    build[88:108] = b"aarch64-apple-darwin"  # target is 20 bytes
    for i, part in enumerate(build_sections):
        build[152 + i * 32:184 + i * 32] = hashlib.sha256(part).digest()
    build[280:312] = hashlib.sha256(b"preaccess compiler; not authority").digest()
    build[312:344] = hashlib.sha256(executable).digest()
    source_identity = identity_words(11, 101, len(source))
    session_sections = [encode_identity(source_identity), encoded_list([b"preaccess-component"]),
                        encoded_list([b"A=1", b"B=2"]), b"/preaccess"]
    session = record(b"MIXLSE01", session_sections, 40)
    put(session, 32, len(source))
    for i, value in enumerate(LIMITS):
        put(session, 72 + i * 8, value)
    nonce = bytes(range(32))
    session[112:144] = nonce
    session[144:176] = hashlib.sha256(source).digest()
    session[176:208] = hashlib.sha256(build).digest()
    session[208:240] = hashlib.sha256(executable).digest()
    for i, part in enumerate(session_sections):
        session[240 + i * 32:272 + i * 32] = hashlib.sha256(part).digest()

    build_cases = []
    for label, off, value, diagnostic in [
        ("version", 8, 2, "Header/Build/0"), ("header-size", 16, 511, "Header/Build/0"),
        ("total", 24, len(build) + 1, "Header/Build/0"),
        ("source-count", 32, 145, "BuildIdentity/Build/32"),
        ("host-count", 40, 12, "BuildIdentity/Build/32"),
        ("output-zero", 80, 0, "BuildIdentity/Build/32"),
        ("output-over-cap", 80, 67108865, "BuildIdentity/Build/32")]:
        build_cases.append(mutated(build, "build-" + label, off, struct.pack("<Q", value), "build parser", diagnostic))
    build_cases += [mutated(build, "build-target", 88, b"X", "build parser", "Reserved/Build/88"),
                    mutated(build, "build-target-padding", 108, b"x", "build parser", "Reserved/Build/88"),
                    mutated(build, "build-reserved", 344, b"x", "build parser", "Reserved/Build/88")]
    for i in range(4):
        build_cases.append(mutated(build, f"build-empty-section-{i}", 48 + i * 8, bytes(8), "build parser", "Extent/Build/current cursor"))
        build_cases.append(mutated(build, f"build-overflow-section-{i}", 48 + i * 8, struct.pack("<Q", U64), "build parser", "Extent/Build/current cursor"))

    session_cases = [mutated(session, "session-reserved", 368, b"x", "session parser", "Reserved/Session/368")]
    for off, label in [(8, "version"), (16, "header-size"), (24, "total")]:
        session_cases.append(mutated(session, "session-" + label, off, struct.pack("<Q", 7), "session parser", "Header/Session/0"))
    for i in range(4):
        session_cases.append(mutated(session, f"session-empty-section-{i}", 40 + i * 8, bytes(8), "session parser", "Extent/Session/current cursor"))
    # The old parser accepts these values. Owner admission MUST reject them.
    session_cases.append(mutated(session, "session-zero-source-extent", 32, bytes(8), "owner admission only", "positive source extent; old parser positive"))
    for i in range(5):
        session_cases.append(mutated(session, f"session-zero-limit-{i}", 72 + i * 8, bytes(8), "owner admission only", "positive exact selected limit; old parser positive"))
    session_cases.append(mutated(session, "session-nonregular-identity", 512 + 24, struct.pack("<Q", 0o040600), "owner admission only", "regular complete source identity; old parser positive"))

    identities = [source_identity, identity_words(11, 102, len(build), 1),
                  identity_words(11, 103, len(session), 2), identity_words(11, 104, len(executable), 3)]
    provenance = {"source": sha(source), "manifest": sha(build_sections[0]), "build": sha(build),
                  "session": sha(session), "executable": sha(executable), "nonce": nonce.hex(),
                  "validation_budget": LIMITS, "source_extent": len(source), "identities": identities}
    correlation = []
    for name in ["source", "manifest", "build", "session", "executable", "nonce"]:
        for byte in range(32):
            raw = bytearray.fromhex(provenance[name])
            raw[byte] ^= 1
            correlation.append({"id": f"correlation-{name}-byte-{byte:02}", "path": [name], "replacement": raw.hex()})
    for i, value in enumerate(LIMITS):
        correlation.append({"id": f"correlation-limit-{i}", "path": ["validation_budget", i], "replacement": value + 1})
    correlation.append({"id": "correlation-extent", "path": ["source_extent"], "replacement": len(source) + 1})
    for slot, fields in enumerate(identities):
        for i, value in enumerate(fields):
            correlation.append({"id": f"correlation-identity-{slot}-{i}", "path": ["identities", slot, i],
                                "replacement": value - 1 if value == MAX_I64 else value + 1})

    read = []
    for extent in [4095, 4096, 4097, 8192]:
        blocks = [(at, min(4096, extent - at)) for at in range(0, extent, 4096)]
        responses = []
        for _, size in blocks:
            responses += ["Interrupted"] * 31 + [size]
        responses += ["Interrupted"] * 31 + [0]
        read.append({"id": f"all-last-attempt-{extent}", "extent": extent, "responses": responses,
                     "expected_calls": 32 * (len(blocks) + 1), "expected_bytes": extent,
                     "outcome": "complete then final metadata gate"})
    read += [
        {"id": "no33rd-block", "extent": 1, "responses": ["Interrupted"] * 32 + [1, 0], "expected_calls": 32, "expected_bytes": 0, "outcome": "Attempts; queued success never called"},
        {"id": "no33rd-eof", "extent": 1, "responses": [1] + ["Interrupted"] * 32 + [0], "expected_calls": 33, "expected_bytes": 1, "outcome": "Attempts at EOF; queued success never called"},
        {"id": "partial-original-io", "extent": 4097, "responses": [2048, "OriginalIo"], "expected_calls": 2, "expected_bytes": 2048, "outcome": "original io retained with partial initialized buffer"},
        {"id": "short-after-prefix", "extent": 4096, "responses": [13, 0], "expected_calls": 2, "expected_bytes": 13, "outcome": "ShortInput offset13"},
        {"id": "overreported", "extent": 4096, "responses": [4097], "expected_calls": 1, "expected_bytes": 0, "outcome": "OverreportedRead offset0"},
        {"id": "extra-eof", "extent": 1, "responses": [1, 1], "expected_calls": 2, "expected_bytes": 2, "outcome": "ExtraInput at EOF"}
    ]
    return {
        "schema": 1, "status": "independent prospective Rust input data; no candidate or operational execution",
        "scope": "binary shape and exact typed values only; data does not authenticate source, compiler, custody or fixture",
        "binary": {
            "MIXPTH01": {"bytes_hex": bytes(path).hex(), "sha256": sha(path), "paths_hex": [p.hex() for p in paths],
                         "test_path_caps": [len(p) for p in paths], "mutations": path_cases,
                         "tail_with_corrected_total_hex": path_extra.hex(), "truncation_lengths": [0, 7, 63, 64, len(path) - 1],
                         "long_path_positive_hex": long_packet.hex(), "long_path_test_caps": [len(p) for p in long_paths]},
            "MIXLBD01": {"bytes_hex": bytes(build).hex(), "sha256": sha(build), "section_hex": [p.hex() for p in build_sections],
                         "mutations": build_cases, "target_bytes": 20, "compile_header_mapping": [0, 1, 2, 4, 3], "authority": False},
            "MIXLSE01": {"bytes_hex": bytes(session).hex(), "sha256": sha(session), "section_hex": [p.hex() for p in session_sections],
                         "mutations": session_cases, "all5_limits": LIMITS, "source_extent": len(source), "authority": False}
        },
        "signed_identity64": {"field_order": ["dev", "inode", "bytes", "mode", "mtime", "mtime_ns", "ctime", "ctime_ns"],
                              "types": ["u64"] * 4 + ["i64"] * 4, "values": source_identity, "bytes_hex": encode_identity(source_identity).hex()},
        "correlation_baseline": provenance, "correlation_mutations": correlation,
        "correlation_each_negative": "one consumed attempt; leaf0; same typed selected proof/error+3+Option resources+usage retained; no refund",
        "read_schedules": read,
        "rejected_json_bytes_hex": b'{"source_extent":1947,"validation_budget":[1947,1000000,65536,1000000,10000]}'.hex(),
        "positive_guard_boundary": "private test fixture only; real ValidatedSwiftReactor separately obtained from actual host validator; synthetic source above is parser-only and must not be passed off as a proof",
        "production_authority": False
    }
