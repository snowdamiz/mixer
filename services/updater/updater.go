// Package updater is a local Go recovery reference. Mobile adapters, platform
// storage semantics and crash classification require separate qualification.
package updater

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"

	"mixer/services/internal/durable"
	"mixer/services/protocol"
)

type Failure string

const StartupTrap Failure = "startup_trap"
const UnknownInterruption Failure = "unknown_interruption"
const NativeCrash Failure = "native_crash"
const UserQuit Failure = "user_quit"

type Candidate struct {
	Manifest   protocol.SignedManifest   `json:"manifest"`
	Assignment protocol.SignedAssignment `json:"assignment"`
	Digest     string                    `json:"digest"`
}
type Attempt struct {
	LaunchID  string `json:"launch_id"`
	Digest    string `json:"digest"`
	StartedAt uint64 `json:"started_at"`
	Reason    string `json:"reason"`
}
type State struct {
	Version         uint64               `json:"version"`
	Host            protocol.Host        `json:"host"`
	Channel         string               `json:"channel"`
	Installation    string               `json:"installation"`
	Sequence        uint64               `json:"sequence"`
	Download        *Candidate           `json:"download"`
	Candidates      map[string]Candidate `json:"candidates"`
	Staged          string               `json:"staged"`
	Healthy         string               `json:"healthy"`
	PreviousHealthy string               `json:"previous_healthy"`
	Attempt         *Attempt             `json:"attempt"`
	Failures        map[string]uint64    `json:"failures"`
	Quarantine      map[string]string    `json:"quarantine"`
	LastRecovery    string               `json:"last_recovery"`
}
type Config struct {
	Directory          string
	Host               protocol.Host
	Roots              []protocol.Root
	Channel            string
	Installation       string
	FailureThreshold   uint64
	ObservationSeconds uint64
	ReserveDiskBytes   uint64
	// Fault exists for deterministic I/O fault tests. Production callers leave nil.
	Fault durable.Fault
}
type Store struct {
	mu       sync.Mutex
	cfg      Config
	state    State
	lock     *durable.Lock
	poisoned bool
}
type Selection struct {
	Digest         string `json:"digest"`
	PayloadPath    string `json:"payload_path"`
	LaunchID       string `json:"launch_id"`
	NativeFallback bool   `json:"native_fallback"`
	Provisional    bool   `json:"provisional"`
}

func Open(cfg Config) (*Store, error) {
	if cfg.ReserveDiskBytes == 0 {
		cfg.ReserveDiskBytes = 16 * 1024 * 1024
	}
	if !protocol.ValidID(cfg.Channel) || !protocol.ValidID(cfg.Installation) || cfg.FailureThreshold == 0 || cfg.ObservationSeconds == 0 {
		return nil, fmt.Errorf("channel, installation and recovery policy required")
	}
	if e := cfg.Host.Scope.Validate(); e != nil {
		return nil, e
	}
	if cfg.Host.MaxPayloadBytes == 0 || cfg.Host.MaxPayloadBytes > protocol.MaxPayloadBytes {
		return nil, fmt.Errorf("invalid payload budget")
	}
	l, e := durable.Acquire(cfg.Directory)
	if e != nil {
		return nil, e
	}
	s := &Store{cfg: cfg, lock: l}
	b, e := os.ReadFile(filepath.Join(cfg.Directory, "state.json"))
	if e != nil && !errors.Is(e, os.ErrNotExist) {
		l.Close()
		return nil, e
	}
	if e == nil {
		if e = json.Unmarshal(b, &s.state); e != nil {
			l.Close()
			return nil, fmt.Errorf("corrupt recovery state: %w", e)
		}
		a, _ := protocol.CanonicalCBOR(s.state.Host)
		c, _ := protocol.CanonicalCBOR(cfg.Host)
		if s.state.Version != 1 || string(a) != string(c) || s.state.Channel != cfg.Channel || s.state.Installation != cfg.Installation || s.state.Candidates == nil || s.state.Failures == nil || s.state.Quarantine == nil {
			l.Close()
			return nil, fmt.Errorf("store host contract or channel changed")
		}
	} else {
		s.state = State{Version: 1, Host: cfg.Host, Channel: cfg.Channel, Installation: cfg.Installation, Candidates: map[string]Candidate{}, Failures: map[string]uint64{}, Quarantine: map[string]string{}}
		if e = s.commit(); e != nil {
			l.Close()
			return nil, e
		}
	}
	return s, nil
}
func (s *Store) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.poisoned = true
	return s.lock.Close()
}
func (s *Store) commit() error {
	if s.poisoned {
		return fmt.Errorf("store unavailable; reopen required")
	}
	if e := durable.JSON(s.cfg.Directory, "state.json", s.state, s.cfg.Fault); e != nil {
		s.poisoned = true
		return fmt.Errorf("durability failure; reopen required: %w", e)
	}
	return nil
}
func (s *Store) path(digest string) string { return filepath.Join(s.cfg.Directory, digest+".payload") }
func (s *Store) Snapshot() State {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, _ := json.Marshal(s.state)
	var out State
	_ = json.Unmarshal(b, &out)
	return out
}

// Begin persists assignment high-water before download. An interrupted download
// resumes through Resume, never by lowering the accepted assignment sequence.
func (s *Store) Begin(a protocol.SignedAssignment, m protocol.SignedManifest, now uint64) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.poisoned {
		return fmt.Errorf("store unavailable")
	}
	if e := protocol.VerifyManifestHeader(m, s.cfg.Roots, s.cfg.Host, now); e != nil {
		return e
	}
	if e := protocol.VerifyAssignment(a, m.Manifest, s.cfg.Roots, s.cfg.Host, s.cfg.Channel, s.cfg.Installation, s.state.Sequence, now); e != nil {
		return e
	}
	digest, _ := protocol.ManifestDigest(m.Manifest)
	if _, ok := s.state.Quarantine[digest]; ok {
		return fmt.Errorf("candidate quarantined")
	}
	if s.state.Attempt != nil {
		return fmt.Errorf("activation in progress")
	}
	if s.state.Download != nil {
		return fmt.Errorf("download already in progress; resume or cancel it")
	}
	if len(s.state.Quarantine) >= 256 {
		return fmt.Errorf("local quarantine capacity reached; native maintenance required")
	}
	free, e := durable.AvailableBytes(s.cfg.Directory)
	if e != nil {
		return e
	}
	if free < m.Manifest.CompressedBytes || free-m.Manifest.CompressedBytes < s.cfg.ReserveDiskBytes {
		return fmt.Errorf("insufficient free disk; recovery reserve retained")
	}
	s.state.Download = &Candidate{m, a, digest}
	s.state.Sequence = a.Assignment.Sequence
	return s.commit()
}

// CancelDownload discards the partial bytes while preserving replay high-water.
func (s *Store) CancelDownload() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.state.Download == nil {
		return nil
	}
	path := s.path(s.state.Download.Digest) + ".part"
	s.state.Download = nil
	if e := s.commit(); e != nil {
		return e
	}
	if e := os.Remove(path); e != nil && !errors.Is(e, os.ErrNotExist) {
		return e
	}
	return durable.SyncDir(s.cfg.Directory)
}

// Resume appends a source positioned at the returned Offset. On success it
// verifies the complete payload, fsyncs it, renames it and only then stages it.
// Reader errors retain the private partial file for explicit resumption.
func (s *Store) Offset() (uint64, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.state.Download == nil {
		return 0, fmt.Errorf("no download")
	}
	st, e := os.Stat(s.path(s.state.Download.Digest) + ".part")
	if errors.Is(e, os.ErrNotExist) {
		return 0, nil
	}
	if e != nil {
		return 0, e
	}
	return uint64(st.Size()), nil
}
func (s *Store) Resume(source io.Reader, now uint64) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.poisoned {
		return fmt.Errorf("store unavailable")
	}
	if s.state.Download == nil {
		return fmt.Errorf("no download")
	}
	c := *s.state.Download
	m := c.Manifest.Manifest
	if e := protocol.VerifyManifestHeader(c.Manifest, s.cfg.Roots, s.cfg.Host, now); e != nil {
		return e
	}
	part := s.path(c.Digest) + ".part"
	f, e := os.OpenFile(part, os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return e
	}
	st, e := f.Stat()
	if e != nil {
		f.Close()
		return e
	}
	if st.Size() < 0 || uint64(st.Size()) > m.CompressedBytes {
		f.Close()
		return fmt.Errorf("partial size exceeds declaration")
	}
	if _, e = f.Seek(0, io.SeekEnd); e != nil {
		f.Close()
		return e
	}
	remaining := m.CompressedBytes - uint64(st.Size())
	if s.cfg.Fault != nil {
		if e = s.cfg.Fault("before_payload_write"); e != nil {
			f.Close()
			return e
		}
	}
	n, copyErr := io.Copy(f, io.LimitReader(source, int64(remaining)+1))
	if n > int64(remaining) {
		f.Close()
		os.Remove(part)
		return fmt.Errorf("download exceeds declared size")
	}
	if s.cfg.Fault != nil {
		if e = s.cfg.Fault("before_payload_sync"); e != nil {
			f.Close()
			return e
		}
	}
	if e = f.Sync(); e != nil {
		f.Close()
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	if copyErr != nil {
		return copyErr
	}
	payload, e := os.ReadFile(part)
	if e != nil {
		return e
	}
	if e = protocol.VerifyManifest(c.Manifest, payload, s.cfg.Roots, s.cfg.Host, now); e != nil {
		if uint64(len(payload)) == m.CompressedBytes {
			os.Remove(part)
		}
		return e
	}
	if s.cfg.Fault != nil {
		if e = s.cfg.Fault("before_payload_rename"); e != nil {
			return e
		}
	}
	if e = os.Rename(part, s.path(c.Digest)); e != nil {
		return e
	}
	if e = durable.SyncDir(s.cfg.Directory); e != nil {
		s.poisoned = true
		return e
	}
	s.state.Candidates[c.Digest] = c
	s.state.Staged = c.Digest
	s.state.Download = nil
	if e = s.commit(); e != nil {
		return e
	}
	return s.prune()
}
func (s *Store) prune() error {
	// Keep at most two healthy generations and one staged/provisional candidate.
	keep := map[string]bool{s.state.Healthy: true, s.state.PreviousHealthy: true, s.state.Staged: true}
	if s.state.Attempt != nil {
		keep[s.state.Attempt.Digest] = true
	}
	if s.state.Download != nil {
		keep[s.state.Download.Digest] = true
	}
	for d := range s.state.Candidates {
		if !keep[d] {
			delete(s.state.Candidates, d)
			_ = os.Remove(s.path(d))
		}
	}
	return s.commit()
}
func (s *Store) available(d string) bool {
	c, ok := s.state.Candidates[d]
	if !ok || d == "" {
		return false
	}
	if _, bad := s.state.Quarantine[d]; bad {
		return false
	}
	if protocol.Compatible(c.Manifest.Manifest, s.cfg.Host) != nil {
		return false
	}
	digest, e := protocol.ManifestDigest(c.Manifest.Manifest)
	if e != nil || digest != d || c.Digest != d {
		return false
	}
	st, e := os.Stat(s.path(d))
	if e != nil || st.Size() < 0 || uint64(st.Size()) != c.Manifest.Manifest.ExpandedBytes || uint64(st.Size()) > protocol.MaxPayloadBytes {
		return false
	}
	b, e := os.ReadFile(s.path(d))
	if e != nil {
		return false
	}
	// A previously healthy offline app retains artifact authorization. Recheck
	// cryptographic integrity against pinned public keys while disregarding
	// subsequent validity-window/revocation changes for this cached selection.
	roots := append([]protocol.Root{}, s.cfg.Roots...)
	for i := range roots {
		roots[i].Revoked = false
		roots[i].NotBeforeUnix = 0
		roots[i].NotAfterUnix = 0
	}
	return protocol.VerifyManifest(c.Manifest, b, roots, s.cfg.Host, 0) == nil && protocol.VerifyAssignment(c.Assignment, c.Manifest.Manifest, roots, s.cfg.Host, s.cfg.Channel, s.cfg.Installation, 0, 0) == nil
}
func (s *Store) fallback() Selection {
	for _, d := range []string{s.state.Healthy, s.state.PreviousHealthy} {
		if s.available(d) {
			return Selection{Digest: d, PayloadPath: s.path(d)}
		}
	}
	return Selection{NativeFallback: true}
}

// Start is called only at a safe cold start. Unknown prior interruption selects
// a healthy implementation for this launch without inventing startup failures.
func (s *Store) Start(now uint64) (Selection, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.poisoned {
		return Selection{}, fmt.Errorf("store unavailable")
	}
	if s.state.Attempt != nil {
		s.state.LastRecovery = string(UnknownInterruption)
		s.state.Attempt = nil
		if e := s.commit(); e != nil {
			return Selection{}, e
		}
		return s.fallback(), nil
	}
	d := s.state.Staged
	if d == "" {
		return s.fallback(), nil
	}
	// A staged candidate has not yet earned healthy offline authorization.
	if !s.available(d) {
		s.state.Quarantine[d] = "missing_or_corrupt_payload"
		s.state.Staged = ""
		if e := s.commit(); e != nil {
			return Selection{}, e
		}
		return s.fallback(), nil
	}
	candidate := s.state.Candidates[d]
	if protocol.VerifyManifestHeader(candidate.Manifest, s.cfg.Roots, s.cfg.Host, now) != nil {
		s.state.Quarantine[d] = "artifact_authority_denied"
		s.state.Staged = ""
		if e := s.commit(); e != nil {
			return Selection{}, e
		}
		return s.fallback(), nil
	}
	var id [16]byte
	if _, e := rand.Read(id[:]); e != nil {
		return Selection{}, e
	}
	launch := hex.EncodeToString(id[:])
	s.state.Attempt = &Attempt{LaunchID: launch, Digest: d, StartedAt: now}
	if e := s.commit(); e != nil {
		return Selection{}, e
	}
	return Selection{Digest: d, PayloadPath: s.path(d), LaunchID: launch, Provisional: true}, nil
}
func (s *Store) MarkHealthy(launch string, now uint64, milestones bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	a := s.state.Attempt
	if a == nil || a.LaunchID != launch {
		return fmt.Errorf("unknown launch")
	}
	if !milestones || now < a.StartedAt || now-a.StartedAt < s.cfg.ObservationSeconds {
		return fmt.Errorf("health observation incomplete")
	}
	if !s.available(a.Digest) {
		return fmt.Errorf("payload no longer valid")
	}
	if s.state.Healthy != a.Digest {
		s.state.PreviousHealthy = s.state.Healthy
	}
	s.state.Healthy = a.Digest
	s.state.Staged = ""
	s.state.Attempt = nil
	delete(s.state.Failures, a.Digest)
	if e := s.commit(); e != nil {
		return e
	}
	return s.prune()
}
func (s *Store) ReportFailure(launch string, reason Failure) (Selection, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if reason != StartupTrap && reason != UnknownInterruption && reason != NativeCrash && reason != UserQuit {
		return Selection{}, fmt.Errorf("unrecognized failure evidence")
	}
	a := s.state.Attempt
	if a == nil || a.LaunchID != launch {
		return Selection{}, fmt.Errorf("unknown launch")
	}
	if reason == StartupTrap {
		s.state.Failures[a.Digest]++
		if s.state.Failures[a.Digest] >= s.cfg.FailureThreshold {
			s.state.Quarantine[a.Digest] = string(reason)
			s.state.Staged = ""
		}
	}
	s.state.LastRecovery = string(reason)
	s.state.Attempt = nil
	if e := s.commit(); e != nil {
		return Selection{}, e
	}
	return s.fallback(), nil
}
