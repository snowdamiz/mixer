//go:build darwin && cgo

package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"
)

func TestWorkerClosedSignerLostPublicationAck(t *testing.T) {
	binary := os.Getenv("MIXER_ATTEST_PROOF_BIN")
	if !filepath.IsAbs(binary) {
		t.Fatal("set MIXER_ATTEST_PROOF_BIN to the standalone pinned signer")
	}
	// The existing fixture serves a settled native_succeeded build without a worker.
	sel := fixtureSelection()
	query := sel.query().Encode()
	var token [32]byte
	rand.Read(token[:])
	session := base64.RawURLEncoding.EncodeToString(token[:])
	fixture := newBuildFixture(t, sel, session, "127.0.0.1:0", nil)

	state := filepath.Join(t.TempDir(), "state")
	if err := os.Mkdir(state, 0700); err != nil {
		t.Fatal(err)
	}
	private, public := writeDevelopmentKeys(t, t.TempDir())
	otherPrivate, otherPublic := writeDevelopmentKeys(t, t.TempDir())

	command := func(ctx context.Context, action, input, key string) *exec.Cmd {
		cmd := exec.CommandContext(ctx, binary, action, "-origin", fixture.origin,
			"-selection", input, "-state", state, "-key", key)
		cmd.Stdin = strings.NewReader(session + "\n")
		return cmd
	}
	call := func(action, input, key string) (string, string, error) {
		t.Helper()
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		cmd := command(ctx, action, input, key)
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		out, err := cmd.Output()
		if ctx.Err() != nil {
			t.Fatal(ctx.Err())
		}
		return string(out), strings.TrimSpace(stderr.String()), err
	}
	refuse := func(action, input, key, want string, requests int32) {
		t.Helper()
		out, stderr, err := call(action, input, key)
		var exit *exec.ExitError
		if !errors.As(err, &exit) || exit.ExitCode() != 1 || out != "" || stderr != want ||
			fixture.requests.Load() != requests {
			t.Fatalf("%s expected exit 1, empty stdout and %q at %d requests; got %v, %q, %q, %d",
				action, want, requests, err, out, stderr, fixture.requests.Load())
		}
	}

	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer writer.Close()
	if err := reader.Close(); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	first := command(ctx, "sign", query, private)
	var stderr bytes.Buffer
	first.Stdout, first.Stderr = writer, &stderr
	err = first.Run()
	if closeErr := writer.Close(); closeErr != nil {
		t.Fatal(closeErr)
	}
	var exit *exec.ExitError
	if !errors.As(err, &exit) || exit.Sys().(syscall.WaitStatus).Signal() != syscall.SIGPIPE ||
		stderr.Len() != 0 || fixture.requests.Load() != 4 {
		t.Fatalf("expected post-publication SIGPIPE with no stderr and 4 requests; got %v, %q, %d",
			err, stderr.String(), fixture.requests.Load())
	}
	t.Logf("first signer pid=%d reaped via SIGPIPE on stdout, stderr empty, HTTP=%d",
		first.ProcessState.Pid(), fixture.requests.Load())

	scope := strings.Join([]string{sel.OrganizationID, sel.ProjectID,
		sel.ApplicationID, sel.Platform, sel.BuildID}, "\x00")
	name := sum([]byte(scope)) + ".json"
	path := filepath.Join(state, name)
	envelope := func() ([]byte, os.FileInfo) {
		t.Helper()
		entries, err := os.ReadDir(state)
		if err != nil || len(entries) != 1 || entries[0].Name() != name {
			t.Fatalf("expected only %s; entries=%v err=%v", name, entries, err)
		}
		info, err := os.Lstat(path)
		if err != nil || !info.Mode().IsRegular() || info.Mode().Perm() != 0400 ||
			info.Sys().(*syscall.Stat_t).Nlink != 1 {
			t.Fatalf("invalid committed envelope metadata: %v, %v", info, err)
		}
		data, err := os.ReadFile(path)
		if err != nil || len(data) == 0 {
			t.Fatalf("cannot read committed envelope: %v", err)
		}
		return data, info
	}
	before, initial := envelope()
	t.Logf("one committed envelope name=%s mode=0400 links=1 bytes=%d sha256=%s", name, len(before), sum(before))

	const already = "build already attested or state unavailable"
	refuse("sign", query, private, already, 4)
	if err := os.Rename(private, private+".offline"); err != nil {
		t.Fatal(err)
	}
	refuse("sign", query, private, already, 4)
	refuse("sign", query, otherPrivate, already, 4)
	conflict := sel
	conflict.SourceSHA256 = strings.Repeat("9", 64)
	refuse("sign", conflict.query().Encode(), otherPrivate, already, 4)
	refuse("sign", conflict.query().Encode(), private, already, 4)
	refuse("verify", query, otherPublic, "attestation signature failed", 4)
	t.Log("same-input retry (also with private key path absent), other-key sign, conflicting-pin sign and wrong-key verify all refused before HTTP")

	out, verifyErr, err := call("verify", query, public)
	if err != nil || out != name+"\n" || verifyErr != "" || fixture.requests.Load() != 8 {
		t.Fatalf("pinned public verifier did not return the committed name after 4 HTTP reads: %q, %q, %v, %d",
			out, verifyErr, err, fixture.requests.Load())
	}
	after, final := envelope()
	if !os.SameFile(initial, final) || initial.ModTime() != final.ModTime() || !bytes.Equal(before, after) {
		t.Fatal("committed inode, modification time or envelope bytes changed")
	}
	t.Log("pinned public verifier returned the exact committed name; +4 HTTP reads; inode, mtime and bytes identical")

	fixture.close()
	address := strings.TrimPrefix(fixture.origin, "http://")
	rebound, err := net.Listen("tcp4", address)
	if err != nil {
		t.Fatalf("fixture port not released: %v", err)
	}
	if err := rebound.Close(); err != nil {
		t.Fatal(err)
	}
	t.Log("fixture server returned and its loopback port rebound and closed")
}
