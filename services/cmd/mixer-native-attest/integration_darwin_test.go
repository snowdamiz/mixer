//go:build darwin && cgo

package main

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"encoding/pem"
	"errors"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestMain(m *testing.M) {
	if len(os.Args) > 1 && (os.Args[1] == "sign" || os.Args[1] == "verify" || os.Args[1] == "attach") {
		main()
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func runAttestation(action, origin, query, state, key, token string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	process := exec.CommandContext(ctx, os.Args[0], action, "-origin", origin,
		"-selection", query, "-state", state, "-key", key)
	process.Stdin = strings.NewReader(token + "\n")
	// Disable the race runtime's one-second delay at exit in child processes.
	process.Env = append(os.Environ(), "GORACE=atexit_sleep_ms=0")
	output, err := process.CombinedOutput()
	if ctx.Err() != nil {
		return "", ctx.Err()
	}
	return strings.TrimSpace(string(output)), err
}

func TestFixedOriginAndACLs(t *testing.T) {
	sel := fixtureSelection()
	var firstSession, restartedSession [32]byte
	rand.Read(firstSession[:])
	rand.Read(restartedSession[:])
	session := base64.RawURLEncoding.EncodeToString(firstSession[:])
	newSession := base64.RawURLEncoding.EncodeToString(restartedSession[:])

	dir := t.TempDir()
	state := filepath.Join(dir, "state")
	if err := os.Mkdir(state, 0700); err != nil {
		t.Fatal(err)
	}
	privatePath, publicPath := writeDevelopmentKeys(t, dir)
	first := newBuildFixture(t, sel, session, "127.0.0.1:0", nil, nil)
	cmd := func(action, origin, query, key, token string) (string, error) {
		return runAttestation(action, origin, query, state, key, token)
	}
	refuse := func(want, action, origin, query, key, token string) {
		t.Helper()
		out, err := cmd(action, origin, query, key, token)
		var exit *exec.ExitError
		if !errors.As(err, &exit) || exit.ExitCode() != 1 || !strings.Contains(out, want) {
			t.Fatalf("expected exit 1 with %q, got %v, %q", want, err, out)
		}
	}
	query := sel.query().Encode()
	setACL(t, state, 0700, "everyone allow list,search,add_file,delete_child")
	refuse("unsafe attestation directory ACL: extended ACL present", "sign", first.origin, query, privatePath, session)
	if first.requests.Load() != 0 {
		t.Fatal("contacted service with an unsafe attestation directory")
	}
	clearACL(t, state)
	setACL(t, privatePath, 0600, "everyone allow read")
	refuse("unsafe local development key ACL: extended ACL present", "sign", first.origin, query, privatePath, session)
	entries, err := os.ReadDir(state)
	if err != nil || len(entries) != 0 {
		t.Fatalf("expected empty state after ACL refusals, got %v, %v", entries, err)
	}
	clearACL(t, privatePath)

	name, err := cmd("sign", first.origin, query, privatePath, session)
	if err != nil || !strings.HasSuffix(name, ".json") || filepath.Base(name) != name {
		t.Fatalf("sign failed: %v, %q", err, name)
	}
	refuse("build already attested", "sign", first.origin, query, privatePath, session)
	first.close()
	restarted := newBuildFixture(t, sel, newSession, strings.TrimPrefix(first.origin, "http://"), nil, nil)
	refuse("HTTP 401", "verify", restarted.origin, query, publicPath, session)
	got, err := cmd("verify", restarted.origin, query, publicPath, newSession)
	if err != nil || got != name || restarted.requests.Load() != 5 {
		t.Fatalf("verification after restart failed: %v, %q, %d requests", err, got, restarted.requests.Load())
	}

	other := newBuildFixture(t, sel, newSession, "127.0.0.1:0", nil, nil)
	refuse("requires the signed Phoenix origin "+strconv.Quote(first.origin),
		"verify", other.origin, query, publicPath, newSession)
	if other.requests.Load() != 0 {
		t.Fatal("sent a request to the origin with the wrong port")
	}
	setACL(t, state, 0700, "everyone allow list,search,add_file,delete_child")
	refuse("unsafe attestation directory ACL: extended ACL present",
		"verify", restarted.origin, query, publicPath, newSession)
	refuse("unsafe attestation directory ACL: extended ACL present",
		"attach", restarted.origin, query, publicPath, newSession)
	clearACL(t, state)
	setACL(t, publicPath, 0600, "everyone allow write")
	refuse("unsafe local development key ACL: extended ACL present",
		"verify", restarted.origin, query, publicPath, newSession)
	refuse("unsafe local development key ACL: extended ACL present",
		"attach", restarted.origin, query, publicPath, newSession)
	clearACL(t, publicPath)
	path := filepath.Join(state, name)
	setACL(t, path, 0400, "everyone allow write")
	refuse("unsafe attestation file ACL: extended ACL present",
		"verify", restarted.origin, query, publicPath, newSession)
	refuse("unsafe attestation file ACL: extended ACL present",
		"attach", restarted.origin, query, publicPath, newSession)
	clearACL(t, path)
	if restarted.requests.Load() != 5 {
		t.Fatal("verification contacted service with unsafe local files")
	}

	restarted.corrupt.Store(true)
	refuse("byte digest mismatch", "verify", restarted.origin, query, publicPath, newSession)
	restarted.corrupt.Store(false)
	got, err = cmd("verify", restarted.origin, query, publicPath, newSession)
	if err != nil || got != name {
		t.Fatalf("verification after removing unsafe ACLs failed: %v, %q", err, got)
	}
}

func TestConcurrentAttestationsPublishOneEnvelope(t *testing.T) {
	sel := fixtureSelection()
	query := sel.query().Encode()
	var rawSession [32]byte
	rand.Read(rawSession[:])
	session := base64.RawURLEncoding.EncodeToString(rawSession[:])
	state := filepath.Join(t.TempDir(), "state")
	if err := os.Mkdir(state, 0700); err != nil {
		t.Fatal(err)
	}

	var arrivals atomic.Int32
	bothObserving := make(chan struct{})
	fixture := newBuildFixture(t, sel, session, "127.0.0.1:0", func(ctx context.Context) bool {
		// Each process checks the state directory before asking for build detail.
		if arrivals.Add(1) == 2 {
			close(bothObserving)
		}
		select {
		case <-bothObserving:
			return true
		case <-ctx.Done():
			return false
		}
	}, nil)

	type result struct {
		output, publicKey string
		err               error
	}
	var keys [2]struct{ private, public string }
	for i := range keys {
		keys[i].private, keys[i].public = writeDevelopmentKeys(t, t.TempDir())
	}
	results := make(chan result, 2)
	for _, key := range keys {
		go func() {
			output, err := runAttestation("sign", fixture.origin, query, state, key.private, session)
			results <- result{output, key.public, err}
		}()
	}
	winner, loser := <-results, <-results
	if winner.err != nil {
		winner, loser = loser, winner
	}
	var exit *exec.ExitError
	if winner.err != nil || !errors.As(loser.err, &exit) || exit.ExitCode() != 1 ||
		loser.output != "build already attested" || fixture.requests.Load() != 8 {
		t.Fatalf("expected one winner after two complete build reads, got %q (%v), %q (%v), %d reads",
			winner.output, winner.err, loser.output, loser.err, fixture.requests.Load())
	}
	entries, err := os.ReadDir(state)
	if err != nil || len(entries) != 1 || entries[0].Name() != winner.output {
		t.Fatalf("expected only the published envelope, got entries %v, error %v", entries, err)
	}
	path := filepath.Join(state, winner.output)
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	got, err := runAttestation("verify", fixture.origin, query, state, winner.publicKey, session)
	if err != nil || got != winner.output || fixture.requests.Load() != 12 {
		t.Fatalf("winner's pinned key did not verify: %q, %v, %d reads", got, err, fixture.requests.Load())
	}
	got, err = runAttestation("verify", fixture.origin, query, state, loser.publicKey, session)
	if !errors.As(err, &exit) || exit.ExitCode() != 1 || got != "attestation signature failed" ||
		fixture.requests.Load() != 12 {
		t.Fatalf("expected loser key refusal before HTTP, got %q, %v, %d reads", got, err, fixture.requests.Load())
	}
	after, err := os.ReadFile(path)
	if err != nil || !bytes.Equal(before, after) {
		t.Fatalf("verification changed the winning envelope: %v", err)
	}
}

func TestCompletedOperationRequiredAndLegacyVerification(t *testing.T) {
	sel := fixtureSelection()
	session := base64.RawURLEncoding.EncodeToString(make([]byte, 32))
	dir := t.TempDir()
	state := filepath.Join(dir, "state")
	if err := os.Mkdir(state, 0700); err != nil {
		t.Fatal(err)
	}
	privatePath, publicPath := writeDevelopmentKeys(t, dir)
	fixture := newBuildFixture(t, sel, session, "127.0.0.1:0", nil, nil)
	call := func(action, key string) (string, error) {
		return runAttestation(action, fixture.origin, sel.query().Encode(), state, key, session)
	}
	for _, operation := range []string{"", strings.Repeat("A", 64)} {
		fixture.operation.Store(operation)
		if output, err := call("sign", privatePath); err == nil ||
			output != "detail does not identify the completed worker operation" {
			t.Fatalf("signed without a valid operation: %v, %q", err, output)
		}
	}
	if fixture.requests.Load() != 2 {
		t.Fatal("read artifacts before validating the completed operation")
	}

	fixture.operation.Store(strings.Repeat("5", 64))
	name, err := call("sign", privatePath)
	if err != nil {
		t.Fatalf("sign: %v, %q", err, name)
	}
	fixture.operation.Store(strings.Repeat("6", 64))
	if output, err := call("verify", publicPath); err == nil || output != "attestation current build binding failed" {
		t.Fatalf("verified replacement operation with identical artifacts: %v, %q", err, output)
	}

	// Build a historical envelope with a test key and verify it against an old API.
	fixture.operation.Store("")
	source, err := newSource(fixture.origin, session)
	if err != nil {
		t.Fatal(err)
	}
	p, subjects, err := source.observe(sel, legacyProfile)
	if err != nil {
		t.Fatal(err)
	}
	private, _, der, err := readKey(privatePath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer clear(private)
	payload, err := json.Marshal(statement{legacyProfile, fixture.origin, sum(der), sel, p, subjects})
	if err != nil {
		t.Fatal(err)
	}
	legacy, err := json.Marshal(attestation{payload, ed25519.Sign(private, append([]byte(legacyProfile+"\x00"), payload...))})
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(state, name)
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, legacy, 0400); err != nil {
		t.Fatal(err)
	}
	for _, operation := range []string{"", strings.Repeat("6", 64)} {
		fixture.operation.Store(operation)
		if output, err := call("verify", publicPath); err != nil || output != name {
			t.Fatalf("historical verification failed: %v, %q", err, output)
		}
	}
	requests := fixture.requests.Load()
	if output, err := call("attach", publicPath); err == nil || output != "attachment requires a V2 attestation" ||
		fixture.requests.Load() != requests {
		t.Fatalf("expected offline V1 attach refusal: %v, %q", err, output)
	}
}

func TestExpectedStatementRefusesReplacementBeforePublication(t *testing.T) {
	sel := fixtureSelection()
	session := base64.RawURLEncoding.EncodeToString(make([]byte, 32))
	state := filepath.Join(t.TempDir(), "state")
	if err := os.Mkdir(state, 0700); err != nil {
		t.Fatal(err)
	}
	privatePath, publicPath := writeDevelopmentKeys(t, t.TempDir())
	fixture := newBuildFixture(t, sel, session, "127.0.0.1:0", nil, nil)
	s, err := newSource(fixture.origin, session)
	if err != nil {
		t.Fatal(err)
	}
	p, subjects, err := s.observe(sel, completionProfile)
	if err != nil {
		t.Fatal(err)
	}
	_, _, der, err := readKey(publicPath, false)
	if err != nil {
		t.Fatal(err)
	}
	expected := statement{completionProfile, fixture.origin, sum(der), sel, p, subjects}
	raw, err := json.MarshalIndent(expected, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	file := filepath.Join(t.TempDir(), "expected.json")
	if err := os.WriteFile(file, raw, 0400); err != nil {
		t.Fatal(err)
	}
	args := []string{"sign", "-origin", fixture.origin, "-selection", sel.query().Encode(),
		"-state", state, "-expected-statement", file}
	fixture.operation.Store(strings.Repeat("6", 64))
	// A mismatching build must be refused even when the signing key cannot be opened.
	_, err = run(append(args, "-key", privatePath+".missing"), strings.NewReader(session))
	entries, readErr := os.ReadDir(state)
	if err == nil || err.Error() != "observed build differs from expected attestation statement" ||
		readErr != nil || len(entries) != 0 || fixture.requests.Load() != 8 {
		t.Fatalf("replacement completion yielded err=%v, files=%v (read error %v), requests=%d",
			err, entries, readErr, fixture.requests.Load())
	}
	fixture.operation.Store(p.WorkerOperationID)
	name, err := run(append(args, "-key", privatePath), strings.NewReader(session))
	if err != nil {
		t.Fatalf("admitted completion did not sign: %v", err)
	}
	verified, err := run([]string{"verify", "-origin", fixture.origin, "-selection", sel.query().Encode(),
		"-state", state, "-key", publicPath}, strings.NewReader(session))
	if err != nil || verified != name {
		t.Fatalf("default verification of the guarded signature failed: %q, %v", verified, err)
	}
}

func writeDevelopmentKeys(t *testing.T, dir string) (string, string) {
	t.Helper()
	public, private, err := ed25519.GenerateKey(nil)
	if err != nil {
		t.Fatal(err)
	}
	defer clear(private)
	privateDER, err := x509.MarshalPKCS8PrivateKey(private)
	if err != nil {
		t.Fatal(err)
	}
	defer clear(privateDER)
	publicDER, err := x509.MarshalPKIXPublicKey(public)
	if err != nil {
		t.Fatal(err)
	}
	privatePath, publicPath := filepath.Join(dir, "private.pem"), filepath.Join(dir, "public.pem")
	for _, key := range []struct {
		path, kind string
		der        []byte
	}{
		{privatePath, "PRIVATE KEY", privateDER},
		{publicPath, "PUBLIC KEY", publicDER},
	} {
		pemBytes := pem.EncodeToMemory(&pem.Block{Type: key.kind, Bytes: key.der})
		err := os.WriteFile(key.path, pemBytes, 0600)
		clear(pemBytes)
		if err != nil {
			t.Fatal(err)
		}
	}
	return privatePath, publicPath
}

func setACL(t *testing.T, path string, mode os.FileMode, entry string) {
	t.Helper()
	if out, err := exec.Command("/bin/chmod", "+a", entry, path).CombinedOutput(); err != nil {
		t.Fatalf("add ACL: %v, %s", err, out)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != mode {
		t.Fatalf("expected unchanged POSIX mode %04o, got %04o", mode, info.Mode().Perm())
	}
}

func clearACL(t *testing.T, path string) {
	t.Helper()
	if out, err := exec.Command("/bin/chmod", "-N", path).CombinedOutput(); err != nil {
		t.Fatalf("remove ACL: %v, %s", err, out)
	}
}

type buildFixture struct {
	operation atomic.Value
	origin    string
	close     func()
	requests  atomic.Int32
	corrupt   atomic.Bool
}

func newBuildFixture(t *testing.T, sel selection, token, address string,
	beforeDetail func(context.Context) bool, attach http.HandlerFunc) *buildFixture {
	t.Helper()
	fixture := new(buildFixture)
	fixture.operation.Store(strings.Repeat("5", 64))
	binding := strings.Repeat("4", 64)
	complete := false
	build := observedBuild{selection: sel, State: "native_succeeded",
		CompletionPending: &complete, Revision: 2, Attempt: 1}
	products := make(map[string][]byte)
	add := func(kind string, contents []byte) artifact {
		descriptor := artifact{kind, sum(contents), int64(len(contents))}
		build.Artifacts = append(build.Artifacts, struct {
			artifact
			DownloadPath string `json:"downloadPath"`
		}{descriptor, artifactPath + kind + "?" + sel.query().Encode()})
		products[artifactPath+kind] = contents
		return descriptor
	}
	archive := func(kind string) artifact {
		var contents bytes.Buffer
		header, err := json.Marshal(map[string]any{"version": 1, "kind": kind, "binding": binding})
		if err != nil {
			t.Fatal(err)
		}
		contents.WriteString(archiveMagic)
		contents.Write(binary.BigEndian.AppendUint64(nil, uint64(len(header))))
		contents.Write(header)
		contents.WriteString("archive payload")
		return add(kind, contents.Bytes())
	}
	app := archive("unsigned_native_binary")
	symbols := archive("debug_symbols")
	inv, err := json.Marshal(inventory{1, "resource_inventory", app, symbols, binding})
	if err != nil {
		t.Fatal(err)
	}
	add("resource_inventory", inv)
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if attach != nil && r.Method == http.MethodPost {
			attach(w, r)
			return
		}
		fixture.requests.Add(1)
		cookie, err := r.Cookie("__Host-mixer-session")
		if err != nil || cookie.Value != token {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		if r.Method != http.MethodGet || r.URL.RawQuery != sel.query().Encode() {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		var data []byte
		contentType := "application/json; charset=utf-8"
		if r.URL.Path == detailPath || r.URL.Path == completionPath {
			if beforeDetail != nil && !beforeDetail(r.Context()) {
				return
			}
			current := build
			if r.URL.Path == completionPath {
				current.WorkerOperationID = fixture.operation.Load().(string)
			}
			data, err = json.Marshal(map[string]any{"build": current})
			if err != nil {
				t.Error(err)
				w.WriteHeader(http.StatusInternalServerError)
				return
			}
		} else {
			var ok bool
			data, ok = products[r.URL.Path]
			if !ok {
				w.WriteHeader(http.StatusNotFound)
				return
			}
			contentType = "application/octet-stream"
			if fixture.corrupt.Load() && r.URL.Path == artifactPath+app.Kind {
				data = bytes.Clone(data)
				data[len(data)-1] ^= 1
			}
		}
		w.Header().Set("Content-Type", contentType)
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("Content-Length", strconv.Itoa(len(data)))
		w.Write(data)
	})
	listener, err := net.Listen("tcp4", address)
	if err != nil {
		t.Fatal(err)
	}
	fixture.origin = "http://" + listener.Addr().String()
	server := &http.Server{Handler: handler, ReadHeaderTimeout: 5 * time.Second}
	terminal := make(chan error, 1)
	go func() { terminal <- server.Serve(listener) }()
	fixture.close = sync.OnceFunc(func() {
		if err := server.Close(); err != nil {
			t.Error(err)
		}
		if err := <-terminal; !errors.Is(err, http.ErrServerClosed) {
			t.Error(err)
		}
	})
	t.Cleanup(fixture.close)
	return fixture
}
