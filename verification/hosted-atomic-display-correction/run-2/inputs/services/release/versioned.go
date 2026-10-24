package release

import (
	"encoding/json"
	"fmt"
	"reflect"

	"mixer/services/protocol"
)

// Artifact remains the unchanged v1 public wire type. V2 has a separate typed
// envelope; a route never guesses a version after failed verification.
type ArtifactV2 struct {
	SignedManifest protocol.SignedManifestV2 `json:"signed_manifest"`
	Payload        []byte                    `json:"payload"`
}

type ArtifactV3 struct {
	SignedManifest protocol.SignedManifestV3 `json:"signed_manifest"`
	Payload        []byte                    `json:"payload"`
}

// All v3 artifact envelopes are closed, including persisted and HTTP values.
func (a *ArtifactV3) UnmarshalJSON(data []byte) error {
	if len(data) > maxV3ArtifactBody {
		return fmt.Errorf("v3 artifact envelope exceeds byte limit")
	}
	fields, e := closedStorageObject(data, "signed_manifest", "payload")
	if e != nil {
		return e
	}
	signed, e := protocol.DecodeSignedManifestV3(fields["signed_manifest"])
	if e != nil {
		return e
	}
	var payload []byte
	if e = protocol.DecodeJSON(fields["payload"], &payload); e != nil {
		return e
	}
	*a = ArtifactV3{signed, payload}
	return nil
}

func (r Record) version() uint64 {
	if r.Version3 != nil {
		if r.Version2 != nil || !reflect.ValueOf(r.Artifact).IsZero() || r.Version3.SignedManifest.Manifest.Schema != 3 || r.Version3.SignedManifest.Manifest.Protocol != 3 {
			return 0
		}
		return 3
	}
	if r.Version2 != nil {
		if !reflect.ValueOf(r.Artifact).IsZero() {
			return 0
		}
		return 2
	}
	if r.Artifact.SignedManifest.Manifest.Schema == 1 {
		return 1
	}
	return 0
}
func (c Channel) version() uint64 {
	if c.Version3 != nil {
		if c.Version2 != nil || !reflect.ValueOf(c.SignedAssignment).IsZero() || c.Version3.Assignment.Schema != 3 {
			return 0
		}
		return 3
	}
	if c.Version2 != nil {
		if !reflect.ValueOf(c.SignedAssignment).IsZero() {
			return 0
		}
		return 2
	}
	if c.SignedAssignment.Assignment.Schema == 1 {
		return 1
	}
	return 0
}

// Stored v1 JSON is byte-compatible with schema1. V2/V3 records carry an explicit
// closed discriminator; an absent, mixed or unknown variant is never defaulted.
func (r Record) MarshalJSON() ([]byte, error) {
	switch r.version() {
	case 1:
		return json.Marshal(struct {
			Artifact  Artifact `json:"artifact"`
			Validated bool     `json:"validated"`
			Published bool     `json:"published"`
		}{r.Artifact, r.Validated, r.Published})
	case 3:
		return json.Marshal(struct {
			Protocol  uint64      `json:"protocol"`
			Artifact  *ArtifactV3 `json:"artifact_v3"`
			Validated bool        `json:"validated"`
			Published bool        `json:"published"`
		}{3, r.Version3, r.Validated, r.Published})
	case 2:
		return json.Marshal(struct {
			Protocol  uint64      `json:"protocol"`
			Artifact  *ArtifactV2 `json:"artifact_v2"`
			Validated bool        `json:"validated"`
			Published bool        `json:"published"`
		}{2, r.Version2, r.Validated, r.Published})
	default:
		return nil, fmt.Errorf("missing or mixed artifact storage variant")
	}
}
func closedStorageObject(data []byte, names ...string) (map[string]json.RawMessage, error) {
	var fields map[string]json.RawMessage
	if e := protocol.DecodeJSON(data, &fields); e != nil {
		return nil, e
	}
	if len(fields) != len(names) {
		return nil, fmt.Errorf("missing or unknown storage fields")
	}
	for _, name := range names {
		if _, ok := fields[name]; !ok {
			return nil, fmt.Errorf("missing storage field")
		}
	}
	return fields, nil
}
func (r *Record) UnmarshalJSON(data []byte) error {
	var fields map[string]json.RawMessage
	if e := protocol.DecodeJSON(data, &fields); e != nil {
		return e
	}
	var result Record
	if _, tagged := fields["protocol"]; tagged {
		var version uint64
		if e := protocol.DecodeJSON(fields["protocol"], &version); e != nil {
			return e
		}
		if version == 3 {
			if _, e := closedStorageObject(data, "protocol", "artifact_v3", "validated", "published"); e != nil {
				return e
			}
			var decoded struct {
				Protocol  uint64     `json:"protocol"`
				Artifact  ArtifactV3 `json:"artifact_v3"`
				Validated bool       `json:"validated"`
				Published bool       `json:"published"`
			}
			if e := protocol.DecodeJSON(data, &decoded); e != nil {
				return e
			}
			if decoded.Artifact.SignedManifest.Manifest.Schema != 3 || decoded.Artifact.SignedManifest.Manifest.Protocol != 3 {
				return fmt.Errorf("mismatched stored v3 artifact protocol")
			}
			*r = Record{Version3: &decoded.Artifact, Validated: decoded.Validated, Published: decoded.Published}
			return nil
		}
		if _, e := closedStorageObject(data, "protocol", "artifact_v2", "validated", "published"); e != nil {
			return e
		}
		var decoded struct {
			Protocol  uint64     `json:"protocol"`
			Artifact  ArtifactV2 `json:"artifact_v2"`
			Validated bool       `json:"validated"`
			Published bool       `json:"published"`
		}
		if e := protocol.DecodeJSON(data, &decoded); e != nil {
			return e
		}
		if decoded.Protocol != 2 || decoded.Artifact.SignedManifest.Manifest.Schema != 2 || decoded.Artifact.SignedManifest.Manifest.Protocol != 2 {
			return fmt.Errorf("unknown or mismatched stored artifact protocol")
		}
		result = Record{Version2: &decoded.Artifact, Validated: decoded.Validated, Published: decoded.Published}
	} else {
		if _, e := closedStorageObject(data, "artifact", "validated", "published"); e != nil {
			return e
		}
		var decoded struct {
			Artifact  Artifact `json:"artifact"`
			Validated bool     `json:"validated"`
			Published bool     `json:"published"`
		}
		if e := protocol.DecodeJSON(data, &decoded); e != nil {
			return e
		}
		if decoded.Artifact.SignedManifest.Manifest.Schema != 1 || decoded.Artifact.SignedManifest.Manifest.Protocol != 1 {
			return fmt.Errorf("mismatched legacy artifact protocol")
		}
		result = Record{Artifact: decoded.Artifact, Validated: decoded.Validated, Published: decoded.Published}
	}
	*r = result
	return nil
}
func (c Channel) MarshalJSON() ([]byte, error) {
	switch c.version() {
	case 1:
		return json.Marshal(struct {
			SignedAssignment protocol.SignedAssignment `json:"signed_assignment"`
		}{c.SignedAssignment})
	case 3:
		return json.Marshal(struct {
			Protocol uint64                       `json:"protocol"`
			Signed   *protocol.SignedAssignmentV3 `json:"signed_assignment_v3"`
		}{3, c.Version3})
	case 2:
		return json.Marshal(struct {
			Protocol uint64                       `json:"protocol"`
			Signed   *protocol.SignedAssignmentV2 `json:"signed_assignment_v2"`
		}{2, c.Version2})
	default:
		return nil, fmt.Errorf("missing or mixed assignment storage variant")
	}
}
func (c *Channel) UnmarshalJSON(data []byte) error {
	var fields map[string]json.RawMessage
	if e := protocol.DecodeJSON(data, &fields); e != nil {
		return e
	}
	var result Channel
	if _, tagged := fields["protocol"]; tagged {
		var version uint64
		if e := protocol.DecodeJSON(fields["protocol"], &version); e != nil {
			return e
		}
		if version == 3 {
			if _, e := closedStorageObject(data, "protocol", "signed_assignment_v3"); e != nil {
				return e
			}
			signed, e := protocol.DecodeSignedAssignmentV3(fields["signed_assignment_v3"])
			if e != nil {
				return e
			}
			if signed.Assignment.Schema != 3 {
				return fmt.Errorf("mismatched stored v3 assignment protocol")
			}
			*c = Channel{Version3: &signed}
			return nil
		}
		if _, e := closedStorageObject(data, "protocol", "signed_assignment_v2"); e != nil {
			return e
		}
		var decoded struct {
			Protocol uint64                      `json:"protocol"`
			Signed   protocol.SignedAssignmentV2 `json:"signed_assignment_v2"`
		}
		if e := protocol.DecodeJSON(data, &decoded); e != nil {
			return e
		}
		if decoded.Protocol != 2 || decoded.Signed.Assignment.Schema != 2 {
			return fmt.Errorf("unknown or mismatched stored assignment protocol")
		}
		result.Version2 = &decoded.Signed
	} else {
		if _, e := closedStorageObject(data, "signed_assignment"); e != nil {
			return e
		}
		if e := protocol.DecodeJSON(fields["signed_assignment"], &result.SignedAssignment); e != nil {
			return e
		}
		if result.SignedAssignment.Assignment.Schema != 1 {
			return fmt.Errorf("mismatched legacy assignment protocol")
		}
	}
	*c = result
	return nil
}

func (r Record) scope() protocol.Scope {
	if r.version() == 3 {
		return r.Version3.SignedManifest.Manifest.Scope
	}
	if r.version() == 2 {
		return r.Version2.SignedManifest.Manifest.Scope
	}
	return r.Artifact.SignedManifest.Manifest.Scope
}
func (r Record) runtime() string {
	if r.version() == 3 {
		return r.Version3.SignedManifest.Manifest.Runtime
	}
	if r.version() == 2 {
		return r.Version2.SignedManifest.Manifest.Runtime
	}
	return r.Artifact.SignedManifest.Manifest.Runtime
}
func (r Record) releaseID() string {
	if r.version() == 3 {
		return r.Version3.SignedManifest.Manifest.ReleaseID
	}
	if r.version() == 2 {
		return r.Version2.SignedManifest.Manifest.ReleaseID
	}
	return r.Artifact.SignedManifest.Manifest.ReleaseID
}
func checkChannelArtifact(r Record, c Channel) error {
	a := c.assignment()
	if !r.Validated || r.version() != c.version() || r.scope() != a.Scope || r.runtime() != a.Runtime || r.releaseID() != a.ReleaseID {
		return apiError{422, "assignment_invalid", "stored assignment must bind a validated artifact of the same protocol and runtime"}
	}
	return nil
}
func (r Record) payload() []byte {
	if r.version() == 3 {
		return r.Version3.Payload
	}
	if r.version() == 2 {
		return r.Version2.Payload
	}
	return r.Artifact.Payload
}
func (r Record) digest() (string, error) {
	if r.version() == 3 {
		return protocol.ManifestDigestV3(r.Version3.SignedManifest.Manifest)
	}
	if r.version() == 2 {
		return protocol.ManifestDigestV2(r.Version2.SignedManifest.Manifest)
	}
	return protocol.ManifestDigest(r.Artifact.SignedManifest.Manifest)
}
func (r Record) wire() any {
	if r.version() == 3 {
		return *r.Version3
	}
	if r.version() == 2 {
		return *r.Version2
	}
	return r.Artifact
}
func (r Record) signedManifest() any {
	if r.version() == 3 {
		return r.Version3.SignedManifest
	}
	if r.version() == 2 {
		return r.Version2.SignedManifest
	}
	return r.Artifact.SignedManifest
}
func (r Record) validate() error {
	switch r.version() {
	case 1:
		m := r.Artifact.SignedManifest.Manifest
		if m.Validate() != nil || uint64(len(r.payload())) != m.ExpandedBytes || protocol.Hash(r.payload()) != m.PayloadSHA256 {
			return fmt.Errorf("invalid v1 stored artifact")
		}
	case 3:
		m := r.Version3.SignedManifest.Manifest
		if m.Validate() != nil || uint64(len(r.payload())) != m.ExpandedBytes || protocol.Hash(r.payload()) != m.PayloadSHA256 {
			return fmt.Errorf("invalid v3 stored artifact")
		}
	case 2:
		m := r.Version2.SignedManifest.Manifest
		if m.Validate() != nil || uint64(len(r.payload())) != m.ExpandedBytes || protocol.Hash(r.payload()) != m.PayloadSHA256 {
			return fmt.Errorf("invalid v2 stored artifact")
		}
	default:
		return fmt.Errorf("missing or mixed stored artifact variant")
	}
	return nil
}
func (r Record) verify(roots []protocol.Root, host protocol.Host, now uint64) error {
	if r.version() == 3 {
		return protocol.VerifyManifestV3(r.Version3.SignedManifest, r.Version3.Payload, roots, host, now)
	}
	if r.version() == 2 {
		return protocol.VerifyManifestV2(r.Version2.SignedManifest, r.Version2.Payload, roots, host, now)
	}
	if r.version() != 1 {
		return fmt.Errorf("invalid stored artifact protocol")
	}
	return protocol.VerifyManifest(r.Artifact.SignedManifest, r.Artifact.Payload, roots, host, now)
}
func (c Channel) assignment() protocol.Assignment {
	if c.version() == 3 {
		return protocol.Assignment(c.Version3.Assignment)
	}
	if c.version() == 2 {
		return protocol.Assignment(c.Version2.Assignment)
	}
	return c.SignedAssignment.Assignment
}
func (c Channel) wire() any {
	if c.version() == 3 {
		return *c.Version3
	}
	if c.version() == 2 {
		return *c.Version2
	}
	return c.SignedAssignment
}
func (c Channel) validate() error {
	if c.version() == 3 {
		return c.Version3.Assignment.Validate()
	}
	if c.version() == 2 {
		return c.Version2.Assignment.Validate()
	}
	if c.version() != 1 {
		return fmt.Errorf("invalid stored assignment protocol")
	}
	return c.SignedAssignment.Assignment.Validate()
}
func (c Channel) verify(r Record, roots []protocol.Root, host protocol.Host, channel string, last, now uint64) error {
	if c.version() != r.version() || c.version() == 0 {
		return fmt.Errorf("artifact and assignment protocol differ")
	}
	if c.version() == 3 {
		return protocol.VerifyAssignmentHeaderV3(*c.Version3, r.Version3.SignedManifest, roots, host, channel, last, now)
	}
	if c.version() == 2 {
		return protocol.VerifyAssignmentHeaderV2(*c.Version2, r.Version2.SignedManifest, roots, host, channel, last, now)
	}
	return protocol.VerifyAssignmentHeader(c.SignedAssignment, r.Artifact.SignedManifest.Manifest, roots, host, channel, last, now)
}

// PostgreSQL keeps the signed bytes unchanged. Dispatch only on an exact uint64
// schema field, then decode the complete closed typed value before using it.
func storedSignedVersion(data []byte, field string) (uint64, error) {
	raw, e := closedStorageObject(data, field, "signature")
	if e != nil {
		return 0, e
	}
	var value map[string]json.RawMessage
	if e = protocol.DecodeJSON(raw[field], &value); e != nil {
		return 0, e
	}
	var schema uint64
	if e = protocol.DecodeJSON(value["schema"], &schema); e != nil || schema != 1 && schema != 2 && schema != 3 {
		return 0, fmt.Errorf("unknown stored signed version")
	}
	return schema, nil
}
func decodeStoredArtifact(data, payload []byte) (Record, error) {
	version, e := storedSignedVersion(data, "manifest")
	if e != nil {
		return Record{}, e
	}
	if version == 3 {
		signed, e := protocol.DecodeSignedManifestV3(data)
		return Record{Version3: &ArtifactV3{signed, payload}}, e
	}
	if version == 2 {
		signed, e := protocol.DecodeSignedManifestV2(data)
		return Record{Version2: &ArtifactV2{signed, payload}}, e
	}
	var signed protocol.SignedManifest
	e = protocol.DecodeJSON(data, &signed)
	return Record{Artifact: Artifact{signed, payload}}, e
}
func decodeStoredChannel(data []byte) (Channel, error) {
	version, e := storedSignedVersion(data, "assignment")
	if e != nil {
		return Channel{}, e
	}
	if version == 3 {
		signed, e := protocol.DecodeSignedAssignmentV3(data)
		return Channel{Version3: &signed}, e
	}
	if version == 2 {
		signed, e := protocol.DecodeSignedAssignmentV2(data)
		return Channel{Version2: &signed}, e
	}
	var signed protocol.SignedAssignment
	e = protocol.DecodeJSON(data, &signed)
	return Channel{SignedAssignment: signed}, e
}
