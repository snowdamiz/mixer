package release

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"mixer/services/internal/durable"
	"mixer/services/protocol"
)

type Artifact struct {
	SignedManifest protocol.SignedManifest `json:"signed_manifest"`
	Payload        []byte                  `json:"payload"`
}
type Record struct {
	Artifact  Artifact `json:"artifact"`
	Validated bool     `json:"validated"`
	Published bool     `json:"published"`
}
type Channel struct {
	SignedAssignment protocol.SignedAssignment `json:"signed_assignment"`
}
type Event struct {
	ID            uint64 `json:"id"`
	Organization  string `json:"organization"`
	Project       string `json:"project"`
	Actor         string `json:"actor"`
	Action        string `json:"action"`
	Reason        string `json:"reason"`
	Previous      string `json:"previous"`
	Current       string `json:"current"`
	SourceIP      string `json:"source_ip"`
	RequestID     string `json:"request_id"`
	CreatedAtUnix uint64 `json:"created_at_unix"`
	PreviousHash  string `json:"previous_hash"`
	Hash          string `json:"hash"`
}
type Work struct {
	ID        uint64 `json:"id"`
	EventID   uint64 `json:"event_id"`
	Kind      string `json:"kind"`
	Status    string `json:"status"`
	RequestID string `json:"request_id"`
}
type Response struct {
	Status int             `json:"status"`
	Body   json.RawMessage `json:"body"`
}
type Dedup struct {
	Hash     string   `json:"hash"`
	Response Response `json:"response"`
}
type database struct {
	Schema      uint64             `json:"schema"`
	Artifacts   map[string]Record  `json:"artifacts"`
	Channels    map[string]Channel `json:"channels"`
	Idempotency map[string]Dedup   `json:"idempotency"`
	Audit       []Event            `json:"audit"`
	Outbox      []Work             `json:"outbox"`
}
type store struct {
	mu       sync.Mutex
	dir      string
	lock     *durable.Lock
	state    database
	fault    durable.Fault
	poisoned bool
}

func openStore(dir string, fault durable.Fault) (*store, error) {
	l, e := durable.Acquire(dir)
	if e != nil {
		return nil, e
	}
	s := &store{dir: dir, lock: l, fault: fault}
	b, e := os.ReadFile(filepath.Join(dir, "release.json"))
	if e != nil && !errors.Is(e, os.ErrNotExist) {
		l.Close()
		return nil, e
	}
	if e == nil {
		if e = protocol.DecodeJSON(b, &s.state); e != nil {
			l.Close()
			return nil, fmt.Errorf("corrupt durable store: %w", e)
		}
		if s.state.Schema != 1 || s.state.Artifacts == nil || s.state.Channels == nil || s.state.Idempotency == nil {
			l.Close()
			return nil, fmt.Errorf("unknown durable store schema")
		}
		prev := ""
		for i, ev := range s.state.Audit {
			hash := ev.Hash
			ev.Hash = ""
			raw, _ := json.Marshal(ev)
			if ev.ID != uint64(i+1) || ev.PreviousHash != prev || hash != protocol.Hash(raw) {
				l.Close()
				return nil, fmt.Errorf("audit chain corrupt")
			}
			prev = hash
		}
	} else {
		s.state = database{Schema: 1, Artifacts: map[string]Record{}, Channels: map[string]Channel{}, Idempotency: map[string]Dedup{}, Audit: []Event{}, Outbox: []Work{}}
		if e = durable.JSON(dir, "release.json", s.state, fault); e != nil {
			l.Close()
			return nil, e
		}
	}
	return s, nil
}
func clone(s database) database {
	b, _ := json.Marshal(s)
	var d database
	_ = json.Unmarshal(b, &d)
	return d
}
func scopeKey(org, project string) string { return org + "/" + project + "/" }
func artifactKey(scope protocol.Scope, digest string) string {
	return scopeKey(scope.Organization, scope.Project) + digest
}
func channelKey(a protocol.Assignment) string {
	return scopeKey(a.Scope.Organization, a.Scope.Project) + a.Scope.App + "/" + a.Scope.Environment + "/" + a.Scope.Platform + "/" + a.Runtime + "/" + a.Channel
}
func (s *store) transaction(key, hash string, event Event, fn func(*database) (Response, error)) (Response, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.poisoned {
		return Response{}, apiError{503, "storage_unavailable", "durable store requires restart"}
	}
	if old, ok := s.state.Idempotency[key]; ok {
		if old.Hash != hash {
			return Response{}, apiError{409, "idempotency_conflict", "key was already used for another request"}
		}
		return old.Response, nil
	}
	next := clone(s.state)
	response, e := fn(&next)
	if e != nil {
		return Response{}, e
	}
	// Previous/current are content hashes of the complete domain state. The
	// referenced immutable artifacts and assignments remain available for audit.
	before, _ := json.Marshal(struct {
		Artifacts map[string]Record  `json:"artifacts"`
		Channels  map[string]Channel `json:"channels"`
	}{s.state.Artifacts, s.state.Channels})
	after, _ := json.Marshal(struct {
		Artifacts map[string]Record  `json:"artifacts"`
		Channels  map[string]Channel `json:"channels"`
	}{next.Artifacts, next.Channels})
	event.Previous = protocol.Hash(before)
	event.Current = protocol.Hash(after)
	event.ID = uint64(len(next.Audit) + 1)
	if len(next.Audit) > 0 {
		event.PreviousHash = next.Audit[len(next.Audit)-1].Hash
	}
	b, _ := json.Marshal(event)
	event.Hash = protocol.Hash(b)
	next.Audit = append(next.Audit, event)
	next.Outbox = append(next.Outbox, Work{ID: uint64(len(next.Outbox) + 1), EventID: event.ID, Kind: event.Action, Status: "pending_local_only", RequestID: event.RequestID})
	next.Idempotency[key] = Dedup{hash, response}
	if e = durable.JSON(s.dir, "release.json", next, s.fault); e != nil {
		s.poisoned = true
		return Response{}, apiError{503, "storage_unavailable", "commit uncertain; restart and retry same idempotency key"}
	}
	s.state = next
	return response, nil
}
func response(status int, v any) Response { b, _ := json.Marshal(v); return Response{status, b} }
