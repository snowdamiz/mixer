package protocol

// These closed v1 model fields are required even when their value is zero or
// false. Requiring the same model under direct json.Unmarshal prevents callers
// from accidentally bypassing DecodeJSON's contract preflight. Canonical CBOR
// serialization, signatures, valid vectors and version separation are unchanged.
const maxV1DocumentBytes = 1_048_576

func (m *Manifest) UnmarshalJSON(data []byte) error {
	if _, e := exactProtocolObject(data, maxV1DocumentBytes, "schema", "scope", "release_id", "source_commit", "provenance_id", "runtime", "protocol", "guest_abi", "ui_schema", "capability_hashes", "state_min", "state_max", "payload_sha256", "compressed_bytes", "expanded_bytes", "compression", "asset_hashes", "source_map_sha256", "limits", "key_id", "created_at_unix"); e != nil {
		return e
	}
	type plain Manifest
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*m = Manifest(decoded)
	return nil
}
func (a *Assignment) UnmarshalJSON(data []byte) error {
	if _, e := exactProtocolObject(data, maxV1DocumentBytes, "schema", "scope", "channel", "cohort", "rollout_basis_points", "sequence", "release_id", "artifact_sha256", "runtime", "key_id", "created_at_unix"); e != nil {
		return e
	}
	type plain Assignment
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*a = Assignment(decoded)
	return nil
}
func (s *Scope) UnmarshalJSON(data []byte) error {
	if _, e := exactProtocolObject(data, maxV1DocumentBytes, "organization", "project", "app", "environment", "platform"); e != nil {
		return e
	}
	type plain Scope
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*s = Scope(decoded)
	return nil
}
func (l *Limits) UnmarshalJSON(data []byte) error {
	if _, e := exactProtocolObject(data, maxV1DocumentBytes, "memory_bytes", "fuel", "startup_milliseconds"); e != nil {
		return e
	}
	type plain Limits
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*l = Limits(decoded)
	return nil
}
func (h *Host) UnmarshalJSON(data []byte) error {
	if _, e := exactProtocolObject(data, maxV1DocumentBytes, "scope", "runtime", "protocol", "guest_abi", "ui_schema", "capability_hashes", "state_version", "max_payload_bytes", "limits"); e != nil {
		return e
	}
	type plain Host
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*h = Host(decoded)
	return nil
}
func (r *Root) UnmarshalJSON(data []byte) error {
	if _, e := exactProtocolObject(data, maxV1DocumentBytes, "key_id", "public_key", "scope", "artifact", "assignment", "revoked", "not_before_unix", "not_after_unix"); e != nil {
		return e
	}
	type plain Root
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*r = Root(decoded)
	return nil
}
func (s *SignedManifest) UnmarshalJSON(data []byte) error {
	raw, e := exactProtocolObject(data, maxV1DocumentBytes, "manifest", "signature")
	if e != nil {
		return e
	}
	if e = signatureEncoding(raw["signature"]); e != nil {
		return e
	}
	type plain SignedManifest
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*s = SignedManifest(decoded)
	return nil
}
func (s *SignedAssignment) UnmarshalJSON(data []byte) error {
	raw, e := exactProtocolObject(data, maxV1DocumentBytes, "assignment", "signature")
	if e != nil {
		return e
	}
	if e = signatureEncoding(raw["signature"]); e != nil {
		return e
	}
	type plain SignedAssignment
	var decoded plain
	if e := DecodeJSON(data, &decoded); e != nil {
		return e
	}
	*s = SignedAssignment(decoded)
	return nil
}
