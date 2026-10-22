package protocol

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"reflect"
	"strings"
	"unicode/utf8"
)

const ArtifactDomain = "mixer.artifact.v1\x00"
const AssignmentDomain = "mixer.assignment.v1\x00"
const MaxPayloadBytes uint64 = 16 * 1024 * 1024

type Scope struct {
	Organization string `json:"organization"`
	Project      string `json:"project"`
	App          string `json:"app"`
	Environment  string `json:"environment"`
	Platform     string `json:"platform"`
}

type Limits struct {
	MemoryBytes         uint64 `json:"memory_bytes"`
	Fuel                uint64 `json:"fuel"`
	StartupMilliseconds uint64 `json:"startup_milliseconds"`
}

type Manifest struct {
	Schema           uint64            `json:"schema"`
	Scope            Scope             `json:"scope"`
	ReleaseID        string            `json:"release_id"`
	SourceCommit     string            `json:"source_commit"`
	ProvenanceID     string            `json:"provenance_id"`
	Runtime          string            `json:"runtime"`
	Protocol         uint64            `json:"protocol"`
	GuestABI         uint64            `json:"guest_abi"`
	UISchema         uint64            `json:"ui_schema"`
	CapabilityHashes map[string]string `json:"capability_hashes"`
	StateMin         uint64            `json:"state_min"`
	StateMax         uint64            `json:"state_max"`
	PayloadSHA256    string            `json:"payload_sha256"`
	CompressedBytes  uint64            `json:"compressed_bytes"`
	ExpandedBytes    uint64            `json:"expanded_bytes"`
	Compression      string            `json:"compression"`
	AssetHashes      map[string]string `json:"asset_hashes"`
	SourceMapSHA256  string            `json:"source_map_sha256"`
	Limits           Limits            `json:"limits"`
	KeyID            string            `json:"key_id"`
	CreatedAtUnix    uint64            `json:"created_at_unix"`
}

type Assignment struct {
	Schema             uint64 `json:"schema"`
	Scope              Scope  `json:"scope"`
	Channel            string `json:"channel"`
	Cohort             string `json:"cohort"`
	RolloutBasisPoints uint64 `json:"rollout_basis_points"`
	Sequence           uint64 `json:"sequence"`
	ReleaseID          string `json:"release_id"`
	ArtifactSHA256     string `json:"artifact_sha256"`
	Runtime            string `json:"runtime"`
	KeyID              string `json:"key_id"`
	CreatedAtUnix      uint64 `json:"created_at_unix"`
}

type SignedManifest struct {
	Manifest  Manifest `json:"manifest"`
	Signature []byte   `json:"signature"`
}
type SignedAssignment struct {
	Assignment Assignment `json:"assignment"`
	Signature  []byte     `json:"signature"`
}

// Root is pinned/configured authority, never supplied by an untrusted package.
// V1 supports direct roots only. Delegation documents are not recognized.
type Root struct {
	KeyID         string `json:"key_id"`
	PublicKey     []byte `json:"public_key"`
	Scope         Scope  `json:"scope"`
	Artifact      bool   `json:"artifact"`
	Assignment    bool   `json:"assignment"`
	Revoked       bool   `json:"revoked"`
	NotBeforeUnix uint64 `json:"not_before_unix"`
	NotAfterUnix  uint64 `json:"not_after_unix"`
}

type Host struct {
	Scope            Scope             `json:"scope"`
	Runtime          string            `json:"runtime"`
	Protocol         uint64            `json:"protocol"`
	GuestABI         uint64            `json:"guest_abi"`
	UISchema         uint64            `json:"ui_schema"`
	CapabilityHashes map[string]string `json:"capability_hashes"`
	StateVersion     uint64            `json:"state_version"`
	MaxPayloadBytes  uint64            `json:"max_payload_bytes"`
	Limits           Limits            `json:"limits"`
}

func Hash(data []byte) string { h := sha256.Sum256(data); return hex.EncodeToString(h[:]) }
func ManifestDigest(m Manifest) (string, error) {
	b, e := CanonicalCBOR(m)
	if e != nil {
		return "", e
	}
	return Hash(b), nil
}
func ValidDigest(s string) bool {
	if len(s) != 64 {
		return false
	}
	b, e := hex.DecodeString(s)
	return e == nil && hex.EncodeToString(b) == s
}
func ValidID(s string) bool {
	if len(s) < 1 || len(s) > 128 {
		return false
	}
	for _, c := range s {
		if !(c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || c == '.' || c == '_' || c == '-') {
			return false
		}
	}
	return true
}
func (s Scope) Validate() error {
	for _, v := range []string{s.Organization, s.Project, s.App, s.Environment} {
		if !ValidID(v) {
			return fmt.Errorf("invalid scope identifier")
		}
	}
	if s.Platform != "ios" && s.Platform != "android" {
		return fmt.Errorf("unsupported platform")
	}
	return nil
}
func (m Manifest) Validate() error {
	if m.CapabilityHashes == nil || m.AssetHashes == nil {
		return fmt.Errorf("capability and asset maps must be explicit objects")
	}
	if e := m.Scope.Validate(); e != nil {
		return e
	}
	if m.Schema != 1 || m.Protocol != 1 || m.GuestABI != 1 || m.UISchema != 1 {
		return fmt.Errorf("unsupported schema, protocol, guest ABI or UI schema")
	}
	if !ValidID(m.ReleaseID) || !ValidID(m.ProvenanceID) || !ValidID(m.KeyID) || len(m.SourceCommit) != 40 && len(m.SourceCommit) != 64 || !ValidDigest(m.Runtime) {
		return fmt.Errorf("invalid manifest identity")
	}
	if _, e := hex.DecodeString(m.SourceCommit); e != nil || strings.ToLower(m.SourceCommit) != m.SourceCommit {
		return fmt.Errorf("invalid source commit")
	}
	if m.StateMin > m.StateMax || m.CreatedAtUnix == 0 {
		return fmt.Errorf("invalid state range or audit time")
	}
	if !ValidDigest(m.PayloadSHA256) || !ValidDigest(m.SourceMapSHA256) || m.Compression != "none" || m.CompressedBytes == 0 || m.CompressedBytes != m.ExpandedBytes || m.ExpandedBytes > MaxPayloadBytes {
		return fmt.Errorf("unsupported payload digest, size or compression")
	}
	// V1 carries exactly one guest payload. Separate assets are deliberately
	// unsupported until each resource has a verified bounded extraction format.
	if len(m.AssetHashes) != 0 {
		return fmt.Errorf("separate asset payloads unsupported in v1")
	}
	if len(m.CapabilityHashes) > 128 {
		return fmt.Errorf("capability limit exceeded")
	}
	for k, v := range m.CapabilityHashes {
		if !ValidID(k) || !ValidDigest(v) {
			return fmt.Errorf("invalid capability hash")
		}
	}
	if m.Limits.MemoryBytes == 0 || m.Limits.Fuel == 0 || m.Limits.StartupMilliseconds == 0 {
		return fmt.Errorf("zero resource limit")
	}
	return nil
}
func (a Assignment) Validate() error {
	if e := a.Scope.Validate(); e != nil {
		return e
	}
	if a.Schema != 1 || a.Sequence == 0 || a.CreatedAtUnix == 0 || a.Cohort != "sha256-v1" || a.RolloutBasisPoints > 10000 || !ValidID(a.Channel) || !ValidID(a.ReleaseID) || !ValidID(a.KeyID) || !ValidDigest(a.ArtifactSHA256) || !ValidDigest(a.Runtime) {
		return fmt.Errorf("invalid or unsupported assignment")
	}
	return nil
}
func Compatible(m Manifest, h Host) error {
	if e := m.Validate(); e != nil {
		return e
	}
	if m.Scope != h.Scope || m.Runtime != h.Runtime || m.Protocol != h.Protocol || m.GuestABI != h.GuestABI || m.UISchema != h.UISchema || !reflect.DeepEqual(nonNil(m.CapabilityHashes), nonNil(h.CapabilityHashes)) {
		return fmt.Errorf("host contract mismatch")
	}
	if h.StateVersion < m.StateMin || h.StateVersion > m.StateMax {
		return fmt.Errorf("state schema incompatible")
	}
	if m.ExpandedBytes > h.MaxPayloadBytes || m.Limits.MemoryBytes > h.Limits.MemoryBytes || m.Limits.Fuel > h.Limits.Fuel || m.Limits.StartupMilliseconds > h.Limits.StartupMilliseconds {
		return fmt.Errorf("host resource budget exceeded")
	}
	return nil
}
func nonNil(m map[string]string) map[string]string {
	if m == nil {
		return map[string]string{}
	}
	return m
}
func authorize(roots []Root, key string, scope Scope, artifact bool, now uint64) (ed25519.PublicKey, error) {
	for _, r := range roots {
		if r.KeyID != key {
			continue
		}
		if r.Scope != scope || r.Revoked || len(r.PublicKey) != ed25519.PublicKeySize || (artifact && !r.Artifact) || (!artifact && !r.Assignment) || now < r.NotBeforeUnix || (r.NotAfterUnix != 0 && now >= r.NotAfterUnix) {
			return nil, fmt.Errorf("signing authority denied")
		}
		return ed25519.PublicKey(r.PublicKey), nil
	}
	return nil, fmt.Errorf("unknown signing key")
}
func SignManifest(m Manifest, key ed25519.PrivateKey) (SignedManifest, error) {
	if e := m.Validate(); e != nil {
		return SignedManifest{}, e
	}
	if len(key) != ed25519.PrivateKeySize {
		return SignedManifest{}, fmt.Errorf("invalid private key")
	}
	b, e := CanonicalCBOR(m)
	if e != nil {
		return SignedManifest{}, e
	}
	return SignedManifest{m, ed25519.Sign(key, append([]byte(ArtifactDomain), b...))}, nil
}
func SignAssignment(a Assignment, key ed25519.PrivateKey) (SignedAssignment, error) {
	if e := a.Validate(); e != nil {
		return SignedAssignment{}, e
	}
	if len(key) != ed25519.PrivateKeySize {
		return SignedAssignment{}, fmt.Errorf("invalid private key")
	}
	b, e := CanonicalCBOR(a)
	if e != nil {
		return SignedAssignment{}, e
	}
	return SignedAssignment{a, ed25519.Sign(key, append([]byte(AssignmentDomain), b...))}, nil
}
func VerifyManifest(s SignedManifest, payload []byte, roots []Root, h Host, now uint64) error {
	if e := VerifyManifestHeader(s, roots, h, now); e != nil {
		return e
	}
	m := s.Manifest
	if uint64(len(payload)) != m.CompressedBytes || Hash(payload) != m.PayloadSHA256 {
		return fmt.Errorf("payload size or hash mismatch")
	}
	return nil
}
func VerifyManifestHeader(s SignedManifest, roots []Root, h Host, now uint64) error {
	if e := Compatible(s.Manifest, h); e != nil {
		return e
	}
	m := s.Manifest
	pub, e := authorize(roots, m.KeyID, m.Scope, true, now)
	if e != nil {
		return e
	}
	b, e := CanonicalCBOR(m)
	if e != nil {
		return e
	}
	if !ed25519.Verify(pub, append([]byte(ArtifactDomain), b...), s.Signature) {
		return fmt.Errorf("artifact signature invalid")
	}
	return nil
}
func VerifyAssignment(s SignedAssignment, m Manifest, roots []Root, h Host, channel, installation string, last uint64, now uint64) error {
	if e := VerifyAssignmentHeader(s, m, roots, h, channel, last, now); e != nil {
		return e
	}
	if !Eligible(s.Assignment, installation) {
		return fmt.Errorf("installation outside cohort")
	}
	return nil
}
func VerifyAssignmentHeader(s SignedAssignment, m Manifest, roots []Root, h Host, channel string, last uint64, now uint64) error {
	a := s.Assignment
	if e := a.Validate(); e != nil {
		return e
	}
	if e := Compatible(m, h); e != nil {
		return e
	}
	digest, e := ManifestDigest(m)
	if e != nil {
		return e
	}
	if a.Scope != m.Scope || a.Runtime != m.Runtime || a.ReleaseID != m.ReleaseID || a.ArtifactSHA256 != digest || a.Channel != channel {
		return fmt.Errorf("assignment binding mismatch")
	}
	if a.Sequence <= last {
		return fmt.Errorf("assignment replay")
	}
	pub, e := authorize(roots, a.KeyID, a.Scope, false, now)
	if e != nil {
		return e
	}
	b, e := CanonicalCBOR(a)
	if e != nil {
		return e
	}
	if !ed25519.Verify(pub, append([]byte(AssignmentDomain), b...), s.Signature) {
		return fmt.Errorf("assignment signature invalid")
	}
	return nil
}

// Cohort includes app/environment/channel and installation, excluding sequence
// and artifact so expanding a rollout preserves the prior installation set.
func Cohort(a Assignment, installation string) (uint64, error) {
	if !ValidID(installation) {
		return 0, fmt.Errorf("invalid installation identifier")
	}
	b, e := CanonicalCBOR(map[string]string{"organization": a.Scope.Organization, "project": a.Scope.Project, "app": a.Scope.App, "environment": a.Scope.Environment, "channel": a.Channel, "installation": installation})
	if e != nil {
		return 0, e
	}
	sum := sha256.Sum256(b)
	n := uint64(0)
	for _, v := range sum {
		n = (n*256 + uint64(v)) % 10000
	}
	return n, nil
}
func Eligible(a Assignment, installation string) bool {
	n, e := Cohort(a, installation)
	return e == nil && n < a.RolloutBasisPoints
}

// DecodeJSON rejects duplicate fields at every depth, unknown fields and trailing
// values. JSON is an inspection/transport form; only canonical CBOR is signed.
func DecodeJSON(data []byte, v any) error {
	if !utf8.Valid(data) {
		return fmt.Errorf("invalid JSON UTF-8")
	}
	d := json.NewDecoder(bytes.NewReader(data))
	if e := walkJSON(d, 0); e != nil {
		return e
	}
	if _, e := d.Token(); e != io.EOF {
		return fmt.Errorf("trailing JSON")
	}
	d = json.NewDecoder(bytes.NewReader(data))
	d.DisallowUnknownFields()
	if e := d.Decode(v); e != nil {
		return e
	}
	return nil
}
func walkJSON(d *json.Decoder, depth int) error {
	if depth > 32 {
		return fmt.Errorf("JSON nesting limit")
	}
	t, e := d.Token()
	if e != nil {
		return e
	}
	switch t {
	case nil:
		return fmt.Errorf("JSON null is not in the v1 data model")
	case json.Delim('{'):
		seen := map[string]bool{}
		for d.More() {
			k, e := d.Token()
			if e != nil {
				return e
			}
			s, ok := k.(string)
			if !ok || seen[s] {
				return fmt.Errorf("duplicate or invalid JSON key")
			}
			seen[s] = true
			if e := walkJSON(d, depth+1); e != nil {
				return e
			}
		}
		_, e = d.Token()
		return e
	case json.Delim('['):
		for d.More() {
			if e := walkJSON(d, depth+1); e != nil {
				return e
			}
		}
		_, e = d.Token()
		return e
	default:
		return nil
	}
}
