package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
)

func TestAttachHTTPResponses(t *testing.T) {
	const secret = "fixture-secret"
	for _, test := range []struct {
		name   string
		status int
		body   string
		want   string
	}{
		{"attached", 201, `{ "status": "attached" }`, "attached"},
		{"duplicate", 200, `{"status":"duplicate"}`, "duplicate"},
		{"wrong success status", 200, `{"status":"attached"}`, "attach: HTTP 200: unexpected response; result unconfirmed"},
		{"wrong success field", 201, `{"Status":"attached"}`, "attach: HTTP 201: unexpected response; result unconfirmed"},
		{"duplicate success key", 201, `{"status":"attached","status":"attached"}`, "attach: HTTP 201: unexpected response; result unconfirmed"},
		{"extra success field", 201, `{"status":"attached","extra":true}`, "attach: HTTP 201: unexpected response; result unconfirmed"},
		{"trailing JSON", 201, `{"status":"attached"} {}`, "attach: HTTP 201: unexpected response; result unconfirmed"},
		{"oversized body", 201, strings.Repeat(" ", 4096) + `{"status":"attached"}`, "attach: HTTP 201: unexpected response; result unconfirmed"},
		{"redirect", 307, `{"status":"duplicate"}`, "attach: HTTP 307: unexpected response; result unconfirmed"},
		{"conflict", 409, `{"error":{"code":"conflict"}}`, "attach: HTTP 409: conflict"},
		{"immutable conflict", 409, `{"error":{"code":"immutable_conflict"}}`, "attach: HTTP 409: immutable_conflict"},
		{"authorization unavailable", 503, `{"error":{"code":"authorization_unavailable"}}`, "attach: HTTP 503: authorization_unavailable"},
		{"bearer unavailable", 503, `{"request_id":"fixture","error":{"message":"` + secret + `","code":"identity_unavailable"}}`, "attach: HTTP 503: identity_unavailable"},
		{"auth required", 401, `{"error":{"code":"unauthenticated","message":"` + secret + `"},"request_id":"fixture"}`, "attach: HTTP 401: unauthenticated"},
		{"forbidden", 403, `{"error":{"code":"permission_denied"}}`, "attach: HTTP 403: permission_denied"},
		{"invalid envelope", 422, `{"error":{"code":"artifact_invalid"}}`, "attach: HTTP 422: artifact_invalid"},
		{"unknown code", 503, `{"error":{"code":"` + secret + `"}}`, "attach: HTTP 503: unexpected response; result unconfirmed"},
		{"conflicting error keys", 403, `{"error":{"code":"` + secret + `","code":"permission_denied"}}`, "attach: HTTP 403: unexpected response; result unconfirmed"},
		{"wrong error status", 401, `{"error":{"code":"permission_denied"}}`, "attach: HTTP 401: unexpected response; result unconfirmed"},
		{"unstructured failure", 502, secret, "attach: HTTP 502: unexpected response; result unconfirmed"},
	} {
		t.Run(test.name, func(t *testing.T) {
			var requests atomic.Int32
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requests.Add(1)
				w.Header().Set("Cache-Control", "no-store")
				w.Header().Set("Content-Type", "application/json; charset=utf-8")
				if r.URL.Path == "/redirect-target" {
					w.WriteHeader(http.StatusCreated)
					io.WriteString(w, `{"status":"attached"}`)
					return
				}
				if test.status == http.StatusTemporaryRedirect {
					w.Header().Set("Location", "/redirect-target")
				}
				if test.status == http.StatusServiceUnavailable {
					w.Header().Set("Retry-After", "0")
				}
				w.WriteHeader(test.status)
				io.WriteString(w, test.body)
			}))
			t.Cleanup(server.Close)
			source, err := newSource(server.URL, secret)
			if err != nil {
				t.Fatal(err)
			}
			result, err := source.postAttestation(fixtureSelection(), []byte("{}"))
			if test.want == "attached" || test.want == "duplicate" {
				if err != nil || result != test.want {
					t.Fatalf("want %q, got %q (%v)", test.want, result, err)
				}
			} else if result != "" || err == nil || err.Error() != test.want {
				t.Fatalf("want error %q, got %q (%v)", test.want, result, err)
			}
			if requests.Load() != 1 {
				t.Fatalf("expected one POST, got %d requests", requests.Load())
			}
		})
	}
}
