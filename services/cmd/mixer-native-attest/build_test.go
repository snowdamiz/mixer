package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"sync/atomic"
	"testing"
)

func fixtureSelection() selection {
	return selection{
		OrganizationID: "local-org", ProjectID: "local-project", ApplicationID: "local-app",
		BuildID: "local-build", Platform: "ios",
		SourceSHA256: strings.Repeat("1", 64), ToolchainLockSHA256: strings.Repeat("2", 64),
		BuildDefinitionSHA256: strings.Repeat("3", 64),
	}
}

func TestReadArtifactRejectsSameSizeCorruption(t *testing.T) {
	const original = "expected native bytes"
	const corrupt = "Expected native bytes"
	descriptor := artifact{"unsigned_native_binary", sum([]byte(original)), int64(len(original))}
	var requests atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != artifactPath+descriptor.Kind {
			t.Errorf("unexpected request path %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/octet-stream")
		w.Header().Set("Cache-Control", "no-store")
		body := original
		if requests.Add(1) > 1 {
			body = corrupt
		}
		w.Header().Set("Content-Length", strconv.Itoa(len(body)))
		io.WriteString(w, body)
	}))
	defer server.Close()
	source, err := newSource(server.URL, "unused")
	if err != nil {
		t.Fatal(err)
	}
	read := func(io.Reader) error { return nil }
	if err := source.readArtifact(selection{}, descriptor, read); err != nil {
		t.Fatal(err)
	}
	if err := source.readArtifact(selection{}, descriptor, read); err == nil ||
		!strings.Contains(err.Error(), "byte digest mismatch") {
		t.Fatalf("expected digest refusal, got %v", err)
	}
}
