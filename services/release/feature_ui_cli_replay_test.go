package release

import (
	"bytes"
	"context"
	"crypto/rand"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

// TestFeatureUICLIOriginReplay uses retained public F10 release inputs and the
// ordinary CLI and service executables. It never loads a private key from disk.
func TestFeatureUICLIOriginReplay(t *testing.T) {
	fixtures := os.Getenv("MIXER_F10_REPLAY_INPUTS")
	if fixtures == "" {
		t.Skip("set MIXER_F10_REPLAY_INPUTS to the retained F10 public/android directory")
	}
	cli, originBinary := os.Getenv("MIXER_F10_REPLAY_CLI"), os.Getenv("MIXER_F10_REPLAY_ORIGIN")
	if cli == "" || originBinary == "" {
		t.Fatal("set MIXER_F10_REPLAY_CLI and MIXER_F10_REPLAY_ORIGIN to the built executable paths")
	}
	var host protocol.Host
	readReplayJSON(t, fixtures, "host.json", &host)
	var roots []protocol.Root
	rootsJSON := readReplayJSON(t, fixtures, "roots.json", &roots)
	pin := protocol.FeatureUIEnrollment{
		Scope: host.Scope, Fingerprint: host.Runtime, DescriptorJSON: readReplayFile(t, fixtures, "identity.json"),
		TrustRootsJSON: rootsJSON,
		StoragePolicy:  protocol.ReadOnlyStorage{Namespace: "material_test", Operations: []string{"get"}},
	}
	historical, err := protocol.NewFeatureUIV3(pin)
	if err != nil {
		t.Fatal(err)
	}
	for i, phase := range []struct {
		name string
		size int
		hash string
	}{
		{"prior", 2002, "39ccd91d0e129de88fd617670caacf02c68d93d406747efc8f70318643437433"},
		{"exact", 14503, "fb225d5722eda20c7591a9e7bb112d560924cedf9da17106b57eeb049f94d3b9"},
		{"rollback", 2002, "39ccd91d0e129de88fd617670caacf02c68d93d406747efc8f70318643437433"},
	} {
		t.Run("historical-"+phase.name, func(t *testing.T) {
			dir := filepath.Join(fixtures, phase.name)
			var m protocol.SignedManifestV3
			readReplayJSON(t, dir, "signed-manifest.json", &m)
			var a protocol.SignedAssignmentV3
			readReplayJSON(t, dir, "assignment.json", &a)
			payload := readReplayFile(t, dir, "payload.wasm")
			if a.Assignment.Sequence != uint64(i+1) || len(payload) != phase.size || protocol.Hash(payload) != phase.hash {
				t.Fatal("retained sequence or exact payload changed")
			}
			at := a.Assignment.CreatedAtUnix
			if err := historical.VerifyManifest(m, payload, at); err != nil {
				t.Fatal(err)
			}
			if err := historical.VerifyAssignment(a, m, "beta", uint64(i), at); err != nil {
				t.Fatal(err)
			}
			t.Logf("sequence=%d bytes=%d sha256=%s", a.Assignment.Sequence, len(payload), phase.hash)
		})
	}
	if t.Failed() {
		return
	}
	f := testutil.New(t)
	now := uint64(time.Now().Unix())
	for i := range f.Roots {
		f.Roots[i].Scope = pin.Scope
		f.Roots[i].NotBeforeUnix = now - 30
		f.Roots[i].NotAfterUnix = now + 600
	}
	pin = testutil.RebindFeatureUIRoots(t, pin, f.Roots)
	f.Host = host
	f.Host.Runtime = pin.Fingerprint

	addr := replayAddress(t)
	scope := host.Scope
	token := rand.Text()
	cfg := Config{
		DeveloperMode: true, Listen: addr, DataDirectory: t.TempDir(), FeatureUI: &pin,
		Hosts: []protocol.Host{}, Roots: []protocol.Root{},
		Tokens: []Token{{SHA256: protocol.Hash([]byte(token)), Role: "publisher",
			Organization: scope.Organization, Project: scope.Project, Actor: "f10-replay"}},
	}
	configPath := filepath.Join(t.TempDir(), "origin.json")
	writeReplayFile(t, configPath, testutil.JSON(t, cfg))
	origin := "http://" + addr
	updateURL := origin + v2OfferPath(f, 3)
	client := &http.Client{Timeout: 2 * time.Second, Transport: &http.Transport{}}
	t.Cleanup(client.CloseIdleConnections)
	startReplayOrigin(t, originBinary, configPath, client, updateURL)

	var priorDigest string
	for _, phase := range []string{"prior", "exact", "rollback"} {
		if !t.Run("cli-"+phase, func(t *testing.T) {
			dir := filepath.Join(fixtures, phase)
			payload := readReplayFile(t, dir, "payload.wasm")
			var source protocol.SignedManifestV3
			readReplayJSON(t, dir, "signed-manifest.json", &source)
			m := source.Manifest
			m.Runtime, m.KeyID, m.CreatedAtUnix = pin.Fingerprint, f.Roots[0].KeyID, now
			signed := testutil.SignFeatureUIManifest(t, m, f.ArtifactKey)
			digest, err := protocol.ManifestDigestV3(m)
			if err != nil {
				t.Fatal(err)
			}
			if phase == "prior" {
				priorDigest = digest
			}
			var selection protocol.SignedAssignmentV3
			readReplayJSON(t, dir, "assignment.json", &selection)
			a := selection.Assignment
			a.Runtime, a.ArtifactSHA256, a.KeyID, a.CreatedAtUnix = pin.Fingerprint, digest, f.Roots[1].KeyID, now
			assignment, err := protocol.SignAssignmentV3(a, f.AssignmentKey)
			if err != nil {
				t.Fatal(err)
			}
			candidate := t.TempDir()
			assignmentPath := filepath.Join(candidate, "assignment.json")
			writeReplayFile(t, assignmentPath, testutil.JSON(t, assignment))
			args := []string{"update", "publish", candidate, "--rollout", "100"}
			if phase == "rollback" {
				if digest != priorDigest {
					t.Fatal("rollback did not target the published predecessor")
				}
				args = []string{"update", "rollback", digest, "--reason", "local F10 replay"}
			} else {
				writeReplayFile(t, filepath.Join(candidate, "signed-manifest.json"), testutil.JSON(t, signed))
				writeReplayFile(t, filepath.Join(candidate, "payload.wasm"), payload)
			}
			args = append(args, "--organization", scope.Organization, "--project", scope.Project,
				"--channel", "beta", "--assignment", assignmentPath)
			ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
			defer cancel()
			cmd := exec.CommandContext(ctx, cli, args...)
			cmd.WaitDelay = 2 * time.Second
			cmd.Env = append(os.Environ(), "MIXER_RELEASE_ORIGIN="+origin, "MIXER_RELEASE_TOKEN="+token)
			if out, err := cmd.CombinedOutput(); err != nil {
				t.Fatalf("ordinary CLI %s: %v\n%s", phase, err, out)
			}

			var offer struct {
				Assignment protocol.SignedAssignmentV3 `json:"signed_assignment"`
				URL        string                      `json:"artifact_url"`
			}
			readReplayResponse(t, client, updateURL, &offer)
			wantPath := fmt.Sprintf("/v3/artifacts/%s?organization=%s&project=%s", digest, scope.Organization, scope.Project)
			if !reflect.DeepEqual(offer.Assignment, assignment) || offer.URL != wantPath {
				t.Fatal("delivered assignment or artifact URL differs from the CLI selection")
			}
			var artifact ArtifactV3
			readReplayResponse(t, client, origin+offer.URL, &artifact)
			if !reflect.DeepEqual(artifact.SignedManifest, signed) || !bytes.Equal(artifact.Payload, payload) {
				t.Fatal("delivered signed manifest or payload differs from the CLI input")
			}
			t.Logf("sequence=%d bytes=%d sha256=%s digest=%s", a.Sequence, len(payload), protocol.Hash(payload), digest)
		}) {
			break
		}
	}
}

func readReplayFile(t *testing.T, dir, name string) []byte {
	t.Helper()
	b, err := os.ReadFile(filepath.Join(dir, name))
	if err != nil {
		t.Fatal(err)
	}
	return b
}

func readReplayJSON(t *testing.T, dir, name string, dest any) []byte {
	t.Helper()
	b := readReplayFile(t, dir, name)
	if err := protocol.DecodeJSON(b, dest); err != nil {
		t.Fatalf("%s: %v", name, err)
	}
	return b
}

func writeReplayFile(t *testing.T, path string, b []byte) {
	t.Helper()
	if err := os.WriteFile(path, b, 0600); err != nil {
		t.Fatal(err)
	}
}

func readReplayResponse(t *testing.T, client *http.Client, url string, dest any) {
	t.Helper()
	res, err := client.Get(url)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		t.Fatalf("GET %s: HTTP %d", url, res.StatusCode)
	}
	b, err := io.ReadAll(io.LimitReader(res.Body, maxV3ArtifactBody+1))
	if err != nil || len(b) > maxV3ArtifactBody {
		t.Fatalf("invalid response body: %v", err)
	}
	if err := protocol.DecodeJSON(b, dest); err != nil {
		t.Fatal(err)
	}
}

func replayAddress(t *testing.T) string {
	t.Helper()
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := l.Addr().String()
	if err := l.Close(); err != nil {
		t.Fatal(err)
	}
	return addr
}

func startReplayOrigin(t *testing.T, binary, config string, client *http.Client, readyURL string) {
	t.Helper()
	var log bytes.Buffer
	cmd := exec.Command(binary)
	cmd.Env = append(os.Environ(), "MIXER_SERVICE_CONFIG="+config)
	cmd.Stderr = &log
	cmd.WaitDelay = 2 * time.Second
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()
	t.Cleanup(func() {
		select {
		case err := <-done:
			t.Errorf("origin exited before cleanup: %v\n%s", err, log.String())
		default:
			_ = cmd.Process.Signal(os.Interrupt)
			select {
			case err := <-done:
				if err != nil {
					t.Errorf("origin shutdown: %v\n%s", err, log.String())
				} else {
					t.Log("origin shut down and reaped")
				}
			case <-time.After(5 * time.Second):
				_ = cmd.Process.Kill()
				select {
				case <-done:
					t.Error("origin required forced shutdown")
				case <-time.After(3 * time.Second):
					t.Error("origin exit was not observed after forced shutdown")
				}
			}
		}
	})
	until := time.Now().Add(5 * time.Second)
	for time.Now().Before(until) {
		res, err := client.Get(readyURL)
		if err == nil {
			res.Body.Close()
			if res.StatusCode == 204 && res.Header.Get("X-Request-ID") != "" {
				return
			}
		}
		time.Sleep(25 * time.Millisecond)
	}
	t.Fatal("origin did not accept the empty update check")
}
