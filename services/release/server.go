// Package release implements a bounded local-development control plane. It
// intentionally refuses production until transactional PostgreSQL, external
// storage/outbox workers, operational review and isolation are implemented.
package release

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"mixer/services/internal/durable"
	"mixer/services/protocol"
)

type Token struct {
	SHA256       string `json:"sha256"`
	Role         string `json:"role"`
	Organization string `json:"organization"`
	Project      string `json:"project"`
	Actor        string `json:"actor"`
}
type Config struct {
	DeveloperMode bool            `json:"developer_mode"`
	Listen        string          `json:"listen"`
	DataDirectory string          `json:"data_directory"`
	Tokens        []Token         `json:"tokens"`
	Roots         []protocol.Root `json:"roots"`
	Hosts         []protocol.Host `json:"hosts"`
}
type apiError struct {
	status        int
	code, message string
}

func (e apiError) Error() string { return e.message }

type rate struct {
	window time.Time
	count  uint64
}
type Server struct {
	cfg       Config
	db        *store
	limiterMu sync.Mutex
	rates     map[string]rate
	inflight  chan struct{}
	now       func() time.Time
}

func ValidateConfig(c Config) error {
	if !c.DeveloperMode {
		return fmt.Errorf("production mode disabled: PostgreSQL/outbox/isolation and operational gates are not implemented")
	}
	host, _, e := net.SplitHostPort(c.Listen)
	if e != nil {
		return fmt.Errorf("literal loopback listen address required")
	}
	ip := net.ParseIP(host)
	if ip == nil || !ip.IsLoopback() {
		return fmt.Errorf("developer mode must listen on literal loopback")
	}
	if c.DataDirectory == "" || len(c.Tokens) == 0 || len(c.Hosts) == 0 || len(c.Roots) == 0 {
		return fmt.Errorf("data directory, scoped tokens, roots and hosts required")
	}
	for _, t := range c.Tokens {
		if !protocol.ValidDigest(t.SHA256) || !protocol.ValidID(t.Actor) || !protocol.ValidID(t.Organization) || !protocol.ValidID(t.Project) || (t.Role != "reader" && t.Role != "editor" && t.Role != "publisher") {
			return fmt.Errorf("invalid scoped bearer token configuration")
		}
	}
	seen := map[string]bool{}
	for _, r := range c.Roots {
		if e := r.Scope.Validate(); e != nil {
			return e
		}
		if !protocol.ValidID(r.KeyID) || len(r.PublicKey) != 32 || (!r.Artifact && !r.Assignment) || r.NotAfterUnix != 0 && r.NotAfterUnix <= r.NotBeforeUnix || seen[r.KeyID] {
			return fmt.Errorf("invalid/duplicate root configuration")
		}
		seen[r.KeyID] = true
	}
	seen = map[string]bool{}
	for _, h := range c.Hosts {
		if e := h.Scope.Validate(); e != nil {
			return e
		}
		a := protocol.Assignment{Scope: h.Scope, Runtime: h.Runtime}
		key := channelKey(a)
		if h.Protocol != 1 || h.GuestABI != 1 || h.UISchema != 1 || !protocol.ValidDigest(h.Runtime) || h.MaxPayloadBytes == 0 || h.MaxPayloadBytes > protocol.MaxPayloadBytes || h.Limits.MemoryBytes == 0 || h.Limits.Fuel == 0 || h.Limits.StartupMilliseconds == 0 || seen[key] {
			return fmt.Errorf("invalid/duplicate registered host")
		}
		seen[key] = true
	}
	return nil
}
func New(cfg Config) (*Server, error) { return NewWithFault(cfg, nil) }
func NewWithFault(cfg Config, fault durable.Fault) (*Server, error) {
	if e := ValidateConfig(cfg); e != nil {
		return nil, e
	}
	db, e := openStore(cfg.DataDirectory, fault)
	if e != nil {
		return nil, e
	}
	return &Server{cfg: cfg, db: db, rates: map[string]rate{}, inflight: make(chan struct{}, 128), now: time.Now}, nil
}
func (s *Server) Close() error {
	s.db.mu.Lock()
	defer s.db.mu.Unlock()
	s.db.poisoned = true
	return s.db.lock.Close()
}

// Run gracefully drains in-flight HTTP requests before releasing the store lock.
func (s *Server) Run(ctx context.Context) error {
	listener, e := net.Listen("tcp", s.cfg.Listen)
	if e != nil {
		return e
	}
	server := &http.Server{Handler: s, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 30 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 16 * 1024}
	done := make(chan error, 1)
	go func() { done <- server.Serve(listener) }()
	select {
	case e := <-done:
		if e == http.ErrServerClosed {
			return nil
		}
		return e
	case <-ctx.Done():
		stop, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		e := server.Shutdown(stop)
		if e != nil {
			_ = server.Close()
		}
		return e
	}
}
func requestID() string { var b [16]byte; _, _ = rand.Read(b[:]); return hex.EncodeToString(b[:]) }
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	id := requestID()
	w.Header().Set("X-Request-ID", id)
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Content-Type", "application/json")
	select {
	case s.inflight <- struct{}{}:
		defer func() { <-s.inflight }()
	default:
		s.fail(w, id, apiError{429, "concurrency_limit", "too many concurrent requests"})
		return
	}
	ip, _, _ := net.SplitHostPort(r.RemoteAddr)
	if !s.allow(ip) {
		w.Header().Set("Retry-After", "60")
		s.fail(w, id, apiError{429, "rate_limit", "request limit exceeded"})
		return
	}
	if r.URL.RawPath != "" {
		s.fail(w, id, apiError{400, "invalid_path", "encoded paths unsupported"})
		return
	}
	out, e := s.route(r, id, ip)
	if e != nil {
		s.fail(w, id, e)
		return
	}
	w.WriteHeader(out.Status)
	if out.Status != 204 {
		_, _ = w.Write(out.Body)
	}
}
func (s *Server) allow(ip string) bool {
	s.limiterMu.Lock()
	defer s.limiterMu.Unlock()
	now := s.now()
	v := s.rates[ip]
	if now.Sub(v.window) >= time.Minute || v.window.IsZero() {
		v = rate{window: now}
	}
	v.count++
	s.rates[ip] = v
	if len(s.rates) > 4096 {
		for k, v := range s.rates {
			if now.Sub(v.window) >= time.Minute {
				delete(s.rates, k)
			}
		}
	}
	return v.count <= 120 && len(s.rates) <= 4096
}
func (s *Server) fail(w http.ResponseWriter, id string, e error) {
	a, ok := e.(apiError)
	if !ok {
		a = apiError{500, "internal_error", "internal operation failed"}
	}
	w.WriteHeader(a.status)
	_ = json.NewEncoder(w).Encode(map[string]any{"error": map[string]string{"code": a.code, "message": a.message}, "request_id": id})
}
func (s *Server) auth(r *http.Request, org, project, role string) (Token, error) {
	header := r.Header.Get("Authorization")
	if !strings.HasPrefix(header, "Bearer ") || len(header) > 4096 {
		return Token{}, apiError{401, "unauthenticated", "bearer credential required"}
	}
	hash := protocol.Hash([]byte(strings.TrimPrefix(header, "Bearer ")))
	for _, t := range s.cfg.Tokens {
		if subtle.ConstantTimeCompare([]byte(hash), []byte(t.SHA256)) == 1 {
			if t.Organization != org || t.Project != project {
				return Token{}, apiError{403, "scope_denied", "project access denied"}
			}
			allowed := role == "reader" || role == "editor" && (t.Role == "editor" || t.Role == "publisher") || role == "publisher" && t.Role == "publisher"
			if !allowed {
				return Token{}, apiError{403, "role_denied", "project permission denied"}
			}
			return t, nil
		}
	}
	return Token{}, apiError{401, "unauthenticated", "invalid bearer credential"}
}
func (s *Server) host(scope protocol.Scope, runtime string) (protocol.Host, error) {
	for _, h := range s.cfg.Hosts {
		if h.Scope == scope && h.Runtime == runtime {
			return h, nil
		}
	}
	return protocol.Host{}, apiError{422, "unknown_runtime", "no registered host contract for scope and runtime"}
}
func body(r *http.Request, v any) ([]byte, error) {
	if r.Header.Get("Content-Type") != "application/json" {
		return nil, apiError{400, "content_type", "application/json required"}
	}
	const max = 24 * 1024 * 1024
	b, e := io.ReadAll(io.LimitReader(r.Body, max+1))
	if e != nil {
		return nil, apiError{400, "malformed_body", "body could not be read"}
	}
	if len(b) > max {
		return nil, apiError{413, "body_too_large", "body exceeds 24 MiB"}
	}
	if e = protocol.DecodeJSON(b, v); e != nil {
		return nil, apiError{400, "invalid_json", e.Error()}
	}
	return b, nil
}
func (s *Server) route(r *http.Request, id, ip string) (Response, error) {
	if r.Method == "GET" && r.URL.Path == "/healthz" {
		return response(200, map[string]any{"mode": "developer", "production_ready": false}), nil
	}
	if r.Method == "GET" && r.URL.Path == "/v1/updates" {
		return s.update(r)
	}
	p := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if r.Method == "GET" && len(p) == 3 && p[0] == "v1" && p[1] == "artifacts" {
		return s.publicArtifact(r, p[2])
	}
	if len(p) < 6 || p[0] != "v1" || p[1] != "orgs" || p[3] != "projects" || !protocol.ValidID(p[2]) || !protocol.ValidID(p[4]) {
		return Response{}, apiError{404, "not_found", "endpoint not found"}
	}
	org, project := p[2], p[4]
	role := "reader"
	if r.Method != "GET" {
		role = "editor"
	}
	if len(p) >= 6 && p[5] == "channels" {
		role = "publisher"
	}
	actor, e := s.auth(r, org, project, role)
	if e != nil {
		return Response{}, e
	}
	if r.Method == "GET" {
		return s.read(r, p, org, project)
	}
	key := r.Header.Get("Idempotency-Key")
	if !protocol.ValidID(key) {
		return Response{}, apiError{400, "idempotency_required", "Idempotency-Key identifier required"}
	}
	event := Event{Organization: org, Project: project, Actor: actor.Actor, Action: r.Method + " " + r.URL.Path, Reason: r.Header.Get("X-Mixer-Reason"), SourceIP: ip, RequestID: id, CreatedAtUnix: uint64(s.now().Unix())}
	if len(event.Reason) > 512 {
		return Response{}, apiError{400, "invalid_reason", "reason exceeds 512 bytes"}
	}
	if event.Reason == "" {
		event.Reason = "local development operation"
	}
	return s.mutate(r, p, org, project, key, event)
}
func (s *Server) read(r *http.Request, p []string, org, project string) (Response, error) {
	s.db.mu.Lock()
	defer s.db.mu.Unlock()
	if s.db.poisoned {
		return Response{}, apiError{503, "storage_unavailable", "durable store requires restart"}
	}
	if len(p) == 7 && p[5] == "artifacts" && protocol.ValidDigest(p[6]) {
		rec, ok := s.db.state.Artifacts[scopeKey(org, project)+p[6]]
		if !ok {
			return Response{}, apiError{404, "not_found", "artifact not found"}
		}
		return response(200, rec.Artifact), nil
	}
	if len(p) == 6 && (p[5] == "audit" || p[5] == "outbox") {
		after, e := strconv.ParseUint(defaulted(r.URL.Query().Get("after"), "0"), 10, 64)
		if e != nil {
			return Response{}, apiError{400, "invalid_cursor", "after must be uint64"}
		}
		limit, e := strconv.Atoi(defaulted(r.URL.Query().Get("limit"), "100"))
		if e != nil || limit < 1 || limit > 100 {
			return Response{}, apiError{400, "invalid_limit", "limit must be 1..100"}
		}
		events := []Event{}
		work := []Work{}
		next := after
		for _, ev := range s.db.state.Audit {
			if ev.ID <= after || ev.Organization != org || ev.Project != project {
				continue
			}
			if len(events) >= limit {
				break
			}
			events = append(events, ev)
			next = ev.ID
			if p[5] == "outbox" {
				for _, x := range s.db.state.Outbox {
					if x.EventID == ev.ID {
						work = append(work, x)
					}
				}
			}
		}
		if p[5] == "audit" {
			return response(200, map[string]any{"events": events, "next": next}), nil
		}
		return response(200, map[string]any{"work": work, "next": next}), nil
	}
	return Response{}, apiError{404, "not_found", "endpoint not found"}
}
func defaulted(v, fallback string) string {
	if v == "" {
		return fallback
	}
	return v
}
func (s *Server) mutate(r *http.Request, p []string, org, project, key string, event Event) (Response, error) {
	dedup := scopeKey(org, project) + key
	commit := func(raw []byte, fn func(*database) (Response, error)) (Response, error) {
		hash := protocol.Hash(append([]byte(r.Method+" "+r.URL.Path+"\x00"), raw...))
		return s.db.transaction(dedup, hash, event, fn)
	}
	if r.Method == "PUT" && len(p) == 7 && p[5] == "artifacts" && protocol.ValidDigest(p[6]) {
		var a Artifact
		raw, e := body(r, &a)
		if e != nil {
			return Response{}, e
		}
		return commit(raw, func(db *database) (Response, error) {
			m := a.SignedManifest.Manifest
			if m.Scope.Organization != org || m.Scope.Project != project {
				return Response{}, apiError{403, "scope_denied", "signed artifact tenant differs from route"}
			}
			h, e := s.host(m.Scope, m.Runtime)
			if e != nil {
				return Response{}, e
			}
			if e = protocol.VerifyManifest(a.SignedManifest, a.Payload, s.cfg.Roots, h, uint64(s.now().Unix())); e != nil {
				return Response{}, apiError{422, "artifact_invalid", e.Error()}
			}
			digest, _ := protocol.ManifestDigest(m)
			if digest != p[6] {
				return Response{}, apiError{422, "digest_mismatch", "artifact identity differs from route"}
			}
			ak := artifactKey(m.Scope, digest)
			if old, ok := db.Artifacts[ak]; ok {
				if protocol.Hash(old.Artifact.Payload) != protocol.Hash(a.Payload) {
					return Response{}, apiError{409, "immutable_conflict", "artifact is immutable"}
				}
				return response(200, map[string]any{"artifact_sha256": digest, "immutable": true}), nil
			}
			if len(db.Artifacts) >= 64 {
				return Response{}, apiError{409, "local_capacity", "local development artifact limit reached"}
			}
			db.Artifacts[ak] = Record{Artifact: a}
			return response(201, map[string]any{"artifact_sha256": digest, "immutable": true}), nil
		})
	}
	if r.Method == "POST" && len(p) == 7 && p[5] == "releases" && p[6] == "validate" {
		var req struct {
			ArtifactSHA256 string `json:"artifact_sha256"`
		}
		raw, e := body(r, &req)
		if e != nil {
			return Response{}, e
		}
		return commit(raw, func(db *database) (Response, error) {
			k := scopeKey(org, project) + req.ArtifactSHA256
			rec, ok := db.Artifacts[k]
			if !ok {
				return Response{}, apiError{404, "not_found", "artifact not found"}
			}
			h, e := s.host(rec.Artifact.SignedManifest.Manifest.Scope, rec.Artifact.SignedManifest.Manifest.Runtime)
			if e != nil {
				return Response{}, e
			}
			if e = protocol.VerifyManifest(rec.Artifact.SignedManifest, rec.Artifact.Payload, s.cfg.Roots, h, uint64(s.now().Unix())); e != nil {
				return Response{}, apiError{422, "artifact_invalid", e.Error()}
			}
			rec.Validated = true
			db.Artifacts[k] = rec
			return response(200, map[string]any{"artifact_sha256": req.ArtifactSHA256, "protocol_valid": true, "compiler_eligibility_verified": false, "policy_approved": false, "mobile_qualified": false}), nil
		})
	}
	if r.Method == "POST" && len(p) == 8 && p[5] == "channels" && protocol.ValidID(p[6]) && (p[7] == "publish" || p[7] == "promote" || p[7] == "rollback") {
		var req struct {
			SignedAssignment protocol.SignedAssignment `json:"signed_assignment"`
		}
		raw, e := body(r, &req)
		if e != nil {
			return Response{}, e
		}
		return commit(raw, func(db *database) (Response, error) {
			a := req.SignedAssignment.Assignment
			if a.Scope.Organization != org || a.Scope.Project != project {
				return Response{}, apiError{403, "scope_denied", "signed assignment tenant differs from route"}
			}
			k := artifactKey(a.Scope, a.ArtifactSHA256)
			rec, ok := db.Artifacts[k]
			if !ok || !rec.Validated {
				return Response{}, apiError{422, "not_validated", "artifact must be uploaded and validated"}
			}
			h, e := s.host(a.Scope, a.Runtime)
			if e != nil {
				return Response{}, e
			}
			if e = protocol.VerifyManifest(rec.Artifact.SignedManifest, rec.Artifact.Payload, s.cfg.Roots, h, uint64(s.now().Unix())); e != nil {
				return Response{}, apiError{422, "artifact_invalid", e.Error()}
			}
			ck := channelKey(a)
			old, exists := db.Channels[ck]
			last := old.SignedAssignment.Assignment.Sequence
			if e = protocol.VerifyAssignmentHeader(req.SignedAssignment, rec.Artifact.SignedManifest.Manifest, s.cfg.Roots, h, p[6], last, uint64(s.now().Unix())); e != nil {
				return Response{}, apiError{409, "assignment_rejected", e.Error()}
			}
			if p[7] == "promote" && (!exists || old.SignedAssignment.Assignment.ArtifactSHA256 != a.ArtifactSHA256 || old.SignedAssignment.Assignment.RolloutBasisPoints > a.RolloutBasisPoints) {
				return Response{}, apiError{409, "invalid_promotion", "promotion must expand current artifact rollout"}
			}
			if p[7] == "rollback" && (!exists || !rec.Published) {
				return Response{}, apiError{409, "invalid_rollback", "rollback target must have been previously published"}
			}
			db.Channels[ck] = Channel{req.SignedAssignment}
			rec.Published = true
			db.Artifacts[k] = rec
			return response(200, map[string]any{"sequence": a.Sequence, "artifact_sha256": a.ArtifactSHA256, "rollout_basis_points": a.RolloutBasisPoints, "delivery": "local_only"}), nil
		})
	}
	return Response{}, apiError{404, "not_found", "endpoint not found"}
}
func (s *Server) update(r *http.Request) (Response, error) {
	q := r.URL.Query()
	scope := protocol.Scope{Organization: q.Get("organization"), Project: q.Get("project"), App: q.Get("app"), Environment: q.Get("environment"), Platform: q.Get("platform")}
	if scope.Validate() != nil || !protocol.ValidDigest(q.Get("runtime")) || !protocol.ValidID(q.Get("channel")) || !protocol.ValidID(q.Get("installation")) {
		return Response{}, apiError{400, "invalid_query", "complete valid public delivery scope required"}
	}
	a := protocol.Assignment{Scope: scope, Runtime: q.Get("runtime"), Channel: q.Get("channel")}
	s.db.mu.Lock()
	defer s.db.mu.Unlock()
	if s.db.poisoned {
		return Response{}, apiError{503, "storage_unavailable", "durable store requires restart"}
	}
	rec, ok := s.db.state.Channels[channelKey(a)]
	if !ok || !protocol.Eligible(rec.SignedAssignment.Assignment, q.Get("installation")) {
		return Response{Status: 204}, nil
	}
	return response(200, map[string]any{"signed_assignment": rec.SignedAssignment, "artifact_url": "/v1/artifacts/" + rec.SignedAssignment.Assignment.ArtifactSHA256 + "?organization=" + scope.Organization + "&project=" + scope.Project}), nil
}
func (s *Server) publicArtifact(r *http.Request, digest string) (Response, error) {
	org, project := r.URL.Query().Get("organization"), r.URL.Query().Get("project")
	if !protocol.ValidID(org) || !protocol.ValidID(project) || !protocol.ValidDigest(digest) {
		return Response{}, apiError{400, "invalid_query", "valid artifact identity and tenant scope required"}
	}
	s.db.mu.Lock()
	defer s.db.mu.Unlock()
	if s.db.poisoned {
		return Response{}, apiError{503, "storage_unavailable", "durable store requires restart"}
	}
	rec, ok := s.db.state.Artifacts[scopeKey(org, project)+digest]
	if !ok || !rec.Published {
		return Response{}, apiError{404, "not_found", "published artifact not found"}
	}
	return response(200, rec.Artifact), nil
}
