package release

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"

	"mixer/services/protocol"
)

// Tenant identity is selected from authenticated routing, never a request body.
// Public delivery uses distinct methods which expose published data only.
type tenant struct{ Organization, Project string }
type access struct {
	tenant
	Actor, Role string
}

func (a access) require(role string) error {
	if !protocol.ValidID(a.Organization) || !protocol.ValidID(a.Project) || !protocol.ValidID(a.Actor) {
		return apiError{403, "scope_denied", "invalid authenticated storage scope"}
	}
	allowed := role == "reader" && (a.Role == "reader" || a.Role == "editor" || a.Role == "publisher") || role == "editor" && (a.Role == "editor" || a.Role == "publisher") || role == "publisher" && a.Role == "publisher"
	if !allowed {
		return apiError{403, "role_denied", "storage permission denied"}
	}
	return nil
}
func (t tenant) valid() bool { return protocol.ValidID(t.Organization) && protocol.ValidID(t.Project) }
func (t tenant) matches(s protocol.Scope) bool {
	return t.Organization == s.Organization && t.Project == s.Project
}
func (t tenant) prefix() string { return scopeKey(t.Organization, t.Project) }

type releaseTransaction interface {
	artifact(string) (Record, bool, error)
	saveArtifact(string, Record) error
	channel(string) (Channel, bool, error)
	saveChannel(string, Channel) error
}
type releaseStorage interface {
	close() error
	transaction(context.Context, access, string, string, string, Event, func(releaseTransaction) (Response, error)) (Response, error)
	artifact(context.Context, access, string) (Record, bool, error)
	publicArtifact(context.Context, tenant, string) (Record, bool, error)
	publicChannel(context.Context, tenant, string) (Channel, bool, error)
	history(context.Context, access, uint64, int) ([]Event, []Work, uint64, error)
}

func immutableEqual(a, b Record) bool {
	left, le := json.Marshal(a.signedManifest())
	right, re := json.Marshal(b.signedManifest())
	return a.version() != 0 && a.version() == b.version() && le == nil && re == nil && bytes.Equal(left, right) && bytes.Equal(a.payload(), b.payload())
}
func checkArtifact(t tenant, digest string, record Record) error {
	if !t.valid() || !t.matches(record.scope()) {
		return apiError{403, "scope_denied", "artifact differs from authenticated storage scope"}
	}
	got, e := record.digest()
	if e != nil || record.validate() != nil || got != digest || !protocol.ValidDigest(digest) {
		return apiError{422, "artifact_invalid", "invalid immutable artifact identity"}
	}
	if record.Published && !record.Validated {
		return apiError{409, "not_validated", "published artifact must be validated"}
	}
	return nil
}
func checkChannel(t tenant, key string, c Channel) error {
	a := c.assignment()
	if !t.valid() || !t.matches(a.Scope) || !strings.HasPrefix(key, t.prefix()) {
		return apiError{403, "scope_denied", "assignment differs from authenticated storage scope"}
	}
	if c.validate() != nil || key != channelKey(a) {
		return apiError{422, "assignment_invalid", "invalid assignment identity"}
	}
	return nil
}

type memoryTransaction struct {
	db  *database
	who access
}

func (t *memoryTransaction) artifact(digest string) (Record, bool, error) {
	rec, ok := t.db.Artifacts[t.who.prefix()+digest]
	return rec, ok, nil
}
func (t *memoryTransaction) saveArtifact(digest string, rec Record) error {
	if e := t.who.require("editor"); e != nil {
		return e
	}
	if e := checkArtifact(t.who.tenant, digest, rec); e != nil {
		return e
	}
	key := t.who.prefix() + digest
	if old, ok := t.db.Artifacts[key]; ok {
		if !immutableEqual(old, rec) {
			return apiError{409, "immutable_conflict", "artifact content is immutable"}
		}
		if old.Published && !rec.Published || old.Validated && !rec.Validated {
			return apiError{409, "immutable_conflict", "artifact state cannot move backwards"}
		}
		if old.Published != rec.Published {
			if e := t.who.require("publisher"); e != nil {
				return e
			}
		}
	} else {
		if rec.Published {
			if e := t.who.require("publisher"); e != nil {
				return e
			}
		}
		if len(t.db.Artifacts) >= 64 {
			return apiError{409, "local_capacity", "local development artifact limit reached"}
		}
	}
	if version := rec.version(); version > t.db.Schema {
		t.db.Schema = version
	}
	t.db.Artifacts[key] = rec
	return nil
}
func (t *memoryTransaction) channel(key string) (Channel, bool, error) {
	if !strings.HasPrefix(key, t.who.prefix()) {
		return Channel{}, false, apiError{403, "scope_denied", "channel scope differs"}
	}
	value, ok := t.db.Channels[key]
	return value, ok, nil
}
func (t *memoryTransaction) saveChannel(key string, c Channel) error {
	if e := t.who.require("publisher"); e != nil {
		return e
	}
	if e := checkChannel(t.who.tenant, key, c); e != nil {
		return e
	}
	artifact, exists, e := t.artifact(c.assignment().ArtifactSHA256)
	if e != nil {
		return e
	}
	if !exists || checkChannelArtifact(artifact, c) != nil {
		return apiError{422, "assignment_invalid", "assignment artifact binding rejected"}
	}
	if old, ok := t.db.Channels[key]; ok && (c.version() != old.version() || c.assignment().Sequence <= old.assignment().Sequence) {
		return apiError{409, "assignment_rejected", "assignment sequence must increase"}
	}
	if version := c.version(); version > t.db.Schema {
		t.db.Schema = version
	}
	t.db.Channels[key] = c
	return nil
}
func (s *store) close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.poisoned = true
	return s.lock.Close()
}
func (s *store) available() error {
	if s.poisoned {
		return apiError{503, "storage_unavailable", "durable store requires restart"}
	}
	return nil
}
func (s *store) artifact(ctx context.Context, who access, digest string) (Record, bool, error) {
	if e := who.require("reader"); e != nil {
		return Record{}, false, e
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if e := s.available(); e != nil {
		return Record{}, false, e
	}
	rec, ok := s.state.Artifacts[who.prefix()+digest]
	return rec, ok, nil
}
func (s *store) publicArtifact(ctx context.Context, t tenant, digest string) (Record, bool, error) {
	if !t.valid() {
		return Record{}, false, apiError{403, "scope_denied", "invalid delivery scope"}
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if e := s.available(); e != nil {
		return Record{}, false, e
	}
	rec, ok := s.state.Artifacts[t.prefix()+digest]
	return rec, ok && rec.Published, nil
}
func (s *store) publicChannel(ctx context.Context, t tenant, key string) (Channel, bool, error) {
	if !t.valid() || !strings.HasPrefix(key, t.prefix()) {
		return Channel{}, false, apiError{403, "scope_denied", "invalid delivery scope"}
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if e := s.available(); e != nil {
		return Channel{}, false, e
	}
	rec, ok := s.state.Channels[key]
	return rec, ok, nil
}
func (s *store) history(ctx context.Context, who access, after uint64, limit int) ([]Event, []Work, uint64, error) {
	if e := who.require("reader"); e != nil {
		return nil, nil, after, e
	}
	if limit < 1 || limit > 100 {
		return nil, nil, after, apiError{400, "invalid_limit", "limit must be 1..100"}
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if e := s.available(); e != nil {
		return nil, nil, after, e
	}
	events := []Event{}
	work := []Work{}
	next := after
	for _, ev := range s.state.Audit {
		if ev.ID <= after || ev.Organization != who.Organization || ev.Project != who.Project {
			continue
		}
		if len(events) >= limit {
			break
		}
		events = append(events, ev)
		next = ev.ID
		for _, x := range s.state.Outbox {
			if x.EventID == ev.ID {
				work = append(work, x)
			}
		}
	}
	return events, work, next, nil
}
func tenantDomainHash(db database, t tenant) string {
	artifacts := map[string]Record{}
	channels := map[string]Channel{}
	for k, v := range db.Artifacts {
		if strings.HasPrefix(k, t.prefix()) {
			artifacts[k] = v
		}
	}
	for k, v := range db.Channels {
		if strings.HasPrefix(k, t.prefix()) {
			channels[k] = v
		}
	}
	b, _ := json.Marshal(struct {
		Artifacts map[string]Record  `json:"artifacts"`
		Channels  map[string]Channel `json:"channels"`
	}{artifacts, channels})
	return protocol.Hash(b)
}
