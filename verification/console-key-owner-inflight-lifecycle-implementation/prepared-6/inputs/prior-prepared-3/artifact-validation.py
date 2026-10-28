"""Exact recursive artifact types and separate clean-gate predicates."""


def validate(value, rule, label="artifact"):
    kind = rule["type"]
    if kind == "object":
        if type(value) is not dict or set(value) != set(rule["fields"]):
            raise ValueError("exact object membership differs: " + label)
        for key, child in rule["fields"].items():
            validate(value[key], child, label + ":" + key)
    elif kind == "array":
        if type(value) is not list or not rule.get("min", 0) <= len(value) <= rule["max"]:
            raise ValueError("array type/count differs: " + label)
        for index, child in enumerate(value):
            validate(child, rule["items"], label + ":" + str(index))
    elif kind == "boolean":
        if type(value) is not bool or ("value" in rule and value is not rule["value"]):
            raise ValueError("boolean differs: " + label)
    elif kind == "integer":
        if type(value) is not int or not rule.get("min", -(2**63)) <= value <= rule.get("max", 2**63 - 1):
            raise ValueError("integer type/range differs: " + label)
        if "value" in rule and value != rule["value"]:
            raise ValueError("integer value differs: " + label)
    elif kind == "string":
        if type(value) is not str or len(value.encode()) > rule.get("max", 65536):
            raise ValueError("string type/cap differs: " + label)
        if "enum" in rule and value not in rule["enum"]:
            raise ValueError("string enum differs: " + label)
    else:
        raise ValueError("unsupported schema type: " + kind)


def validate_artifacts(artifacts, packet):
    if type(artifacts) is not dict or set(artifacts) != set(packet["schemas"]):
        raise ValueError("exact terminal artifact membership differs")
    if type(packet["required_artifacts"]) is not int or len(artifacts) != packet["required_artifacts"]:
        raise ValueError("terminal artifact count differs")
    for path, schema in packet["schemas"].items():
        validate(artifacts[path], schema, path)


def validate_openssl(artifact, plan, owned_test_group):
    calls = artifact["invocations"]
    starts = artifact["starts"]
    if len(calls) != 7 or calls[0]["args"] != ["version"]:
        raise ValueError("exact version plus six fixture OpenSSL calls required")
    directories = []
    for offset in [1, 4]:
        first = calls[offset]["args"]
        directory = first[first.index("-keyout") + 1].removesuffix("/ca.key")
        if "/tmp/mixer-key-owner-tls-" not in directory or "/../" in directory:
            raise ValueError("OpenSSL key directory outside owned temporary fixture")
        expected = [
            ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", directory + "/ca.key", "-out", directory + "/ca.pem", "-days", "1", "-subj", "/CN=Mixer Fixture CA"],
            ["req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", directory + "/leaf.key", "-out", directory + "/leaf.csr", "-subj", "/CN=jwks.fixture.invalid"],
            ["x509", "-req", "-in", directory + "/leaf.csr", "-CA", directory + "/ca.pem", "-CAkey", directory + "/ca.key", "-CAcreateserial", "-out", directory + "/leaf.pem", "-days", "1", "-extfile", directory + "/leaf.ext"],
        ]
        if [item["args"] for item in calls[offset:offset + 3]] != expected:
            raise ValueError("fixture OpenSSL recipe differs")
        directories.append(directory)
    if len(set(directories)) != 2:
        raise ValueError("two distinct sequential fixture key directories required")
    for start, call in zip(starts, calls, strict=True):
        if start != {key: call[key] for key in start}:
            raise ValueError('OpenSSL launch/completion binding differs')
        if (call["executable"] != plan["openssl"] or call["process_group"] != owned_test_group or
                call["exit_code"] != 0 or call["output_cap_exceeded"] or
                call["finished_ns"] < call["started_ns"]):
            raise ValueError("OpenSSL identity/group/exit/output/timing differs")


def validate_clean_gates(artifacts):
    result = artifacts["test/exunit-result.json"]
    if result != {"total": 9, "failures": 0, "skipped": 0, "excluded": 0}:
        raise ValueError("nine clean methods required; retained adverse failure is not a pass")
    for case in ["KOL08-GRACEFUL", "KOL09-KILL"]:
        record = artifacts["test/" + case + "-observation.json"]
        if record["cleanup_errors"] or not all(value is True for key, value in record["cleanup"].items()
                                                 if key not in ["resume_result", "component_stop_result", "fixture_stop_result"]):
            raise ValueError("inflight cleanup failed: " + case)
        if record["cleanup"]["component_stop_result"] not in [":ok", ":already_stopped"] or record["cleanup"]["fixture_stop_result"] not in [":ok", ":already_stopped"]:
            raise ValueError("component/fixture stop failed: " + case)
        required = ["tls_preconditions", "raw_explicit_reply", "public_denial"]
        required += (["fresh_denial", "raw_port_closed_while_held", "parent_stop_pending", "old_resources_down_at_stop", "owner_alive_at_raw_reply", "table_alive_at_raw_reply", "pointer_absent_at_raw_reply"]
                     if case == "KOL08-GRACEFUL" else ["replacement_observed", "replacement_empty", "old_resources_down_before_replacement", "callback_clean", "old_permit_rejected", "stale_lease_rejected"])
        if not all(record["observations"][key] is True for key in required):
            raise ValueError("inflight gate failed: " + case)
