package release

import (
	"bytes"
	"net/http"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

func TestV3HealthHaltAuthorizationAndAudit(t *testing.T) {
	f := testutil.New(t)
	cfg := v3Config(t, f)
	s, err := New(cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	checkV3HealthHalt(t, s, f.Protocol3(), v3Publisher, "TEST ONLY editor", "TEST ONLY reader")
}

func checkV3HealthHalt(t *testing.T, s http.Handler, f testutil.Fixture, publisher, editor, reader string) {
	t.Helper()
	artifact, digest := v3Upload(t, s, f, "halt-target", publisher)
	m := artifact.SignedManifest.Manifest
	v2Status(t, v3Publish(s, "publish", "halt-target-publish", publisher, f.AssignmentV3(t, m, 1, 10000)), 200)
	halt := f.AssignmentV3(t, m, 2, 0)
	badSignature := f.AssignmentV3(t, m, 2, 0)
	badSignature.Signature[0] ^= 1
	path := v3Base + "/channels/beta/halt"
	health := RolloutHealth{Sequence: 1, Activated: 1, Pending: 2, AdverseSignals: 1}
	request := func(key, token string, signed protocol.SignedAssignmentV3, health any) *bytes.Buffer {
		t.Helper()
		result := v2Request(s, "POST", path, key, token, map[string]any{
			"signed_assignment": signed, "health": health,
		})
		v2Status(t, result, 200)
		return result.Body
	}
	for _, test := range []struct {
		name, token string
		assignment  protocol.SignedAssignmentV3
		sample      any
		status      int
	}{
		{"anonymous", "", halt, health, 401},
		{"editor", editor, halt, health, 403},
		{"missing-counts", publisher, halt, map[string]uint64{"sequence": 1, "adverse_signals": 1}, 400},
		{"null-counts", publisher, halt, map[string]any{"sequence": 1, "adverse_signals": 1, "activated": nil, "pending": 2}, 400},
		{"no-adverse-signal", publisher, halt, RolloutHealth{Sequence: 1, Pending: 3}, 422},
		{"wrong-sequence", publisher, halt, RolloutHealth{Sequence: 2, AdverseSignals: 1}, 409},
		{"nonzero", publisher, f.AssignmentV3(t, m, 2, 1), health, 422},
		{"bad-signature", publisher, badSignature, health, 409},
	} {
		t.Run(test.name, func(t *testing.T) {
			body := map[string]any{"signed_assignment": test.assignment, "health": test.sample}
			v2Status(t, v2Request(s, "POST", path, "test-"+test.name, test.token, body), test.status)
		})
	}
	v2Status(t, v2Request(s, "GET", v2OfferPath(f, 3), "", "", nil), 200)

	result := request("halt", publisher, halt, health)
	if retry := request("halt", publisher, halt, health); !bytes.Equal(retry.Bytes(), result.Bytes()) {
		t.Fatal("halt replay changed response")
	}
	v2Status(t, v2Request(s, "GET", v2OfferPath(f, 3), "", "", nil), 204)
	audit := v2Request(s, "GET", v3Base+"/audit", "", reader, nil)
	v2Status(t, audit, 200)
	var history struct {
		Events []Event `json:"events"`
		Next   uint64  `json:"next"`
	}
	if err := protocol.DecodeJSON(audit.Body.Bytes(), &history); err != nil {
		t.Fatal(err)
	}
	want := RolloutHalt{Scope: m.Scope, Runtime: m.Runtime, Channel: "beta", ArtifactSHA256: digest, HaltSequence: 2, Health: health}
	if len(history.Events) != 4 || history.Events[3].RolloutHalt == nil || *history.Events[3].RolloutHalt != want {
		t.Fatalf("incorrect or duplicated halt audit: %s", audit.Body)
	}
	v2Status(t, v3Publish(s, "promote", "stale-promotion", publisher, f.AssignmentV3(t, m, 2, 10000)), 409)
	v2Status(t, v3Publish(s, "promote", "resume", publisher, f.AssignmentV3(t, m, 3, 10000)), 200)
	v2Status(t, v2Request(s, "GET", v2OfferPath(f, 3), "", "", nil), 200)
}
