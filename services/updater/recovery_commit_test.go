package updater_test

import (
	"bytes"
	"errors"
	"os"
	"syscall"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/updater"
)

// Exercise the activation, health and quarantine checkpoints independently of
// Begin's high-water commit. Every case uses a fresh filesystem store and reopens
// it after the injected write failure; Snapshot on the poisoned writer is not
// evidence of what reached disk.
func TestRecoveryTransitionCommitFaultsReopen(t *testing.T) {
	for _, transition := range []string{"activation", "health", "quarantine"} {
		t.Run(transition, func(t *testing.T) {
			for _, point := range []string{"before_write", "before_file_sync", "before_rename", "after_rename", "after_directory_sync"} {
				t.Run(point, func(t *testing.T) {
					f := testutil.New(t)
					cfg := config(t, f)
					armed, hits := false, 0
					cfg.Fault = func(p string) error {
						if armed && p == point {
							hits++
							return syscall.ENOSPC
						}
						return nil
					}
					s, err := updater.Open(cfg)
					if err != nil {
						t.Fatal(err)
					}
					t.Cleanup(func() {
						if s != nil {
							if err := s.Close(); err != nil {
								t.Error(err)
							}
						}
					})
					first := stage(t, s, f, "healthy", 1)
					healthy(t, s, 100)
					candidate := stage(t, s, f, "candidate", 2)
					var boot updater.Selection
					if transition != "activation" {
						boot, err = s.Start(200)
						if err != nil || boot.Digest != candidate || !boot.Provisional {
							t.Fatalf("candidate did not start: %+v %v", boot, err)
						}
					}
					if transition == "quarantine" {
						if _, err = s.ReportFailure(boot.LaunchID, updater.StartupTrap); err != nil {
							t.Fatal(err)
						}
						boot, err = s.Start(201)
						if err != nil || boot.Digest != candidate || !boot.Provisional {
							t.Fatalf("threshold attempt did not start: %+v %v", boot, err)
						}
					}
					armed = true
					switch transition {
					case "activation":
						var selected updater.Selection
						selected, err = s.Start(200)
						if selected != (updater.Selection{}) {
							t.Fatalf("failed launch commit authorized a payload: %+v", selected)
						}
					case "health":
						err = s.MarkHealthy(boot.LaunchID, 210, true)
					case "quarantine":
						var selected updater.Selection
						selected, err = s.ReportFailure(boot.LaunchID, updater.StartupTrap)
						if selected != (updater.Selection{}) {
							t.Fatalf("failed quarantine commit returned recovery: %+v", selected)
						}
					}
					if !errors.Is(err, syscall.ENOSPC) || hits != 1 {
						t.Fatalf("expected one ENOSPC at %s, got hits=%d err=%v", point, hits, err)
					}
					if selected, err := s.Start(220); err == nil || selected != (updater.Selection{}) {
						t.Fatalf("uncertain writer authorized another launch: %+v %v", selected, err)
					}
					if err := s.Close(); err != nil {
						t.Fatal(err)
					}
					armed = false
					s, err = updater.Open(cfg)
					if err != nil {
						t.Fatal(err)
					}
					st := s.Snapshot()
					committed := point == "after_rename" || point == "after_directory_sync"
					if st.Version != 1 || st.Sequence != 2 || st.Download != nil || len(st.Candidates) != 2 {
						t.Fatalf("unrelated durable state changed: %+v", st)
					}
					wantHealthy, wantStaged, wantFailures := first, candidate, uint64(0)
					wantAttempt := transition != "activation" || committed
					wantQuarantine := ""
					if transition == "health" && committed {
						wantHealthy, wantStaged, wantAttempt = candidate, "", false
						if st.PreviousHealthy != first {
							t.Fatal("health promotion lost previous recovery target")
						}
					}
					if transition == "quarantine" {
						wantFailures = 1
						if committed {
							wantFailures, wantStaged, wantAttempt = 2, "", false
							wantQuarantine = string(updater.StartupTrap)
						}
					}
					if st.Healthy != wantHealthy || st.Staged != wantStaged || (st.Attempt != nil) != wantAttempt || st.Failures[candidate] != wantFailures || st.Quarantine[candidate] != wantQuarantine {
						t.Fatalf("partial recovery transition persisted: %+v", st)
					}
					if wantAttempt && (st.Attempt.Digest != candidate || st.Attempt.LaunchID == "") {
						t.Fatalf("persisted attempt lost candidate binding: %+v", st.Attempt)
					}
					if wantAttempt && transition != "activation" && st.Attempt.LaunchID != boot.LaunchID {
						t.Fatal("persisted attempt launch identity changed")
					}
					recovered, err := s.Start(230)
					if err != nil {
						t.Fatal(err)
					}
					wantSelected := wantHealthy
					wantProvisional := transition == "activation" && !committed
					if wantProvisional {
						wantSelected = candidate
					}
					if recovered.NativeFallback || recovered.Digest != wantSelected || recovered.Provisional != wantProvisional {
						t.Fatalf("wrong cold-start recovery: %+v", recovered)
					}
					payload, err := os.ReadFile(recovered.PayloadPath)
					wantPayload := []byte("guest healthy")
					if wantSelected == candidate {
						wantPayload = []byte("guest candidate")
					}
					if err != nil || !bytes.Equal(payload, wantPayload) {
						t.Fatalf("selected payload unavailable or changed: %q %v", payload, err)
					}
					after := s.Snapshot()
					if after.Failures[candidate] != wantFailures || after.Quarantine[candidate] != wantQuarantine {
						t.Fatal("unknown interruption invented a startup failure")
					}
					if wantAttempt && (after.Attempt != nil || after.LastRecovery != string(updater.UnknownInterruption)) {
						t.Fatal("interrupted attempt was not durably classified")
					}
					if transition != "activation" && s.MarkHealthy(boot.LaunchID, 240, true) == nil {
						t.Fatal("retired pre-interruption launch accepted health")
					}
					old := f.Manifest(t, []byte("guest healthy"), "healthy")
					stale := f.Assignment(t, old.Manifest, 2, 10000)
					if s.Begin(stale, old, 240) == nil || s.Snapshot().Sequence != 2 {
						t.Fatal("reopen lowered assignment replay protection")
					}
					if wantQuarantine != "" {
						m := f.Manifest(t, []byte("guest candidate"), "candidate")
						a := f.Assignment(t, m.Manifest, 3, 10000)
						if s.Begin(a, m, 240) == nil || s.Snapshot().Sequence != 2 {
							t.Fatal("reopened quarantine allowed a newer reassignment")
						}
						rollback := f.Assignment(t, old.Manifest, 3, 10000)
						if err := s.Begin(rollback, old, 240); err != nil {
							t.Fatal(err)
						}
						if err := s.Resume(bytes.NewReader([]byte("guest healthy")), 240); err != nil {
							t.Fatal(err)
						}
						if selected := healthy(t, s, 250); selected.Digest != first {
							t.Fatal("new rollback assignment selected different content")
						}
						if err := s.Close(); err != nil {
							t.Fatal(err)
						}
						s, err = updater.Open(cfg)
						if err != nil {
							t.Fatal(err)
						}
						if st := s.Snapshot(); st.Sequence != 3 || st.Healthy != first || st.Quarantine[candidate] != wantQuarantine {
							t.Fatalf("rollback reopen lost replay/quarantine state: %+v", st)
						}
						if s.Begin(rollback, old, 270) == nil {
							t.Fatal("reopened rollback accepted the same sequence twice")
						}
					}
					t.Logf("transition=%s fault=%s committed=%t recovered=%s provisional=%t failures=%d quarantine=%q replay_rejected=true", transition, point, committed, wantSelected, wantProvisional, wantFailures, wantQuarantine)
				})
			}
		})
	}
}
