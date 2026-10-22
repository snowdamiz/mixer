package updater_test

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/updater"
)

func config(t *testing.T, f testutil.Fixture) updater.Config {
	return updater.Config{Directory: t.TempDir(), Host: f.Host, Roots: f.Roots, Channel: "beta", Installation: "installation-1", FailureThreshold: 2, ObservationSeconds: 10}
}
func stage(t *testing.T, s *updater.Store, f testutil.Fixture, id string, seq uint64) string {
	t.Helper()
	payload := []byte("guest " + id)
	m := f.Manifest(t, payload, id)
	a := f.Assignment(t, m.Manifest, seq, 10000)
	if e := s.Begin(a, m, 100); e != nil {
		t.Fatal(e)
	}
	if e := s.Resume(bytes.NewReader(payload), 100); e != nil {
		t.Fatal(e)
	}
	return a.Assignment.ArtifactSHA256
}
func healthy(t *testing.T, s *updater.Store, now uint64) updater.Selection {
	t.Helper()
	sel, e := s.Start(now)
	if e != nil || !sel.Provisional {
		t.Fatalf("provisional: %+v %v", sel, e)
	}
	if e = s.MarkHealthy(sel.LaunchID, now+10, true); e != nil {
		t.Fatal(e)
	}
	return sel
}

func TestColdStartHealthQuarantineAndRollback(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s, e := updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	sel, e := s.Start(100)
	if e != nil || !sel.NativeFallback {
		t.Fatal("missing native fallback", e)
	}
	first := stage(t, s, f, "r1", 1)
	boot, e := s.Start(100)
	if e != nil {
		t.Fatal(e)
	}
	if s.MarkHealthy(boot.LaunchID, 109, true) == nil || s.MarkHealthy(boot.LaunchID, 99, true) == nil || s.MarkHealthy(boot.LaunchID, 110, false) == nil {
		t.Fatal("accepted incomplete health evidence")
	}
	if e = s.MarkHealthy(boot.LaunchID, 110, true); e != nil {
		t.Fatal(e)
	}
	second := stage(t, s, f, "r2", 2)
	for attempt := 0; attempt < 2; attempt++ {
		boot, e = s.Start(120 + uint64(attempt))
		if e != nil || boot.Digest != second {
			t.Fatal("candidate not selected", e)
		}
		recovery, e := s.ReportFailure(boot.LaunchID, updater.StartupTrap)
		if e != nil || recovery.Digest != first {
			t.Fatal("healthy recovery missing", e)
		}
	}
	if s.Snapshot().Quarantine[second] != "startup_trap" {
		t.Fatal("candidate not quarantined")
	}
	boot, e = s.Start(130)
	if e != nil || boot.Digest != first || boot.Provisional {
		t.Fatal("quarantined candidate retried", e)
	}
	m := f.Manifest(t, []byte("guest r2"), "r2")
	a := f.Assignment(t, m.Manifest, 3, 10000)
	if s.Begin(a, m, 100) == nil {
		t.Fatal("quarantined package admitted at new seq")
	}
	old := f.Manifest(t, []byte("guest r1"), "r1")
	rollback := f.Assignment(t, old.Manifest, 4, 10000)
	if e = s.Begin(rollback, old, 100); e != nil {
		t.Fatal(e)
	}
	if e = s.Resume(strings.NewReader("guest r1"), 100); e != nil {
		t.Fatal(e)
	}
	healthy(t, s, 200)
	if s.Snapshot().Sequence != 4 {
		t.Fatal("rollback lowered replay sequence")
	}
}

func TestInterruptedLaunchClassificationAndOfflineHealthy(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s, e := updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	first := stage(t, s, f, "r1", 1)
	healthy(t, s, 100)
	second := stage(t, s, f, "r2", 2)
	_, e = s.Start(200)
	if e != nil {
		t.Fatal(e)
	}
	s.Close()
	s, e = updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	boot, e := s.Start(201)
	if e != nil || boot.Digest != first || boot.Provisional || len(s.Snapshot().Quarantine) > 0 || s.Snapshot().Failures[second] != 0 {
		t.Fatalf("unknown interruption incorrectly blamed guest: %+v %v", boot, e)
	}
	for _, reason := range []updater.Failure{updater.NativeCrash, updater.UserQuit, updater.UnknownInterruption} {
		boot, e = s.Start(210)
		if e != nil || boot.Digest != second {
			t.Fatal(e)
		}
		if _, e = s.ReportFailure(boot.LaunchID, reason); e != nil {
			t.Fatal(e)
		}
	}
	if len(s.Snapshot().Quarantine) > 0 || s.Snapshot().Failures[second] != 0 {
		t.Fatal("non-guest interruption quarantined")
	}
	if _, e = updater.Open(cfg); e == nil {
		t.Fatal("concurrent process lock not held")
	}
	s.Close()
	cfg.Roots[0].Revoked = true
	s, e = updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	boot, e = s.Start(300)
	if e != nil || boot.Digest != first || s.Snapshot().Quarantine[second] != "signing_authority_denied" {
		t.Fatal("revoked candidate activated or healthy cache blocked", e)
	}
}

func TestStagedAssignmentRevocationRetainsHealthy(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s, e := updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	first := stage(t, s, f, "healthy", 1)
	healthy(t, s, 100)
	candidate := stage(t, s, f, "candidate", 2)
	s.Close()
	cfg.Roots[1].Revoked = true
	s, e = updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	sel, e := s.Start(200)
	if e != nil || sel.Digest != first || s.Snapshot().Quarantine[candidate] != "signing_authority_denied" {
		t.Fatal("revoked assignment activated", e)
	}
}

type interrupted struct {
	data []byte
	used bool
}

func (r *interrupted) Read(p []byte) (int, error) {
	if r.used {
		return 0, errors.New("network interrupted")
	}
	r.used = true
	n := copy(p, r.data)
	return n, errors.New("network interrupted")
}
func TestDownloadResumeCancellationBoundsAndTamper(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s, e := updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	payload := []byte("guest payload to resume")
	m := f.Manifest(t, payload, "resume")
	a := f.Assignment(t, m.Manifest, 1, 10000)
	if e = s.Begin(a, m, 100); e != nil {
		t.Fatal(e)
	}
	if e = s.Resume(&interrupted{data: payload[:5]}, 100); e == nil {
		t.Fatal("network interruption hidden")
	}
	offset, e := s.Offset()
	if e != nil || offset != 5 {
		t.Fatal("offset lost", offset, e)
	}
	s.Close()
	s, e = updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	if e = s.Resume(bytes.NewReader(payload[5:]), 100); e != nil {
		t.Fatal(e)
	}
	if s.Snapshot().Staged != a.Assignment.ArtifactSHA256 {
		t.Fatal("resume did not stage")
	}
	m = f.Manifest(t, []byte("123"), "over")
	a = f.Assignment(t, m.Manifest, 2, 10000)
	if e = s.Begin(a, m, 100); e != nil {
		t.Fatal(e)
	}
	if s.Resume(strings.NewReader("1234"), 100) == nil {
		t.Fatal("accepted size overrun")
	}
	if e = s.CancelDownload(); e != nil {
		t.Fatal(e)
	}
	if s.Begin(a, m, 100) == nil {
		t.Fatal("cancel erased replay defense")
	}
	a = f.Assignment(t, m.Manifest, 3, 10000)
	if e = s.Begin(a, m, 100); e != nil {
		t.Fatal(e)
	}
	if s.Resume(strings.NewReader("456"), 100) == nil {
		t.Fatal("accepted digest tamper")
	}
	if s.Snapshot().Staged == a.Assignment.ArtifactSHA256 {
		t.Fatal("tamper selected")
	}
}

func TestCrashCommitFaultMatrix(t *testing.T) {
	for _, point := range []string{"before_write", "before_file_sync", "before_rename", "after_rename", "after_directory_sync"} {
		t.Run(point, func(t *testing.T) {
			f := testutil.New(t)
			cfg := config(t, f)
			armed := false
			cfg.Fault = func(p string) error {
				if armed && p == point {
					return syscall.ENOSPC
				}
				return nil
			}
			s, e := updater.Open(cfg)
			if e != nil {
				t.Fatal(e)
			}
			m := f.Manifest(t, []byte("guest"), "r1")
			a := f.Assignment(t, m.Manifest, 1, 10000)
			armed = true
			if s.Begin(a, m, 100) == nil {
				t.Fatal("fault not exercised")
			}
			if s.Begin(a, m, 100) == nil {
				t.Fatal("uncertain store still writable")
			}
			s.Close()
			armed = false
			s, e = updater.Open(cfg)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			st := s.Snapshot()
			want := uint64(0)
			if point == "after_rename" || point == "after_directory_sync" {
				want = 1
			}
			if st.Sequence != want {
				t.Fatalf("atomic state want sequence %d got %d", want, st.Sequence)
			}
			boot, e := s.Start(100)
			if e != nil || !boot.NativeFallback {
				t.Fatal("unverified candidate activated", e)
			}
		})
	}
}

func TestPayloadFaultsAndEvictionRecovery(t *testing.T) {
	for _, point := range []string{"before_payload_write", "before_payload_sync", "before_payload_rename"} {
		t.Run(point, func(t *testing.T) {
			f := testutil.New(t)
			cfg := config(t, f)
			armed := false
			cfg.Fault = func(p string) error {
				if armed && p == point {
					return syscall.ENOSPC
				}
				return nil
			}
			s, e := updater.Open(cfg)
			if e != nil {
				t.Fatal(e)
			}
			m := f.Manifest(t, []byte("guest"), "r1")
			a := f.Assignment(t, m.Manifest, 1, 10000)
			if e = s.Begin(a, m, 100); e != nil {
				t.Fatal(e)
			}
			armed = true
			if s.Resume(strings.NewReader("guest"), 100) == nil {
				t.Fatal("fault not exercised")
			}
			boot, e := s.Start(100)
			if e != nil || !boot.NativeFallback {
				t.Fatal("unverified bytes activated", e)
			}
			s.Close()
			armed = false
			s, e = updater.Open(cfg)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			offset, e := s.Offset()
			if e != nil {
				t.Fatal(e)
			}
			if e = s.Resume(strings.NewReader("guest"[offset:]), 100); e != nil {
				t.Fatal(e)
			}
			healthy(t, s, 100)
			if e = os.Remove(filepath.Join(cfg.Directory, a.Assignment.ArtifactSHA256+".payload")); e != nil {
				t.Fatal(e)
			}
			boot, e = s.Start(200)
			if e != nil || !boot.NativeFallback {
				t.Fatal("evicted cache prevented fallback", e)
			}
		})
	}
}

func TestBoundedCacheCorruptionDiskAndHostChanges(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s, e := updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	for i := 1; i <= 5; i++ {
		stage(t, s, f, fmt.Sprintf("release-%d", i), uint64(i))
		healthy(t, s, uint64(i*20))
	}
	if len(s.Snapshot().Candidates) != 2 {
		t.Fatal("healthy cache not bounded")
	}
	third := stage(t, s, f, "candidate", 6)
	if e = os.WriteFile(filepath.Join(cfg.Directory, third+".payload"), []byte("corrupt"), 0600); e != nil {
		t.Fatal(e)
	}
	boot, e := s.Start(200)
	if e != nil || boot.NativeFallback || boot.Provisional {
		t.Fatal("corrupt candidate did not restore healthy", e)
	}
	s.Close()
	changed := cfg
	changed.Host.StateVersion++
	if _, e = updater.Open(changed); e == nil {
		t.Fatal("changed state contract reused recovery store")
	}
	cfg.ReserveDiskBytes = math.MaxUint64
	s, e = updater.Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	m := f.Manifest(t, []byte("reserve"), "reserve")
	a := f.Assignment(t, m.Manifest, 7, 10000)
	if s.Begin(a, m, 100) == nil {
		t.Fatal("disk reserve ignored")
	}
}

func TestCachedSignatureAndBindingTamperFailClosed(t *testing.T) {
	for _, change := range []string{"signature", "assignment", "identity"} {
		t.Run(change, func(t *testing.T) {
			f := testutil.New(t)
			cfg := config(t, f)
			s, e := updater.Open(cfg)
			if e != nil {
				t.Fatal(e)
			}
			d := stage(t, s, f, "healthy", 1)
			healthy(t, s, 100)
			st := s.Snapshot()
			s.Close()
			c := st.Candidates[d]
			switch change {
			case "signature":
				c.Manifest.Signature[0] ^= 1
			case "assignment":
				c.Assignment.Assignment.ReleaseID = "different"
			case "identity":
				c.Digest = strings.Repeat("0", 64)
			}
			st.Candidates[d] = c
			b, e := json.Marshal(st)
			if e != nil {
				t.Fatal(e)
			}
			if e = os.WriteFile(filepath.Join(cfg.Directory, "state.json"), b, 0600); e != nil {
				t.Fatal(e)
			}
			s, e = updater.Open(cfg)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			sel, e := s.Start(200)
			if e != nil || !sel.NativeFallback {
				t.Fatal("tampered cache trusted", e)
			}
		})
	}
}
