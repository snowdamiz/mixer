//go:build darwin && cgo

package main

import (
	"bytes"
	"encoding/base64"
	"errors"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
)

func TestAttachRetainedEnvelope(t *testing.T) {
	selection := fixtureSelection()
	query := selection.query().Encode()
	session := base64.RawURLEncoding.EncodeToString(make([]byte, 32))
	const bearer = "fixture.header.signature"
	const postPath = "/v3/orgs/local-org/projects/local-project/apps/local-app/builds/local-build/ios/native-development-attestation"
	postQuery := "build_definition_sha256=" + selection.BuildDefinitionSHA256 +
		"&source_sha256=" + selection.SourceSHA256 +
		"&toolchain_lock_sha256=" + selection.ToolchainLockSHA256

	dir := t.TempDir()
	state := filepath.Join(dir, "state")
	if err := os.Mkdir(state, 0700); err != nil {
		t.Fatal(err)
	}
	private, public := writeDevelopmentKeys(t, dir)
	_, otherPublic := writeDevelopmentKeys(t, t.TempDir())
	privateBytes, err := os.ReadFile(private)
	if err != nil {
		t.Fatal(err)
	}

	var retained atomic.Value
	var posts atomic.Int32
	fixture := newBuildFixture(t, selection, session, "127.0.0.1:0", nil,
		func(w http.ResponseWriter, r *http.Request) {
			body, err := io.ReadAll(r.Body)
			expected := retained.Load().([]byte)
			if err != nil || !bytes.Equal(body, expected) ||
				r.ContentLength != int64(len(expected)) || len(r.TransferEncoding) != 0 {
				t.Error("POST must send the exact retained envelope with Content-Length")
			}
			if r.URL.EscapedPath() != postPath || r.URL.RawQuery != postQuery {
				t.Errorf("unexpected attachment target %s", r.URL)
			}
			if len(r.Header.Values("Authorization")) != 1 || r.Header.Get("Authorization") != "Bearer "+bearer ||
				len(r.Header.Values("Cookie")) != 0 || r.Header.Get("Content-Type") != "application/json" ||
				r.Header.Get("Content-Encoding") != "" {
				t.Error("unexpected attachment request headers")
			}
			w.Header().Set("Cache-Control", "no-store")
			w.Header().Set("Content-Type", "application/json; charset=utf-8")
			if posts.Add(1) == 1 {
				http.SetCookie(w, &http.Cookie{Name: "ignored", Value: "fixture"})
				w.WriteHeader(http.StatusCreated)
				io.WriteString(w, `{"status":"attached"}`)
				return
			}
			io.WriteString(w, `{"status":"duplicate"}`)
		})

	name, err := runAttestation("sign", fixture.origin, query, state, private, session)
	if err != nil {
		t.Fatalf("sign failed: %v, %q", err, name)
	}
	path := filepath.Join(state, name)
	expected, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	before, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	retained.Store(expected)

	for _, want := range []string{"attached", "duplicate"} {
		out, err := runAttestation("attach", fixture.origin, query, state, public, bearer)
		if err != nil || out != want {
			t.Fatalf("attach: want %q, got %q (%v)", want, out, err)
		}
	}

	other := newBuildFixture(t, selection, session, "127.0.0.1:0", nil, nil)
	for _, check := range []struct{ name, origin, query, key, token, want string }{
		{"wrong origin", other.origin, query, public, bearer, "requires the signed Phoenix origin"},
		{"different lock pin", fixture.origin, strings.Replace(query, selection.ToolchainLockSHA256, strings.Repeat("0", 64), 1), public, bearer, "attestation selection does not match"},
		{"different key", fixture.origin, query, otherPublic, bearer, "attestation signature failed"},
		{"private key", fixture.origin, query, private, bearer, "expected one local Ed25519 key"},
		{"unsafe token", fixture.origin, query, public, "bad\ntoken", "expected a Mixer bearer token"},
		{"oversized token", fixture.origin, query, public, strings.Repeat("x", 4090), "expected a Mixer bearer token"},
		{"duplicate lock pin", fixture.origin, query + "&toolchain_lock_sha256=" + selection.ToolchainLockSHA256, public, bearer, "expected one exact iOS build selection"},
		{"uppercase lock pin", fixture.origin, strings.Replace(query, selection.ToolchainLockSHA256, strings.Repeat("A", 64), 1), public, bearer, "invalid build pin"},
	} {
		t.Run(check.name, func(t *testing.T) {
			out, err := runAttestation("attach", check.origin, check.query, state, check.key, check.token)
			var exit *exec.ExitError
			if !errors.As(err, &exit) || exit.ExitCode() != 1 || !strings.Contains(out, check.want) {
				t.Fatalf("want exit 1 with %q, got %q (%v)", check.want, out, err)
			}
		})
	}
	if posts.Load() != 2 || fixture.requests.Load() != 4 || other.requests.Load() != 0 {
		t.Fatal("attach performed extra reads, posts, or sent a request to the wrong origin")
	}
	after, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if !os.SameFile(before, after) || before.Mode() != after.Mode() || !before.ModTime().Equal(after.ModTime()) {
		t.Fatal("attach changed retained envelope metadata")
	}
	for file, want := range map[string][]byte{private: privateBytes, path: expected} {
		if got, err := os.ReadFile(file); err != nil || !bytes.Equal(got, want) {
			t.Fatalf("attach changed %s: %v", filepath.Base(file), err)
		}
	}
	if entries, err := os.ReadDir(state); err != nil || len(entries) != 1 || entries[0].Name() != name {
		t.Fatalf("attach changed state entries: %v (%v)", entries, err)
	}
	if out, err := runAttestation("verify", fixture.origin, query, state, public, session); err != nil || out != name {
		t.Fatalf("post-attach verification: %q (%v)", out, err)
	}
}
