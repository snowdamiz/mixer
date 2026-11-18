package release

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"mixer/services/protocol"
)

// The Event shape and field order from the parent of d58e41289f.
type parentAuditEvent struct {
	ID            uint64       `json:"id"`
	Organization  string       `json:"organization"`
	Project       string       `json:"project"`
	Actor         string       `json:"actor"`
	Action        string       `json:"action"`
	Reason        string       `json:"reason"`
	Previous      string       `json:"previous"`
	Current       string       `json:"current"`
	SourceIP      string       `json:"source_ip"`
	RequestID     string       `json:"request_id"`
	CreatedAtUnix uint64       `json:"created_at_unix"`
	PreviousHash  string       `json:"previous_hash"`
	Hash          string       `json:"hash"`
	RolloutHalt   *RolloutHalt `json:"rollout_halt,omitempty"`
}

func auditBody(t *testing.T, s http.Handler, base, reader string, after uint64, limit int) []byte {
	t.Helper()
	result := v2Request(s, "GET", fmt.Sprintf("%s/audit?after=%d&limit=%d", base, after, limit), "", reader, nil)
	if result.Code != 200 {
		t.Fatalf("%s audit after %d limit %d: HTTP %d: %s", base, after, limit, result.Code, result.Body)
	}
	return result.Body.Bytes()
}

func auditJSON(t *testing.T, value any) []byte {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

// Verify each wire chain independently, then compare every non-hash value and
// require byte-identical legacy events until the first incompatible event.
func checkAuditViews(t *testing.T, s http.Handler, reader string, limit int) []Event {
	t.Helper()
	var all []Event
	var after uint64
	var legacyHash, canonicalHash, stateHash string
	diverged := false
	for {
		var legacy struct {
			Events []parentAuditEvent `json:"events"`
			Next   uint64             `json:"next"`
		}
		var canonical struct {
			Events []Event `json:"events"`
			Next   uint64  `json:"next"`
		}
		body := auditBody(t, s, v1Base, reader, after, limit)
		if !bytes.Equal(body, auditBody(t, s, v2Base, reader, after, limit)) {
			t.Fatalf("v1/v2 page mismatch after %d", after)
		}
		if err := protocol.DecodeJSON(body, &legacy); err != nil {
			t.Fatalf("parent strict decoder after %d: %v", after, err)
		}
		if err := protocol.DecodeJSON(auditBody(t, s, v3Base, reader, after, limit), &canonical); err != nil {
			t.Fatal(err)
		}
		if len(legacy.Events) != len(canonical.Events) || len(legacy.Events) > limit || legacy.Next != canonical.Next {
			t.Fatalf("page boundaries changed after %d", after)
		}
		for i, ev := range canonical.Events {
			old := legacy.Events[i]
			if ev.ID != after+1 || old.ID != ev.ID || old.PreviousHash != legacyHash ||
				ev.PreviousHash != canonicalHash || after > 0 && ev.Previous != stateHash {
				t.Fatalf("broken chain link at event %d", ev.ID)
			}
			legacyHash, canonicalHash, stateHash = old.Hash, ev.Hash, ev.Current
			old.Hash, ev.Hash = "", ""
			if protocol.Hash(auditJSON(t, old)) != legacyHash || protocol.Hash(auditJSON(t, ev)) != canonicalHash {
				t.Fatalf("wire event hash mismatch at %d", ev.ID)
			}
			diverged = diverged || ev.ChannelChange != nil
			if !diverged && legacyHash != canonicalHash {
				t.Fatalf("compatible prefix changed at %d", ev.ID)
			}
			old.PreviousHash, ev.PreviousHash, ev.ChannelChange = "", "", nil
			if !bytes.Equal(auditJSON(t, old), auditJSON(t, ev)) {
				t.Fatalf("legacy event values changed at %d", ev.ID)
			}
			after = ev.ID
			all = append(all, canonical.Events[i])
		}
		if legacy.Next != after {
			t.Fatalf("cursor %d did not follow last event %d", legacy.Next, after)
		}
		if len(legacy.Events) == 0 {
			break
		}
	}
	return all
}

func requireAuditHeads(t *testing.T, events []Event, runtime string, heads ...ChannelHead) {
	t.Helper()
	var changes []*ChannelChange
	for _, event := range events {
		if c := event.ChannelChange; c != nil && c.Runtime == runtime {
			changes = append(changes, c)
		}
	}
	if len(changes) != len(heads) {
		t.Fatalf("runtime %s has %d channel changes, want %d", runtime, len(changes), len(heads))
	}
	for i, change := range changes {
		var previous *ChannelHead
		if i > 0 {
			previous = &heads[i-1]
		}
		if !reflect.DeepEqual(change.Previous, previous) || change.Current != heads[i] {
			t.Fatalf("channel change %d has previous %+v and current %+v", i, change.Previous, change.Current)
		}
	}
}

// The contenders share a sequence and differ in the signed rollout. The
// winning response identifies which exact head the next event must inherit.
func raceAuditPromotion(t *testing.T, a, b http.Handler, publisher string, left, right protocol.SignedAssignmentV3) ChannelHead {
	t.Helper()
	type outcome struct {
		response *httptest.ResponseRecorder
		head     ChannelHead
	}
	results := make(chan outcome, 2)
	race := func(s http.Handler, key string, signed protocol.SignedAssignmentV3) {
		results <- outcome{v3Publish(s, "promote", key, publisher, signed), channelHead(protocol.Assignment(signed.Assignment))}
	}
	go race(a, "promote-audit-left", left)
	go race(b, "promote-audit-right", right)
	first, second := <-results, <-results
	if first.response.Code == http.StatusConflict {
		first, second = second, first
	}
	v2Status(t, first.response, http.StatusOK)
	v2Status(t, second.response, http.StatusConflict)
	return first.head
}
